# Hong Kong Property Monitor

## [Open Dashboard →](https://hogan-cyber.github.io/Real-Estate-Data/)

Use the link above to view the live dashboard. No installation or login is required.

A dashboard of official Hong Kong residential and commercial property data. Residential coverage includes prices, rents, sales, mortgages and supply; Commercial covers offices, retail premises and private flatted factories. Public visitors can explore, filter and download the dataset.

## Run locally

Requires Node.js 24 and Python 3.10+.

```sh
npm ci
python -m pip install -r updater/requirements.txt
python updater/refresh.py --output data --app .
python updater/validate.py data
npm run dev
```

A refresh exit code of 2 means one or more sources retained their last valid observations. Inspect `data/refresh_status.json`. A fatal error stops publication. `npm run build` generates a static dashboard in `dist/`.

## GitHub Pages and monthly updates

The workflow `.github/workflows/monthly.yml` runs on the first day of every month at 02:00 UTC (10:00 Hong Kong), on manual dispatch, and when application code is pushed to main. It fetches official releases, validates the dataset, retains history in Git, builds the dashboard and deploys through GitHub Pages. It does not require a personal computer to be running.

Repository setup: open **Settings → Pages → Build and deployment → Source → GitHub Actions**. The workflow needs write permission for repository contents so it can retain history, plus Pages and OIDC deployment permissions. No external API key or personal access token is stored in source.

GitHub scheduled runs may be delayed. Public repository schedules can be disabled after 60 days of inactivity; successful monthly refresh commits maintain activity. Check the Actions tab if runs stop or fail. See [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

A source failure is visibly recorded. The workflow can deploy valid retained data, then reports the source issue as a failed run. It never silently replaces missing observations with zero. Website availability and source freshness are separate checks.

## Files

- `src/content/dashboard/`: English UI and charts.
- `src/data.json`: reviewed app snapshot, including original source URLs and statuses.
- `updater/refresh.py`: portable refresh pipeline.
- `updater/collectors/`: RVD PDF, Land Registry and HKMA collectors.
- `updater/archives/`: content-addressed public source vintages.
- `data/`: CSV / JSON outputs and refresh status; raw caches and SQLite are generated.
- `updater/DATA_DICTIONARY.md`: metric definitions, units and flags.

## Clear charts and comparisons

The Overview shows price and rent year-on-year changes, with exact month-on-month comparisons and the reference month. The large A–E price-index chart uses consistent colours, full size-class labels and dated endpoint values. Rental indices are separate. Missing observations remain gaps; no smoothing or interpolation changes the reviewed monthly values. All pages share Reference period.

## Coverage and caveats

The Sales & Mortgages page compares average residential prices for classes A–E in HKD per square foot, with district selection. Prices are converted from RVD table 1.2 using 0.09290304 square metres per square foot. Reference period is shared across the dashboard; both the price trend and latest-price table follow the applied range. The filtered price download preserves original values, units and flags.


RVD: monthly series since 1999, covering average prices/rents by size and district, price/rental indices, popular development indices and yields. Ten residential tables are extracted from the monthly PDF, with annual, quarterly, monthly, year-to-date and forecast rows kept separate.

Commercial: nine official RVD monthly CSVs (2.1–2.4, 3.1–3.2, 4.1–4.2, 5.2), covering office grades A–C and districts, retail and private flatted factories. Commercial averages use internal floor area; office grades are quality categories, not dwelling sizes. Averages are available in HKD per sq ft using the exact 0.09290304 conversion. The latest-value table never fills a missing current value with an older observation.

Land Registry: initial 24-month history for primary, secondary and total residential agreement counts and values; old observations are retained on each refresh. Registration month can lag the transaction date.

HKMA: monthly mortgage survey plus explicitly stated mortgage lending rates from half-yearly reports. The rate is not imputed for missing months. Pricing-method shares are never used as interest rates.

P means provisional; X/Y/Z mean fewer than 5/10/20 cases. Sale-price statistics exclude primary residential sales. Average prices/rents may shift with transaction mix. Market yields are not property-specific net rental yields.

Sources: [RVD](https://www.rvd.gov.hk/en/publications/property_market_statistics.html), [Land Registry](https://www.landreg.gov.hk/en/monthly/agt-primary.htm), [HKMA](https://www.hkma.gov.hk/eng/data-publications-and-research/publications/half-yearly-monetary-financial-stability-report/).

## How automated extraction works

Every run downloads the rolling RVD monthly PDF and official CSVs, discovers Land Registry JSON endpoints and the latest HKMA half-yearly PDF reports, then runs deterministic Python extraction. No GPT, LLM API key, OCR service or monthly manual file upload is required. RVD tables are located by table number and title, then parsed from text coordinates. PDF tables 1.1–1.5 and 5.1 are cross-checked with official CSVs. Differences are surfaced for review because later CSV revisions can be legitimate.

RVD CSV/PDF vintages, HKMA source PDFs and Land Registry raw JSON responses are archived by content hash. Source status distinguishes a successful check from new rows, revised values or a new PDF. A source can publish with a lag or remain unchanged; current checks do not independently enforce each agency's release calendar. Major layout or wording changes may require parser maintenance, with last valid data retained and failures reported.
