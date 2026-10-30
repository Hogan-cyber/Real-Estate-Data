# Hong Kong property database

[Download the latest SQLite database](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_housing.sqlite) · [Python example](examples/query_database.py) · [SQL examples](examples/queries.sql)

The database contains the same official residential and commercial observations as the dashboard, plus source status, PDF extraction and revision history. Each monthly GitHub Actions run rebuilds and publishes it at the same URL. No ChatGPT, account, API key or database server is needed to download or query it. A downloaded file is a snapshot: download it again to receive subsequent releases. This is a complete, unfiltered dataset; dashboard date selections do not change its contents.

## Quick start with Python

Python 3.10+ is sufficient; all dependencies below are built in. Download the example script from this repository, or use it in a checkout:

```sh
python examples/query_database.py --download --database hk_housing.sqlite --list-metrics
python examples/query_database.py --database hk_housing.sqlite --metric rvd_1_4_all_classes --start 2020-01 --end 2025-12 --format csv > price_index.csv
```

`--download` fetches the current published database, checks its identity, integrity and row counts, then replaces the local file. A failed download preserves the existing local database. Without `--download`, the script reads your existing file without network access. Source warnings go to stderr; query results go to stdout.

Use ordinary SQL from any Python program:

```python
import sqlite3
from pathlib import Path

db = sqlite3.connect(Path("hk_housing.sqlite").resolve().as_uri() + "?mode=ro", uri=True)
try:
    prices = db.execute("""
        SELECT period, class_name, price_hkd_per_sqft, flags
        FROM residential_sale_prices
        WHERE region = ? AND period BETWEEN ? AND ?
        ORDER BY period, class_name
    """, ("Kowloon", "2025-01", "2025-12")).fetchall()
    print(prices[:5])
finally:
    db.close()
```

If you already use pandas, `pd.read_sql_query(sql, db, params=...)` returns a DataFrame. A SQLite SQL client can open the same file directly. Queries do not modify the published website.

## Tables and views

| Object | Grain / purpose |
|---|---|
| `observations` | One current official monthly value per `(metric_id, period)`. A missing value is SQL `NULL`. |
| `metric_catalog` | View: one series identifier, dimensions, unit, first/last month, row count, non-null count and latest value. |
| `latest_observations` | View: the latest reference-month row for every series, including a NULL latest value. Different series can have different latest months. |
| `residential_sale_prices` | View: RVD table 1.2 by size class and district, with `price_hkd_per_sqm` and `price_hkd_per_sqft`. |
| `sources` | One source feed and its check time, last successful check, latest reference period, status and change summary. |
| `pdf_observations` | One extracted PDF cell, preserving table/page, period/frequency, original text, flags and observed/forecast distinction. |
| `revisions` | One detected value change, with `old_value`, `new_value` and `detected_at`; history retained by the refresh pipeline. |
| `pdf_csv_checks` | One PDF-to-CSV comparison per report table, with compared-cell and mismatch counts. |
| `pdf_csv_differences` | Detailed differing PDF and CSV cells from those comparisons. |
| `dataset_info` | One snapshot metadata row: schema version, market, check date, counts, `errors_json` and `report_json`. |

`observations` exposes source fields as SQL columns: `market`, `category`, `metric_name`, `region`, `class_name`, `property_type`, `measure`, `grade`, `area_basis`, `source_table`, `source_field`, `source_url`, `flags`, `status`, `small_sample`, `missing_reason`, `fetch_mode`, observation/publication/check dates and notes. Fields not supplied by a source remain NULL. Original complete records remain in `payload` JSON. Foreign keys link observations to `sources`; indexes support period, source, category, region, class and property-type filters.

Schema version is **2**, available through `PRAGMA user_version` and `dataset_info.schema_version`. The seven original observation columns remain available: `metric_id`, `period`, `date`, `value`, `unit`, `source_id`, `payload`. Consumers should select named columns rather than depend on `SELECT *` column positions. The JSON dataset retains its separate existing version.

## Data meaning

- `period` is the observation month (`YYYY-MM`); `date` is its month-end. `checked_at` is a retrieval/check time, not a reference month or evidence that a new release appeared.
- `value` uses the original published unit. Never sum mixed units, indices, overlapping totals or PDF frequencies. Frequencies preserve their original labels (`M` / `monthly` in the monthly table).
- The sale-price view converts HKD/sq m to HKD/sq ft using **0.09290304**. These are transaction averages by saleable-area class, not room counts or per-home totals; primary residential sales are excluded by RVD's sale-price series. A–E mean <40, 40–69.9, 70–99.9, 100–159.9 and ≥160 sq m.
- Commercial `property_type` is Office, Retail or Industrial. Office A–C grades describe building quality; they are not residential size classes. Commercial averages use internal floor area; Industrial covers private flatted factories. Residential source rows do not currently supply `property_type`; use their series IDs or source tables.
- Missing latest values remain NULL; no forward-fill, interpolation or zero substitution. HKMA mortgage rates exist only for explicitly disclosed months.
- Check `sources.status` and `dataset_info.errors_json` before using results. Failed sources retain last valid data. PDF and CSV vintages can disagree; their separate values and comparison warnings remain queryable. A successful database download does not mean every source is current or free of warnings.
- Revisions record detected numerical changes since collection began, including changes to/from NULL. They do not reconstruct revisions before the archive began, and do not constitute a complete history of flag-only changes. Raw official source vintages remain in `updater/archives/`, outside the database.

## Rebuild from a saved dataset

```sh
python updater/database.py --dataset data/hk_housing_dataset.json --output data/hk_housing.sqlite
python updater/validate.py data
```

The builder uses a temporary file and replaces the prior database only after integrity, foreign-key, row-count and monthly-value reconciliation checks pass. The existing monthly `updater/refresh.py` invokes the same builder automatically before website publication.
