import tempfile
import unittest
from pathlib import Path

from hk_property_data.simple import export


def row(metric='hk_m3_hkd', value=0, period='2002-01', frequency='M'):
    return dict(metric_id=metric, metric_name=metric, value=value, period=period,
                date=period+'-31', frequency=frequency, unit='HKD million', source_id='hkma',
                source_name='HKMA', source_url='https://www.hkma.gov.hk/', status='Published', flags='')


class DatasetExportTests(unittest.TestCase):
    def test_compact_status_keeps_official_quality_qualifications(self):
        values=[dict(row(),flags='Z'),dict(row(),value=None,flags='below_reporting_threshold'),
                dict(row(),flags='OTHER_OFFICIAL_FLAG')]
        status=export._data_status(values)
        self.assertIn('Z: fewer than 20 cases',status)
        self.assertIn('Below reporting threshold',status)
        self.assertIn('OTHER_OFFICIAL_FLAG',status)
        self.assertNotIn('Source blank',status)

    def test_official_data_precedes_estimates_and_notes_are_replaced_by_visible_method(self):
        from openpyxl import load_workbook
        from hk_property_data.simple import mortgage_estimates
        from updater.tests.test_simple_mortgage_estimates import inputs
        raw=inputs(hk_all_property_mortgage_deeds_count=1000)
        prior_bank=[r for r in inputs('2025-12') if r['metric_id'].startswith('hk_mortgage_')]
        observations=raw+mortgage_estimates.build(raw+prior_bank)
        for item in observations:
            item['note']='Long per-observation note that should not be in Excel'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.xlsx'
            export.build_excel(observations,path,'2026-01','2026-01-31',[])
            wb=load_workbook(path,data_only=True)
            ws=wb['Mortgage_Monthly']
            header=next(r for r in ws if r[0].value=='Period')
            labels=[c.value for c in header[1:-1]]
            raw_labels={r['metric_name'] for r in raw if export.sheet_for(r)=='Mortgage_Monthly'}
            self.assertEqual(set(labels[:len(raw_labels)]),raw_labels)
            self.assertIn('Residential total: count estimate',labels[len(raw_labels):])
            self.assertTrue(any(c.hyperlink and 'mortgage_estimates.py' in c.hyperlink.target
                                for r in ws for c in r))
            self.assertTrue(any('residential sale agreements / all building sale agreements' in str(c.value)
                                for r in ws.iter_rows(max_row=header[0].row-1) for c in r))
            self.assertFalse(any(c.comment for sheet in wb for r in sheet for c in r))
            self.assertFalse(any('Long per-observation note' in str(c.value)
                                 for sheet in wb for r in sheet for c in r))
            data=next(r for r in ws.iter_rows(values_only=True) if hasattr(r[0],'year'))
            residual=labels.index('Money-lender residual: count estimate')+1
            self.assertEqual(data[residual],-1550)
            self.assertIn('Negative residual',data[-1])
            self.assertEqual(ws.freeze_panes,f'B{header[0].row+1}')
            wb.close()

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
