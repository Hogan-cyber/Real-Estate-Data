import json
from pathlib import Path
import sys
import tempfile
import unittest
import datetime as dt
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_latest_rates as rates

HTML = b'''<h2>Rates as at 11:15a.m.<br/>Hong Kong Time on 2026-11-3.</h2>
<div>Maturity</div><div>HKD Interest Settlement Rates</div>
<div>1 Month</div><div>2.68000</div><div>3 Months</div><div>3.21399</div>'''


class LatestRatesTests(unittest.TestCase):
    def test_transient_wrong_date_html_is_rechecked_before_acceptance(self):
        expected=({'end_of_date':'2026-10-05','hibor_fixing_1m':2.9422},{'html':'checked'})
        with patch.object(rates,'_html_day',side_effect=[ValueError('wrong source date'),expected]) as source:
            self.assertEqual(rates.verified_html_day(dt.date(2026,10,5),lambda url:b''),expected)
        self.assertEqual(source.call_count,2)

    def test_api_outage_uses_dated_official_html_for_october(self):
        def fetch(url):
            if url==rates.HKAB_URL: return HTML
            if url==rates.CALENDAR_URL: return b'{}'
            raise OSError('API down')
        dates={'2026-10':{dt.date(2026,10,30)},'2026-11':{dt.date(2026,11,3)}}
        def day(date,fetch):
            return {'end_of_date':date.isoformat(),'hibor_fixing_1m':2.68 if date.month==11 else 2.70923}, {'url':'https://www.hkma.gov.hk/'+date.isoformat(),'html':'<html>verified fixture</html>'}
        with tempfile.TemporaryDirectory() as folder, patch.object(rates,'_calendar',return_value=(dates,{})), patch.object(rates,'_html_day',side_effect=day):
            rows,warnings=rates.collect_hibor(folder,'2026-11-04','2026-11-04T01:00:00+00:00',fetch)
        self.assertEqual(warnings,[])
        self.assertEqual(next(r['value'] for r in rows if r['date']=='2026-10-30'),2.70923)
        self.assertEqual(len(rows),3)

    def test_daily_dates_and_tenors_are_not_monthly_averages(self):
        rows = rates.parse_hkab(HTML, '2026-11-04', '2026-11-04T01:00:00+00:00')
        self.assertEqual([(r['metric_id'], r['date'], r['value']) for r in rows], [
            ('hk_hibor_1m_daily', '2026-11-03', 2.68), ('hk_hibor_3m_daily', '2026-11-03', 3.21399)])
        self.assertTrue(all(r['frequency'] == 'D' and r['status'] == 'Published' for r in rows))
        with self.assertRaises(ValueError):
            rates.parse_hkab(HTML, '2026-11-02', '2026-11-02T01:00:00+00:00')
        with self.assertRaises(ValueError):
            rates.parse_hkab(HTML.replace(b'3 Months', b'6 Months'), '2026-11-04', '2026-11-04T01:00:00+00:00')

    def test_merge_preserves_october_and_checks_source_conflicts(self):
        day = rates.parse_hkab(HTML, '2026-11-04', '2026-11-04T01:00:00+00:00')[0]
        october = dict(day, date='2026-10-30', value=2.70923)
        merged = rates.merge_rates([october], [day])
        self.assertEqual([r['date'] for r in merged], ['2026-10-30', '2026-11-03'])
        with self.assertRaises(ValueError):
            rates.merge_rates([day], [dict(day, value=3, source_name='Conflicting source')], check_conflicts=True)

    def test_failed_daily_sources_keep_dates_and_do_not_claim_a_new_check(self):
        prior = rates.parse_hkab(HTML, '2026-11-04', '2026-11-03T12:00:00+00:00')
        def fail(url):
            raise OSError('offline')
        with tempfile.TemporaryDirectory() as folder:
            rows, statuses, errors = rates.refresh(prior, [], Path(folder), '2026-11-04', '2026-11-04T01:00:00+00:00', fail)
        self.assertEqual(rows, prior)
        self.assertTrue(errors)
        self.assertTrue(all(s['status'].startswith('Retained') for s in statuses))
        self.assertEqual(rows[0]['checked_at'], '2026-11-03T12:00:00+00:00')

    def test_later_hkma_history_cannot_overwrite_conflicting_retained_hkab_fixing(self):
        prior = rates.parse_hkab(HTML, '2026-11-04', '2026-11-03T12:00:00+00:00')
        conflicting = dict(prior[0],value=3.0,source_name='Hong Kong Monetary Authority')
        next_day = dict(prior[0],date='2026-11-04',value=2.7)
        with tempfile.TemporaryDirectory() as folder, patch.object(rates,'collect_hibor',return_value=([conflicting,next_day],[])):
            rows,statuses,errors = rates.refresh(prior,[],folder,'2026-11-04','2026-11-04T12:00:00+00:00',lambda url: b'no prime feed')
        self.assertEqual(rows,prior)
        self.assertTrue(any('conflict' in error for error in errors))
        self.assertEqual(next(s['status'] for s in statuses if s['source_id']=='hk_rates_hibor'),'Retained: refresh failed')

    def test_exports_keep_daily_data_out_of_monthly_table(self):
        from hk_property_data.database import build_database
        from hk_property_data.export_excel import build_excel, validate_excel
        import sqlite3
        rows = rates.parse_hkab(HTML, '2026-11-04', '2026-11-04T01:00:00+00:00')
        dataset = {'checked_at':'2026-11-04T01:00:00+00:00','as_of':'2026-11-04',
                   'observations': [], 'rate_observations': rows, 'source_status': [], 'pdf_observations': [], 'revisions': []}
        with tempfile.TemporaryDirectory() as folder:
            dbpath = build_database(dataset, Path(folder)/'rates.sqlite')
            with sqlite3.connect(dbpath) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM observations').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT metric_id,date,value FROM rate_observations ORDER BY metric_id').fetchall(),
                    [(r['metric_id'],r['date'],r['value']) for r in rows])
            path = Path(folder)/'rates.xlsx'
            build_excel(dataset, path)
            self.assertEqual(validate_excel(path, dataset)['rate_rows'], 2)


if __name__ == '__main__':
    unittest.main()
