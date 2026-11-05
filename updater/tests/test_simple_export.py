import tempfile
import unittest
from pathlib import Path

from hk_property_data.simple import export


def row(metric='hk_m3_hkd', value=0, period='2002-01', frequency='M'):
    return dict(metric_id=metric, metric_name=metric, value=value, period=period,
                date=period+'-31', frequency=frequency, unit='HKD million', source_id='hkma',
                source_name='HKMA', source_url='https://www.hkma.gov.hk/', status='Published', flags='')


class DatasetExportTests(unittest.TestCase):
    def test_dictionary_deduplicates_urls_inside_combined_provenance(self):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.xlsx'
            a=dict(row(),source_url='https://a.example/1; https://b.example/shared')
            b=dict(row(period='2002-03'),source_url='https://a.example/2; https://b.example/shared')
            export.build_excel([a,b],path,'2002-01','2002-03-31',[])
            wb=load_workbook(path,data_only=True)
            sources=wb['Data_Dictionary']['N2'].value
            self.assertEqual(sources.count('https://b.example/shared'),1)
            self.assertIn('https://a.example/1',sources)
            self.assertIn('https://a.example/2',sources)
            wb.close()

    def test_business_classification_and_frequency(self):
        self.assertEqual(export.sheet_for(row('hk_residential_sales_count')), 'Transactions')
        self.assertEqual(export.sheet_for(row('rvd_1_4_all_classes')), 'Price_Indices')
        self.assertEqual(export.sheet_for(row('hk_mortgage_outstanding')), 'Mortgage_Monthly')
        self.assertEqual(export.sheet_for(row('hk_negative_equity_count', frequency='Q')), 'Negative_Equity_Quarterly')
        self.assertEqual(export.sheet_for(row('hk_hibor_1m_daily', frequency='D')), 'HIBOR_Daily')

    def test_mortgage_hibor_pricing_share_is_not_a_macro_interest_rate(self):
        self.assertEqual(export.sheet_for(row('hk_mortgage_pricing_hibor_share')), 'Mortgage_Monthly')

    def test_conflicting_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            export.validate([row(value=1), row(value=2)], '2002-01', '2026-11-04')

    def test_excel_distinguishes_blank_from_zero_and_fills_calendar(self):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.xlsx'
            export.build_excel([row(value=0), row(value=None, period='2002-03')], path,
                               '2002-01', '2002-03-31', [])
            wb = load_workbook(path, data_only=True)
            ws = wb['Money_Supply']
            # Four metadata rows precede dates/header; locate by typed date.
            values = [(r[0],r[1]) for r in ws.iter_rows(values_only=True)
                      if hasattr(r[0], 'year')]
            self.assertEqual(len(values),3)
            self.assertEqual(values[0][1],0)
            self.assertIsNone(values[1][1])
            self.assertIsNone(values[2][1])
            self.assertIn('Data_Dictionary', wb.sheetnames)
