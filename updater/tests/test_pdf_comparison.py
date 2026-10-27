import csv
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'collectors'))
from hk_pdf_extract import compare_csvs

class PdfComparisonTest(unittest.TestCase):
    def test_area_class_price_cells_are_compared_and_differences_remain_visible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with (root/'1.2M.csv').open('w') as handle:
                writer=csv.writer(handle);writer.writerow(['Official title']);writer.writerow(['Month','Class A Hong Kong']);writer.writerow(['08-2026','145769'])
            rows=[{'table_id':'1.2','frequency':'monthly','period':'2026-08','column':'Class A | Hong Kong','value':145769}]
            result=next(r for r in compare_csvs(rows,root) if r['table_id']=='1.2')
            self.assertEqual(result['status'],'matched');self.assertEqual(result['compared_cells'],1)
            rows[0]['value']=145700
            result=next(r for r in compare_csvs(rows,root) if r['table_id']=='1.2')
            self.assertEqual(result['status'],'review');self.assertEqual(result['mismatch_count'],1)
            self.assertEqual(rows[0]['value'],145700)
