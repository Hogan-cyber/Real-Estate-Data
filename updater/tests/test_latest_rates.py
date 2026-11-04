import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_latest_rates as rates

AS_OF = '2026-11-04'
NOW = '2026-11-04T06:00:00+00:00'
PRIME = [{'effect_date': '2025-10-31', 'best_lending_rate': 5.0},
         {'effect_date': '2025-09-19', 'best_lending_rate': 5.125}]
HIBOR = [{'end_of_day': '2026-10-30', 'ir_1m': 2.70923, 'ir_3m': 3.21256}]


def payload(records):
    return json.dumps({'header': {'success': True}, 'result': {'records': records}}).encode()


def official_rows(kind='hibor', records=None):
    return rates.parse_records(kind, records if records is not None else HIBOR if kind == 'hibor' else PRIME,
                               AS_OF, NOW, rates.TABLES[kind]['api'])


def source_fetch(url):
    if url.startswith(rates.PRIME_API_URL):
        return payload([] if parse_qs(urlparse(url).query).get('offset', ['0']) != ['0'] else PRIME)
    if url.startswith(rates.HIBOR_API_URL):
        if parse_qs(urlparse(url).query).get('segment') != ['hibor.fixing']:
            raise AssertionError('Must use the fixing segment')
        return payload([] if parse_qs(urlparse(url).query).get('offset', ['0']) != ['0'] else HIBOR)
    if url.startswith(rates.API_URL):
        return payload([{'end_of_date': '2026-11-03', 'hibor_fixing_1m': 2.68}])
    raise OSError('Unrecognised source ' + url)


