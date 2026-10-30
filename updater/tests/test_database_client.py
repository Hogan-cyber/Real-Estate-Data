"""The public download client preserves local data and binds query inputs."""
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(APP / 'examples'), str(APP / 'updater')]
from database import build_database
try:
    import query_database as client
except ImportError:
    client = None


class DatabaseClientTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(client, 'A runnable database download/query example must exist')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'my data.sqlite'
        self.data = json.loads((APP / 'data/hk_housing_dataset.json').read_text())
        build_database(self.data, self.path)

    def test_valid_download_and_read_only_parameterized_query(self):
        binary = self.path.read_bytes()
        with patch.object(client.urllib.request, 'urlopen', return_value=io.BytesIO(binary)):
            client.download_database(self.path)
        with client.open_database(self.path) as db:
            rows = client.query_series(db, 'rvd_1_4_all_classes', start='2025-01', end='2025-12')
            self.assertEqual(len(rows), 12)
            self.assertEqual(rows[0]['period'], '2025-01')
            self.assertEqual(client.query_series(db, "x' OR 1=1 --"), [])
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('DELETE FROM observations')

    def test_failed_or_unrelated_download_preserves_existing_file(self):
        before = self.path.read_bytes()
        for content in [b'<html>not a database</html>', b'SQLite format 3\x00broken']:
            with patch.object(client.urllib.request, 'urlopen', return_value=io.BytesIO(content)):
                with self.assertRaises((ValueError, sqlite3.DatabaseError)):
                    client.download_database(self.path)
            self.assertEqual(self.path.read_bytes(), before)
        with patch.object(client.urllib.request, 'urlopen', side_effect=OSError('network down')):
            with self.assertRaises(OSError):
                client.download_database(self.path)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
