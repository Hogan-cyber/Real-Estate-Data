import csv
import io
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'collectors'))
import hk_commercial_collector as commercial

class CommercialTest(unittest.TestCase):
    def fixture(self, table, values):
        _, _, title, columns = commercial.TABLES[table]
        buffer = io.StringIO(); writer = csv.writer(buffer)
        writer.writerow([title]);writer.writerow(['Month'] + [v for c in columns for v in (c, c + ' - Remarks')])
        writer.writerow(['08-2026'] + [v for value, flag in values for v in (value, flag)])
        return buffer.getvalue().encode()
    def test_office_missing_values_and_grades_are_not_residential_classes(self):
        rows = commercial.parse('2.2', self.fixture('2.2', [('n/a', 'P'), ('340012', 'PX')] + [('1', '')] * 19), '2026-10-27')
        self.assertIsNone(rows[0]['value']);self.assertEqual(rows[1]['region'], 'Central')
        self.assertEqual(rows[1]['grade'], 'A');self.assertEqual(rows[1]['property_type'], 'Office')
        self.assertTrue(rows[1]['small_sample']);self.assertEqual(rows[1]['unit'], 'HKD / sq m')
    def test_combined_retail_columns_keep_rent_and_price_separate(self):
        rows = commercial.parse('3.1', self.fixture('3.1', [('100', 'P')] * 6), '2026-10-27')
        self.assertEqual([r['measure'] for r in rows], ['average_rent'] * 3 + ['average_price'] * 3)
        self.assertEqual(rows[0]['unit'], 'HKD / sq m / month');self.assertEqual(rows[3]['unit'], 'HKD / sq m')
    def test_column_order_change_is_rejected(self):
        raw = self.fixture('3.2', [('1',''),('2','')]).replace(b'Rents,Rents - Remarks,Prices,Prices - Remarks', b'Prices,Prices - Remarks,Rents,Rents - Remarks')
        with self.assertRaisesRegex(ValueError, 'column names'): commercial.parse('3.2', raw, '2026-10-27')
    def test_yields_retain_sector_and_grade(self):
        rows = commercial.parse('5.2', self.fixture('5.2', [('3.5', 'P')] * 4), '2026-10-27')
        self.assertEqual([r['property_type'] for r in rows], ['Office', 'Office', 'Industrial', 'Retail'])
        self.assertEqual([r['grade'] for r in rows], ['A','B','All','All'])
