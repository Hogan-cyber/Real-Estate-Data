"""User-facing analysis tables keep values numeric and provenance available."""
import io
import unittest
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import hk_property_data as hk
from updater.tests.residential_fixtures import payload


def sample(rows=None, changes=None):
    table = pq.read_table(io.BytesIO(payload(rows)))
    records = table.to_pylist()
    for record in records:
        record['metric_name'] = {'m3': 'Money supply', 'hibor': 'HIBOR daily'}.get(record['metric_id'], record['metric_id'])
        if record['metric_id'] == 'hibor':
            record.update(frequency='D', unit='% p.a.')
    for index, values in (changes or {}).items():
        records[index].update(values)
    output = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(records, schema=table.schema), output, write_page_checksum=True)
    return output.getvalue()


class ResidentialFrameTests(unittest.TestCase):
    def setUp(self):
        hk.clear_residential_cache()

    def tearDown(self):
        hk.clear_residential_cache()

    def reader(self, series=None):
        self.assertTrue(callable(getattr(hk, 'Residential', None)), 'A pandas-first Residential interface is required')
        return hk.Residential(series)

    def test_history_has_datetime_index_numeric_columns_and_preserves_zero_null(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample())):
            result = self.reader('m3').history(start='2026-08', end='2026-09')
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIsInstance(result.index, pd.DatetimeIndex)
        self.assertEqual(result.index.name, 'Date')
        self.assertEqual(result.index.tolist(), [pd.Timestamp('2026-08-31'), pd.Timestamp('2026-09-30')])
        self.assertEqual(result.columns.tolist(), ['Money supply'])
        self.assertEqual(str(result.dtypes.iloc[0]), 'float64')
        self.assertEqual(result.iloc[0, 0], 0.0)
        self.assertTrue(pd.isna(result.iloc[1, 0]))
        self.assertEqual(result.attrs['series']['Money supply']['unit'], 'HKD million')

    def test_different_frequencies_align_only_observed_dates_without_filling(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample())):
            result = self.reader(['m3', 'hibor']).history(labels='id')
        self.assertEqual(result.columns.tolist(), ['m3', 'hibor'])
        self.assertEqual(len(result), 4)
        self.assertEqual(result.loc['2026-09-01', 'hibor'], 2.5)
        self.assertTrue(pd.isna(result.loc['2026-09-01', 'm3']))
        self.assertTrue(pd.isna(result.loc['2026-08-31', 'hibor']))
        self.assertEqual(result.attrs['series']['hibor']['frequency'], 'D')

    def test_no_matches_keeps_known_numeric_columns_and_datetime_index(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample())):
            result = self.reader('m3').history(start='2020-01', end='2020-12')
        self.assertEqual(result.shape, (0, 1))
        self.assertIsInstance(result.index, pd.DatetimeIndex)
        self.assertEqual(str(result['Money supply'].dtype), 'float64')

    def test_all_missing_series_is_not_dropped(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample([('m3', '2026-09-30', '')]))):
            result = self.reader('m3').history()
        self.assertEqual(result.shape, (1, 1))
        self.assertTrue(pd.isna(result.iloc[0, 0]))
        self.assertEqual(str(result.dtypes.iloc[0]), 'float64')

    def test_unknown_ids_raise_instead_of_silent_empty_or_partial_results(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample())):
            reader = self.reader()
            for method in (reader.history, reader.catalog, reader.observations):
                with self.subTest(method=method.__name__), self.assertRaisesRegex(ValueError, 'missing'):
                    method(series=['m3', 'missing'])

    def test_invalid_query_fails_before_http(self):
        reader = self.reader()
        with patch('urllib.request.urlopen', side_effect=AssertionError('Invalid input must not access HTTP')):
            for options in ({'start':'2026-13'}, {'start':'2026-12','end':'2026-01'},
                            {'labels':'invalid'}, {'series':[]}, {'timeout':0}, {'cache':1}):
                with self.subTest(options=options), self.assertRaises(ValueError):
                    reader.history(**options)

    def test_catalogue_keeps_all_sources_and_uses_typed_coverage_counts(self):
        raw = sample(changes={1:dict(source_name='Second official source', source_url='https://example.org/second')})
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            catalog = self.reader().catalog()
        self.assertEqual(catalog.index.name, 'metric_id')
        row = catalog.loc['m3']
        self.assertEqual(row['metric_name'], 'Money supply')
        self.assertEqual(row['observations'], 3)
        self.assertEqual(row['non_missing'], 2)
        self.assertEqual(row['first_date'], pd.Timestamp('2026-08-31'))
        self.assertEqual(row['last_date'], pd.Timestamp('2026-10-31'))
        self.assertIn('Second official source', row['sources'])
        self.assertIn('https://example.org/second', row['source_urls'])
        self.assertTrue(pd.api.types.is_integer_dtype(catalog['observations']))

    def test_duplicate_display_names_remain_distinct_with_ids(self):
        raw = sample(changes={0:dict(metric_name='Same name'), 1:dict(metric_name='Same name'),
                              2:dict(metric_name='Same name'), 3:dict(metric_name='Same name')})
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            result = self.reader(['m3','hibor']).history()
        self.assertEqual(result.columns.tolist(), ['Same name [m3]', 'Same name [hibor]'])
        self.assertEqual(result.loc['2026-09-01', 'Same name [hibor]'], 2.5)

    def test_duplicate_observations_are_not_silently_averaged(self):
        raw = sample([('m3','2026-09-30','10'), ('m3','2026-09-30','20')])
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            with self.assertRaises(hk.CloudDataError):
                self.reader('m3').history()

    def test_inconsistent_definitions_for_one_id_fail_visibly(self):
        for field, value in [('unit','different unit'), ('frequency','Q'), ('metric_name','Different definition')]:
            hk.clear_residential_cache()
            with self.subTest(field=field), patch('urllib.request.urlopen', return_value=io.BytesIO(sample(changes={1:{field:value}}))):
                with self.assertRaises(hk.CloudDataError):
                    self.reader('m3').history()

    def test_observations_retain_flags_and_notes_with_typed_values_and_dates(self):
        raw = sample(changes={1:dict(status='Provisional', flags='P', note='Check this release')})
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            result = self.reader('m3').observations(end='2026-09')
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result['date']))
        self.assertEqual(str(result['value'].dtype), 'float64')
        self.assertIsInstance(result['status'].dtype, pd.CategoricalDtype)
        self.assertEqual(result.iloc[-1]['flags'], 'P')
        self.assertEqual(result.iloc[-1]['note'], 'Check this release')

    def test_objects_methods_and_legacy_reads_share_cache_without_mutation_aliases(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample())):
            history = self.reader('m3').history()
        history.iloc[0,0] = 999
        with patch('urllib.request.urlopen', side_effect=AssertionError('Redundant HTTP')):
            reader = self.reader((metric for metric in ['m3']))
            detail = reader.observations()
            detail.loc[0,'value'] = 888
            self.assertEqual(reader.history().iloc[0,0], 0)
            self.assertEqual(reader.history().iloc[-1,0], 123.45)
            self.assertEqual(reader.history(series='hibor').iloc[0,0], 2.5)
            self.assertEqual(reader.catalog().loc['m3','non_missing'], 2)
            self.assertEqual(hk.fetch_residential(series='m3')[0]['value'], 0)

    def test_explicit_refresh_is_visible_to_other_objects(self):
        first = self.reader('m3'); other = self.reader('m3')
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample())):
            first.history()
        with patch('urllib.request.urlopen', return_value=io.BytesIO(sample([('m3','2026-10-31','200')]))):
            self.assertEqual(first.history(refresh=True).iloc[0,0], 200)
        with patch('urllib.request.urlopen', side_effect=AssertionError('Redundant HTTP')):
            self.assertEqual(other.history().iloc[0,0], 200)


if __name__ == '__main__':
    unittest.main()
