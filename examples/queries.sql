-- Check the snapshot date and source issues before analysis.
SELECT checked_at, as_of, monthly_rows, errors_json FROM dataset_info;
SELECT source_id, status, latest_period, last_success
FROM sources WHERE status <> 'Verified';

-- Discover indicators and coverage. Counts exclude no rows; non_null_count is separate.
SELECT metric_id, metric_name, region, class_name, property_type, unit,
       first_period, last_period, observation_count, non_null_count
FROM metric_catalog ORDER BY category, metric_id;

-- Residential price index (1999=100), inclusive reference-month range.
SELECT period, value, unit, flags FROM observations
WHERE metric_id = 'rvd_1_4_all_classes' AND period BETWEEN '2020-01' AND '2025-12'
ORDER BY period;

-- Average Kowloon sale prices for all five size classes, in HKD per sq ft.
SELECT period, class_name, price_hkd_per_sqft, flags
FROM residential_sale_prices
WHERE region = 'Kowloon' AND period BETWEEN '2025-01' AND '2025-12'
ORDER BY period, class_name;

-- Latest recorded observation for each commercial series, even if value is NULL.
SELECT metric_id, property_type, measure, grade, region, period, value, unit
FROM latest_observations WHERE property_type IN ('Office', 'Retail', 'Industrial')
ORDER BY property_type, metric_id;

-- Value revisions are a history of detected changes, not extra observations.
SELECT metric_id, period, old_value, new_value, detected_at
FROM revisions ORDER BY detected_at DESC, metric_id, period;

-- Monthly PDF cells only. Annual/quarterly/YTD/forecast rows are separate records.
SELECT table_id, period, column_name, value, unit, pdf_page, raw_cell
FROM pdf_observations WHERE frequency = 'monthly' AND observation_kind = 'observed'
ORDER BY table_id, period, column_name;

-- Inspect source-version differences rather than silently overwriting one source.
SELECT table_id, period, column_name, pdf_value, csv_value
FROM pdf_csv_differences ORDER BY table_id, period, column_name;
