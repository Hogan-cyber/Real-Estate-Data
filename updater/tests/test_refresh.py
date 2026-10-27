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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import refresh


class CleanCheckoutTest(unittest.TestCase):
    def test_failed_survey_is_flagged_while_successful_rate_is_updated(self):
        app = Path(__file__).resolve().parents[2]
        snapshot = json.loads((app / 'src/data.json').read_text())
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
            with patch.object(refresh, 'rvd', side_effect=cached_rvd), \
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
