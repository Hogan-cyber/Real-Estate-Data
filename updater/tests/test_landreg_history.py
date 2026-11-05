"""Official Land Registry history, deed scope and archive failure safeguards."""
import datetime as dt
import calendar
import hashlib
import json
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_landreg_collector as lr


def payload(rows, url='https://www.landreg.gov.hk/datagovhk/202609_data.json'):
    return {'url': url, 'body': json.dumps(rows)}


def deeds(year=2026, month=9, totals=True):
    rows = [{'Year':year, 'Month':month,
             'Description':f'Number of {district} deeds received for registration (ASP Building Units)',
             'Units':str(value), 'Consideration (nearest $ million)':'-'}
            for district,value in [('Urban',3329),('New Territories',3109)]]
    # Unit counts are deliberately different from agreement/document counts.
    rows.append({'Year':year,'Month':month,'Description':'Number of Urban ASP of Building Units (Unit Involved)',
                 'Units':'3653','Consideration (nearest $ million)':'-'})
    for category, values in (
        ('Building Mortgages/Building Legal Charges', (1, 1)),
        ('Other Mortgages/Legal Charges', (3775, 4059)),
        ('Receipts/Discharges/Releases', (3419, 3898)),
    ):
        for district, value in zip(('Urban', 'New Territories'), values):
            rows.append({'Year': year, 'Month': month,
                         'Description': f'Number of {district} deeds received for registration for {category}',
                         'Units': f'{value:,}', 'Consideration (nearest $ million)': '-'})
        if totals:
            rows.append({'Year': year, 'Month': month,
                         'Description': f'Total Number of Urban & New Territories deeds received for registration for {category}',
                         'Units': sum(values)})
    if totals:
        for district, value in (('Urban', 3776), ('New Territories', 4060), ('Urban & New Territories', 7836)):
            rows.append({'Year': year, 'Month': month,
                         'Description': f'Sub-total (5)+(6) of {district}', 'Units': value})
    return rows


def release_catalog(period='2026-09'):
    year, month = map(int, period.split('-'))
    published = dt.date(year + (month == 12), month % 12 + 1, 3)
    return {'url': lr.PRESS_URL, 'body': 'var pressReleaseJson=' + json.dumps([{'items': [{
        'title': 'Land Registry releases statistics for ' + calendar.month_name[month],
        'date': published.strftime('%Y/%m/%d'),
        'url': f'https://www.info.gov.hk/gia/general/{published:%Y%m/%d}/P{published:%Y%m%d}00276.htm',
    }]}])}


