"""Published totals can lead the primary/secondary breakdown without filling it."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'python'))
from hk_property_data.database import build_database
from hk_property_data.export_excel import build_excel
from hk_property_data.validation import validate


class SalesCoverageTest(unittest.TestCase):
    def test_new_official_totals_remain_usable_until_components_are_published(self):
        data=json.loads((Path(__file__).resolve().parents[2]/'data/hk_housing_dataset.json').read_text())
        data['observations']=[r for r in data['observations'] if not (r['source_id']=='landreg' and r['period']=='2026-10')]
        for metric,value in [('hk_residential_sales_count',4512),('hk_residential_sales_value',42346)]:
            template=next(r for r in data['observations'] if r['metric_id']==metric)
            data['observations'].append(dict(template,period='2026-10',date='2026-10-31',value=value))
        data['as_of']='2026-11-03'
        # Keep this historical fixture's daily observations within its cutoff
        # as the live dataset gains newer fixing dates.
        from hk_property_data.collectors.hk_latest_rates import government_rows
        data['rate_observations']=[r for r in government_rows(data.get('rate_observations',[])) if r['date']<=data['as_of']]
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            (out/'hk_housing_dataset.json').write_text(json.dumps(data))
            build_database(data,out/'hk_housing.sqlite');build_excel(data,out/'hk_property_data.xlsx')
            from hk_property_data.pipeline import csvwrite
            csvwrite(out/'hk_observations.csv',data['observations'])
            csvwrite(out/'hk_rate_observations.csv',data.get('rate_observations',[]))
            result=validate(out)
            self.assertIn('2026-10',result['sale_breakdown_unavailable_periods'])
            self.assertGreater(result['sale_periods_checked'],0)
            self.assertFalse(any(r['metric_id']=='hk_residential_primary_sales_count' and r['period']=='2026-10' for r in data['observations']))
            broken=copy.deepcopy(data)
            next(r for r in broken['observations'] if r['metric_id']=='hk_residential_sales_count' and r['period']=='2026-09')['value']+=1
            (out/'hk_housing_dataset.json').write_text(json.dumps(broken))
            with self.assertRaises(AssertionError):validate(out)
