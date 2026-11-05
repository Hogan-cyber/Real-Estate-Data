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
the extracted records. Nothing in these outputs is needed for a first run.

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

- Sales & Rent: residential registered sale agreements and consideration, primary
  and secondary breakdown; official RVD price/rent averages and indices by class
  and region; selected popular development indices; annual stock/completions/vacancy.
- Mortgage: official HKMA monthly survey fields, all-property mortgage/charge
  registrations (separate scope), quarterly negative-equity figures.
- Macro: M1/M2/M3 by HKD/foreign currency/total; daily HKAB HIBOR fixings published
  by HKMA; HSBC effective Prime rate history; source-published monthly rate averages.

Blanks remain blanks. No estimates, interpolation, artificial daily/monthly
conversion, trend calculation or forecasting. RVD average sale prices exclude
primary sales; Land Registry transactions and HKMA mortgage approvals measure
different events. Land Registry mortgage deeds cover all property types and do
not publish mortgage amounts in that table. HKMA loans supply residential amounts.
9-month HIBOR ceased in April 2014; overnight/1-week fixing coverage starts later
than other tenors. Effective Prime dates are rate-change dates, not stale-check dates.
Annual partial completions retain their actual cutoff and source flag.
An HKMA `*` write-off ratio means below its reporting threshold, not zero.

The script uses complete official CSV/Excel downloads first. Existing small
HTML/PDF routines supply newer official release periods when the workbook lags.
Unpublished categories remain blank even when a total is available. Source
warnings appear in `collection_status.json` and Excel; failed required sources
make the command exit nonzero. Published dates and detailed source scope stay
in the original raw tables and observation metadata.

## Automatic updates

The separate **Residential Excel collection** workflow runs daily at 18:00 Hong
Kong time and can be started manually. GitHub schedules may run later than their
nominal time. A successful run publishes the Excel, CSV, compressed CSV, SQLite and status JSON to
the `residential-data-latest` GitHub Release. Run artifacts also include original
source files and extracted records. This workflow does not depend on the dashboard.

## Read from GitHub without running collectors

The lightweight package reads the same published dataset. See [PYTHON_PACKAGE.md](PYTHON_PACKAGE.md)
for record filters, streaming, direct Excel/CSV URLs, and in-memory SQL. The reader
creates no dataset/cache file and has no third-party runtime dependencies.

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
