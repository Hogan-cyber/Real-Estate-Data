"""Monthly allocation arithmetic, missingness and auditability safeguards."""
import calendar
import copy
import unittest

from hk_property_data.simple import mortgage_estimates as model


def inputs(period='2026-01', **changes):
    values = {
        'hk_all_building_sales_count': 10000,
        'hk_residential_sales_count': 7000,
        'hk_all_property_mortgage_deeds_count': 6000,
        'hk_mortgage_drawn_count': 3000,
        'hk_mortgage_approved_count': 4000,
        'hk_mortgage_approved_refinancing_count': 1000,
        'hk_mortgage_drawn_amount': 15000,
        'hk_mortgage_approved_amount': 20000,
        'hk_mortgage_approved_refinancing_amount': 4000,
    }
    values.update(changes)
    y, m = map(int, period.split('-'))
    return [dict(metric_id=k, metric_name=k, value=v, frequency='M',
                 period=period, date=f'{period}-{calendar.monthrange(y,m)[1]}',
                 unit='HKD million' if k.endswith('_amount') else 'loans',
                 status='Published', flags='', source_name='Official input',
                 source_url='https://www.hkma.gov.hk/test' if k.startswith('hk_mortgage')
                            else 'https://www.landreg.gov.hk/test',
                 source_checked_at='2026-11-05T00:00:00+00:00')
            for k, v in values.items()]


class MortgageEstimateTests(unittest.TestCase):
    def test_distinct_monthly_count_and_amount_shares_and_bank_only_refi_removal(self):
        original = inputs() + inputs('2026-02', hk_residential_sales_count=5000,
                                    hk_mortgage_approved_refinancing_count=0,
                                    hk_mortgage_approved_refinancing_amount=0)
        before = copy.deepcopy(original)
        result = {(r['period'],r['metric_id']): r for r in model.build(original)}
        expected = {
            'hk_residential_sales_share': 0.7,
            'hk_residential_mortgage_count_estimate': 4200,
            'hk_bank_mortgage_purchase_drawn_count_estimate': 2250,
            'hk_bank_mortgage_purchase_drawn_amount_estimate': 12000,
            'hk_money_lender_mortgage_count_estimate': 1950,
            'hk_residential_mortgage_amount_estimate': 22400,
            'hk_money_lender_mortgage_amount_estimate': 10400,
        }
        for metric, value in expected.items():
            self.assertAlmostEqual(result['2026-01',metric]['value'],value)
        self.assertEqual(result['2026-02','hk_money_lender_mortgage_count_estimate']['value'],0)
        self.assertEqual(result['2026-02','hk_money_lender_mortgage_amount_estimate']['value'],0)
        residual = result['2026-01','hk_money_lender_mortgage_count_estimate']
        self.assertEqual(residual['status'],'Estimated')
        self.assertIn('LR_REFINANCING_NOT_REMOVED',residual['flags'])
        self.assertIn('landreg.gov.hk',residual['source_url'])
        self.assertIn('hkma.gov.hk',residual['source_url'])
        self.assertIn('hk_all_property_mortgage_deeds_count',residual['note'])
        self.assertEqual(original,before)

    def test_missing_month_input_is_not_filled_and_count_does_not_require_amount(self):
        rows=inputs('2026-01')+inputs('2026-02',hk_mortgage_approved_refinancing_count=None)
        result={(r['period'],r['metric_id']):r for r in model.build(rows)}
        missing=result['2026-02','hk_money_lender_mortgage_count_estimate']
        self.assertIsNone(missing['value'])
        self.assertEqual(missing['status'],'Unavailable')
        self.assertIn('MISSING_INPUT',missing['flags'])
        self.assertEqual(result['2026-02','hk_residential_mortgage_count_estimate']['value'],4200)
        rows=inputs(hk_mortgage_approved_amount=None)
        result={r['metric_id']:r for r in model.build(rows)}
        self.assertEqual(result['hk_money_lender_mortgage_count_estimate']['value'],1950)
        self.assertIsNone(result['hk_money_lender_mortgage_amount_estimate']['value'])

    def test_negative_residual_is_retained_and_flagged(self):
        rows=inputs(hk_all_property_mortgage_deeds_count=1000)
        result={r['metric_id']:r for r in model.build(rows)}
        self.assertEqual(result['hk_money_lender_mortgage_count_estimate']['value'],-1550)
        self.assertIn('NEGATIVE_RESIDUAL',result['hk_money_lender_mortgage_count_estimate']['flags'])
        self.assertLess(result['hk_money_lender_mortgage_amount_estimate']['value'],0)

    def test_zero_denominator_invalid_shares_and_nonfinite_values_stay_unavailable(self):
        for changes in [dict(hk_all_building_sales_count=0),
                        dict(hk_residential_sales_count=10001),
                        dict(hk_mortgage_approved_count=0),
                        dict(hk_mortgage_approved_refinancing_count=4001),
                        dict(hk_mortgage_drawn_count=float('nan'))]:
            with self.subTest(changes=changes):
                result={r['metric_id']:r for r in model.build(inputs(**changes))}
                self.assertIsNone(result['hk_money_lender_mortgage_count_estimate']['value'])
                self.assertIn('INVALID_INPUT',result['hk_money_lender_mortgage_count_estimate']['flags'])

    def test_zero_purchase_bank_count_does_not_create_average_or_amount(self):
        result={r['metric_id']:r for r in model.build(inputs(hk_mortgage_approved_refinancing_count=4000))}
        self.assertEqual(result['hk_money_lender_mortgage_count_estimate']['value'],4200)
        self.assertIsNone(result['hk_money_lender_mortgage_amount_estimate']['value'])

    def test_duplicate_monthly_input_rejected_and_daily_data_not_used(self):
        rows=inputs()
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            model.build(rows+[rows[0]])
        daily=dict(rows[0],frequency='D',value=1)
        self.assertEqual(len(model.build(rows+[daily])),len(model.build(rows)))

    def test_monetary_unit_change_is_not_silently_scaled_as_millions(self):
        rows=inputs()
        next(r for r in rows if r['metric_id']=='hk_mortgage_drawn_amount')['unit']='HKD billion'
        result={r['metric_id']:r for r in model.build(rows)}
        self.assertIsNone(result['hk_money_lender_mortgage_amount_estimate']['value'])
        self.assertIn('INVALID_INPUT',result['hk_money_lender_mortgage_amount_estimate']['flags'])
        self.assertEqual(result['hk_money_lender_mortgage_count_estimate']['value'],1950)
