# Residential dataset: 2002 onward

Run one command to download official source tables and generate Excel:

```bash
python -m pip install -r requirements-residential.txt
python scripts/collect_residential.py
```

Use Python 3.10 or newer. These are terminal commands (macOS, Linux or Windows).
From a Jupyter notebook use `%pip install -r requirements-residential.txt`, then
`!python scripts/collect_residential.py` while the current directory is this repository.
No OpenAI, ChatGPT, AI model, login, secret or paid API is used.

The generated `outputs/residential_2002/HK_Residential_Data.xlsx` contains three
business groups: **Sales & Rent**, **Mortgage**, and **Macro**. Tabs retain official
fields, units and frequencies. The `Data_Dictionary` provides sources and each
series' actual coverage. `observations.csv` is the same data in long format for
Python/R analysis. `raw/` retains the original downloaded files; `parts/` retains
the extracted records. `INDICATORS.md` explains every indicator and is regenerated
on each publication. Nothing in these outputs is needed for a first run.

Optional arguments:

```bash
python scripts/collect_residential.py --start 2002-01 --output my-data
python scripts/collect_residential.py --from-saved --output my-data
```

`--from-saved` only re-exports existing parts. It does **not** claim a live refresh.
`--as-of YYYY-MM-DD` bounds observation dates; it does not recreate past publication vintages.
Each normal run downloads current official tables again; revised historical values
therefore replace prior values. GitHub Actions artifacts preserve run snapshots.

## Tables and definitions

The [5 November 2026 source audit](docs/SOURCE_AUDIT_2026-11-05.md) reconciled all
72,142 published observations with official source values. It also identified
historical HKMA coverage gaps: additional mortgage details before December 2016
and negative-equity history before Q4 2016 exist in official announcements but
have not been backfilled. The negative-equity delinquency series currently contains
only the three quarters in the latest annex. A series' collected start date is
not necessarily the earliest date published by the authority.

- Sales & Rent: residential registered sale agreements and consideration, primary
  and secondary breakdown; official RVD price/rent averages and indices by class
  and region; selected popular development indices; annual stock/completions/vacancy.
- Mortgage: official HKMA monthly survey fields, all-property mortgage/charge
  registrations (separate scope), quarterly negative-equity figures, and the
  explicitly labelled [monthly allocation trial](docs/MORTGAGE_ESTIMATES.md).
- Macro: M1/M2/M3 by HKD/foreign currency/total; daily HKAB HIBOR fixings published
  by HKMA; HSBC effective Prime rate history; source-published monthly rate averages.

Blanks remain blanks. Official observations are not interpolated or converted
between frequencies. The mortgage trial adds separately identified calculated
and estimated indicators; these are not official money-lender observations.
RVD average sale prices exclude
primary sales; Land Registry transactions and HKMA mortgage approvals measure
different events. Land Registry mortgage deeds cover all property types and do
not publish mortgage amounts in that table. HKMA loans supply residential amounts.
9-month HIBOR ceased in April 2014; overnight/1-week fixing coverage starts later
than other tenors. Effective Prime dates are rate-change dates, not stale-check dates.
Annual partial completions retain their actual cutoff and source flag.
RVD annual supply has historical coverage changes: the table-specific sources
exclude village houses from 2003, while general technical notes say 2002. Treat
the 2002–2003 boundary cautiously. Annual completion notes also preserve the
2025 Starter Homes inclusion and earlier source-specific exceptions.
An HKMA `*` write-off ratio means below its reporting threshold, not zero.

HKMA collection uses the official APIs first, with the recovery rules below.
Other sources retain their existing official CSV/Excel/API collectors.
Unpublished categories remain blank even when a total is available. Source
warnings appear in `collection_status.json` and Excel; failed required sources
make the command exit nonzero. Published dates and detailed source scope stay
in the original raw tables and observation metadata.

## HKMA API and official-file supplements

