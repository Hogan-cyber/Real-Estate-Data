"""The current residential client reads published files without local storage."""
import csv
import gzip
import http.client
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import hk_property_data as hk

FIELDS = ['metric_id', 'metric_name', 'period', 'date', 'frequency', 'value', 'unit',
          'status', 'flags', 'source_name', 'source_url', 'source_table', 'source_field',
          'note', 'checked_at', 'source_checked_at']


def payload(rows=None):
    if rows is None:
        rows = [('m3', '2026-08-31', '0'), ('m3', '2026-09-30', ''),
                ('hibor', '2026-09-01', '2.5'), ('m3', '2026-10-31', '123.45')]
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=FIELDS); writer.writeheader()
    for metric, date, value in rows:
        writer.writerow(dict(metric_id=metric, metric_name=metric, period=date[:7], date=date,
                             frequency='M', value=value, unit='HKD million', status='Published',
                             source_name='Official', source_url='https://example.org/source',
                             note='Original, source\nnotes', checked_at='2026-11-04'))
    return gzip.compress(out.getvalue().encode('utf-8-sig'))


class BoundedResponse(io.BytesIO):
    def read(self, size=-1):
        if size < 0:
            raise AssertionError('The full response must never be read into memory')
        return super().read(size)


class ResidentialClientTests(unittest.TestCase):
    def test_interrupted_http_transfers_raise_the_public_error_type(self):
        class Socket:
            def __init__(self, raw): self.raw = raw
            def makefile(self, *args, **kwargs): return io.BytesIO(self.raw)

        compressed = payload()
        chunk = f'{len(compressed):x}\r\n'.encode() + compressed[:-5]
        for function, raw in (
            (hk.fetch_residential_status, b'HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n{}'),
            (hk.fetch_residential, b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n' + chunk),
            (hk.connect_residential, b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n' + chunk),
        ):
            response = http.client.HTTPResponse(Socket(raw)); response.begin()
            with self.subTest(function=function.__name__), patch('urllib.request.urlopen', return_value=response):
                with self.assertRaises(hk.CloudDataError): function()
            self.assertTrue(response.closed)

    def test_filtering_preserves_null_zero_provenance_and_inclusive_month(self):
        with patch('urllib.request.urlopen', return_value=BoundedResponse(payload())):
            rows = hk.fetch_residential(series='m3', start='2026-08', end='2026-09')
        self.assertEqual([r['date'] for r in rows], ['2026-08-31', '2026-09-30'])
        self.assertEqual([r['value'] for r in rows], [0.0, None])
        self.assertEqual(rows[0]['note'], 'Original, source\nnotes')
        self.assertEqual(rows[0]['source_url'], 'https://example.org/source')

    def test_iterator_is_lazy_and_closes_early_without_loading_whole_file(self):
        response = BoundedResponse(payload())
        with patch('urllib.request.urlopen', return_value=response) as request:
            rows = hk.iter_residential(series=['m3'])
            request.assert_not_called()
            self.assertEqual(next(rows)['value'], 0)
            rows.close()
        self.assertTrue(response.closed)

    def test_sql_is_in_memory_and_matches_filtered_records(self):
        with patch('urllib.request.urlopen', return_value=BoundedResponse(payload())):
            conn = hk.connect_residential(series='m3', end='2026-09')
        try:
            self.assertEqual(conn.execute('select count(*), sum(value) from observations').fetchone(), (2, 0.0))
            self.assertEqual(conn.execute('select date from observations where value is null').fetchone(), ('2026-09-30',))
            self.assertEqual(conn.execute('pragma database_list').fetchone()[2], '')
        finally:
            conn.close()

    def test_bad_inputs_fail_before_network_access(self):
        for kwargs in ({'start': '2026-13'}, {'end': '2026-02-30'}, {'start': '2026-10', 'end': '2026-01'},
                       {'series': []}, {'series': 2}, {'timeout': 0}):
            with self.subTest(kwargs=kwargs), patch('urllib.request.urlopen') as request:
                with self.assertRaises(ValueError):
                    hk.fetch_residential(**kwargs)
                request.assert_not_called()

    def test_network_gzip_schema_and_numeric_failures_raise(self):
        with patch('urllib.request.urlopen', side_effect=URLError('offline')):
            with self.assertRaises(hk.CloudDataError): hk.fetch_residential()
        for raw in (b'<html>failed</html>', gzip.compress(b'wrong,header\n1,2\n'),
                    payload([('m3', '2026-09-30', 'NaN')]), payload()[:-8]):
            with self.subTest(raw=raw[:15]), patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
                with self.assertRaises(hk.CloudDataError): hk.connect_residential()

    def test_status_is_a_small_separate_metadata_request(self):
        expected = dict(schema_version=1, generated_at='2026-11-04T12:00:00Z', as_of='2026-11-04',
                        mode='live collection', observations=4, series=2, source_runs=[], errors=[])
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(expected).encode())) as request:
            self.assertEqual(hk.fetch_residential_status(), expected)
        self.assertTrue(request.call_args.args[0].full_url.endswith('/collection_status.json'))
        self.assertTrue(hk.residential_url('sqlite').endswith('/observations.sqlite'))
        self.assertTrue(hk.residential_url('excel').endswith('/HK_Residential_Data.xlsx'))
        with self.assertRaises(ValueError): hk.residential_url('unknown')

    def test_client_uses_only_standard_library_and_creates_no_data_files(self):
        script = '''
import sys, io, base64
from unittest.mock import patch
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import hk_property_data as hk
with patch('urllib.request.urlopen', return_value=io.BytesIO(base64.b64decode(sys.argv[2]))):
    conn = hk.connect_residential(series='m3')
assert conn.execute('select count(*) from observations').fetchone()[0] == 3
conn.close()
assert not any(x in sys.modules for x in ('pandas','numpy','openpyxl','hk_property_data.pipeline'))
'''
        import base64
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, '-S', '-c', script,
                                  str(Path(__file__).resolve().parents[2] / 'python'),
                                  base64.b64encode(payload()).decode()], cwd=directory,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == '__main__': unittest.main()
