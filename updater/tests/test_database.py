"""Database contract: lossless values, visible caveats, safe replacement."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
try:
    from hk_property_data.database import build_database, validate_database, OBSERVATION_COLUMNS
except ImportError:
    build_database = validate_database = None


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(build_database, 'The queryable database builder must exist')
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'housing.sqlite'
        self.data = json.loads((Path(__file__).resolve().parents[2] / 'data/hk_housing_dataset.json').read_text())

    def test_all_original_rows_fields_pdf_and_warnings_are_queryable(self):
        build_database(self.data, self.path)
        with sqlite3.connect(self.path) as db:
            validate_database(db, self.data)
            db.row_factory = sqlite3.Row
            original = {(r['metric_id'], r['period']): r for r in self.data['observations']}
            for row in db.execute('SELECT * FROM observations'):
                expected = original[row['metric_id'], row['period']]
                self.assertEqual(json.loads(row['payload']), expected)
                for key, value in expected.items():
                    if key in OBSERVATION_COLUMNS:
                        self.assertEqual(row[key], value, (key, expected['metric_id']))
            self.assertEqual(db.execute('SELECT count(*) FROM pdf_observations').fetchone()[0], len(self.data['pdf_observations']))
            self.assertEqual(db.execute('SELECT count(*) FROM revisions').fetchone()[0], len(self.data['revisions']))
            self.assertEqual(json.loads(db.execute('SELECT errors_json FROM dataset_info').fetchone()[0]), self.data['errors'])
            self.assertEqual(db.execute('SELECT count(*) FROM sources').fetchone()[0], len(self.data['source_status']))
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 2)

    def test_extra_source_metadata_remains_queryable_in_lossless_payload(self):
        original = self.data['observations'][0]
        original['extra_source_metadata'] = {'daily_count':20, 'basis':'Historical calculation evidence'}
        build_database(self.data,self.path)
        with sqlite3.connect(self.path) as db:
            value,payload=db.execute("SELECT json_extract(payload,'$.extra_source_metadata.daily_count'),payload FROM observations WHERE metric_id=? AND period=?",(original['metric_id'],original['period'])).fetchone()
            self.assertEqual(value,20)
            self.assertEqual(json.loads(payload),original)

    def test_latest_view_keeps_missing_latest_value_and_price_view_converts_exactly(self):
        row = next(r for r in self.data['observations'] if r.get('source_table') == '1.2' and r['value'] is not None)
        self.data['observations'] = [row, dict(row, period='2099-01', date='2099-01-31', value=None)]
        build_database(self.data, self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT period,value FROM latest_observations').fetchall(), [('2099-01', None)])
            converted = db.execute('SELECT price_hkd_per_sqft FROM residential_sale_prices WHERE period=?', (row['period'],)).fetchone()[0]
            self.assertAlmostEqual(converted, row['value'] * 0.09290304)
            self.assertEqual(db.execute('SELECT count(*) FROM metric_catalog').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT last_period,non_null_count FROM metric_catalog').fetchone(), ('2099-01', 1))

    def test_informational_notes_and_latest_release_check_warnings_are_queryable(self):
        self.data['warnings'] = ['Recorded CSV revisions explain the PDF snapshot differences.']
        self.data['observations'][0]['refresh_warning'] = 'Latest monthly release check unavailable'
        build_database(self.data, self.path)
        with sqlite3.connect(self.path) as db:
            columns = {r[1] for r in db.execute('PRAGMA table_info(dataset_info)')}
            self.assertIn('warnings_json', columns)
            self.assertEqual(json.loads(db.execute('SELECT warnings_json FROM dataset_info').fetchone()[0]), self.data['warnings'])
            self.assertEqual(db.execute('SELECT refresh_warning FROM observations WHERE metric_id=? AND period=?',
                (self.data['observations'][0]['metric_id'], self.data['observations'][0]['period'])).fetchone()[0],
                'Latest monthly release check unavailable')

    def test_invalid_rebuild_preserves_the_previous_database(self):
        build_database(self.data, self.path)
        original = self.path.read_bytes()
        invalid = copy.deepcopy(self.data)
        invalid['observations'].append(invalid['observations'][0])
        with self.assertRaises(sqlite3.IntegrityError):
            build_database(invalid, self.path)
        self.assertEqual(self.path.read_bytes(), original)
        invalid = copy.deepcopy(self.data)
        invalid['observations'][0]['source_id'] = 'missing-source'
        with self.assertRaises(sqlite3.IntegrityError):
            build_database(invalid, self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_rebuild_is_idempotent_and_applies_revisions_without_duplicates(self):
        build_database(self.data, self.path)
        self.data['observations'][0]['value'] = 12345
        build_database(self.data, self.path)
        with sqlite3.connect(self.path) as db:
            validate_database(db, self.data)
            row = self.data['observations'][0]
            self.assertEqual(db.execute('SELECT value FROM observations WHERE metric_id=? AND period=?', (row['metric_id'], row['period'])).fetchone()[0], 12345)
            self.assertEqual(db.execute('SELECT count(*) FROM observations').fetchone()[0], len(self.data['observations']))


if __name__ == '__main__':
    unittest.main()
