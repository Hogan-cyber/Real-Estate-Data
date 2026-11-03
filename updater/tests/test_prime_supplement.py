import copy
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_prime_supplement as prime


CHANGES = [('31 Oct 2025', '5.00'), ('19 Sep 2025', '5.125'),
           ('20 Dec 2024', '5.25'), ('11 Nov 2024', '5.375'), ('20 Sep 2024', '5.625')]


def page(changes=CHANGES, current='5.00', table_class='desktop'):
    return ('<html><table class="' + table_class + '"><caption>'
            "HSBC's Current Hong Kong Dollar Best Lending Rate: " + current + '%(for reference only)'
            '</caption><thead><tr><th>Effective Date</th><th>HSBC\'s Hong Kong Dollar Best Lending Rate</th></tr></thead>'
            '<tbody>' + ''.join(f'<tr><td><strong>{date}</strong></td><td>{value}%</td></tr>' for date, value in changes)
            + '</tbody></table></html>').encode()


def official(period='2026-09', value=5.0):
    return {'metric_id': 'hk_prime_rate_hsbc', 'period': period, 'value': value,
            'source_id': 'hkma_prime', 'source_name': 'Hong Kong Monetary Authority',
            'status': 'Published', 'fetch_mode': 'automatic_excel'}


class PrimeSupplementTests(unittest.TestCase):
    def run_supplement(self, rows=None, as_of='2026-11-03', raw=None, folder=None):
        with patch.object(prime, '_today', return_value=dt.date(2026, 11, 3)):
            return prime.supplement(rows or [official()], folder, as_of, lambda url: raw or page())

    def test_full_october_constant_rate_has_calculated_provenance_and_raw_archive(self):
        rows = [official()]
        original = copy.deepcopy(rows)
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_supplement(rows, folder=folder)
            self.assertEqual(len(list(Path(folder).glob('hsbc_prime_history_*.html'))), 1)
        self.assertEqual(rows, original)
        self.assertEqual([(r['period'], r['value']) for r in result], [('2026-10', 5.0)])
        row = result[0]
        self.assertEqual(row['source_url'], prime.HISTORY_URL)
        self.assertEqual(row['source_name'], 'HSBC')
        self.assertEqual(row['status'], 'Calculated')
        self.assertEqual(row['fetch_mode'], 'automatic_derived')
        self.assertIn('calendar', row['note'])
        self.assertIsNone(row['published_date'])

    def test_calendar_day_weighting_matches_change_months(self):
        result = self.run_supplement([official('2024-10', 5.63)])
        values = {row['period']: row['value'] for row in result}
        self.assertAlmostEqual(values['2024-11'], (10 * 5.625 + 20 * 5.375) / 30)
        self.assertAlmostEqual(values['2024-12'], (19 * 5.375 + 12 * 5.25) / 31)
        self.assertAlmostEqual(values['2025-09'], (18 * 5.25 + 12 * 5.125) / 30)
        self.assertAlmostEqual(values['2025-10'], (30 * 5.125 + 5.0) / 31)

    def test_first_and_last_day_changes_are_inclusive(self):
        changes = [('31 Oct 2026', '5.00'), ('01 Oct 2026', '5.125'),
                   ('20 Dec 2024', '5.25'), ('11 Nov 2024', '5.375'), ('20 Sep 2024', '5.625')]
        result = self.run_supplement([official(value=5.25)], raw=page(changes))
        self.assertAlmostEqual(result[0]['value'], (30 * 5.125 + 5.0) / 31)

    def test_partial_and_future_months_are_not_invented(self):
        self.assertEqual(self.run_supplement(as_of='2026-10-20'), [])
        self.assertEqual(self.run_supplement(as_of='2026-10-31'), [])
        self.assertEqual([r['period'] for r in self.run_supplement(as_of='2026-11-01')], ['2026-10'])
        result = self.run_supplement(as_of='2027-12-31')
        self.assertEqual([r['period'] for r in result], ['2026-10'])

    def test_published_values_are_never_replaced_or_backfilled_before_coverage(self):
        self.assertEqual(self.run_supplement([official('2026-10')]), [])
        result = self.run_supplement([official('2020-01', 5.0)], as_of='2024-11-01')
        self.assertEqual([r['period'] for r in result], ['2024-10'])

    def test_current_or_historical_schema_ambiguity_fails_closed(self):
        cases = [page(current='5.25'), page(table_class='non-desktop'), page() + page(),
                 page(CHANGES[:4]), page(CHANGES[:-1] + [CHANGES[0]]),
                 page().replace(b'Hong Kong Dollar', b'US Dollar'),
                 page().replace(b'5.125%', b'not available')]
        for raw in cases:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                self.run_supplement(raw=raw)

    def test_conflicting_official_overlap_is_not_silently_extrapolated(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.run_supplement([official(value=5.125)])

    def test_fetch_failure_propagates_instead_of_using_old_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'hsbc_prime_history_old.html').write_bytes(page())
            with self.assertRaisesRegex(RuntimeError, 'unavailable'):
                prime.supplement([official()], folder, '2026-11-03',
                                 lambda url: (_ for _ in ()).throw(RuntimeError('unavailable')))


if __name__ == '__main__':
    unittest.main()