class LatestRatesTests(unittest.TestCase):
    def test_government_only_migration_drops_unverified_private_source_on_outage(self):
        private = dict(metric_id='hk_prime_rate_hsbc_effective', date='2025-10-31', value=5,
                       source_id='hsbc_prime_effective', source_url='https://www.hsbc.com.hk/rates',
                       checked_at='2026-11-03T12:00:00+00:00')
        official = dict(private, source_url=rates.PRIME_API_URL)
        def fail(url):
            raise OSError('offline')
        with tempfile.TemporaryDirectory() as folder:
            rows, statuses, errors = rates.refresh([private], [{'source_id': 'hsbc_prime_effective',
                'last_success': private['checked_at']}], folder, AS_OF, NOW, fail)
            kept, _, _ = rates.refresh([official], [], folder, AS_OF, NOW, fail)
        self.assertEqual(rows, [], 'Private-source cache must not bypass government-only collection')
        self.assertEqual(kept, [official])
        self.assertEqual(kept[0]['checked_at'], private['checked_at'])
        self.assertTrue(errors)
        self.assertTrue(all(s['status'].startswith('Retained') for s in statuses))
        self.assertIsNone(next(s['last_success'] for s in statuses if s['source_id'] == 'hsbc_prime_effective'))

    def test_refresh_requests_government_only_and_keeps_each_reference_date(self):
        requested = []
        def fetch(url):
            requested.append(url)
            return source_fetch(url)
        private = dict(metric_id='hk_hibor_3m_daily', date='2026-11-04', value=3.2,
                       source_id='hk_rates_hibor', source_url='https://www.hkab.org.hk/rates')
        with tempfile.TemporaryDirectory() as folder:
            rows, statuses, errors = rates.refresh([private], [], folder, AS_OF, NOW, fetch)
        self.assertEqual(errors, [])
        self.assertTrue(all(urlparse(u).hostname == 'api.hkma.gov.hk' for u in requested))
        latest = {r['metric_id']: r for r in sorted(rows, key=lambda r: r['date'])}
        self.assertEqual(latest['hk_prime_rate_hsbc_effective']['date'], '2025-10-31')
        self.assertEqual(latest['hk_prime_rate_hsbc_effective']['value'], 5)
        self.assertEqual(latest['hk_prime_rate_hsbc_effective']['frequency'], 'E')
        self.assertEqual(latest['hk_hibor_1m_daily']['date'], '2026-11-03')
        self.assertEqual(latest['hk_hibor_3m_daily']['date'], '2026-10-30')
        self.assertEqual(latest['hk_hibor_3m_daily']['value'], 3.21256)
        self.assertTrue(all(r['source_name'] == 'Hong Kong Monetary Authority' for r in rows))
        self.assertTrue(all(s['status'] == 'Verified' for s in statuses))

    def test_official_null_tenor_is_not_filled_from_other_tenor(self):
        rows = official_rows(records=[dict(HIBOR[0], ir_3m=None)])
        self.assertEqual([(r['metric_id'], r['value']) for r in rows], [('hk_hibor_1m_daily', 2.70923)])
        self.assertEqual(rows[0]['frequency'], 'D')
        self.assertEqual(rows[0]['source_table'], '6.3.3')

    def test_wholly_missing_tenor_warns_and_retains_only_prior_official_history(self):
        prior = official_rows()
        partial = official_rows(records=[dict(HIBOR[0], ir_3m=None)])
        with tempfile.TemporaryDirectory() as folder, patch.object(rates, 'collect_table', return_value=partial):
            rows, warnings = rates.collect_hibor(folder, AS_OF, NOW, source_fetch)
        self.assertFalse(any(r['metric_id'] == 'hk_hibor_3m_daily' for r in rows))
        self.assertTrue(any('3M' in warning for warning in warnings))
        with tempfile.TemporaryDirectory() as folder, patch.object(rates, 'collect_hibor', return_value=(rows, warnings)):
            kept, statuses, errors = rates.refresh(prior, [], folder, AS_OF, NOW, source_fetch)
        old_3m = next(r for r in kept if r['metric_id'] == 'hk_hibor_3m_daily')
        self.assertEqual((old_3m['date'], old_3m['value']), ('2026-10-30', 3.21256))
        self.assertTrue(errors)
        self.assertEqual(next(s['status'] for s in statuses if s['source_id'] == 'hk_rates_hibor'), 'Review: partial source refresh')

    def test_source_schema_invalid_values_future_and_duplicate_dates_fail(self):
        invalid = [[dict(HIBOR[0], ir_3m=True)], [dict(HIBOR[0], ir_1m=float('nan'))],
                   [dict(HIBOR[0], end_of_day='2026-11-05')], [HIBOR[0], HIBOR[0]],
                   [{'end_of_day': '2026-10-30', 'ir_1m': 2.7}]]
        for records in invalid:
            with self.subTest(records=records), self.assertRaises((ValueError, KeyError)):
                official_rows(records=records)

    def test_daily_monetary_stats_conflicts_do_not_overwrite_official_fixings(self):
        def fetch(url):
            if url.startswith(rates.API_URL):
                return payload([{'end_of_date': '2026-10-30', 'hibor_fixing_1m': 9.0}])
            return source_fetch(url)
        with tempfile.TemporaryDirectory() as folder, self.assertRaisesRegex(ValueError, 'conflict'):
            rates.collect_hibor(folder, AS_OF, NOW, fetch)

    def test_later_history_cannot_overwrite_conflicting_retained_official_fixing(self):
        prior = official_rows()
        conflicting = dict(prior[0], value=3.0)
        with tempfile.TemporaryDirectory() as folder, patch.object(rates, 'collect_hibor', return_value=([conflicting], [])):
            rows, statuses, errors = rates.refresh(prior, [], folder, AS_OF, NOW, source_fetch)
        kept = [r for r in rows if r['source_id'] == 'hk_rates_hibor']
        self.assertEqual(kept, prior)
        self.assertTrue(any('conflict' in error for error in errors))
        self.assertEqual(next(s['status'] for s in statuses if s['source_id'] == 'hk_rates_hibor'), 'Retained: refresh failed')

    def test_transient_wrong_date_html_is_rechecked_before_acceptance(self):
        expected = ({'end_of_date': '2026-10-05', 'hibor_fixing_1m': 2.9422}, {'html': 'checked'})
        with patch.object(rates, '_html_day', side_effect=[ValueError('wrong source date'), expected]) as source:
            self.assertEqual(rates.verified_html_day(dt.date(2026, 10, 5), lambda url: b''), expected)
        self.assertEqual(source.call_count, 2)

    def test_daily_api_outage_uses_dated_government_html_without_inventing_3m(self):
        def fetch(url):
            if url == rates.CALENDAR_URL:
                return b'{}'
            if url.startswith(rates.API_URL):
                raise OSError('daily API down')
            return source_fetch(url)
        dates = {'2026-10': {dt.date(2026, 10, 30)}, '2026-11': {dt.date(2026, 11, 3)}}
        def day(date, fetch):
            return ({'end_of_date': date.isoformat(), 'hibor_fixing_1m': 2.68 if date.month == 11 else 2.70923},
                    {'url': 'https://www.hkma.gov.hk/' + date.isoformat(), 'html': '<html>fixture</html>'})
        with tempfile.TemporaryDirectory() as folder, patch.object(rates, '_calendar', return_value=(dates, {})), patch.object(rates, '_html_day', side_effect=day):
            rows, warnings = rates.collect_hibor(folder, AS_OF, NOW, fetch)
        self.assertEqual(warnings, [])
        self.assertEqual([(r['date'], r['value']) for r in rows if r['metric_id'] == 'hk_hibor_3m_daily'], [('2026-10-30', 3.21256)])
        self.assertEqual(len(rows), 3)

    def test_workbook_fallback_retains_official_basis_and_rejects_changed_columns(self):
        import xlrd
        from types import SimpleNamespace
        class Sheet:
            nrows = 20
            def __init__(self, kind):
                self.types = {}
                self.cells = {(3, 0): 'Table 6.3.3 : Daily figures', (0, 0): 'Interest Settlement Rates',
                              (7, 0): 'As at 11:15 am', (7, 5): '1-month', (7, 6): '3-month',
                              (14, 0): 46325.0, (14, 5): 2.70923, (14, 6): 3.21256}
                if kind == 'prime':
                    self.cells = {(3, 0): 'Table 6.4.1 : Rates as at effective dates', (7, 10): 'Best',
                                  (8, 10): 'lending', (9, 10): 'rate2', (14, 0): 45961.0, (14, 10): 5.0,
                                  (19, 0): 'Hongkong and Shanghai Banking Corporation Limited'}
            def cell_value(self, i, j): return self.cells.get((i, j), '')
            def row_values(self, i): return [self.cell_value(i, j) for j in range(11)]
            def cell(self, i, j):
                value = self.cell_value(i, j)
                return SimpleNamespace(value=value, ctype=self.types.get((i, j),
                    xlrd.XL_CELL_DATE if (i, j) == (14, 0)
                    else xlrd.XL_CELL_NUMBER if isinstance(value, (int, float)) else xlrd.XL_CELL_TEXT))
        for kind in ('prime', 'hibor'):
            sheet = Sheet(kind)
            book = SimpleNamespace(datemode=0, sheet_by_name=lambda name: sheet)
            def fetch(url):
                if url.endswith('.xls'): return b'workbook'
                raise OSError('API offline')
            with tempfile.TemporaryDirectory() as folder, patch.object(xlrd, 'open_workbook', return_value=book):
                rows = rates.collect_table(kind, folder, AS_OF, NOW, fetch)
                self.assertTrue(all(r['fetch_mode'] == 'automatic_excel' and r['source_url'].startswith('https://www.hkma.gov.hk/') for r in rows))
                self.assertEqual(rows[-1]['date'], '2025-10-31' if kind == 'prime' else '2026-10-30')
                if kind == 'hibor':
                    sheet.cells[(14, 5)] = 42
                    sheet.types[(14, 5)] = xlrd.XL_CELL_ERROR
                    missing = rates.parse_excel(kind, b'fixture', AS_OF, NOW)
                    self.assertEqual([r['metric_id'] for r in missing], ['hk_hibor_3m_daily'])
                sheet.cells[(3, 0)] = 'Period average figures'
                with self.assertRaisesRegex(ValueError, 'title/basis'):
                    rates.collect_table(kind, folder, AS_OF, NOW, fetch)

    def test_excel_error_codes_cannot_become_interest_rates(self):
        import xlrd
        from types import SimpleNamespace
        for cell, expected in [(SimpleNamespace(ctype=xlrd.XL_CELL_ERROR, value=42), None),
                               (SimpleNamespace(ctype=xlrd.XL_CELL_EMPTY, value=''), None),
                               (SimpleNamespace(ctype=xlrd.XL_CELL_BLANK, value=''), None),
                               (SimpleNamespace(ctype=xlrd.XL_CELL_TEXT, value='N.A. '), None),
                               (SimpleNamespace(ctype=xlrd.XL_CELL_NUMBER, value=0), 0)]:
            with self.subTest(cell=cell):
                self.assertEqual(rates.excel_rate_value(cell), expected)
        for cell in [SimpleNamespace(ctype=xlrd.XL_CELL_ERROR, value=7),
                     SimpleNamespace(ctype=xlrd.XL_CELL_BOOLEAN, value=1),
                     SimpleNamespace(ctype=xlrd.XL_CELL_TEXT, value='5.0'),
                     SimpleNamespace(ctype=xlrd.XL_CELL_TEXT, value='unexpected')]:
            with self.subTest(cell=cell), self.assertRaises(ValueError):
                rates.excel_rate_value(cell)

    def test_exports_keep_daily_data_out_of_monthly_table(self):
        from hk_property_data.database import build_database
        from hk_property_data.export_excel import build_excel, validate_excel
        import sqlite3
        rows = official_rows()
        dataset = {'checked_at': NOW, 'as_of': AS_OF, 'observations': [], 'rate_observations': rows,
                   'source_status': [], 'pdf_observations': [], 'revisions': []}
        with tempfile.TemporaryDirectory() as folder:
            dbpath = build_database(dataset, Path(folder) / 'rates.sqlite')
            with sqlite3.connect(dbpath) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM observations').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT metric_id,date,value FROM rate_observations ORDER BY metric_id').fetchall(),
                                 [(r['metric_id'], r['date'], r['value']) for r in rows])
            path = Path(folder) / 'rates.xlsx'
            build_excel(dataset, path)
            self.assertEqual(validate_excel(path, dataset)['rate_rows'], 2)


if __name__ == '__main__':
    unittest.main()
