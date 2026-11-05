"""Focused guards against date, unit, coverage and column mistakes in HKMA data."""
import io
import sys
import unittest
import tempfile
import sqlite3
from contextlib import closing
from unittest.mock import patch
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.simple import hkma
from hk_property_data.residential_schema import populate_database


def exported_sources(rows):
    """Exercise the publisher's real 16-column SQLite projection."""
    with closing(sqlite3.connect(':memory:')) as connection:
        populate_database(connection, rows)
        return {(metric, period): (table, field, value) for metric, period, table, field, value in
                connection.execute('SELECT metric_id, period, source_table, source_field, value FROM observations')}


class SimpleHKMATest(unittest.TestCase):
    def test_survey_annex_preserves_exact_values_and_percentage_units(self):
        text=(Path(__file__).parent/'fixtures'/'hkma_survey_202609_eng.txt').read_text()
        rows=hkma.parse_survey_annex(text,'2026-09','https://www.hkma.gov.hk/annex.pdf','2026-10-30')
        values={r['metric_id']:r for r in rows if r['period']=='2026-09'}
        self.assertEqual(len(values),33)
        self.assertEqual(values['hk_mortgage_approved_amount']['value'],31835)
        self.assertEqual(values['hk_mortgage_drawn_count']['value'],4788)
        self.assertEqual(values['hk_mortgage_approved_ltv']['value'],60.1)
        self.assertEqual(values['hk_mortgage_delinquency']['value'],0.11)
        self.assertEqual(values['hk_mortgage_pricing_hibor_share']['value'],52.7)
        self.assertEqual(values['hk_mortgage_approved_tenor']['value'],320)
        self.assertIsNone(values['hk_mortgage_written_off_12m_ratio']['value'])
        self.assertEqual(values['hk_mortgage_written_off_12m_ratio']['flags'],'below_reporting_threshold')
        self.assertTrue(all(r['date']=='2026-09-30' for r in values.values()))
        exported=exported_sources(rows)
        self.assertEqual(exported['hk_mortgage_approved_average_size','2026-09'],
                         ('Residential Mortgage Survey annex','2.c. Average size',5.10))
        # Existing annex metadata remains meaningful rather than being replaced
        # by a generic table/metric identifier.
        self.assertEqual(exported['hk_mortgage_approved_amount','2026-09'][0:2],
                         ('HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7',
                          'new_loans_approved_amt'))
        with self.assertRaises(ValueError):
            hkma.parse_survey_annex(text.replace('60.1 59.1','MISSING'),'2026-09','url','2026-10-30')

    def test_workbook_joins_only_expanded_group_and_normalizes_pricing_shares(self):
        book=openpyxl.Workbook();old=book.active;old.title='T3.7 (old)'
        old['A1']='Table 3.7 Residential mortgage survey results1'
        # Distinct old/new survey populations must never silently overlap.
        for n,(year,month,value) in enumerate([(1999,'Jan',900),(2002,'Jan',100),(2016,'Dec',200)],17):
            old.cell(n,1,year);old.cell(n,2,month)
            for col in hkma.OLD_COLUMNS:old[f'{col}{n}']=value
        new=book.create_sheet('T3.7');new['A1']='Table 3.7 Residential mortgage survey results1,2'
        new['AI9']='Loan-to-value ratio7';new['AJ9']='Contractual life7'
        new['A17']=2016;new['B17']='December'
        for col in hkma.SURVEY:new[f'{col}17']=300
        new['AY17']=.949;new['AZ17']=.025;new['BA17']=.008;new['BB17']=.018;new['N17']=.03
        raw=io.BytesIO();book.save(raw)
        rows=hkma.parse_survey_workbook(raw.getvalue());values={(r['metric_id'],r['period']):r for r in rows}
        self.assertEqual(len(rows),len(values))
        self.assertNotIn('1999-01',{r['period'] for r in rows})
        self.assertEqual(values['hk_mortgage_outstanding','2002-01']['value'],100)
        self.assertEqual(values['hk_mortgage_outstanding','2016-12']['value'],300)
        self.assertAlmostEqual(values['hk_mortgage_pricing_hibor_share','2016-12']['value'],94.9)
        self.assertEqual(values['hk_mortgage_delinquency','2016-12']['value'],.03)
        self.assertNotIn(('hk_mortgage_applications','2002-01'),values)
        exported=exported_sources(rows)
        self.assertEqual(exported['hk_mortgage_approved_amount','2002-01'],
                         ('T3.7 (old)','L18: New mortgage loans approved: amount',100))
        self.assertEqual(exported['hk_mortgage_approved_amount','2016-12'],
                         ('T3.7','AC17: New mortgage loans approved: amount',300))

    def test_money_annex_uses_published_total_and_rejects_swapped_values(self):
        text='''TABLE 1A : HONG KONG MONETARY STATISTICS - September 2026
(HK$ Million)
Money Supply
M1 - HK$ 1 ,845,746 1 ,870,130 ( -1.3 )
Foreign currency 1 ,590,379 1 ,665,419 ( -4.5 )
Total 3 ,436,125 3 ,535,549 ( -2.8 )
M2 - HK$2 9 ,491,899 9 ,573,225 ( -0.8 )
Foreign currency1 1 2,781,535 1 2,601,169 ( 1.4 )
Total 2 2,273,435 2 2,174,394 ( 0.4 )
M3 - HK$2 9 ,505,133 9 ,586,157 ( -0.8 )
Foreign currency1 1 2,812,010 1 2,635,329 ( 1.4 )
Total 2 2,317,144 2 2,221,486 ( 0.4 )
Notes and coins in circulation'''
        rows=hkma.parse_money_annex(text,'2026-09','url','2026-10-30');values={r['metric_id']:r['value'] for r in rows}
        self.assertEqual(values['hk_m3_hkd'],9505133)
        self.assertEqual(values['hk_m3_fc'],12812010)
        self.assertEqual(values['hk_m3_total'],22317144)  # Official rounding differs by 1.
        self.assertEqual(exported_sources(rows)['hk_m3_total','2026-09'],
                         ('Table 1A: Hong Kong Monetary Statistics','Money Supply: M3 - Total',22317144))
        with self.assertRaises(ValueError):
            hkma.parse_money_annex(text.replace('2 2,317,144','2 1,317,144'),'2026-09','url','2026-10-30')

    def test_negative_equity_remains_quarterly_with_no_interpolation(self):
        text='''Residential mortgage loans in negative equity: End of September 2026
(End of period figures) Sep-2026 Jun-2026 Mar-2026
Total outstanding number 3,819 4,356 11,424
As % of total mortgage borrowers 0.62% 0.71% 1.88%
Total outstanding value (HK$ million) 17,327 19,621 55,037
As % of total outstanding value 0.87% 1% 2.84%
Value of unsecured portion (HK$ million) 837 922 2,769
Loan-to-value ratio 105% 105% 105%
Delinquency ratio (more than 3 months) 1.34% 1.25% 0.50%'''
        rows=hkma.parse_negative_annex(text,'2026-09','url','2026-10-30')
        self.assertEqual({r['frequency'] for r in rows},{'Q'})
        self.assertEqual({r['period'] for r in rows},{'2026-03','2026-06','2026-09'})
        self.assertEqual(next(r['value'] for r in rows if r['metric_id']=='hk_negative_equity_ltv' and r['period']=='2026-09'),105)
        self.assertEqual(len(rows),21)
        self.assertEqual(exported_sources(rows)['hk_negative_equity_amount','2026-09'],
                         ('Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity',
                          'Total outstanding value (HK$ million)',17327))

    def test_negative_workbook_cell_survives_public_export(self):
        book=openpyxl.Workbook();sheet=book.active;sheet.title='T3.16'
        sheet['A1']='Table 3.16 Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity'
        sheet['D6']='Total outstanding number';sheet['A10']=2016;sheet['B10']='Q4'
        sheet['D10']=4;sheet['E10']='*';sheet['G10']=11;sheet['H10']='*';sheet['I10']=.08;sheet['J10']=1.01
        raw=io.BytesIO();book.save(raw)
        exported=exported_sources(hkma.parse_negative_workbook(raw.getvalue()))
        self.assertEqual(exported['hk_negative_equity_count','2016-12'],
                         ('T3.16','D10: Negative-equity mortgages: outstanding count',4))


    def test_both_negative_equity_sources_failing_cannot_report_success(self):
        # Other HKMA datasets succeed; a missing required category must still fail.
        row = dict(metric_id='hk_m3_hkd', period='2026-09', date='2026-09-30', value=1)
        def release(kind, as_of, directory):
            if kind == 'negative':
                raise RuntimeError('negative release unavailable')
            return '2026-09', '2026-10-30', 'https://www.hkma.gov.hk/', 'https://www.hkma.gov.hk/annex.pdf', ''
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(hkma, '_download', return_value=b'fixture'), \
             patch.object(hkma, '_latest_release', side_effect=release), \
             patch.object(hkma, 'parse_survey_workbook', return_value=[dict(row, metric_id='hk_mortgage_outstanding')]), \
             patch.object(hkma, 'parse_money_workbook', return_value=[row]), \
             patch.object(hkma, 'parse_survey_annex', return_value=[]), \
             patch.object(hkma, 'parse_money_annex', return_value=[]), \
             patch.object(hkma, 'parse_negative_workbook', side_effect=RuntimeError('negative workbook unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'negative:.*negative workbook unavailable.*negative release unavailable'):
                hkma.collect(Path(directory), '2026-11-04')
            self.assertFalse((Path(directory) / 'parts' / 'hkma.json').exists())


if __name__=='__main__':unittest.main()
