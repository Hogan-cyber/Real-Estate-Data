# Hong Kong Property Monitor

## Residential Excel dataset — 2002 onward

The new data-collection entry point is [RESIDENTIAL_DATA.md](RESIDENTIAL_DATA.md).
It downloads official Land Registry, RVD, HKMA and HSBC tables, then produces one
Excel workbook and a long-format CSV grouped into Sales & Rent, Mortgage and Macro.

```bash
python -m pip install -r requirements-residential.txt
python scripts/collect_residential.py
```

[Download the latest successful dataset](https://github.com/Hogan-cyber/Real-Estate-Data/releases/tag/residential-data-latest)
or inspect the [independent collection workflow](https://github.com/Hogan-cyber/Real-Estate-Data/actions/workflows/residential-data.yml).
The legacy dashboard pipeline below is currently suspended; these Excel updates
run separately and do not republish the dashboard.

## Read the residential dataset from Python

GitHub stores and updates the dataset daily at **18:00 Hong Kong time**. The package
reads its published files; it does not run the crawler or save local data/cache files.
Install the small code-only wheel (Python 3.10+, no third-party runtime dependencies):

```bash
python -m pip install --upgrade "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.3.0-py3-none-any.whl"
```

```python
from hk_property_data import fetch_residential, connect_residential

rows = fetch_residential(series="hk_m3_hkd", start="2020-01")
conn = connect_residential(series="hk_mortgage_approved_amount", start="2020-01")
print(conn.execute("SELECT date, value FROM observations ORDER BY date DESC LIMIT 3").fetchall())
conn.close()
```

Use `iter_residential()` for bounded-memory row processing, or `residential_url()`
for CSV, Excel and SQLite file URLs. Filtering happens while reading the compressed
CSV stream; returned lists/DataFrames and SQL tables still use RAM. GitHub is file
storage, not a remote SQL server. See the [package guide](PYTHON_PACKAGE.md) and
[maintenance boundaries](docs/RESIDENTIAL_ARCHITECTURE.md).

## Legacy dashboard documentation — updates suspended

The sections below describe the older dashboard and its exports. Use the residential
Release and reader above for the actively updated dataset. `fetch_dataset()` and
`fetch_status()` remain legacy compatibility functions.

## [Open Dashboard →](https://hogan-cyber.github.io/Real-Estate-Data/)

Use the link above to view the live dashboard. No installation or login is required.

The **Updated / Refresh data** menu works independently of any AI:

- **Check latest published data** checks the public website for a newer data release. It reloads when one exists, preserving the selected tab and reference period. If no newer release exists, it shows the actual source-check time; it does not change the data timestamp. Network errors leave the displayed data intact. Offline HTML copies open the public website.
- **Run source update on GitHub** opens the [existing update workflow](https://github.com/Hogan-cyber/Real-Estate-Data/actions/workflows/monthly.yml). Sign in with repository write access, choose **Run workflow**, select **main**, and run it. After deployment finishes, use **Check latest published data** on the dashboard. This starts the same Python collectors as the daily schedule, without ChatGPT.

Visitors can check and read published data without signing in. Starting a new official-source crawl requires GitHub repository access; the public page contains no write token. Automatic source checks continue regardless of whether anyone opens the dashboard.

A dashboard of official Hong Kong residential and commercial property data. Residential coverage includes prices, rents, sales, mortgages and supply; Commercial covers offices, retail premises and private flatted factories. Public visitors can explore, filter and download the dataset.

## Dataset-first update workflow

The persistent dataset is the foundation of the dashboard. Every refresh follows this sequence:

1. Fetch official public sources and validate their dates, fields and values.
2. Merge new observations into existing history using series and period/date keys. Keep older records that have disappeared from rolling downloads, and record revisions to monthly values.
3. Save the master dataset as `data/hk_housing_dataset.json`, together with the CSV exports and source status.
4. Generate Excel, SQLite and the dashboard snapshot from that same batch of records. Before publication, validate their agreement, including original values and dates.

GitHub retains the JSON/CSV dataset, revision history and archived raw sources in repository commits. Excel and SQLite are generated downloads published alongside the dashboard. A downloaded file is a snapshot; download it again to receive later updates.

The Python package reads this published dataset with `fetch_dataset()`. It returns data in memory for analysis; it does not crawl official sites or create local files. The optional `[collector]` tools run the existing source-refresh and export pipeline in GitHub Actions.

## Download data in Excel

[Download the latest Excel workbook (.xlsx)](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_property_data.xlsx)

Open `hk_property_data.xlsx` directly in Excel to read and filter the data. It includes an overview, residential prices and rents, indices and yields, commercial property, sales and mortgages, Money & Rates, PDF tables, source checks and revision history. Each data sheet has readable headings and filter controls. Average sale prices include HKD per square foot as well as the original per-square-metre values.

The workbook contains **all available periods**, independently of dashboard Reference period and chart selections. Use Excel filters to choose a month, district, size class or property type. Missing observations remain blank and source warnings are retained. Download the workbook again after a refresh to update your local copy.

The existing daily Python workflow rebuilds and publishes Excel at the same link, without ChatGPT, a login or an API key. The **Data & Updates** page makes Excel the main download; CSV, JSON and SQLite remain under **Other formats**.

## Download and query the database

[Download SQLite database](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_housing.sqlite) · [Database guide](DATABASE.md) · [Python example](examples/query_database.py) · [SQL examples](examples/queries.sql)

The same daily task publishes a queryable database containing monthly observations, PDF cells, sources, revision history and source-comparison warnings. Regions, size classes, property types and provenance are ordinary SQL columns. Ready-to-use views provide a metric catalog, latest observations and A–E average sale prices per square foot. No account or API key is needed. Re-download the file to receive future updates; downloaded copies work offline.

```sh
python examples/query_database.py --download --list-metrics
python examples/query_database.py --metric rvd_1_4_all_classes --start 2020-01 --format csv > price_index.csv
```

## Run locally

Requires Node.js 24 and Python 3.10+.

```sh
npm ci
python -m pip install ".[collector]"
hk-property-data refresh --output data --app .
hk-property-data validate data
npm run dev
```

A refresh exit code of 2 means a source was retained or a source comparison needs review. Inspect `data/refresh_status.json`. A fatal error stops publication. `npm run build` generates a static dashboard in `dist/`.

## GitHub Pages and daily source checks

The workflow `.github/workflows/monthly.yml` runs every day at 10:00 UTC (18:00 Hong Kong), on manual dispatch, and when application code is pushed to main. It fetches official releases, validates the dataset, retains history in Git, builds the dashboard and deploys through GitHub Pages. It does not require a personal computer to be running.

Repository setup: open **Settings → Pages → Build and deployment → Source → GitHub Actions**. The workflow needs write permission for repository contents so it can retain history, plus Pages and OIDC deployment permissions. No external API key or personal access token is stored in source.

GitHub scheduled runs may be delayed. Public repository schedules can be disabled after 60 days of inactivity; successful refresh commits maintain activity. Check the Actions tab if runs stop or fail. See [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

A source failure is visibly recorded. The workflow can deploy valid retained data, then reports the source issue as a failed run. It never silently replaces missing observations with zero. Website availability and source freshness are separate checks.

## Files

- `src/content/dashboard/`: English UI and charts.
- `src/data.json`: reviewed app snapshot, including original source URLs and statuses.
- `python/hk_property_data/`: installable collectors, pipeline, validation and export API.
- `updater/refresh.py`: compatibility entry point for the package.
- `python/hk_property_data/export_excel.py`: builds the company-ready Excel workbook from the same validated dataset.
- `python/hk_property_data/collectors/`: RVD PDF, Land Registry and HKMA collectors.
- `updater/archives/`: content-addressed public source vintages.
- `data/`: CSV / JSON outputs and refresh status; raw caches, SQLite and the Excel workbook are generated.
- `updater/DATA_DICTIONARY.md`: metric definitions, units and flags.

## Clear charts and comparisons

The Overview shows price and rent year-on-year changes, with exact month-on-month comparisons and the reference month. The large A–E price-index chart uses consistent colours, full size-class labels and dated endpoint values. Rental indices are separate. Missing observations remain gaps; no smoothing or interpolation changes the reviewed monthly values. All pages share Reference period.

## Money & Rates

The **Money & Rates** tab follows Sales & Mortgages and uses the same Reference period. M3 offers HK-dollar and all-currency views, with levels and exact-year-over-year changes. The HKMA adjusted new series starts in April 1997; the older series is not spliced across that methodology break.

M3 is measured at **month end**, in HKD million. **HSBC prime rate** and **1-month / 3-month HKAB HIBOR** use **officially published monthly averages**, in % p.a. Each series updates independently when its source publishes a newer monthly value; otherwise it retains its latest published reference month. Daily fixings and effective-rate history are not used to create additional monthly observations. Prime is HSBC's quoted best lending rate; HIBOR is a market benchmark rather than an HSBC quote. Neither is an actual mortgage borrowing rate. The reference month and measurement basis remain visible in the chart, Excel and database.

Sources: [HKMA Monthly Statistical Bulletin](https://www.hkma.gov.hk/eng/data-publications-and-research/data-and-statistics/monthly-statistical-bulletin/), tables 2.2.1, 6.4.2 and 6.3.2. The collector uses the API and falls back to the same official Excel table if the API is unavailable; it records the actual source URL and format and archives the retrieved file.

## Coverage and caveats

The Sales & Mortgages page compares average residential prices for classes A–E in HKD per square foot, with district selection. Prices are converted from RVD table 1.2 using 0.09290304 square metres per square foot. Reference period is shared across the dashboard; both the price trend and latest-price table follow the applied range. The filtered price download preserves original values, units and flags.

The Sales chart's **Chart view** selector offers **Price (HKD / sq ft)** and **Log price · ln(P)**. The log view takes the natural logarithm of each positive converted price; it is a price-level transform, not a percentage change or log return. Dates, districts and missing observations retain the same meaning. The latest-price table and price CSV retain actual prices. The default view remains Price.


RVD: monthly series since 1999, covering average prices/rents by size and district, price/rental indices, popular development indices and yields. Ten residential tables are extracted from the monthly PDF, with annual, quarterly, monthly, year-to-date and forecast rows kept separate.

Commercial: nine official RVD monthly CSVs (2.1–2.4, 3.1–3.2, 4.1–4.2, 5.2), covering office grades A–C and districts, retail and private flatted factories. Commercial averages use internal floor area; office grades are quality categories, not dwelling sizes. Averages are available in HKD per sq ft using the exact 0.09290304 conversion. The latest-value table never fills a missing current value with an older observation.

Land Registry: full published residential agreement count/consideration blocks from January 2002; separate all-property mortgage/charge/discharge instrument counts from April 1993. Registration month can lag the transaction date.

HKMA: monthly mortgage survey via API or its official Excel fallback, supplemented by the latest official survey-annex PDF when it is newer; plus explicitly stated mortgage lending rates from half-yearly reports. The rate is not imputed for missing months. Pricing-method shares are never used as interest rates.

P means provisional; X/Y/Z mean fewer than 5/10/20 cases. Sale-price statistics exclude primary residential sales. Average prices/rents may shift with transaction mix. Market yields are not property-specific net rental yields.

Sources: [RVD](https://www.rvd.gov.hk/en/publications/property_market_statistics.html), [Land Registry](https://www.landreg.gov.hk/en/monthly/agt-primary.htm), [HKMA](https://www.hkma.gov.hk/eng/data-publications-and-research/publications/half-yearly-monetary-financial-stability-report/).

## How automated extraction works

Every run downloads the rolling RVD monthly PDF and official CSVs, discovers Land Registry JSON endpoints and its latest official monthly release annex, plus HKMA monthly survey annexes and half-yearly PDF reports, then runs deterministic Python extraction. No GPT, LLM API key, OCR service or monthly manual file upload is required. RVD tables are located by table number and title, then parsed from text coordinates. PDF tables 1.1–1.5 and 5.1 are cross-checked with official CSVs. Differences remain inspectable. A provisional PDF cell is classified as a confirmed revision only when its exact old and current values match recorded CSV revision history and the current CSV was successfully refreshed. Unexplained differences still require review.

RVD CSV/PDF vintages, HKMA source PDFs and Land Registry raw JSON responses are archived by content hash. Source status distinguishes a successful check from new rows, revised values or a new PDF. A source can publish with a lag or remain unchanged; the mortgage and residential-sales collectors also check their latest official release catalogs so a newer announcement can supplement a lagging statistical feed. Major layout or wording changes may require parser maintenance, with last valid data retained and failures reported.

### Publication freshness and partial coverage

The daily job runs at 18:00 Hong Kong time; releases are picked up on the next successful check, not streamed in real time. Each metric uses its latest officially published period, so a newer release for one metric does not advance the reference month of another. HKMA survey data use the API, an official Excel fallback, and newer official survey-annex PDFs. Land Registry totals can be supplemented from its newer monthly release annex; primary/secondary figures remain missing until the official breakdown is available. Totals are reconciled against components only for months in which all components have been published. Raw annexes and source links are retained.

PDF comparison notes never overwrite printed PDF values. Confirmed revisions require an exact recorded CSV revision chain; unexplained changes and failed downloads remain visible. Revision logging ignores at most two binary floating-point steps introduced by API/Excel serialization; it retains original values and records substantive changes and missing/zero transitions.

## Latest rate cards

Card dates use **YYYY-MM** from the official record: the effective month for HSBC Prime and the fixing month for HIBOR. The program's check time never advances this label. Full effective/fixing dates and check timestamps remain separate in the dataset and card tooltip; formatting the label does not turn a daily rate into a monthly average. M3 continues to show its reference month.

Money & Rates shows current HSBC effective Prime and the latest published 1M/3M HKAB HIBOR daily fixings. These cards are explicitly independent of Reference period; the interest-rate chart defaults to **Daily rates**, with a **Monthly averages** option retaining the separate HKMA official monthly series. Daily history, the chart, Excel and SQLite use the same `rate_observations` snapshot. The reference-period selector includes newly collected fixing dates; older saved links offer **Show latest data**. Effective/fixing dates and source-check dates are distinct. Daily and effective observations are stored separately as `rate_observations` in the dataset and SQLite, `hk_rate_observations.csv`, and the Excel sheet `Daily & Effective Rates`. The same daily GitHub workflow fetches these sources without AI. Before publication, `hk-property-data validate data --app .` checks JSON, CSV, Excel, SQLite and the dashboard snapshot together, including values, source URLs, reference-period coverage and refresh timestamps. A mismatch stops publication.


## Source audit and mortgage dataset

- [Complete Overview source, formula and display audit](docs/OVERVIEW_AUDIT.md)
- [Sales/mortgage definitions and why a non-bank residual is not identified](docs/MORTGAGE_METHOD.md)
- [Official source catalogue](docs/OFFICIAL_SOURCES.md)
- [Python mortgage-data example](examples/inspect_mortgages.py)

This update prioritises the dataset. Primary/secondary/refinancing bank approvals and their amounts are collected from HKMA; purchase approvals are separately marked derived. Actual drawdowns remain their own official total. Land Registry residential sales and all-property mortgage/charge/discharge documents remain separate units. No `total moneylender mortgages` series is fabricated from incompatible aggregates.

Only government/regulator-hosted source observations are accepted. Daily HIBOR and HSBC Prime effective dates now come from HKMA 6.3.3 / 6.4.1; direct HSBC/HKAB website records are excluded. C01 Money and Credit is fetched from HKMA, with monthly M3/credit growth and quarterly nominal GDP retained at their actual frequencies.
