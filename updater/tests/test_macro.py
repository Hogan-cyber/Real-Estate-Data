"""Macro source contract: units, series basis, complete pages and safe fallback."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_macro_collector as macro


class MacroTest(unittest.TestCase):
    def test_original_money_units_missing_zero_future_and_new_series_break(self):
        records = [dict(end_of_month='1997-03',m3_hkd=10,m3_total=20),
                   dict(end_of_month='2026-08',m3_hkd=0,m3_total=None),
                   dict(end_of_month='2026-09',m3_hkd=10,m3_total=20)]
        rows = macro.parse_records('hkma_m3',records,'2026-09-15')
        self.assertEqual(len(rows),2)
        self.assertEqual([r['value'] for r in rows],[0,None])
        self.assertTrue(all(r['period']=='2026-08' and r['unit']=='HKD million' and r['observation_basis']=='End of month' for r in rows))
        self.assertIn('April 1997',rows[0]['note'])

    def test_prime_is_hsbc_and_both_rates_are_official_monthly_averages(self):
        prime=macro.parse_records('hkma_prime',[dict(end_of_month='2026-09',best_lending_rate=5.0)],'2026-11-03')[0]
        rates=macro.parse_records('hkma_hibor',[dict(end_of_month='2026-09',ir_1m=2.6,ir_3m=3.1)],'2026-11-03')
        self.assertEqual(prime['metric_id'],'hk_prime_rate_hsbc')
        self.assertIn('HSBC',prime['metric_name'])
        self.assertEqual([r['value'] for r in rates],[2.6,3.1])
        self.assertTrue(all(r['observation_basis']=='Monthly average' and r['unit']=='% p.a.' for r in [prime]+rates))
        self.assertIn('hibor.fixing',rates[0]['source_url'])

    def test_malformed_duplicate_and_unavailable_field_fail_instead_of_filling(self):
        valid=dict(end_of_month='2026-08',m3_hkd=10,m3_total=20)
        for records in ([valid,valid],[dict(valid,end_of_month='2026')],[dict(valid,m3_hkd=True)],
                        [dict(valid,m3_total=float('nan'))],[{'end_of_month':'2026-08','m3_hkd':10}]):
            with self.assertRaises(ValueError):macro.parse_records('hkma_m3',records,'2026-11-03')

    def test_pagination_handles_server_cap_smaller_than_requested(self):
        requests=[]
        def fetch(url):
            offset=int(parse_qs(urlparse(url).query)['offset'][0]);requests.append(offset)
            records=[] if offset==2 else [dict(end_of_month=f'2026-0{offset+1}',m3_hkd=10,m3_total=20)]
            return json.dumps({'header':{'success':True},'result':{'datasize':len(records),'records':records}}).encode()
        records,_=macro._api_records('hkma_m3',fetch)
        self.assertEqual(requests,[0,1,2]);self.assertEqual(len(records),2)

    def test_repeated_page_and_error_header_are_rejected(self):
        for response in ({'header':{'success':False},'result':{'records':[]}},
                         {'header':{'success':True},'result':{'records':[{'end_of_month':'2026-08'}]}}):
            with self.assertRaises(ValueError):macro._api_records('hkma_m3',lambda _:json.dumps(response).encode())

    def test_official_excel_fallback_records_actual_provenance_and_both_failure_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            def fetch(url):
                if url.startswith(macro.API_ROOT):raise OSError('API unavailable')
                return b'official spreadsheet bytes'
            row={'note':'Original source note','source_url':macro.XLS_ROOT+'T020201.xls','fetch_mode':'automatic_excel'}
            with patch.object(macro,'parse_excel',return_value=[row]):
                rows=macro.collect('hkma_m3',directory,'2026-11-03',fetch)
            self.assertEqual(rows[0]['fetch_mode'],'automatic_excel')
            self.assertIn('official Excel table',rows[0]['note'])
            self.assertTrue((Path(directory)/'hkma_m3.xls').exists())
            saved=(Path(directory)/'hkma_m3.xls').read_bytes()
            with self.assertRaises(RuntimeError):
                macro.collect('hkma_m3',directory,'2026-11-03',lambda _: (_ for _ in ()).throw(OSError('offline')))
            self.assertEqual((Path(directory)/'hkma_m3.xls').read_bytes(),saved)

    def test_excel_year_labels_and_months_only_no_annual_rows(self):
        import xlrd
        grid=[['']*14 for _ in range(20)]
        grid[3][0]='Table 2.2.1 : Adjusted for foreign currency swap deposits'
        grid[7][11]='M3';grid[9][11]='HK$2';grid[9][13]='Total'
        grid[13][:2]=[2025,'Dec'];grid[13][11]=100;grid[13][13]=200
        grid[14][:2]=[2026,''];grid[14][11]=999;grid[14][13]=999  # Annual total excluded.
        grid[15][:2]=[2026,'Jan'];grid[15][11]=0;grid[15][13]='N.A.'
        grid[16][:2]=['','Feb'];grid[16][11]=110;grid[16][13]=220
        class Sheet:
            nrows=len(grid)
            def row_values(self,i):return grid[i]
            def cell_value(self,i,j):return grid[i][j]
        class Book:
            def sheet_by_name(self,name):
                self.name=name
                return Sheet()
        with patch.object(xlrd,'open_workbook',return_value=Book()):
            rows=macro.parse_excel('hkma_m3',b'x','2026-11-03')
        self.assertEqual(len(rows),6)
        self.assertEqual({r['period'] for r in rows},{'2025-12','2026-01','2026-02'})
        self.assertFalse(any(r['value']==999 for r in rows))
        self.assertTrue(all(r['fetch_mode']=='automatic_excel' for r in rows))


    def test_monthly_refresh_never_calls_unpublished_rate_supplements(self):
        from hk_property_data.collectors import hk_prime_supplement, hk_hibor_supplement
        for key,records in [('hkma_prime',[dict(end_of_month='2026-09',best_lending_rate=5.0)]),
                            ('hkma_hibor',[dict(end_of_month='2026-09',ir_1m=2.9,ir_3m=3.1)])]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory, \
                 patch.object(macro,'_api_records',return_value=(records,[])), \
                 patch.object(hk_prime_supplement,'supplement',return_value=[]) as prime, \
                 patch.object(hk_hibor_supplement,'supplement',return_value=[]) as hibor:
                rows=macro.collect(key,directory,'2026-11-03',lambda _:b'')
                self.assertTrue(all(r['period']=='2026-09' and r['status']=='Published' for r in rows))
                prime.assert_not_called();hibor.assert_not_called()



if __name__=='__main__':unittest.main()
