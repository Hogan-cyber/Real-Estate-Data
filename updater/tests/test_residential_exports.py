"""All published formats must describe the same source observations."""
import contextlib
import gzip
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.collect_residential import main


class ResidentialExportTests(unittest.TestCase):
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
