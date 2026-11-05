"""Dataset bounds and source-evidence safeguards for the simple LR export."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.simple import landreg


def observation(period, metric='hk_residential_sales_count', **extra):
    year, month = map(int, period.split('-'))
    import calendar
    return dict(metric_id=metric, metric_name='Official series', period=period,
                date=f'{period}-{calendar.monthrange(year, month)[1]}', value=100,
                unit='deeds', source_name='香港土地注册处',
                source_url='https://www.landreg.gov.hk/test.json',
                frequency='monthly', note='Official scope retained.', **extra)


class SimpleLandregTests(unittest.TestCase):
    def test_output_bounds_and_instrument_fetch_start_follow_requested_month(self):
        def instruments(cache, cutoff, start, latest_sales_period):
            # A wrong start triggers pre-2002 requests in the real collector.
            self.assertEqual(start, dt.date(2002, 1, 31))
            self.assertEqual(latest_sales_period, '2026-10')
            return [observation('2002-01', 'hk_all_property_mortgage_deeds_count',
                                property_type='All property types')]
        sales = [observation(p) for p in ('2001-12', '2002-01', '2026-10')]
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(landreg.lr, '_collect_sales', return_value=sales), \
             patch.object(landreg.lr, '_collect_instruments', side_effect=instruments):
            result = landreg.collect(Path(folder), '2026-11-04')
        self.assertEqual(len(result), 3)
        self.assertTrue(all(row['period'] >= '2002-01' for row in result))
        self.assertTrue(all(row['frequency'] == 'M' and row['source_id'] == 'landreg' for row in result))
        instrument = next(row for row in result if 'all_property' in row['metric_id'])
        self.assertEqual(instrument['property_type'], 'All property types')

    def test_old_source_check_and_missing_value_cannot_be_relabeled_current_or_zero(self):
        sales = [dict(observation('2026-09'), value=None, status='unavailable',
                      missing_reason='Not published', source_checked_at='2026-10-01T00:00:00+00:00')]
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(landreg.lr, '_collect_sales', return_value=sales), \
             patch.object(landreg.lr, '_collect_instruments', return_value=[]):
            result = landreg.collect(Path(folder), '2026-11-04')
        self.assertIsNone(result[0]['value'])
        self.assertEqual(result[0]['status'], 'Unavailable')
        self.assertEqual(result[0]['source_checked_at'], '2026-10-01T00:00:00+00:00')
        self.assertEqual(result[0]['missing_reason'], 'Not published')

    def test_instrument_network_failure_preserves_sales_with_visible_failure_scope(self):
        error = landreg.lr.InstrumentCollectionError('archive unavailable', ['2026-10'])
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(landreg.lr, '_collect_sales', return_value=[observation('2026-10')]), \
             patch.object(landreg.lr, '_collect_instruments', side_effect=error):
            result = landreg.collect(Path(folder), '2026-11-04')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['value'], 100)
        self.assertIn('archive unavailable', result[0]['refresh_warning'])
        self.assertEqual(result[0]['refresh_failed_periods'], ['2026-10'])
        self.assertEqual(len(result[0]['refresh_failed_metric_ids']), 5)
        self.assertIn('SOURCE_CHECK_WARNING', result[0]['flags'])


if __name__ == '__main__':
    unittest.main()
