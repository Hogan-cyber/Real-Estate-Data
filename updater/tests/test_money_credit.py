"""C01 reports direct growth rates with monthly money/credit and quarterly GDP."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_money_credit_collector as c


def cell(kind=0, value=''):
    return SimpleNamespace(ctype=kind, value=value)


def date_cell(year, month):
    serial=(dt.date(year,month,15)-dt.date(1899,12,30)).days
    return cell(3,float(serial))


class Workbook:
    datemode=0

    def __init__(self, changes=None, extra_rows=None):
        self.rows=[
            [cell(),cell(),cell(1,'Money and Credit'),cell(),cell()],
            [cell(),cell(),cell(1,'HK dollar M3'),cell(1,'Domestic credit'),cell(1,'Nominal GDP')],
            [cell(),cell(),cell(1,'(yoy %)'),cell(1,'(yoy %)'),cell(1,'(yoy %)')],
            [cell(),date_cell(2026,7),cell(2,5.524159681586904),cell(2,6.516200617632222),cell(5,42)],
            [cell(),date_cell(2026,8),cell(2,9.863447725491682),cell(2,7.064389846096645),cell(5,42)],
            [cell(),date_cell(2026,9),cell(2,0.0),cell(2,-0.5),cell(2,6.8)],
            [cell(),date_cell(2026,12),cell(),cell(),cell(5,42)],
        ]
        for (row,column),value in (changes or {}).items():self.rows[row][column]=value
        self.rows.extend(extra_rows or [])
        self.nrows=len(self.rows);self.ncols=5

    def sheet_names(self):return ['Data']
    def sheet_by_name(self,name):
        if name!='Data':raise KeyError(name)
        return self
    def cell(self,row,column):return self.rows[row][column]


class MoneyCreditTest(unittest.TestCase):
    def parse(self,book=None,as_of='2026-11-04'):
        with patch('xlrd.open_workbook',return_value=book or Workbook()):
            return c.parse(b'fixture',as_of)

    def test_preserves_direct_values_units_provenance_and_mixed_frequency(self):
        rows=self.parse()
        self.assertEqual(len(rows),7)
        monthly=[r for r in rows if r['frequency']=='M']
        quarterly=[r for r in rows if r['frequency']=='Q']
        self.assertEqual(len(monthly),6)
        self.assertEqual(len(quarterly),1)
        first=next(r for r in rows if r['metric_id']=='hk_money_credit_m3_yoy' and r['period']=='2026-07')
        self.assertEqual(first['value'],5.524159681586904)
        self.assertEqual(first['source_column'],'C')
        self.assertEqual(first['source_row'],4)
        self.assertEqual(first['date'],'2026-07-31')
        self.assertEqual(quarterly[0]['period'],'2026-09')
        self.assertEqual(quarterly[0]['source_period'],'2026-Q3')
        self.assertEqual(quarterly[0]['date'],'2026-09-30')
        self.assertEqual(quarterly[0]['source_field'],'Nominal GDP')
        self.assertTrue(all(r['category']=='macro' and r['property_type']=='Macro' and r['unit']=='% yoy' for r in rows))
        self.assertTrue(all(r['source_url']==c.SOURCE_URL for r in rows))
        self.assertFalse(any(r['period']=='2026-12' for r in rows))
        self.assertEqual(next(r['value'] for r in rows if r['metric_id']=='hk_money_credit_m3_yoy' and r['period']=='2026-09'),0)
        self.assertEqual(next(r['value'] for r in rows if r['metric_id']=='hk_domestic_credit_yoy' and r['period']=='2026-09'),-0.5)

    def test_missing_quarter_is_not_filled_from_previous_or_next_value(self):
        book=Workbook(extra_rows=[[cell(),date_cell(2027,3),cell(2,1),cell(2,2),cell(2,3)]])
        rows=self.parse(book,'2027-04-01')
        self.assertEqual([r['source_period'] for r in rows if r['frequency']=='Q'],['2026-Q3','2027-Q1'])

    def test_rejects_changed_titles_headers_and_units(self):
        for coordinate,value in (((0,2),'Credit'),((1,3),'Other credit'),((2,4),'(HK$ billion)')):
            with self.subTest(coordinate=coordinate),self.assertRaisesRegex(ValueError,'schema'):
                self.parse(Workbook({coordinate:cell(1,value)}))

    def test_rejects_nonnumeric_values_unknown_excel_errors_and_bad_dates(self):
        cases=[{(3,2):cell(1,'5.5')},{(3,2):cell(5,7)},{(3,2):cell(4,1)},
               {(3,2):cell(2,float('nan'))},{(3,2):cell(2,float('inf'))},
               {(3,1):cell(1,'Jul 2026')},{(3,1):cell()}]
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.parse(Workbook(changes))

    def test_rejects_duplicate_month_nonquarter_gdp_and_future_numeric_observation(self):
        for changes in ({(4,1):date_cell(2026,7)},{(3,4):cell(2,5.0)},{(6,2):cell(2,5.0)}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.parse(Workbook(changes))

    def test_collect_archives_only_after_validation_and_retains_last_valid_source(self):
        fetch=Mock(return_value=b'official-workbook')
        with tempfile.TemporaryDirectory() as temporary,patch('xlrd.open_workbook',return_value=Workbook()):
            rows=c.collect(Path(temporary),'2026-11-04',fetch)
            self.assertEqual(len(rows),7)
            fetch.assert_called_once_with(c.SOURCE_URL)
            archive=Path(temporary)/'C01.xls'
            self.assertEqual(archive.read_bytes(),b'official-workbook')
            with patch('xlrd.open_workbook',return_value=Workbook({(1,2):cell(1,'Changed')})):
                with self.assertRaises(ValueError):c.collect(Path(temporary),'2026-11-04',lambda url:b'bad')
            self.assertEqual(archive.read_bytes(),b'official-workbook')


if __name__=='__main__':unittest.main()