| Dataset | Primary official API | Supplement |
| --- | --- | --- |
| Monthly residential mortgages | [Residential mortgage survey](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey/), `segment=new` and `segment=old` | Table 3.7 workbook for history gaps/API failure; latest survey PDF for missing fields or periods |
| Monthly M1, M2 and M3, by currency | [Adjusted money supply](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/money/supply-adjusted/), `segment=new` | Table 2.2.1 workbook for gaps/API failure; latest monetary-statistics PDF when necessary |
| Quarterly negative equity | [Residential mortgage loans in negative equity](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-loans-neg-equity/) | Table 3.16 workbook for gaps/API failure; latest PDF also supplies the delinquency ratio absent from the API |

No API key is needed. The collector follows pagination, rejects duplicate periods
and invalid values, preserves API percentage-point units, and checks that the
previously supported historical coverage is present. The pre-December-2000
mortgage survey population is excluded. API observations take priority; a source's
explicit `*` threshold is not turned into zero. PDFs fill missing observations
and do not overwrite available API values. When only files are available, survey
and negative-equity PDF revisions take priority over their workbooks; monetary
workbooks retain their more precise values.

The collector checks the official release listing even when API data are current.
It skips unnecessary PDF downloads for complete mortgage and money-supply API
responses. A failed API can recover from complete official files; the recovery
is reported, not described as API success. Unresolved coverage/freshness errors
prevent publication. Raw API responses and downloaded files remain in run
artifacts. `collection_status.json` → `hkma_collection` records the actual number
of API/workbook/PDF/retained observations and recovery events. Older observations
outside a current source's coverage are retained from the previous published
snapshot with their original check date and a `historical_retained` flag. This
cannot supply the latest required month/quarter. GitHub passes the prior Parquet
snapshot; local runs use the existing `parts/hkma.json`, or an explicit
`--previous-snapshot path/to/observations.parquet`. `source_url`, `source_table`
and `source_field` identify the actual source for each observation in every export.

The Python reader still loads published GitHub data and its local cache. Users do
not call HKMA when using `hk.Residential().history()` or `hk.fetch_residential()`. Daily HIBOR
continues to use the existing HKAB fixing collector; this migration does not
replace it with a monthly series.

## Automatic updates

The separate **Residential Excel collection** workflow runs daily at 18:00 Hong
Kong time and can be started manually. GitHub schedules may run later than their
nominal time. A successful run publishes the Excel, CSV, compressed CSV, Parquet, SQLite and status JSON to
the `residential-data-latest` GitHub Release. Run artifacts also include original
source files and extracted records. This workflow does not depend on the dashboard.

## Read from GitHub without running collectors

The lightweight package reads the same published dataset. See [PYTHON_PACKAGE.md](PYTHON_PACKAGE.md)
for numeric DataFrames through `Residential.history()`, indicator catalogues, typed
observation details, compatible record filters, Excel/CSV URLs and in-memory SQL.
Pandas and PyArrow load lazily and share one compact Arrow snapshot in RAM; the
reader creates no dataset/cache file. Use refresh=True for a new snapshot.

The shared observation contract is in `python/hk_property_data/residential_schema.py`.
All machine-readable formats use that contract; SQLite has an `observations` table
and a `metadata` table with the exact `collection_status` of that export.
See [maintenance boundaries](docs/RESIDENTIAL_ARCHITECTURE.md) before changing fields.

## Validation

```bash
PYTHONPATH=python python -m unittest discover -s updater/tests
python scripts/collect_residential.py --output /tmp/hk-residential-clean-run
```

The second command proves the pipeline can start with an empty output directory.
On Windows use a suitable empty folder instead of `/tmp/...`.

The generated `api/` directory contains the Parquet snapshot, manifest and status. After a successful collection, Actions publishes this directory atomically to the `residential-data` branch. Python reads its direct raw URL, with a visible Release fallback if the direct endpoint is unavailable. CSV and Excel remain manual download exports.
