"""API contracts and safeguards for switching an existing published dataset."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from hk_property_data.simple import hkma


def envelope(records, success=True):
    return json.dumps({'header': {'success': success, 'err_msg': 'test error' if not success else ''},
                       'result': {'datasize': len(records), 'records': records}}).encode()


class HKMAAPITest(unittest.TestCase):
    def test_api_adapter_exists(self):
        self.assertTrue(callable(getattr(hkma, 'parse_api_records', None)),
                        'Production collection needs an HKMA JSON adapter')

    def test_api_mixed_percent_units_match_official_september_release(self):
        # Actual HKMA API record captured by the 9 November 2026 cloud run.
        # Unlike LTV/delinquency, the four pricing shares are decimal fractions.
        records = [json.loads((Path(__file__).parent / 'fixtures' /
                               'hkma_survey_api_202609.json').read_text())]
        rows = hkma.parse_api_records(records, 'survey', 'new')
        values = {r['metric_id']: r for r in rows}
        self.assertEqual(values['hk_mortgage_pricing_hibor_share']['value'], 52.7)
        self.assertAlmostEqual(values['hk_mortgage_pricing_blr_share']['value'], 1.3)
        self.assertAlmostEqual(values['hk_mortgage_pricing_fixed_share']['value'], 42.4)
        self.assertAlmostEqual(values['hk_mortgage_pricing_other_share']['value'], 3.7)
        self.assertEqual(values['hk_mortgage_pricing_hibor_share']['source_raw_value'], .527)
        self.assertEqual(values['hk_mortgage_delinquency']['value'], .11)
        self.assertEqual(values['hk_mortgage_approved_count']['value'], 6240)
        self.assertEqual(values['hk_mortgage_approved_ltv']['value'], 60.1)
        self.assertIsNone(values['hk_mortgage_written_off_12m_ratio']['value'])
        self.assertEqual(values['hk_mortgage_written_off_12m_ratio']['flags'], 'below_reporting_threshold')
        self.assertEqual(values['hk_mortgage_drawn_count']['source_field'], 'new_loans_drawn')
        self.assertTrue(all(r['source_url'].startswith('https://api.hkma.gov.hk/') for r in rows))
        self.assertTrue(all(r['date'] == '2026-09-30' for r in rows))
        money = hkma.parse_api_records([{'end_of_month': '2025-01', 'm3_hkd': 8618343.478}], 'money', 'new')
        self.assertEqual(money[0]['value'], 8618343.478)

    def test_negative_equity_ltv_fraction_and_borrower_percentage(self):
        # Actual public endpoint: 2026-Q2 lv_ratio=1.05, borrower share='0.71'.
        rows = hkma.parse_api_records([{'end_of_quarter': '2026-Q2', 'outstanding_loans': 4356,
                                       'outstanding_loans_ratio': '0.71', 'lv_ratio': 1.05}], 'negative')
        values = {r['metric_id']: r for r in rows}
        self.assertEqual(values['hk_negative_equity_ltv']['value'], 105)
        self.assertEqual(values['hk_negative_equity_borrower_share']['value'], .71)
        self.assertTrue(all(r['frequency'] == 'Q' and r['period'] == '2026-06' for r in rows))
        self.assertNotIn('hk_negative_equity_delinquency', values)

    def test_pricing_share_schema_drift_is_rejected(self):
        for shares in [(52.7, 1.3, 42.4, 3.7), (.527, .013, .1, .037)]:
            record = dict(zip(('ir_new_loans_approved_hibor', 'ir_new_loans_approved_blr',
                               'ir_new_loans_approved_fixed', 'ir_new_loans_approved_other'), shares))
            record['end_of_month'] = '2026-09'
            with self.subTest(shares=shares), self.assertRaisesRegex(ValueError, 'pricing shares'):
                hkma.parse_api_records([record], 'survey', 'new')

    def test_old_survey_does_not_mix_pre_expansion_population(self):
        rows = hkma.parse_api_records([
            {'end_of_month': '1999-01', 'new_loans_approved': 99},
            {'end_of_month': '2002-01', 'new_loans_approved': 101},
        ], 'survey', 'old')
        self.assertEqual([(r['period'], r['value']) for r in rows], [('2002-01', 101)])

    def test_rejects_invalid_dates_counts_and_duplicate_periods(self):
        for record in [{'end_of_month': '2026-13', 'new_loans_drawn': 1},
                       {'end_of_month': '2026-09', 'new_loans_drawn': 1.5},
                       {'end_of_month': '2026-09', 'new_loans_drawn': True},
                       {'end_of_month': '2026-09', 'new_loans_drawn': -1}]:
            with self.subTest(record=record), self.assertRaises(ValueError):
                hkma.parse_api_records([record], 'survey', 'new')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            hkma.parse_api_records([{'end_of_month': '2026-09'}] * 2, 'survey', 'new')

    def test_fetches_all_pages_and_keeps_raw_responses(self):
        pages = [envelope([{'end_of_month': '2026-08'}, {'end_of_month': '2026-09'}]),
                 envelope([{'end_of_month': '2026-10'}])]
        with tempfile.TemporaryDirectory() as directory, patch.object(hkma, '_download', side_effect=pages) as fetch:
            rows = hkma._api_records('survey', 'new', Path(directory), pagesize=2)
            self.assertEqual(len(rows), 3)
            offsets = [parse_qs(urlparse(c.args[0]).query)['offset'][0] for c in fetch.call_args_list]
            self.assertEqual(offsets, ['0', '2'])
            self.assertTrue(all('segment=new' in c.args[0] for c in fetch.call_args_list))

    def test_rejects_api_error_and_repeated_page(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(hkma, '_download', return_value=envelope([], False)):
                with self.assertRaisesRegex(ValueError, 'test error'):
                    hkma._api_records('money', 'new', Path(directory))
            with patch.object(hkma, '_download', return_value=envelope([{'end_of_month': '2026-09'}])):
                with self.assertRaisesRegex(ValueError, 'Duplicate'):
                    hkma._api_records('money', 'new', Path(directory), pagesize=1)

    def test_server_page_cap_cannot_truncate_reported_total(self):
        pages=[]
        for records in [[{'end_of_month': '2026-08'}], [{'end_of_month': '2026-09'}]]:
            payload=json.loads(envelope(records));payload['result']['datasize']=2
            pages.append(json.dumps(payload).encode())
        with tempfile.TemporaryDirectory() as directory, patch.object(hkma, '_download', side_effect=pages):
            self.assertEqual(len(hkma._api_records('money','new',Path(directory),pagesize=1000)),2)

    def test_gap_check_preserves_history_and_known_missing_is_not_zero(self):
        rows = hkma.parse_api_records([{'end_of_month': '2026-09', 'm3_hkd': None}], 'money', 'new')
        missing = hkma._missing_keys('money', rows, '2026-08', '2026-09')
        self.assertIn(('hk_m3_hkd', '2026-08'), missing)
        self.assertNotIn(('hk_m3_hkd', '2026-09'), missing)
        self.assertIsNone(rows[0]['value'])

    def test_api_priority_only_fills_missing_keys_and_unavailable_values(self):
        api = [dict(metric_id='a', period='2026-09', value=52.7, flags=''),
               dict(metric_id='b', period='2026-09', value=None, flags='below_reporting_threshold'),
               dict(metric_id='c', period='2026-09', value=None, flags='not_available')]
        pdf = [dict(metric_id=m, period='2026-09', value=v, flags='') for m, v in [('a', 50), ('b', 0), ('c', 7), ('d', 8)]]
        values = {r['metric_id']: r['value'] for r in hkma._merge_rows(api, pdf)}
        self.assertEqual(values, {'a': 52.7, 'b': None, 'c': 7, 'd': 8})

    def test_current_complete_api_skips_workbooks_and_only_negative_needs_pdf(self):
        # Sparse fixtures are deliberate: isolate routing; coverage validation is tested separately.
        def api(kind, directory):
            metric = {'survey': 'hk_mortgage_approved_count', 'money': 'hk_m3_hkd', 'negative': 'hk_negative_equity_count'}[kind]
            return [hkma._row(metric, metric, '2026-09', 123, 'loans', 'hkma', 'https://api.hkma.gov.hk/test', '',
                              frequency='Q' if kind == 'negative' else 'M')]
        metadata = ('2026-09', '2026-10-30', 'https://www.hkma.gov.hk/release/', 'https://www.hkma.gov.hk/annex.pdf')
        extra = hkma._row('hk_negative_equity_delinquency', 'Delinquency', '2026-09', 1.34, '%',
                         'hkma_negative_equity', metadata[3], '', frequency='Q')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(hkma, '_collect_api', side_effect=api), \
             patch.object(hkma, '_missing_keys', return_value=set()), \
             patch.object(hkma, '_find_latest_release', return_value=metadata), \
             patch.object(hkma, '_latest_release', return_value=(*metadata, 'text')) as pdf, \
             patch.object(hkma, 'parse_negative_annex', return_value=[extra]), \
             patch.object(hkma, '_download') as download:
            rows = hkma.collect(Path(directory), '2026-11-09')
            self.assertEqual(pdf.call_count, 1)
            self.assertEqual(pdf.call_args.args[0], 'negative')
            download.assert_not_called()
            self.assertEqual(len(rows), 4)
            self.assertFalse(any(r.get('refresh_warning') for r in rows))

    def test_prior_api_history_is_retained_but_never_supplies_latest_period(self):
        old=[hkma._row('hk_negative_equity_count','Count',p,v,'loans','hkma_negative_equity',
                      'https://api.hkma.gov.hk/test','',frequency='Q',checked_at='2026-10-31')
             for p,v in [('2002-03',100),('2026-09',200)]]
        old[0]['refresh_warning']='Previous run could not check the release listing'
        rows=hkma._preserve_history([],old,'negative','2002-01','2026-09')
        self.assertEqual([(r['period'],r['value']) for r in rows],[('2002-03',100)])
        self.assertEqual(rows[0]['checked_at'],'2026-10-31')
        self.assertEqual(rows[0]['source_method'],'retained')
        self.assertNotIn('refresh_warning',rows[0])
        self.assertEqual(old[0].get('source_method'),None)

    def test_history_retention_cannot_restore_misscaled_pricing_shares(self):
        previous = []
        for period, shares in [('2026-07', (61, 1.3, 34, 3.7)),
                               ('2026-08', (.570, .019, .374, .037))]:
            for category, value in zip(('hibor', 'blr', 'fixed', 'other'), shares):
                previous.append(hkma._row('hk_mortgage_pricing_' + category + '_share',
                                          category, period, value, '%', 'hkma_survey',
                                          'https://api.hkma.gov.hk/test', ''))
        rows = hkma._preserve_history([], previous, 'survey', '2002-01', '2026-09')
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r['period'] == '2026-07' for r in rows))
        self.assertEqual([r['value'] for r in rows], [61, 1.3, 34, 3.7])

    def test_new_attempt_removes_previous_success_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'raw/hkma/diagnostics.json';path.parent.mkdir(parents=True)
            path.write_text('{"as_of":"2026-11-08","survey":{"errors":[]}}')
            with patch.object(hkma,'_collect_api',side_effect=RuntimeError('offline')), \
                 patch.object(hkma,'_download',side_effect=RuntimeError('offline')), \
                 patch.object(hkma,'_find_latest_release',side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError):hkma.collect(Path(directory),'2026-11-09')
            self.assertFalse(path.exists())

    def test_lagging_release_cannot_remove_previously_published_latest_supplement(self):
        def api(kind,directory):
            metric={'survey':'hk_mortgage_approved_count','money':'hk_m3_hkd','negative':'hk_negative_equity_count'}[kind]
            return [hkma._row(metric,metric,'2026-09',123,'loans','hkma','https://api.hkma.gov.hk/test','')]
        old=hkma._row('hk_negative_equity_delinquency','Delinquency','2026-09',1.34,'%',
                     'hkma_negative_equity','https://www.hkma.gov.hk/annex.pdf','',frequency='Q')
        metadata=('2026-06','2026-07-31','https://www.hkma.gov.hk/release/','https://www.hkma.gov.hk/annex.pdf')
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(hkma,'_collect_api',side_effect=api), \
             patch.object(hkma,'_missing_keys',return_value=set()), \
             patch.object(hkma,'_find_latest_release',return_value=metadata), \
             patch.object(hkma,'_latest_release',return_value=(*metadata,'text')), \
             patch.object(hkma,'parse_negative_annex',return_value=[dict(old,period='2026-06',date='2026-06-30')]):
            with self.assertRaisesRegex(RuntimeError,'negative:.*missing observations'):
                hkma.collect(Path(directory),'2026-11-09',previous=[old])


if __name__ == '__main__':
    unittest.main()
