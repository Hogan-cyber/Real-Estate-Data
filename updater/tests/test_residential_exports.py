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
            sheet=wb['Mortgage_Monthly']
            header=next(r for r in sheet if r[0].value=='Period')
            cols={c.value:c.column for c in header}
            data=header[0].row+1
            for label,want in [('Residential total: count estimate',4200),
                               ('Bank excluding refinancing: count estimate',2250),
                               ('Money-lender residual: count estimate',1950),
                               ('Residential total: amount scenario',22400),
                               ('Bank excluding refinancing: amount estimate',12000),
                               ('Money-lender residual: amount scenario',10400)]:
                self.assertEqual(sheet.cell(data,cols[label]).value,want)
            dictionary={r[2]:r for r in wb['Data_Dictionary'].iter_rows(min_row=2,values_only=True)}
            residual=dictionary['hk_money_lender_mortgage_count_estimate']
            self.assertIn('landreg.gov.hk',residual[13])
            self.assertIn('hkma.gov.hk',residual[13])
            self.assertIn('mortgage_estimates.py',residual[15])
            self.assertFalse(any(c.comment for r in sheet for c in r))
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
                self.assertIn('LR_REFINANCING_NOT_REMOVED',parquet_rows[metric]['flags'])
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
