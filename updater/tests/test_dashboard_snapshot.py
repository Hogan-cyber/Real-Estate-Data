"""Dashboard publication preserves failure evidence when the status API is down."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/content/dashboard'))
spec = importlib.util.spec_from_file_location('dashboard_snapshot', ROOT / 'src/content/dashboard/prepare_snapshot.py')
snapshot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot_module)


class DashboardSnapshotTests(unittest.TestCase):
    def run_snapshot(self, outcome='auto', errors=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'src').mkdir()
            source = root / 'input'
            source.mkdir()
            output = root / 'src/data.json'
            output.write_text(json.dumps({'id': 'dashboard:test', 'title': 'Test', 'refresh': {'errors': ['obsolete checkout error']}}))
            row = dict(metric_id='hk_m3_hkd', metric_name='Hong Kong dollar M3', period='2026-09', date='2026-09-30', frequency='M', value=12.0, unit='HKD million', status='Published', flags='', source_name='Hong Kong Monetary Authority', source_url='https://www.hkma.gov.hk/', source_table='T2.2', source_field='M3', note='', checked_at='2026-11-09', source_checked_at='')
            pq.write_table(pa.Table.from_pylist([row]), source / 'observations.parquet')
            (source / 'collection_status.json').write_text(json.dumps({'generated_at': '2026-11-09T00:00:00Z', 'as_of': '2026-11-09', 'observations': 1, 'series': 1, 'errors': errors or []}))
            arguments = ['prepare_snapshot.py', '--input', str(source), '--output', str(output), '--collection-outcome', outcome, '--collection-run-url', 'https://github.com/Hogan-cyber/Real-Estate-Data/actions/runs/123']
            with patch.object(snapshot_module, 'ROOT', root), patch.object(sys, 'argv', arguments), patch.object(snapshot_module, 'get_bytes', side_effect=OSError('API unavailable')) as fetch:
                snapshot_module.main()
            return json.loads(output.read_text()), fetch.call_count

    def test_api_outage_retains_current_errors_not_stale_checkout_errors(self):
        result, calls = self.run_snapshot(errors=['current dataset source failure'])
        self.assertEqual(calls, 1)
        self.assertEqual(result['refresh']['errors'], ['current dataset source failure'])
        self.assertTrue(any('could not be verified' in note for note in result['refresh']['warnings']))

    def test_explicit_failed_run_needs_no_api_and_retains_data_timestamp(self):
        result, calls = self.run_snapshot(outcome='failure')
        self.assertEqual(calls, 0)
        self.assertEqual(result['generatedAt'], '2026-11-09T00:00:00Z')
        self.assertIn('status failure', result['refresh']['errors'][0])
        self.assertIn('/runs/123', result['refresh']['errors'][0])
        self.assertEqual(result['queries']['observations']['rows'][0]['value'], 12.0)


if __name__ == '__main__':
    unittest.main()
