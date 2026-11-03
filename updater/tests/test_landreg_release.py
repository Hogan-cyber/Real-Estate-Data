import copy
import datetime as dt
import json
import hashlib
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_landreg_collector as lr


RELEASE_URL = 'https://www.info.gov.hk/gia/general/202611/03/P2026110300276.htm'
ANNEX_URL = 'https://gia.info.gov.hk/general/202611/03/P2026110300276_557525_1_1793678584832.pdf'
TEXT = '''Table 5
THE LAND REGISTRY
Number of Sale and Purchase Agreements of residential building units and total consideration
from October 2025 to October 2026
Year 2025 2026
Month 10 11 12 1 2 3 4 5 6 7 8 9 10
Total No. 5,714 5,588 5,883 5,669 6,669 6,316 7,368 7,138 7,650 4,462 4,019 4,761 4,512
Total Consideration ($ million) 51,073 51,667 51,227 49,221 57,598 55,184 63,673 65,593 75,607 41,891 36,202 46,808 42,346
'''


def catalog():
    return 'var pressReleaseJson=' + json.dumps([{'year_title': '2026', 'items': [
        {'title': 'Land Registry releases statistics for October', 'date': '2026/11/03', 'url': RELEASE_URL},
        {'title': 'Land Registry releases Trading Fund Annual Report', 'date': '2026/11/04', 'url': 'ignore'},
    ]}]) + ';'


