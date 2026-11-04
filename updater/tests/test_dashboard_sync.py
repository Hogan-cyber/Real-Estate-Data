import copy
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'python'))
from hk_property_data import validation


class DashboardSyncTests(unittest.TestCase):
    def fixture(self):
        monthly=[{'metric_id':'hk_prime_rate_hsbc','date':'2026-09-30','period':'2026-09','value':5,'unit':'% p.a.','source_url':'monthly'}]
        daily=[{'metric_id':'hk_hibor_1m_daily','date':'2026-11-04','value':2.63982,'unit':'% p.a.','source_url':'daily'}]
        data={'as_of':'2026-11-04','checked_at':'2026-11-04T04:00:00Z','observations':monthly,'rate_observations':daily,'pdf_observations':[]}
        snapshot={'asOf':data['as_of'],'generatedAt':data['checked_at'],'queries':{name:{'rows':rows} for name,rows in [('observations',monthly),('rates',daily),('pdf',[])]},'filters':[{'id':'date','queryIds':['observations','rates'],'defaultValue':'2020-01-01..2026-11-04'}]}
        return data,copy.deepcopy(snapshot)

    def test_same_snapshot_passes_but_stale_daily_dashboard_fails(self):
        data,snapshot=self.fixture()
        validation.validate_dashboard(snapshot,data)
        snapshot['queries']['rates']['rows'][0]['date']='2026-09-30'
        with self.assertRaisesRegex(ValueError,'rates'):
            validation.validate_dashboard(snapshot,data)

    def test_wrong_value_or_source_link_is_detected(self):
        for key,value in [('value',8),('source_url','wrong interest rate table')]:
            data,snapshot=self.fixture();snapshot['queries']['observations']['rows'][0][key]=value
            with self.assertRaisesRegex(ValueError,'observations'):
                validation.validate_dashboard(snapshot,data)

    def test_old_filter_end_or_other_refresh_timestamp_is_detected(self):
        data,snapshot=self.fixture();snapshot['filters'][0]['defaultValue']='2020-01-01..2026-09-30'
        with self.assertRaisesRegex(ValueError,'Reference period'):
            validation.validate_dashboard(snapshot,data)
        data,snapshot=self.fixture();snapshot['generatedAt']='2026-11-03T04:00:00Z'
        with self.assertRaisesRegex(ValueError,'timestamp'):
            validation.validate_dashboard(snapshot,data)

    def test_csv_values_and_links_match_and_duplicate_rows_are_rejected(self):
        data,_=self.fixture();rows=data['rate_observations']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rates.csv'
            def write(values):
                with path.open('w',newline='') as f:
                    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(values)
            write(rows);validation.validate_csv(path,rows)
            write([dict(rows[0],value=3)])
            with self.assertRaisesRegex(ValueError,'CSV'):
                validation.validate_csv(path,rows)
            write(rows+rows)
            with self.assertRaisesRegex(ValueError,'CSV'):
                validation.validate_csv(path,rows)


if __name__=='__main__':unittest.main()
