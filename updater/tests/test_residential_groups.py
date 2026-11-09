"""Group navigation must select original observations and preserve reader guarantees."""
import io
import unittest
from unittest.mock import patch

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import hk_property_data as hk
from updater.tests.residential_fixtures import payload


def grouped_sample(price=100):
    rows = [
        ('rvd_1_4_class_a', '2025-01-31', str(price)),
        ('rvd_1_4_class_a', '2025-02-28', '0'),
        ('rvd_1_4_class_a', '2025-03-31', ''),
        ('rvd_1_4_class_b', '2025-01-31', '80'),
        ('rvd_1_3_all_classes', '2025-01-31', '50'),
        ('rvd_1_1_class_a_kowloon', '2025-01-31', '300'),
        ('rvd_1_2_class_a_kowloon', '2025-01-31', '100000'),
        ('rvd_1_5_overall_all', '2025-01-31', '200'),
        ('rvd_stock_total_stock', '2024-12-31', '1000'),
        ('hk_residential_sales_count', '2025-01-31', '10'),
        ('hk_mortgage_drawn_amount', '2025-01-31', '1000'),
        ('hk_all_property_mortgage_deeds_count', '2025-01-31', '20'),
        ('hk_negative_equity_count', '2025-03-31', '4'),
        ('hk_residential_sales_share', '2025-01-31', '0.5'),
        ('hk_bank_mortgage_refinancing_count_share', '2025-01-31', '0.2'),
        ('hk_bank_mortgage_refinancing_amount_share', '2025-01-31', '0.3'),
        ('hk_money_lender_mortgage_count_estimate', '2025-01-31', '-1'),
        ('hk_m3_hkd', '2025-01-31', '9000'),
        ('hk_hibor_1m', '2025-01-31', '2.2'),
        ('hk_hibor_1m_daily', '2025-01-02', '2.3'),
        ('hk_prime_rate_hsbc_effective', '2025-01-01', '5.25'),
        ('new_official_indicator', '2025-01-31', ''),
    ]
    table = pq.read_table(io.BytesIO(payload(rows)))
    records = table.to_pylist()
    for r in records:
        if r['metric_id'].endswith('_daily'):
            r['frequency'] = 'D'
        elif r['metric_id'].endswith('_effective'):
            r['frequency'] = 'E'
        elif r['metric_id'].startswith('rvd_stock_'):
            r['frequency'] = 'A'
        elif r['metric_id'].startswith('hk_negative_equity_'):
            r['frequency'] = 'Q'
    target = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(records, schema=table.schema), target, write_page_checksum=True)
    return target.getvalue()


