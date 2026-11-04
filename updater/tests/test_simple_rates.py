import datetime as dt
import unittest
from unittest.mock import patch

from hk_property_data.simple import rates


class RateExtractionTests(unittest.TestCase):
    def test_hsbc_validates_current_page_before_historical_cutoff(self):
        html = '<h2>Current Hong Kong Dollar Best Lending Rate: 5.00%</h2><table><tr><td>31 Oct 2025</td><td>5.00%</td></tr><tr><td>20 Dec 2024</td><td>5.25%</td></tr></table>'
        rows = rates.hsbc_rows(html, '2024-12-31')
        self.assertEqual([(r['date'], r['value']) for r in rows], [('2024-12-20', 5.25)])
        self.assertEqual(rates.hsbc_rows(html, '2023-12-31'), [])
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            rates.hsbc_rows(html.replace('Rate: 5.00%', 'Rate: 6.00%'), '2024-12-31')

    def test_prime_workbook_validates_live_dates_then_bounds_observations(self):
        with patch.object(rates.legacy, 'parse_excel', return_value=[
            {'date': '2024-12-20', 'value': 5.25}, {'date': '2025-10-31', 'value': 5.0},
        ]) as parse:
            rows = rates.prime_rows(b'workbook', '2024-12-31', '2026-11-04T12:00:00+00:00')
        self.assertEqual([r['date'] for r in rows], ['2024-12-20'])
        self.assertEqual(parse.call_args.args[2], '2026-11-04')

    def test_daily_fixings_preserve_missing_tenor_and_zero(self):
        rows = rates.daily_rows([
            [dt.datetime(2026, 10, 30), '', '', 0, 2.66923, 2.70923, 3.21256, 3.45732, 'N.A.', 3.94095],
            ['Footnotes', '', '', '', '', '', '', '', '', ''],
        ], '2026-11-04', '2002-01')
        values = {r['metric_id']: r['value'] for r in rows}
        self.assertEqual(len(rows), 7)
        self.assertEqual(values['hk_hibor_overnight_daily'], 0)
        self.assertEqual(values['hk_hibor_1m_daily'], 2.70923)
        self.assertIsNone(values['hk_hibor_9m_daily'])
        self.assertTrue(all(r['frequency'] == 'D' for r in rows))

    def test_daily_observations_respect_cutoffs(self):
        cells = [[dt.datetime(y, 1, 2), '', '', *([1] * 7)] for y in (2001, 2002, 2027)]
        self.assertEqual({r['date'] for r in rates.daily_rows(cells, '2026-11-04', '2002-01')}, {'2002-01-02'})

    def test_hsbc_effective_dates_are_not_scrape_dates(self):
        html = '<h2>HSBC\'s Current Hong Kong Dollar Best Lending Rate: 5.00%</h2><table><tr><th>Effective Date</th><th>Rate</th></tr><tr><td>31 Oct 2025</td><td>5.00%</td></tr><tr><td>19 Sep 2025</td><td>5.125%</td></tr></table>'
        rows = rates.hsbc_rows(html, '2026-11-04', '2002-01')
        self.assertEqual(rows[-1]['date'], '2025-10-31')
        self.assertEqual(rows[-1]['value'], 5)
        self.assertIn('HSBC current rate checked', rows[-1]['note'])
