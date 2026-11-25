import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from openpyxl import load_workbook
import hk_property_data as hk
from residential_fixtures import payload
from hk_property_data.simple import export,monitor
from test_simple_monitor import snapshot


class MonitorReaderTests(unittest.TestCase):
    def tearDown(self):hk.clear_residential_cache()

    def test_monitor_scopes_shared_snapshot_and_reuses_warm_cache(self):
        hk.clear_residential_cache()
        raw=payload([('monitor_completed_count','2026-09-30','100'),
                     ('monitor_completed_count','2026-10-31','110'),
                     ('monitor_nonbank_residual_count','2026-10-31','-10'),
                     ('rvd_1_4_all_classes','2026-10-31','320')])
        with patch('urllib.request.urlopen',return_value=io.BytesIO(raw)) as fetch:
            reader=hk.Monitor()
            df=reader.history(start='2026-10',labels='id')
            self.assertEqual(set(df.columns),{'monitor_completed_count','monitor_nonbank_residual_count'})
            self.assertEqual(df.loc[pd.Timestamp('2026-10-31'),'monitor_nonbank_residual_count'],-10)
            self.assertEqual(len(reader.history(group='Monitor registrations',labels='id').columns),1)
            self.assertEqual(len(hk.Residential().catalog()),3)
            self.assertEqual(fetch.call_count,1)
            with self.assertRaisesRegex(ValueError,'Monitor'):
                reader.history(series='rvd_1_4_all_classes')

    def test_old_snapshot_has_actionable_message(self):
        hk.clear_residential_cache()
        with patch('urllib.request.urlopen',return_value=io.BytesIO(payload())):
            with self.assertRaisesRegex(ValueError,'refresh=True'):
                hk.Monitor().history()

    def test_excel_separates_frequencies_and_labels_saved_estimates(self):
        _,_,data=snapshot()
        rows=monitor.observations(data['series'],'a'*40,{'checked_at':'2026-11-25T04:31:37+08:00'},checked_at='2026-11-25T08:00:00+00:00')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'dataset.xlsx'
            export.build_excel(rows,path,'2025-01','2026-11-25',[])
            book=load_workbook(path,data_only=True)
            self.assertTrue({'Monitor_Registrations','Monitor_Nonbank','Monitor_Hibor','Monitor_Prime'}<=set(book.sheetnames))
            dictionary=list(book['Data_Dictionary'].values)
            item=next(r for r in dictionary if r[2]=='monitor_nonbank_residual_count')
            self.assertEqual(item[14],'Calculated / estimated')
            values=[c for row in book['Monitor_Nonbank'].values for c in row]
            self.assertIn(-10,values)
            book.close()
