"""Copy contract, independently specified from the supplied Monitor workbook."""
import hashlib
import io
import json
import unittest
import tempfile
from pathlib import Path
from openpyxl import Workbook

from hk_property_data.simple import monitor


def snapshot():
    # Small independently specified workbook, including zero, missing and signed model values.
    layouts = [
        ('registrations','中原按揭',['月份','现楼按揭宗数','楼花按揭宗数','私人住宅现楼宗数','资助房屋宗数'],
         [['2026-10',100,10,80,0]]),
        ('bank','HKMA',['月份','新申请宗数','新批出宗数','新批出金额(HK$Mn)','一手宗数','二手宗数','转按宗数','一手金额(HK$Mn)','二手金额(HK$Mn)','转按金额(HK$Mn)','新取用宗数','新取用金额(HK$Mn)','平均贷款额(HK$Mn)','未偿还总额(HK$Mn)'],
         [['2026-09',120,100,500,20,60,20,100,300,100,150,600,5,10000]]),
        ('registry','土地注册处',['月份','楼宇按揭宗数','其他按揭/法定押记宗数','撤销按揭宗数'],
         [['2026-10',1,150,130]]),
        ('m3','M3',['月份','港元M3(HK$Mn)','所有货币M3(HK$Mn)'],[['2026-09',9000000,22000000]]),
        ('prime','HSBC Prime',['生效日期','HSBC Prime Rate(%)'],[['2025-10-31',5]]),
        ('hibor','HIBOR Daily',['日期','Overnight(%)','1 Week(%)','1 Month(%)','3 Months(%)','6 Months(%)','12 Months(%)'],
         [['2026-11-24',0,2,3,4,5,None]]),
        ('nonbank','非银行',['Date','非银行贷款宗数','真实买卖总数'],[['2026-09',None,120],['2026-10',-10,None]]),
    ]
    book=Workbook();book.remove(book.active)
    for _,name,headers,records in layouts:
        sheet=book.create_sheet(name);sheet.append(headers)
        for row in records:sheet.append(row)
    book['非银行']['F2']='Workbook presentation note outside the data table'
    stream=io.BytesIO();book.save(stream);raw=stream.getvalue()
    payload={'schemaVersion':1,'revision':hashlib.sha256(raw).hexdigest(),
             'series':{key:rows for key,_,_,rows in layouts}}
    html='<script id="workbook-data" type="application/json">'+json.dumps(payload)+'</script>'
    return raw,html,payload


class MonitorCopyTests(unittest.TestCase):
    def local_snapshot(self, folder):
        raw,html,_=snapshot()
        files={'hk_mortgage_data.xlsx':raw,'HK_Mortgage_Dashboard.html':html.encode(),
               'collection_report.json':json.dumps({'checked_at':'2026-11-25T04:31:37+08:00','issues':[],'status':'partial'}).encode(),
               'source_evidence.json':b'[]'}
        for name,content in files.items():(folder/name).write_bytes(content)
        (folder/'diagnostics.json').write_text(json.dumps({'commit':'a'*40,'hashes':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}))

    def test_local_replay_refuses_wrong_commit_and_file_digest(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path);self.local_snapshot(root)
            with self.assertRaisesRegex(ValueError,'commit'):
                monitor.collect(root/'out','2026-11-25',commit='b'*40,snapshot_dir=root)
            (root/'source_evidence.json').write_text('[{}]')
            with self.assertRaisesRegex(ValueError,'digest'):
                monitor.collect(root/'out','2026-11-25',commit='a'*40,snapshot_dir=root)

    def test_historical_coverage_describes_exported_rows(self):
        with tempfile.TemporaryDirectory() as path:
            root=Path(path);self.local_snapshot(root)
            rows=monitor.collect(root/'out','2026-09-30',commit='a'*40,snapshot_dir=root)
            report=json.loads((root/'out/raw/monitor/diagnostics.json').read_text())
            self.assertEqual(report['coverage']['registrations'],{'first':None,'last':None,'rows':0})
            self.assertEqual(report['upstream_coverage']['registrations']['last'],'2026-10')
            self.assertEqual(report['coverage']['bank']['last'],'2026-09')
            self.assertTrue(all(row['date']<='2026-09-30' for row in rows))

    def test_exact_copy_keeps_original_periods_nulls_and_negative_residual(self):
        raw,html,_=snapshot()
        series=monitor.read_verified_snapshot(raw,html)
        rows=monitor.observations(series,'a'*40,{'checked_at':'2026-11-25T04:31:37+08:00'},
                                  checked_at='2026-11-25T08:00:00+00:00')
        data={(r['metric_id'],r['period']):r for r in rows}
        self.assertEqual(len(data),33)
        self.assertEqual(data['monitor_nonbank_residual_count','2026-10']['value'],-10)
        self.assertIsNone(data['monitor_bank_purchase_drawn_count_estimate','2026-10']['value'])
        self.assertEqual(data['monitor_hibor_overnight_daily','2026-11-24']['value'],0)
        self.assertEqual(data['monitor_prime_rate_hsbc_effective','2025-10-31']['frequency'],'E')
        model=data['monitor_nonbank_residual_count','2026-10']
        self.assertEqual(model['date'],'2026-10-31')
        self.assertEqual(model['status'],'Estimate')
        self.assertIn('prior-month',model['note'])
        self.assertIn('/'+'a'*40+'/',model['source_url'])
        self.assertEqual(model['source_checked_at'],'2026-11-25T04:31:37+08:00')

    def test_rejects_workbook_hash_and_embedded_value_mismatch(self):
        raw,html,payload=snapshot()
        with self.assertRaisesRegex(ValueError,'hash'):
            monitor.read_verified_snapshot(raw+b'changed',html)
        payload['series']['registrations'][0][1]=999
        with self.assertRaisesRegex(ValueError,'match'):
            monitor.read_verified_snapshot(raw,'<script id="workbook-data" type="application/json">'+json.dumps(payload)+'</script>')

    def test_rejects_changed_headers_and_unknown_series(self):
        raw,html,payload=snapshot()
        payload['series']['extra']=[]
        with self.assertRaisesRegex(ValueError,'series'):
            monitor.read_verified_snapshot(raw,'<script id="workbook-data" type="application/json">'+json.dumps(payload)+'</script>')

    def test_model_is_validated_without_clamping_or_relabeling(self):
        _,_,payload=snapshot()
        monitor.validate_model(payload['series'])
        payload['series']['nonbank'][1][1]=0
        with self.assertRaisesRegex(ValueError,'model'):
            monitor.validate_model(payload['series'])
