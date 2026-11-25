# Residential Dataset integration preview

All changes belong to `Hogan-cyber/Real-Estate-Data`. Mortgage Monitor is a
read-only upstream source; this project never runs its updater or writes to it.

## Copied snapshot

The preview copies Monitor commit
`c564a70ce4b8a6991e3af4205d2a516183d74128`, checked at 04:31:37 HKT on
25 November 2026. Its workbook SHA-256 is
`7c854a8ee7ce68607f18fe8d6d20b64b68026eb077c1e4fd96b2dc72d3c27c1a`.
All 24,895 values/blanks across the seven data sheets (31 indicators) match the
same commit's dashboard payload. Saved formula results are independently checked
and copied without recalculation or clipping.

| Worksheet | Coverage in copied snapshot |
| --- | --- |
| Centaline | January 2012–October 2026 |
| HKMA bank mortgages | December 2016–September 2026 |
| Land Registry | November 2024–October 2026 |
| M3 | See `preview/collection_status.json` for exact coverage |
| HSBC Prime | Original effective dates; last change 31 October 2025 |
| HIBOR | Original business days through 24 November 2026 |
| Non-bank model | Original bank-month and registration-month records |

The source report's `partial` status is preserved. A copied workbook is not
represented as a fresh direct check of every underlying official website.
The residential project's direct daily HIBOR series can be newer than the copied
Monitor series; both retain their actual dates and different IDs.

## Formula retained from Excel

Bank purchase drawdowns in month b:

`(primary approval count[b] + secondary approval count[b]) / total approval count[b] * drawdown count[b]`

Residual in registration month t:

`completed registrations[t] + off-plan registrations[t] - bank purchase drawdowns[t-1]`

The one-month lag and approval mix are assumptions. Completed-property totals
are broader than private residential housing; a residual is not an observed
licensed money-lender count. The workbook supplies no non-bank amount. Existing
`hk_*_estimate` indicators still refer to the older LR allocation model and are
not mixed into these charts.

## Reproduce independently

Python 3.10+; the same commands work on Windows (use `python` in its environment).
Run from the checked-out repository root:

```sh
python -m pip install -r requirements-residential.txt
python scripts/collect_residential.py --output outputs/residential_2002
```

The collector resolves Monitor `main` once, pins all downloads to that immutable
commit, compares every copied cell, and saves the raw workbook, snapshot, report,
evidence and SHA-256 hashes under `outputs/residential_2002/raw/monitor/`.
Header drift, incompatible types, duplicated periods, missing model caches or
hash/value mismatches fail visibly. Existing workflows only publish successful
collections. No AI services, new credentials or Monitor changes are required.

For an exact historical copy, pass
`--monitor-commit c564a70ce4b8a6991e3af4205d2a516183d74128`.
For downloaded evidence, also pass `--monitor-snapshot PATH_TO_SNAPSHOT`.
That folder must include the `diagnostics.json` receipt saved by a prior pinned
collection. The supplied commit and every file digest must match that receipt.
`--from-saved` re-exports existing verified source parts without pretending to
check them again. Legacy saved parts without Monitor remain readable.

## Inspect the preview before publication

The small `preview/observations.parquet` file contains the integrated long table;
`preview/HK_Residential_Data.xlsx` contains the same values in grouped sheets.

```python
import pandas as pd

rows = pd.read_parquet("preview/observations.parquet")
rows["date"] = pd.to_datetime(rows["date"])
monitor = rows[rows.metric_id.str.startswith("monitor_")]
catalog = monitor.groupby("metric_id").agg(
    name=("metric_name", "first"), unit=("unit", "first"),
    first_date=("date", "min"), last_date=("date", "max"))
df = monitor.pivot(index="date", columns="metric_id", values="value")
df.loc["2025-01-01":"2026-10-31", ["monitor_completed_count", "monitor_offplan_count"]]
```

The package `Monitor()` interface is ready in this branch but production readers
continue using the current published residential endpoint until integration is
merged and collected. This distinction prevents silently redirecting existing
package users to an experimental dataset.

## Dashboard reproduction

The source build retains the project's already-customized standalone toolbar.
No protected runtime files are changed. With the existing locked Node/Vite
dependencies available, prepare the preview and run the repository build:

```sh
python src/content/dashboard/prepare_snapshot.py --input preview --collection-outcome success --build-status complete
npm run build
python src/content/dashboard/export_preview.py --input preview
python -m http.server 4186 --bind 127.0.0.1 --directory dist
```

For a local full-data run, use `--input outputs/residential_2002` instead.
The 70 MB full JSON snapshot is generated locally and is not added as another
large source commit. The Python reader transfers the compressed Parquet (about
1.1 MB), not this HTML. Dashboard menus retain source inspection, chart editing,
date filters and CSV export; Overview retains existing RVD market sections.

## Validation of this preview

The full Python suite passed 266 tests and the JavaScript suite passed 39 tests.
CSV, Excel, SQLite and Parquet were independently compared across all 100,424
observations. The source build verified all 240 protected runtime files unchanged.
Safari visual checks covered both pages, dates and reset, daily HIBOR ranges and
tenors, bank approval units, source inspection, the model's month alignment, and
light/dark readability. Mobile viewport and Windows execution were not tested.
This is a branch preview, not a production deployment or package release.
The measured cached filter time in `preview/verification.json` excludes network
latency and is a local benchmark, not a service-level guarantee.