class LandRegistryHistoryTests(unittest.TestCase):
    def test_residential_history_does_not_drop_older_blocks_or_current_revisions(self):
        script = ('var agtP6="2026"; var agtP1="2002-2005"; '
                  'var blocks={"agt-primary":agtP6,"agt-pri-1":agtP1}; '
                  'var jsonInterPath="/json/monthly_agt-pri/";')

        def get(url, cache):
            if url == lr.SCRIPT_URL:
                return {'url': url, 'body': script}
            current = '/agt-primary/' in url
            dates = [(2026, 9)] if current else [(2002, 1), (2026, 9)]
            rows = []
            for year, month in dates:
                row = {'Year': year, 'Month': month}
                for metric, key, *_, table in lr.SERIES:
                    if url.endswith(table + '.json'):
                        value = 1 if '_primary_' in metric else 2 if '_secondary_' in metric else 3
                        row[key] = value * (10 if current else 1)
                rows.append(row)
            return payload(rows, url)

        with patch.object(lr, '_get', side_effect=get), \
             patch.object(lr, '_release_supplement', side_effect=lambda rows, *args: rows), \
             patch.object(lr, '_collect_instruments', return_value=[]):
            rows = lr.collect(as_of='2026-11-04')
        self.assertEqual({r['period'] for r in rows}, {'2002-01', '2026-09'})
        self.assertEqual(len(rows), 12)
        total = next(r for r in rows if r['period'] == '2026-09' and r['metric_id'] == 'hk_residential_sales_count')
        self.assertEqual(total['value'], 30)

    def test_partial_current_month_never_borrows_components_from_older_revision(self):
        script = ('var agtP6="2026"; var agtP1="2021-2025"; '
                  'var blocks={"agt-primary":agtP6,"agt-pri-1":agtP1}; '
                  'var jsonInterPath="/json/monthly_agt-pri/";')
        def get(url, cache):
            if url == lr.SCRIPT_URL:
                return {'url': url, 'body': script}
            current = '/agt-primary/' in url
            rows = []
            for month in ([9] if current else [8, 9]):
                row = {'Year': 2026, 'Month': month}
                for metric, key, *_, table in lr.SERIES:
                    if url.endswith(table + '.json'):
                        value = 1 if '_primary_' in metric else 2 if '_secondary_' in metric else 3
                        row[key] = (None if '_primary_' in metric else value * 10) if current else value
                rows.append(row)
            return payload(rows, url)
        with patch.object(lr, '_get', side_effect=get), \
             patch.object(lr, '_release_supplement', side_effect=lambda rows, *args: rows):
            rows = lr._collect_sales(as_of='2026-11-04')
        latest = {r['metric_id']: r for r in rows if r['period'] == '2026-09'}
        for metric in ('hk_residential_primary_sales_count', 'hk_residential_primary_sales_value'):
            self.assertIsNone(latest[metric]['value'])
            self.assertIn('/agt-primary/', latest[metric]['source_url'])
            self.assertTrue(latest[metric]['missing_reason'])
        # Pipeline's ordinary key merge must replace the previous value with
        # explicit missingness, never resurrect the old revision as a component.
        prior = {('hk_residential_primary_sales_count', '2026-09'): {'value': 1}}
        prior.update({(r['metric_id'], r['period']): r for r in rows})
        self.assertIsNone(prior[('hk_residential_primary_sales_count', '2026-09')]['value'])
        self.assertEqual(latest['hk_residential_sales_count']['value'], 30)
        self.assertEqual(latest['hk_residential_secondary_sales_count']['value'], 20)
        self.assertTrue(all(r.get('refresh_warning') for r in latest.values()))

    def test_deeds_are_all_property_instruments_and_no_amount_is_invented(self):
        rows = lr._parse_instruments(payload(deeds()), expected_period='2026-09')
        by_id = {r['metric_id']: r for r in rows}
        self.assertEqual(by_id['hk_all_property_mortgage_deeds_count']['value'], 7836)
        self.assertEqual(by_id['hk_all_property_discharge_deeds_count']['value'], 7317)
        self.assertEqual(by_id['hk_all_building_sales_count']['value'], 6438)
        self.assertEqual(len(rows), 5)
        for row in rows[:4]:
            self.assertEqual(row['unit'], 'deeds')
            self.assertIn('非住宅', row['scope'])
            self.assertIn('不是', row['note'])
            self.assertEqual(row['category'], 'registration')
            self.assertEqual(row['property_type'], 'All property types')
            self.assertIsNone(row['published_date'])

    def test_merged_sales_count_reconciles_even_if_amount_breakdown_is_missing(self):
        date = dt.date(2026, 9, 30)
        series = {metric: {date: (None, 'current.json', None)} for metric, *_ in lr.SERIES}
        for metric, value in [('hk_residential_sales_count', 30),
                              ('hk_residential_primary_sales_count', 10),
                              ('hk_residential_secondary_sales_count', 20)]:
            series[metric][date] = (value, 'current.json', None)
        lr._validate_sales_month(series, date)
        series['hk_residential_sales_count'][date] = (31, 'current.json', None)
        with self.assertRaisesRegex(ValueError, 'components disagree'):
            lr._validate_sales_month(series, date)
        series['hk_residential_primary_sales_count'][date] = (None, 'current.json', None)
        series['hk_residential_secondary_sales_count'][date] = (32, 'current.json', None)
        with self.assertRaisesRegex(ValueError, 'components disagree'):
            lr._validate_sales_month(series, date)

    def test_old_district_only_schema_accepts_integer_whitespace_zero(self):
        rows = deeds(1993, 4, totals=False)
        for row in rows:
            row['Consideration ($)'] = row.pop('Consideration (nearest $ million)')
            row['Units'] = ' 0 ' if 'Building Mortgages/' in row['Description'] else int(row['Units'].replace(',', ''))
        result = lr._parse_instruments(payload(rows), expected_period='1993-04')
        self.assertEqual(result[0]['value'], 0)
        self.assertEqual(result[2]['value'], 7834)

    def test_official_archives_empty_trailing_spreadsheet_rows_are_ignored(self):
        rows = deeds(2015, 1, totals=False) + [
            {'Year': ''},
            {'Year': None, 'Month': None, 'Description': '', 'Units': '', 'Consideration (nearest $ million)': ''},
        ]
        result = lr._parse_instruments(payload(rows), expected_period='2015-01')
        self.assertEqual(result[2]['value'], 7836)
        with self.assertRaises(ValueError):
            lr._parse_instruments(payload(rows + [{'Year': '', 'Units': '5'}]))

    def test_wrong_month_duplicate_missing_or_mismatched_total_rejected(self):
        cases = [deeds(month=8), deeds() + [deeds()[0]], deeds()[1:]]
        bad_total = deeds()
        bad_total[-1]['Units'] = 9999
        cases.append(bad_total)
        bad_value = deeds()
        bad_value[0]['Units'] = '-'
        cases.append(bad_value)
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                lr._parse_instruments(payload(rows), expected_period='2026-09')

    def test_partial_archive_failure_is_visible_and_does_not_fabricate_missing_month(self):
        def get(url, cache):
            if url == lr.PRESS_URL:
                return release_catalog()
            return payload(deeds(month=9), url)

        def archive(url, cache, **kwargs):
            if '202608' in url:
                raise RuntimeError('archive offline')
            return payload(deeds(month=7), url)

        with patch.object(lr, '_get', side_effect=get), patch.object(lr, '_get_archive', side_effect=archive):
            rows = lr._collect_instruments(None, dt.date(2026, 10, 5), start=dt.date(2026, 7, 31))
        self.assertEqual({r['period'] for r in rows}, {'2026-07', '2026-09'})
        self.assertTrue(all('2026-08' in r['refresh_warning'] for r in rows))
        self.assertTrue(all('archive offline' in r['refresh_warning'] for r in rows))
        self.assertTrue(all(r.get('refresh_failed_periods') == ['2026-08'] for r in rows))
        self.assertTrue(all(set(r.get('refresh_failed_metric_ids', [])) == {
            'hk_all_property_building_mortgage_deeds_count', 'hk_all_property_other_mortgage_deeds_count',
            'hk_all_property_mortgage_deeds_count', 'hk_all_property_discharge_deeds_count',
            'hk_all_building_sales_count'} for r in rows))

    def test_stale_moving_month_is_advanced_from_official_release_catalog(self):
        def get(url, cache):
            if url == lr.PRESS_URL:
                return release_catalog('2026-10')
            return payload(deeds(month=8 if url == lr.INSTRUMENT_URL else 10), url)
        def archive(url, cache, **kwargs):
            return payload(deeds(month=int(url.rsplit('/', 1)[-1][4:6])), url)
        with patch.object(lr, '_get', side_effect=get), patch.object(lr, '_get_archive', side_effect=archive):
            rows = lr._collect_instruments(None, dt.date(2026, 11, 4), start=dt.date(2026, 8, 31))
        self.assertEqual({r['period'] for r in rows}, {'2026-08', '2026-09', '2026-10'})
        self.assertTrue(all('/stat1026/' in r['source_url'] for r in rows if r['period'] == '2026-10'))

    def test_future_moving_numeric_month_is_rejected_with_warning(self):
        def get(url, cache):
            if url == lr.PRESS_URL:
                return release_catalog('2026-10')
            return payload(deeds(month=12 if url == lr.INSTRUMENT_URL else 10), url)
        with patch.object(lr, '_get', side_effect=get):
            rows = lr._collect_instruments(None, dt.date(2026, 11, 4), start=dt.date(2026, 10, 31))
        self.assertEqual({r['period'] for r in rows}, {'2026-10'})
        self.assertTrue(all('future' in r.get('refresh_warning', '').lower() for r in rows))

    def test_all_instrument_failures_expose_structured_scope_on_sales_rows(self):
        sale = {'metric_id': 'hk_residential_sales_count', 'period': '2026-10', 'date': '2026-10-31', 'value': 4512}
        def get(url, cache):
            if url == lr.PRESS_URL:
                return release_catalog('2026-10')
            raise RuntimeError('no instrument source available')
        with patch.object(lr, '_collect_sales', return_value=[sale]), patch.object(lr, '_get', side_effect=get), \
             patch.object(lr, '_get_archive', side_effect=RuntimeError('archive offline')):
            rows = lr.collect(as_of='2026-11-04')
        self.assertEqual(len(rows), 1)
        self.assertIn('2026-10', rows[0].get('refresh_failed_periods', []))
        self.assertEqual(len(rows[0].get('refresh_failed_metric_ids', [])), 5)
        self.assertNotIn(sale['metric_id'], rows[0]['refresh_failed_metric_ids'])

    def test_recent_archive_cache_rechecks_but_old_archive_respects_ttl(self):
        url = 'https://www.landreg.gov.hk/datagovhk/200201_data.json'
        with tempfile.TemporaryDirectory() as folder:
            cached = payload(deeds(2002, 1), url)
            cached['checked_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
            name = hashlib.sha256(url.encode()).hexdigest() + '.json'
            Path(folder, name).write_text(json.dumps(cached))
            with patch.object(lr, '_get', side_effect=RuntimeError('must recheck')):
                self.assertEqual(lr._get_archive(url, folder, recheck=False), cached)
                with self.assertRaisesRegex(RuntimeError, 'must recheck'):
                    lr._get_archive(url, folder, recheck=True)

    def test_expired_archive_cache_failure_cannot_relabel_old_data_as_checked(self):
        url = 'https://www.landreg.gov.hk/datagovhk/200201_data.json'
        with tempfile.TemporaryDirectory() as folder:
            cached = payload(deeds(2002, 1), url)
            cached['checked_at'] = '2003-01-01T00:00:00+00:00'
            name = hashlib.sha256(url.encode()).hexdigest() + '.json'
            Path(folder, name).write_text(json.dumps(cached))
            with patch.object(lr, '_get', side_effect=RuntimeError('source unavailable')):
                with self.assertRaisesRegex(RuntimeError, 'source unavailable'):
                    lr._get_archive(url, folder)
            self.assertEqual(json.loads(Path(folder, name).read_text())['checked_at'], cached['checked_at'])

    def test_conflicting_latest_sources_omit_latest_month_and_preserve_history(self):
        def get(url, cache):
            if url == lr.PRESS_URL:
                return release_catalog()
            data = deeds(month=9, totals=False)
            if 'stat0926' in url:
                data[0]['Units'] = 100
            return payload(data, url)
        with patch.object(lr, '_get', side_effect=get), \
             patch.object(lr, '_get_archive', side_effect=lambda url, cache, **kw: payload(deeds(month=8), url)):
            rows = lr._collect_instruments(None, dt.date(2026, 10, 5), start=dt.date(2026, 8, 31))
        self.assertEqual({r['period'] for r in rows}, {'2026-08'})
        self.assertTrue(all('disagree' in r['refresh_warning'] for r in rows))
        self.assertTrue(all(r.get('refresh_failed_periods') == ['2026-09'] for r in rows))


if __name__ == '__main__':
    unittest.main()