class LandRegistryReleaseTests(unittest.TestCase):
    def test_exact_totals_and_units_from_thirteen_month_table(self):
        data = lr._parse_release_table(TEXT, '2026-10')
        self.assertEqual(len(data), 13)
        self.assertEqual(data['2026-10'], (4512, 42346))
        self.assertEqual(data['2025-10'], (5714, 51073))

    def test_wrong_month_unit_count_and_duplicate_rows_fail(self):
        for broken in (TEXT.replace('Month 10 11', 'Month 9 11'),
                       TEXT.replace('$ million', '$ billion'),
                       TEXT.replace('4,512', '4,512 99'),
                       TEXT + 'Total No. 1 2 3\n',
                       TEXT.replace('October 2026', 'September 2026')):
            with self.subTest(text=broken), self.assertRaises(ValueError):
                lr._parse_release_table(broken, '2026-10')

    def test_catalog_ignores_nonmonthly_and_future_release(self):
        release = lr._latest_release(catalog(), dt.date(2026, 11, 3))
        self.assertEqual(release['period'], '2026-10')
        self.assertEqual(release['published_date'], '2026-11-03')
        self.assertIsNone(lr._latest_release(catalog(), dt.date(2026, 11, 2)))

    def test_legacy_catalog_url_does_not_prevent_checking_latest_release(self):
        body = catalog().replace('"items": [', '"items": [{"title":"Land Registry releases statistics for January", "date":"2005/02/02", "url":"http://legacy.example/old.htm"},')
        self.assertEqual(lr._latest_release(body, dt.date(2026, 11, 3))['url'], RELEASE_URL)

    def records(self):
        totals = lr._parse_release_table(TEXT, '2026-10')
        rows = []
        for period, values in totals.items():
            if period == '2026-10':
                continue
            for metric, value in zip(('hk_residential_sales_count', 'hk_residential_sales_value'), values):
                rows.append({'metric_id': metric, 'period': period, 'value': value,
                             'fetch_mode': 'automatic_json', 'source_url': 'current.json',
                             'published_date': None, 'note': 'Original JSON note'})
        return rows

    def mocks(self, table=TEXT):
        def get(url, cache):
            body = catalog() if url == lr.PRESS_URL else f'<a href="{ANNEX_URL}">Annex</a>'
            return {'url': url, 'body': body}
        return (patch.object(lr, '_get', side_effect=get),
                patch.object(lr, '_get_pdf', return_value={'body': b'%PDF fixture', 'url': ANNEX_URL}),
                patch.object(lr, '_annex_table_text', return_value=(table, 5)))

    def test_supplements_only_two_totals_with_exact_provenance(self):
        before = self.records()
        original = copy.deepcopy(before)
        a, b, c = self.mocks()
        with a, b, c:
            result = lr._release_supplement(before, None, dt.date(2026, 11, 3))
        self.assertEqual(before, original)
        self.assertEqual(result[:-2], original)
        newest = result[-2:]
        self.assertEqual({row['metric_id'] for row in newest},
                         {'hk_residential_sales_count', 'hk_residential_sales_value'})
        self.assertEqual([row['value'] for row in newest], [4512, 42346])
        for row in newest:
            self.assertEqual(row['published_date'], '2026-11-03')
            self.assertEqual(row['source_url'], ANNEX_URL)
            self.assertEqual(row['source_field'], 'Table 5, page 5')
            self.assertIn('primary/secondary', row['note'])
            self.assertNotIn('refresh_warning', row)

    def test_misaligned_overlap_is_not_accepted(self):
        rows = self.records()
        rows[-1]['value'] += 1
        a, b, c = self.mocks()
        with a, b, c, self.assertRaisesRegex(ValueError, 'overlap'):
            lr._release_supplement(rows, None, dt.date(2026, 11, 3))

    def test_current_json_never_replaced_by_rounded_headline_or_annex(self):
        rows = self.records() + [dict(self.records()[-2], period='2026-10', value=4512),
                                 dict(self.records()[-1], period='2026-10', value=42346)]
        a, b, c = self.mocks()
        with a, b as pdf_fetch, c:
            result = lr._release_supplement(rows, None, dt.date(2026, 11, 3))
        self.assertEqual(result, rows)
        pdf_fetch.assert_not_called()

    def test_failed_pdf_is_not_replaced_with_cached_bytes(self):
        from urllib.error import URLError
        with tempfile.TemporaryDirectory() as folder:
            key = hashlib.sha256(ANNEX_URL.encode()).hexdigest()
            body = b'%PDF previously downloaded'
            Path(folder, key + '.pdf').write_bytes(body)
            Path(folder, key + '.headers.json').write_text(json.dumps({
                'url': ANNEX_URL, 'sha256': hashlib.sha256(body).hexdigest(), 'etag': 'old'}))
            with patch.object(lr.urllib.request, 'urlopen', side_effect=URLError('offline')):
                with self.assertRaisesRegex(RuntimeError, 'request failed'):
                    lr._get_pdf(ANNEX_URL, folder)

    def test_latest_check_failure_keeps_fresh_base_with_visible_warning(self):
        count_rows, value_rows = [], []
        for year, months in ((2024, range(10, 13)), (2025, range(1, 13)), (2026, range(1, 10))):
            for month in months:
                count, amount = {'Year': year, 'Month': month}, {'Year': year, 'Month': month}
                for metric, key, *_, table in lr.SERIES:
                    value = 1 if '_primary_' in metric else 2 if '_secondary_' in metric else 3
                    (count if table == 't1' else amount)[key] = value if table == 't1' else value * 10
                count_rows.append(count)
                value_rows.append(amount)
        def get(url, cache):
            if url == lr.PRESS_URL:
                raise RuntimeError('catalog unavailable')
            body = ('var agtP6="2026"; var blocks={"agt-primary":agtP6}; var jsonInterPath="/json/test";'
                    if url == lr.SCRIPT_URL else json.dumps(count_rows if url.endswith('t1.json') else value_rows))
            return {'url': url, 'body': body}
        with patch.object(lr, '_get', side_effect=get):
            rows = lr.collect(as_of='2026-11-03')
        self.assertEqual(len(rows), 144)
        self.assertTrue(all(row['fetch_mode'] == 'automatic_json' for row in rows))
        self.assertTrue(all('catalog unavailable' in row['refresh_warning'] for row in rows))
        self.assertFalse(any(row.get('status') == 'stale_cache' for row in rows))


if __name__ == '__main__':
    unittest.main()
