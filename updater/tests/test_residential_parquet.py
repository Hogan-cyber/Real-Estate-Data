import io
import unittest
from unittest.mock import patch
import hk_property_data as hk
from updater.tests.residential_fixtures import payload


class ParquetReaderTests(unittest.TestCase):
    def setUp(self):
        hk.clear_residential_cache()

    def tearDown(self):
        hk.clear_residential_cache()

    def test_parquet_preserves_typed_null_zero_dates_and_provenance(self):
        raw=payload([('m3','2026-08-31','0'),('m3','2026-09-30',''),('m3','2026-10-31','123.45')])
        with patch('urllib.request.urlopen',return_value=io.BytesIO(raw)) as request:
            try:
                rows=hk.fetch_residential(series='m3',start='2026-08',end='2026-09')
            except hk.CloudDataError as exc:
                self.fail('A valid typed Parquet response must load: '+str(exc))
        self.assertEqual([r['value'] for r in rows],[0.0,None])
        self.assertEqual([r['date'] for r in rows],['2026-08-31','2026-09-30'])
        self.assertEqual(rows[0]['note'],'Original, source\nnotes')
        self.assertTrue(request.call_args.args[0].full_url.endswith('/observations.parquet'))
