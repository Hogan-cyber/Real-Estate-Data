import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'python'))
from hk_property_data.pipeline import seed_landreg_archives,merge_source_rows
from hk_property_data.validation import validate_official_sources,validate_mortgage_reconciliations


class SourcePolicyTests(unittest.TestCase):
    def test_failed_period_retains_value_but_not_verified_status(self):
        old=dict(metric_id='mortgage_deeds',period='2026-09',value=7836,source_id='landreg',status='Published',checked_at='2026-10-03')
        fresh=dict(metric_id='sales',period='2026-10',value=4512,refresh_failed_metric_ids=['mortgage_deeds'],refresh_failed_periods=['2026-09'])
        rows=merge_source_rows([old],[fresh],'landreg')
        retained=next(r for r in rows if r['metric_id']=='mortgage_deeds')
        self.assertEqual((retained['value'],retained['checked_at'],retained['status']),(7836,'2026-10-03','stale_cache'))
        restored=merge_source_rows(rows,[dict(old,value=7837,checked_at='2026-11-04')],'landreg')
        self.assertEqual(next(r for r in restored if r['metric_id']=='mortgage_deeds')['status'],'Published')

    def test_only_https_government_hosts_are_accepted(self):
        validate_official_sources([{'source_url':'https://api.hkma.gov.hk/a'}, {'source_pdf':'https://www.rvd.gov.hk/full.pdf'}])
        for url in ['https://www.hsbc.com.hk/rates','https://www.hkab.org.hk/rates','https://www.hkma.gov.hk.example.com/a','http://www.hkma.gov.hk/a','']:
            with self.assertRaises(ValueError):
                validate_official_sources([{'source_url':url}])

    def test_archive_hydration_preserves_source_check_time_and_uses_newest(self):
        url='https://www.landreg.gov.hk/datagovhk/200101_data.json'
        with tempfile.TemporaryDirectory() as directory:
            app=Path(directory); archive=app/'updater'/'archives';archive.mkdir(parents=True)
            old={'url':url,'body':'old','checked_at':'2026-10-01T00:00:00+00:00'}
            new=dict(old,body='new',checked_at='2026-11-01T00:00:00+00:00')
            for name,data in [('old',old),('new',new),('other',dict(new,url='https://private.example/data'))]:
                (archive/(name+'.json')).write_text(json.dumps(data))
            seed_landreg_archives(app,app/'cache')
            folder=app/'cache'/'landreg'
            result=json.loads((folder/(hashlib.sha256(url.encode()).hexdigest()+'.json')).read_text())
            self.assertEqual(result,new)
            self.assertEqual(len(list(folder.iterdir())),1)

    def test_purchase_derivation_cannot_use_drawdowns_or_missing_inputs(self):
        rows=[]
        for measure,values in [('count',[6240,1499,2974,1767,4473]),('amount',[31835,8452,14443,8940,22895])]:
            rows += [dict(metric_id='hk_mortgage_approved_'+part+measure,period='2026-09',value=value) for part,value in zip(['','primary_','secondary_','refinancing_','purchase_'],values)]
        validate_mortgage_reconciliations(rows)
        validate_mortgage_reconciliations(rows[:5])  # A count-only published breakdown is valid.
        with self.assertRaises(ValueError):
            validate_mortgage_reconciliations(rows[1:])
        rows[4]['value']=4788-1767
        with self.assertRaises(ValueError):
            validate_mortgage_reconciliations(rows)
