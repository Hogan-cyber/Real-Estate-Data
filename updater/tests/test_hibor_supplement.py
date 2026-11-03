"""Closed-month HIBOR calculations must have every official fixing date."""
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_macro_collector as macro

OCTOBER = {
    '02': 2.96839, '05': 2.94220, '06': 2.90000, '07': 2.83905,
    '08': 2.76494, '09': 2.75000, '12': 2.75810, '13': 2.76327,
    '14': 2.75000, '15': 2.73792, '16': 2.70780, '20': 2.70446,
    '21': 2.67917, '22': 2.74500, '23': 2.77893, '26': 2.75000,
    '27': 2.70000, '28': 2.71351, '29': 2.71494, '30': 2.70923,
}
SEPTEMBER = ['01','02','03','04','07','08','09','10','11','14','15',
             '16','17','18','21','22','23','24','25','28','29','30']


class HiborSupplementTest(unittest.TestCase):
    def setUp(self):
        name = 'hk_property_data.collectors.hk_hibor_supplement'
        self.assertIsNotNone(importlib.util.find_spec(name), 'HIBOR supplement is not implemented')
        self.module = importlib.import_module(name)
        clock = patch.object(self.module, '_today', return_value=dt.date(2026,11,3), create=True)
        clock.start()
        self.addCleanup(clock.stop)
        self.rows = macro.parse_records('hkma_hibor', [dict(end_of_month='2026-09', ir_1m=2.5, ir_3m=3.1)], '2026-11-03')
        self.records = [dict(end_of_date='2026-09-'+day, hibor_fixing_1m=2.5) for day in SEPTEMBER]
        self.records += [dict(end_of_date='2026-10-'+day, hibor_fixing_1m=value) for day, value in OCTOBER.items()]
        self.records += [dict(end_of_date='2026-11-02', hibor_fixing_1m=9)]
        self.calendar = {'vcalendar': [{'prodid':'-//1823 Contact Centre, HKSARG//Hong Kong Public Holidays//EN',
            'vevent': [{'dtstart':[date, {'value':'DATE'}], 'summary':label} for date,label in [
                ('20260101','The first day of January'), ('20260926','Mid-Autumn Festival'),
                ('20261001','National Day'), ('20261019','Chung Yeung Festival'), ('20261225','Christmas Day')]]}]}

    def fetcher(self, records=None, api_error=None, wrong_html_date=False):
        records = self.records if records is None else records
        def fetch(url):
            if '1823.gov.hk' in url:
                return ('\ufeff'+json.dumps(self.calendar)).encode()
            if 'api.hkma.gov.hk' in url:
                if api_error: raise api_error
                return json.dumps({'header':{'success':True},'result':{'datasize':len(records),'records':records}}).encode()
            if '/ms-' in url and api_error:
                stamp = url.rstrip('/').split('ms-')[-1]
                period = stamp[:4]+'-'+stamp[4:6]+'-'+stamp[6:]
                day = next(row for row in self.records if row['end_of_date']==period)
                date = '01/01/2000' if wrong_html_date else stamp[6:]+'/'+stamp[4:6]+'/'+stamp[:4]
                return f'<h1>Daily Monetary Statistics</h1><p>HKAB 1-Month HIBOR Fixing : (香港銀行公會一個月期港元銀行同業拆息定價)</p><span>{day["hibor_fixing_1m"]}%</span><p>Date and Time (日期和時間) : 18:30, {date}</p>'.encode()
            raise OSError('Unexpected or unavailable source '+url)
        return fetch

    def test_complete_month_mean_excludes_november_and_archives_provenance(self):
        original = copy.deepcopy(self.rows)
        with tempfile.TemporaryDirectory() as folder:
            rows = self.module.supplement(self.rows, folder, '2026-11-03', self.fetcher())
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual((row['metric_id'],row['period'],row['date']), ('hk_hibor_1m','2026-10','2026-10-31'))
            self.assertAlmostEqual(row['value'], 2.7688455, places=10)
            self.assertEqual(row['status'], 'Calculated')
            self.assertEqual(row['daily_observation_count'], 20)
            self.assertIn('daily', row['calculation_basis'].lower())
            self.assertIn('hkma.gov.hk',row['source_url'])
            archive = list(Path(folder).glob('*.json'))
            self.assertTrue(archive)
            self.assertIn('2026-10-30', archive[0].read_text())
        self.assertEqual(self.rows,original)

    def test_published_month_is_never_replaced_and_current_month_is_not_added(self):
        published = self.rows + macro.parse_records('hkma_hibor', [dict(end_of_month='2026-10',ir_1m=2.7,ir_3m=3.2)], '2026-11-03')
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.module.supplement(published,folder,'2026-11-03',lambda _:self.fail('No fetch needed')),[])
            self.assertEqual(self.module.supplement(self.rows,folder,'2026-10-30',lambda _:self.fail('No fetch needed')),[])

    def test_missing_duplicate_future_null_and_wrong_overlap_fail_closed(self):
        variants = [self.records[:-2]+self.records[-1:], self.records+[self.records[0]],
            self.records+[dict(end_of_date='2026-11-04',hibor_fixing_1m=2)],
            [dict(r,hibor_fixing_1m=None) if r['end_of_date']=='2026-10-02' else r for r in self.records],
            [dict(r,hibor_fixing_1m=4) if r['end_of_date'].startswith('2026-09') else r for r in self.records]]
        for records in variants:
            with self.subTest(records=records[-1]), tempfile.TemporaryDirectory() as folder:
                with self.assertRaises((ValueError,RuntimeError)):
                    self.module.supplement(self.rows,folder,'2026-11-03',self.fetcher(records))
                self.assertFalse(list(Path(folder).glob('*.json')))

    def test_calendar_must_cover_reference_year(self):
        self.calendar['vcalendar'][0]['vevent'] = []
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            self.module.supplement(self.rows,folder,'2026-11-03',self.fetcher())

    def test_future_as_of_is_clamped_to_actual_hong_kong_date(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = self.module.supplement(self.rows,folder,'2030-01-01',self.fetcher())
            self.assertEqual([r['period'] for r in rows],['2026-10'])

    def test_last_calendar_day_has_not_yet_closed_even_with_future_as_of(self):
        with patch.object(self.module,'_today',return_value=dt.date(2026,10,31)), tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.module.supplement(self.rows,folder,'2026-11-03',lambda _:self.fail('October is still open')),[])

    def test_api_failure_uses_fresh_date_validated_official_html(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = self.module.supplement(self.rows,folder,'2026-11-03',self.fetcher(api_error=OSError('HTTP405')))
            self.assertAlmostEqual(rows[0]['value'],2.7688455,places=10)
            self.assertIn('html',rows[0]['fetch_mode'])
            self.assertIn('HTTP405',rows[0]['source_fallback_reason'])
            self.assertIn('ms-20261030',next(Path(folder).glob('*.json')).read_text())

    def test_wrong_html_date_cannot_reuse_old_archive_as_fresh_data(self):
        with tempfile.TemporaryDirectory() as folder:
            prior = Path(folder)/'hkma_hibor_daily_supplement.json'
            prior.write_text('last successful raw source')
            with self.assertRaises((ValueError,RuntimeError)):
                self.module.supplement(self.rows,folder,'2026-11-03',self.fetcher(api_error=OSError('HTTP405'),wrong_html_date=True))
            self.assertEqual(prior.read_text(),'last successful raw source')


if __name__ == '__main__': unittest.main()
