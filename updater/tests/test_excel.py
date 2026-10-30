"""Excel contract: numeric cells, blank preservation and safe standalone downloads."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_excel import build_excel, validate_excel, NS


class ExcelTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'data.xlsx'
        row = dict(metric_id='price_a', metric_name='Average price', source_table='1.2', source_id='rvd_1.2',
                   period='2026-01', value=10000, unit='HKD / sq m', class_name='A', region='Kowloon')
        self.data = dict(as_of='2026-10-30', checked_at='2026-10-30T08:00:00+00:00',
            observations=[row, dict(row, period='2026-02', value=0), dict(row, period='2026-03', value=None),
                dict(row, metric_id='yield_a', source_table='5.1', value=3.26, unit='%', metric_name='=1+2')],
            pdf_observations=[dict(period='2027', frequency='annual', observation_kind='forecast', table_id='6', value=0)],
            source_status=[], revisions=[dict(metric_id='price_a', period='2026-01', old=None, new=10000)],
            errors=['pdf: CSV comparison needs review'], report={'edition':'2026-10','latest_period':'2026-08'})

    def cells(self, sheet):
        with zipfile.ZipFile(self.path) as z:
            root = ET.fromstring(z.read(f'xl/worksheets/sheet{sheet}.xml'))
        return {cell.attrib['r']: cell for cell in root.findall('.//s:c', NS)}

    def test_download_keeps_numeric_values_blanks_cached_formulas_and_frequencies(self):
        build_excel(self.data, self.path)
        self.assertEqual(validate_excel(self.path, self.data)['monthly_rows'], 4)
        cells = self.cells(2)
        self.assertIsNone(cells['F7'].find('s:v', NS))  # Latest month remains missing.
        self.assertEqual(cells['F8'].find('s:v', NS).text, '0')
        self.assertEqual(float(cells['H8'].find('s:v', NS).text), 0)
        self.assertAlmostEqual(float(cells['H9'].find('s:v', NS).text), 929.0304)
        self.assertEqual(cells['H9'].find('s:f', NS).text, 'IF(ISNUMBER(F9),F9*Overview!$B$8,"")')
        self.assertNotEqual(cells['A7'].attrib.get('t'), 'inlineStr')  # Real Excel date.
        indices = self.cells(4)
        self.assertEqual(float(indices['F7'].find('s:v', NS).text), 3.26)
        self.assertIsNone(indices['H7'].find('s:f', NS))  # Percentages are not floor-area prices.
        self.assertIsNone(indices['B7'].find('s:f', NS))  # Source text cannot become a formula.
        pdf = self.cells(7)
        self.assertIn('annual', ''.join(pdf['B7'].itertext()))
        self.assertIn('forecast', ''.join(pdf['C7'].itertext()))
        self.assertEqual(float(pdf['F7'].find('s:v', NS).text), 0)
        self.assertIn('SOURCE REVIEW', ''.join(self.cells(1)['A10'].itertext()))

    def test_invalid_rebuild_preserves_previous_excel(self):
        build_excel(self.data, self.path)
        saved = self.path.read_bytes()
        for invalid in ('duplicate', 'nonfinite', 'date'):
            data = copy.deepcopy(self.data)
            if invalid == 'duplicate':
                data['observations'].append(data['observations'][0])
            elif invalid == 'nonfinite':
                data['observations'][0]['value'] = float('inf')
            else:
                data['observations'][0]['period'] = 'bad-date'
            with self.assertRaises(ValueError):
                build_excel(data, self.path)
            self.assertEqual(self.path.read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
