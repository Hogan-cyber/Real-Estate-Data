"""Fast reads must preserve data while avoiding redundant remote work."""
import io
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import hk_property_data as hk
from updater.tests.residential_fixtures import payload

SAMPLE = payload()


class FastReaderTests(unittest.TestCase):
    def setUp(self):
        if hasattr(hk, 'clear_residential_cache'):
            hk.clear_residential_cache()

    def tearDown(self):
        self.setUp()

    def test_first_read_gets_one_shared_direct_snapshot(self):
        seen=[]
        def remote(request, **kwargs):
            seen.append(request.full_url)
            return io.BytesIO(SAMPLE)
        with patch('urllib.request.urlopen', side_effect=remote):
            rows=hk.fetch_residential(series='m3', end='2026-09')
        self.assertEqual([r['value'] for r in rows], [0.0, None])
        self.assertEqual(seen, ['https://raw.githubusercontent.com/Hogan-cyber/Real-Estate-Data/residential-data/observations.parquet'])

    def test_repeated_and_changed_dates_work_without_network_and_without_aliasing(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(SAMPLE)):
            first=hk.fetch_residential(series='m3', end='2026-09')
        first[0]['value']=999
        with patch('urllib.request.urlopen', side_effect=AssertionError('Redundant download')):
            repeated=hk.fetch_residential(series='m3', end='2026-09')
            later=hk.fetch_residential(series=['m3'], start='2026-10')
            other=hk.fetch_residential(series='hibor')
        self.assertEqual([r['value'] for r in repeated], [0.0, None])
        self.assertEqual([r['value'] for r in later], [123.45])
        self.assertEqual([r['value'] for r in other], [2.5])

    def test_session_snapshot_stays_stable_until_explicit_refresh(self):
        updated=payload([('m3','2026-10-31','200')])
        with patch('time.monotonic', return_value=0), patch('urllib.request.urlopen', return_value=io.BytesIO(SAMPLE)):
            hk.fetch_residential(series='m3')
        with patch('time.monotonic', return_value=86400), patch('urllib.request.urlopen', side_effect=AssertionError('Implicit refresh')):
            self.assertEqual(len(hk.fetch_residential(series='m3')),3)
        with patch('urllib.request.urlopen', return_value=io.BytesIO(updated)) as request:
            rows=hk.fetch_residential(series='m3', refresh=True)
        self.assertEqual([r['value'] for r in rows],[200])
        self.assertIn('refresh=',request.call_args.args[0].full_url)

    def test_failed_forced_refresh_evicts_old_data_and_does_not_return_it(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(SAMPLE)):
            hk.fetch_residential(series='m3')
        with patch('urllib.request.urlopen', side_effect=URLError('offline')):
            with self.assertWarns(hk.SourceDataWarning), self.assertRaises(hk.CloudDataError):
                hk.fetch_residential(series='m3',refresh=True)
        self.assertEqual(hk.residential_cache_info()['entries'],0)

    def test_bad_parquet_never_enters_cache(self):
        for raw in (SAMPLE[:-8],b'not parquet'):
            with self.subTest(raw=raw[:20]), patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
                with self.assertRaises(hk.CloudDataError):
                    hk.fetch_residential(series='m3')
            self.assertEqual(hk.residential_cache_info()['entries'],0)

    def test_release_fallback_is_visible_and_filters_full_data(self):
        seen=[]
        def remote(request, **kwargs):
            seen.append(request.full_url)
            if 'raw.githubusercontent.com' in request.full_url:
                raise HTTPError(request.full_url,404,'Not found',{},None)
            return io.BytesIO(payload())
        with patch('urllib.request.urlopen',side_effect=remote), self.assertWarns(hk.SourceDataWarning):
            rows=hk.fetch_residential(series='m3')
        self.assertEqual([r['value'] for r in rows],[0.0,None,123.45])
        self.assertEqual(len(seen),2)
        self.assertTrue(seen[1].endswith('/observations.parquet'))

    def test_cache_false_is_a_fresh_read_without_persisting_response(self):
        with patch('urllib.request.urlopen',return_value=io.BytesIO(SAMPLE)):
            rows=hk.fetch_residential(series='m3',cache=False)
        self.assertEqual(len(rows),3)
        self.assertEqual(hk.residential_cache_info()['entries'],0)

    def test_multiple_metrics_use_one_consistent_full_file(self):
        with patch('urllib.request.urlopen',return_value=io.BytesIO(payload())) as request:
            rows=hk.fetch_residential(series=['m3','hibor'])
        self.assertEqual(len(rows),4)
        self.assertTrue(request.call_args.args[0].full_url.endswith('/residential-data/observations.parquet'))

    def test_sql_reuses_cached_response_and_remains_read_only(self):
        with patch('urllib.request.urlopen',return_value=io.BytesIO(SAMPLE)):
            hk.fetch_residential(series='m3')
        with patch('urllib.request.urlopen',side_effect=AssertionError('Redundant download')):
            conn=hk.connect_residential(series='m3')
        try:
            self.assertEqual(conn.execute('SELECT count(*),sum(value) FROM observations').fetchone(),(3,123.45))
            self.assertEqual(conn.execute('PRAGMA database_list').fetchone()[2],'')
        finally:
            conn.close()

    def test_concurrent_requests_share_one_validated_download(self):
        calls=[]
        def remote(request, **kwargs):
            calls.append(request.full_url)
            return io.BytesIO(SAMPLE)
        with patch('urllib.request.urlopen',side_effect=remote), ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:hk.fetch_residential(series='m3'),range(8)))
        self.assertEqual([len(r) for r in results],[3]*8)
        self.assertEqual(len(calls),1)

    def test_cache_byte_budget_includes_decoded_arrow_memory(self):
        from hk_property_data.residential_parquet import validate
        table = validate(SAMPLE)
        retained_bytes = table.get_total_buffer_size()
        # Logical nbytes omits terminal offsets; budget all retained buffers.
        self.assertGreater(retained_bytes, table.nbytes)
        with patch('hk_property_data.residential_cache.MAX_BYTES',table.nbytes), patch('urllib.request.urlopen',return_value=io.BytesIO(SAMPLE)):
            self.assertEqual(len(hk.fetch_residential(series='m3')),3)
            self.assertEqual(hk.residential_cache_info()['entries'],0)
        with patch('urllib.request.urlopen',return_value=io.BytesIO(SAMPLE)):
            hk.fetch_residential(series='m3')
        info=hk.residential_cache_info()
        self.assertEqual(info['bytes'],retained_bytes)
        self.assertEqual(info['entries'],1)
        hk.clear_residential_cache()
        self.assertEqual(hk.residential_cache_info()['bytes'],0)


if __name__=='__main__': unittest.main()