class ResidentialGroupTests(unittest.TestCase):
    def setUp(self):
        hk.clear_residential_cache()

    def tearDown(self):
        hk.clear_residential_cache()

    def test_overview_accounts_for_every_indicator_and_keeps_zero_null_and_unknown(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            reader = hk.Residential()
            overview = reader.overview()
            catalog = reader.catalog()
        self.assertEqual(overview.index.names, ['group', 'frequency'])
        self.assertEqual(overview['indicators'].sum(), len(catalog))
        self.assertEqual(overview['records'].sum(), 22)
        self.assertEqual(overview['available_values'].sum(), 20)
        price = overview.loc[('Price indices', 'M')]
        self.assertEqual((price['indicators'], price['records'], price['available_values']), (2, 4, 3))
        self.assertEqual(price['first_date'], pd.Timestamp('2025-01-31'))
        self.assertEqual(price['last_date'], pd.Timestamp('2025-03-31'))
        self.assertEqual(catalog.loc['new_official_indicator', 'group'], 'Other / new indicators')
        self.assertEqual(len(overview.index.get_level_values('group').unique()), 15)

    def test_model_shares_and_negative_estimates_are_separate_from_bank_observations(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            reader = hk.Residential()
            catalog = reader.catalog(group='Mortgage estimates')
            values = reader.history(group='Mortgage estimates', labels='id')
            banks = reader.catalog(group='Bank mortgages')
        self.assertEqual(len(catalog), 4)
        self.assertIn('hk_residential_sales_share', catalog.index)
        self.assertEqual(values.at[pd.Timestamp('2025-01-31'), 'hk_money_lender_mortgage_count_estimate'], -1)
        self.assertEqual(banks.index.tolist(), ['hk_mortgage_drawn_amount'])

    def test_group_and_inclusive_dates_return_original_numeric_dataframe(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            reader = hk.Residential()
            actual = reader.history(group='Price indices', start='2025-01', end='2025-02', labels='id')
            expected = reader.history(series=['rvd_1_4_class_a', 'rvd_1_4_class_b'], start='2025-01', end='2025-02', labels='id')
        pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(actual.index[-1], pd.Timestamp('2025-02-28'))
        self.assertEqual(actual.iloc[-1, 0], 0)
        self.assertTrue(pd.isna(actual.iloc[-1, 1]))
        self.assertTrue(all(str(t) == 'float64' for t in actual.dtypes))

    def test_unknown_estimate_family_is_not_relabelled_as_mortgage(self):
        metric = 'future_unrelated_indicator_estimate'
        raw = payload([(metric, '2025-01-31', '1')])
        with patch('urllib.request.urlopen', return_value=io.BytesIO(raw)):
            reader = hk.Residential()
            self.assertEqual(reader.catalog().at[metric, 'group'], 'Other / new indicators')
            self.assertEqual(reader.history(group='Other / new indicators', labels='id').columns.tolist(), [metric])

    def test_multiple_groups_case_and_underscore_aliases_select_union_without_duplicates(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            actual = hk.Residential().history(group=['price_indices', ' RENT INDICES ', 'Price indices'], labels='id')
        self.assertEqual(set(actual.columns), {'rvd_1_4_class_a', 'rvd_1_4_class_b', 'rvd_1_3_all_classes'})
        self.assertEqual(len(actual.columns), 3)

    def test_daily_filter_never_implies_monthly_resampling(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            reader = hk.Residential()
            daily = reader.history(group='HIBOR', frequency='d', labels='id')
            monthly = reader.catalog(group='HIBOR', frequency='M')
        self.assertEqual(daily.columns.tolist(), ['hk_hibor_1m_daily'])
        self.assertEqual(daily.index.tolist(), [pd.Timestamp('2025-01-02')])
        self.assertEqual(monthly.index.tolist(), ['hk_hibor_1m'])

    def test_constructor_selection_and_method_override_share_cache_and_keep_raw_schema(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())) as http:
            reader = hk.Residential(group='HIBOR', frequency='M')
            reader.overview()
            self.assertEqual(reader.history(labels='id').columns.tolist(), ['hk_hibor_1m'])
            self.assertEqual(reader.history(frequency='D', labels='id').columns.tolist(), ['hk_hibor_1m_daily'])
            self.assertEqual(reader.catalog(group='Price indices').shape[0], 2)
            raw = reader.observations(frequency='D')
            legacy = hk.fetch_residential(series='hk_hibor_1m_daily')
        self.assertEqual(http.call_count, 1)
        self.assertEqual(raw['value'].tolist(), [legacy[0]['value']])
        self.assertNotIn('group', raw.columns)

    def test_series_and_group_intersect_preserving_requested_id_order(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            result = hk.Residential().history(series=['rvd_1_4_class_b', 'hk_m3_hkd', 'rvd_1_4_class_a'], group='Price indices', labels='id')
        self.assertEqual(result.columns.tolist(), ['rvd_1_4_class_b', 'rvd_1_4_class_a'])

    def test_invalid_selectors_fail_before_network(self):
        invalid = [{'group': ''}, {'group': []}, {'group': ['Price indices', 'typo']},
                   {'group': 3}, {'frequency': 'monthly'}, {'frequency': []}, {'frequency': 1}]
        with patch('urllib.request.urlopen', side_effect=AssertionError('Bad input must not fetch')):
            for options in invalid:
                for method in ('history', 'catalog', 'overview', 'observations'):
                    with self.subTest(options=options, method=method), self.assertRaises(ValueError):
                        getattr(hk.Residential(), method)(**options)
                with self.subTest(options=options, method='constructor'), self.assertRaises(ValueError):
                    hk.Residential(**options)

    def test_empty_selection_does_not_fall_back_to_full_dataset(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            for options in ({'group': 'Annual supply', 'frequency': 'M'},
                            {'group': 'Price indices', 'series': 'hk_m3_hkd'}):
                with self.subTest(options=options), self.assertRaisesRegex(ValueError, 'No indicators'):
                    hk.Residential().history(**options)
            empty_dates = hk.Residential().history(group='Price indices', start='1990-01', end='1991-12', labels='id')
        self.assertEqual(empty_dates.shape, (0, 2))
        self.assertIsInstance(empty_dates.index, pd.DatetimeIndex)

    def test_group_refresh_is_visible_to_existing_reader_and_results_are_independent(self):
        reader = hk.Residential(group='Price indices')
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample())):
            before = reader.history(labels='id')
            overview = reader.overview()
        before.iloc[0, 0] = 999
        overview.iloc[0, 0] = 999
        with patch('urllib.request.urlopen', return_value=io.BytesIO(grouped_sample(price=101))):
            reader.overview(refresh=True)
        with patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected repeated request')):
            self.assertEqual(reader.history(labels='id').iloc[0, 0], 101)
            self.assertEqual(reader.overview().iloc[0]['indicators'], 2)


if __name__ == '__main__':
    unittest.main()
