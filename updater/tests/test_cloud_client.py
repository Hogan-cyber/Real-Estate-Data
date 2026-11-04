"""Cloud reads preserve published data and require no local collector or files."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from urllib.error import URLError
from unittest.mock import patch

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP / 'python'))


class CloudClientTest(unittest.TestCase):
    def client(self):
        package = importlib.import_module('hk_property_data')
        self.assertTrue(callable(getattr(package, 'fetch_dataset', None)),
                        'Package must read the published cloud dataset')
        return package

    def snapshot(self):
        return {'schema_version': 1, 'market': 'HK', 'as_of': '2026-11-04',
                'checked_at': '2026-11-04T05:38:47+00:00',
                'observations': [{'metric_id': 'hk_m3_hkd', 'period': '2026-08',
                                  'date': '2026-08-31', 'value': None, 'unit': 'HKD million',
                                  'source_url': 'https://example.org/source'}],
                'rate_observations': [{'metric_id': 'hk_hibor_1m_daily',
                                       'date': '2026-11-04', 'value': 2.63982}],
                'pdf_observations': [], 'source_status': [], 'revisions': [],
                'errors': [], 'warnings': [], 'report': {}}

    def test_reads_published_values_and_metadata_without_importing_collectors(self):
        package = self.client()
        expected = self.snapshot()
        with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(expected).encode())) as request:
            actual = package.fetch_dataset()
        self.assertEqual(actual, expected)
        self.assertEqual(request.call_args.args[0].full_url,
                         'https://hogan-cyber.github.io/Real-Estate-Data/data/hk_housing_dataset.json')
        self.assertIsNone(actual['observations'][0]['value'])
        self.assertEqual(actual['rate_observations'][0]['value'], 2.63982)

    def test_each_call_reads_again_instead_of_reusing_an_old_snapshot(self):
        package = self.client()
        first = self.snapshot()
        second = self.snapshot()
        second['checked_at'] = '2026-11-05T10:00:00Z'
        second['rate_observations'][0].update(date='2026-11-05', value=2.6)
        with patch('urllib.request.urlopen', side_effect=[BytesIO(json.dumps(x).encode()) for x in (first, second)]):
            self.assertEqual(package.fetch_dataset()['rate_observations'][0]['date'], '2026-11-04')
            self.assertEqual(package.fetch_dataset()['rate_observations'][0]['date'], '2026-11-05')

    def test_source_errors_are_visible_and_published_check_time_is_preserved(self):
        package = self.client()
        expected = self.snapshot()
        expected['errors'] = ['HIBOR source unavailable; retained last valid observations']
        with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(expected).encode())):
            with self.assertWarnsRegex(package.SourceDataWarning, 'HIBOR source unavailable'):
                actual = package.fetch_dataset()
        self.assertEqual(actual['checked_at'], expected['checked_at'])
        self.assertEqual(actual['errors'], expected['errors'])

    def test_transport_and_invalid_snapshot_fail_explicitly(self):
        package = self.client()
        with patch('urllib.request.urlopen', side_effect=URLError('offline')):
            with self.assertRaisesRegex(package.CloudDataError, 'offline'):
                package.fetch_dataset()
        for body in (b'<html>unavailable</html>', b'{}', b'[]',
                     json.dumps({**self.snapshot(), 'schema_version': 99}).encode()):
            with self.subTest(body=body[:25]), patch('urllib.request.urlopen', return_value=BytesIO(body)):
                with self.assertRaises(package.CloudDataError):
                    package.fetch_dataset()

    def test_status_can_be_read_without_downloading_observations(self):
        package = self.client()
        expected = {k: v for k, v in self.snapshot().items()
                    if k not in ('observations', 'rate_observations', 'pdf_observations')}
        with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(expected).encode())) as request:
            self.assertEqual(package.fetch_status(timeout=12), expected)
        self.assertTrue(request.call_args.args[0].full_url.endswith('/refresh_status.json'))
        self.assertEqual(request.call_args.kwargs['timeout'], 12)

    def test_core_client_runs_with_only_standard_library_and_no_output_files(self):
        self.client()
        script = '''
import json, sys
from io import BytesIO
from unittest.mock import patch
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import hk_property_data as hk
payload = json.loads(sys.argv[2])
with patch('urllib.request.urlopen', return_value=BytesIO(json.dumps(payload).encode())):
    assert hk.fetch_dataset()['checked_at'] == payload['checked_at']
assert not any(n in sys.modules for n in ('numpy', 'pandas', 'pdfplumber', 'xlsxwriter', 'hk_property_data.pipeline'))
try:
    hk.refresh()
except RuntimeError as error:
    assert '[collector]' in str(error)
else:
    raise AssertionError('Collector dependency error must explain how to install optional tools')
'''
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, '-S', '-c', script, str(APP / 'python'),
                                  json.dumps(self.snapshot())], cwd=directory, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
