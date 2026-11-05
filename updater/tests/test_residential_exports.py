"""All published formats must describe the same source observations."""
import contextlib
import csv
import gzip
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import pyarrow.parquet as pq

from scripts.collect_residential import main


class ResidentialExportTests(unittest.TestCase):
    def test_monthly_estimates_export_as_three_separate_columns_with_sources(self):
        from openpyxl import load_workbook
        from updater.tests.test_simple_mortgage_estimates import inputs
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);parts=out/'parts';parts.mkdir()
            official=inputs()
            grouped={name:[] for name in ('rvd','landreg','hkma','rates')}
            for row in official:
                grouped['hkma' if row['metric_id'].startswith('hk_mortgage_') else 'landreg'].append(row)
            for source,metric in [('rvd','rvd_1_4_all_classes'),('rates','hk_hibor_1m_daily')]:
                grouped[source]=[dict(official[0],metric_id=metric,metric_name=metric,value=1)]
            for source,rows in grouped.items():
                (parts/(source+'.json')).write_text(json.dumps(rows))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--from-saved','--output',directory,'--start','2026-01','--as-of','2026-01-31']),0)
            wb=load_workbook(out/'HK_Residential_Data.xlsx',data_only=True)
            count=wb['Mortgage_Monthly'];amount=count
            self.assertEqual([count.cell(5,c).value for c in range(2,5)],[4200,2250,1950])
            self.assertEqual([amount.cell(5,c).value for c in range(5,8)],[22400,12000,10400])
            self.assertIn('landreg.gov.hk',count['D5'].comment.text)
            self.assertIn('LR_REFINANCING_NOT_REMOVED',count['D5'].comment.text)
            self.assertFalse(any(s.startswith('Mortgage_Estimate') for s in wb.sheetnames))
            wb.close()
            with (out/'observations.csv').open(encoding='utf-8-sig') as f:
                csv_rows={r['metric_id']:r for r in csv.DictReader(f)}
            parquet_rows={r['metric_id']:r for r in pq.read_table(out/'observations.parquet').to_pylist()}
            for metric,want in [('hk_money_lender_mortgage_count_estimate',1950),
                                ('hk_money_lender_mortgage_amount_estimate',10400)]:
                self.assertEqual(float(csv_rows[metric]['value']),want)
                self.assertEqual(parquet_rows[metric]['value'],want)
                self.assertEqual(parquet_rows[metric]['status'],'Estimated')
            conn=sqlite3.connect(out/'observations.sqlite')
            try:
                self.assertEqual(conn.execute("select value from observations where metric_id='hk_money_lender_mortgage_count_estimate'").fetchone(),(1950,))
            finally:
                conn.close()

    def test_csv_gzip_and_sqlite_preserve_values_and_published_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); parts = out / 'parts'; parts.mkdir()
            for source, metric, value, frequency in (
                ('rvd', 'rvd_1_4_all_classes', 0, 'M'),
                ('landreg', 'hk_residential_sales_count', None, 'M'),
                ('hkma', 'hk_m3_hkd', 123.45, 'M'),
                ('rates', 'hk_hibor_1m_daily', 2.6, 'D'),
            ):
                row = dict(metric_id=metric, metric_name=metric, value=value, frequency=frequency,
                           period='2026-09-30' if frequency == 'D' else '2026-09', date='2026-09-30',
                           unit='index', source_url='https://example.org/source', source_name='Official',
                           checked_at='2026-11-04', status='Published', flags='')
                (parts / (source + '.json')).write_text(json.dumps([row]))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--from-saved', '--output', directory, '--as-of', '2026-11-04']), 0)
            self.assertTrue((out / 'api/observations.parquet').is_file())
            typed = pq.read_table(out / 'api/observations.parquet').to_pylist()
            self.assertEqual(len(typed), 4)
            self.assertEqual({r['metric_id']: r['value'] for r in typed}, {
                'rvd_1_4_all_classes': 0.0, 'hk_residential_sales_count': None,
                'hk_m3_hkd': 123.45, 'hk_hibor_1m_daily': 2.6})
            self.assertEqual((out / 'api/observations.parquet').read_bytes(), (out / 'observations.parquet').read_bytes())
            obsolete = out / 'api/removed.parquet'; obsolete.write_bytes(b'obsolete')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--from-saved', '--output', directory, '--as-of', '2026-11-04']), 0)
            self.assertFalse(obsolete.exists())
            self.assertEqual(gzip.decompress((out / 'observations.csv.gz').read_bytes()),
                             (out / 'observations.csv').read_bytes())
            status = json.loads((out / 'collection_status.json').read_text())
            self.assertEqual(status['schema_version'], 1)
            conn = sqlite3.connect(out / 'observations.sqlite')
            try:
                self.assertEqual(conn.execute('select count(*) from observations').fetchone(), (4,))
                self.assertEqual(conn.execute('select count(*) from observations where value is null').fetchone(), (1,))
                self.assertEqual(conn.execute("select value from observations where metric_id='rvd_1_4_all_classes'").fetchone(), (0.0,))
                self.assertEqual(json.loads(conn.execute("select value from metadata where key='collection_status'").fetchone()[0]), status)
                self.assertEqual(conn.execute('pragma integrity_check').fetchone(), ('ok',))
            finally:
                conn.close()
