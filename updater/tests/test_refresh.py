"""Exercise a later GitHub checkout with committed history but no local cache."""
import argparse
import copy
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data import pipeline as refresh


class CleanCheckoutTest(unittest.TestCase):
    def test_failed_survey_is_flagged_while_successful_rate_is_updated(self):
        # This regression exercises the retained legacy pipeline. The current
        # dashboard uses the new dataset and must not serve as its test fixture.
        snapshot = json.loads((Path(__file__).parent / 'fixtures' /
                               'legacy_refresh_snapshot.json').read_text())
        prior = copy.deepcopy(snapshot['queries']['observations']['rows'])
        rate = next(r for r in prior if r['metric_id'] == 'hk_new_mortgage_rate')
        fresh_rate = dict(rate, value=rate['value'] + 0.01, status='updated')
        as_of = max(snapshot['asOf'], dt.date.today().isoformat())
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            refresh.save(out / 'hk_housing_dataset.json', {
                'observations': prior,
                'pdf_observations': snapshot['queries']['pdf']['rows'],
                'source_status': snapshot['queries']['status']['rows'],
                'report': snapshot['refresh']['report'],
            })
            def cached_rvd(table, *_):
                return [dict(r) for r in prior if r['source_id'] == 'rvd_' + table]
            c01 = dict(market='HK', metric_id='hk_nominal_gdp_yoy', metric_name='Nominal GDP growth',
                       period='2025-12', date='2025-12-31', value=3, unit='% yoy', frequency='Q',
                       source_period='2025-Q4', source_id='hkma_money_credit',
                       source_name='Hong Kong Monetary Authority', status='Published',
                       source_url=refresh.hk_money_credit_collector.SOURCE_URL,
                       source_table=refresh.hk_money_credit_collector.SOURCE_TABLE,
                       source_field='Nominal GDP', fetch_mode='automatic_excel')
            with patch.object(refresh, 'rvd', side_effect=cached_rvd), \
                 patch.object(refresh.hk_commercial_collector, 'TABLES', {}), \
                 patch.object(refresh.hk_macro_collector, 'SOURCES', {}), \
                 patch.object(refresh.hk_money_credit_collector, 'collect', return_value=[c01]), \
                 patch.object(refresh.hk_landreg_collector, 'collect', return_value=[dict(r) for r in prior if r['source_id'] == 'landreg']), \
                 patch.object(refresh.hk_hkma_collector, '_survey', side_effect=OSError('simulated outage')), \
                 patch.object(refresh.hk_hkma_collector, '_mortgage_rate', return_value=[fresh_rate]), \
                 patch.object(refresh, 'fetch', side_effect=OSError('simulated PDF outage')), \
                 redirect_stdout(io.StringIO()):
                refresh.run(argparse.Namespace(output=str(out), app=None, as_of=as_of, pdf=None))
            result = json.loads((out / 'hk_housing_dataset.json').read_text())
            hkma = next(s for s in result['source_status'] if s['source_id'] == 'hkma')
            self.assertEqual(hkma['status'], 'Retained: refresh failed')
            self.assertTrue(any('hkma' in error for error in result['errors']))
            rates = [r for r in result['observations'] if r['metric_id'] == rate['metric_id'] and r['period'] == rate['period']]
            self.assertEqual(rates[0]['value'], fresh_rate['value'])
            before = {(r['metric_id'], r['period'], r['value']) for r in prior if r['source_id'] == 'hkma' and r['metric_id'] != 'hk_new_mortgage_rate'}
            after = {(r['metric_id'], r['period'], r['value']) for r in result['observations'] if r['source_id'] == 'hkma' and r['metric_id'] != 'hk_new_mortgage_rate'}
            self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
