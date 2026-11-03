"""Excel contract: numeric cells, blank preservation and safe standalone downloads."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.export_excel import build_excel, validate_excel, NS


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
        pdf = self.cells(8)
        self.assertIn('annual', ''.join(pdf['B7'].itertext()))
        self.assertIn('forecast', ''.join(pdf['C7'].itertext()))
        self.assertEqual(float(pdf['F7'].find('s:v', NS).text), 0)
        self.assertIn('SOURCE REVIEW', ''.join(self.cells(1)['A10'].itertext()))

    def test_macro_is_separate_with_formula_growth_and_no_area_conversion(self):
        row = dict(metric_id='hk_m3_hkd', metric_name='M3 HKD', category='macro', property_type='Macro', source_id='hkma_m3', source_table='2.2.1', period='2025-01', value=100, unit='HKD million')
        rate = dict(row, metric_id='hk_hibor_1m', unit='% p.a.', period='2026-01', value=4.75)
        self.data['observations'] += [row,dict(row,period='2026-01',value=110), rate,dict(rate,period='2025-12',value=5)]
        build_excel(self.data,self.path)
        cells = self.cells(7)
        records = {''.join(cells[f'M{r}'].itertext())+':'+str(float(cells[f'F{r}'].find('s:v',NS).text)):r for r in range(7,11)}
        m = records['hk_m3_hkd:110.0']; h = records['hk_hibor_1m:4.75']
        self.assertAlmostEqual(float(cells[f'R{m}'].find('s:v',NS).text),10)
        self.assertAlmostEqual(float(cells[f'S{h}'].find('s:v',NS).text),-0.25)
        self.assertIsNone(cells[f'H{m}'].find('s:f',NS))
        self.assertEqual(validate_excel(self.path,self.data)['monthly_rows'],8)

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

    def test_confirmed_revision_notes_and_evidence_remain_visible_without_errors(self):
        self.data['errors'] = []
        self.data['warnings'] = ['PDF snapshot values match recorded official CSV revisions.']
        self.data['report']['comparisons'] = [dict(table_id='1.2', status='revisions_confirmed', compared_cells=1,
            mismatch_count=1, confirmed_revision_count=1, unexplained_mismatch_count=0,
            mismatches=[dict(period='2026-01', column='Class A Hong Kong', pdf=10000, csv=10020,
                resolution='recorded_csv_revision', revision_evidence=[dict(old=10000,new=10020)])])]
        build_excel(self.data, self.path)
        overview = ''.join(self.cells(1)['A10'].itertext())
        self.assertIn(self.data['warnings'][0], overview)
        self.assertNotIn('SOURCE REVIEW', overview)
        checks = ' '.join(''.join(cell.itertext()) for cell in self.cells(9).values())
        self.assertIn('recorded_csv_revision', checks)
        self.assertIn('Confirmed revisions', checks)


if __name__ == '__main__':
    unittest.main()
