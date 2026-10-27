# Hong Kong Housing Monitor

## [Open Dashboard →](https://hogan-cyber.github.io/Real-Estate-Data/)

Use the link above to view the live dashboard. No installation or login is required.

A dashboard of official Hong Kong residential prices, rents, sales, mortgages and supply. Public visitors can explore, filter and download the dataset.

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

## Coverage and caveats

RVD: monthly series since 1999, covering average prices/rents by size and district, price/rental indices, popular development indices and yields. Ten residential tables are extracted from the monthly PDF, with annual, quarterly, monthly, year-to-date and forecast rows kept separate.

Land Registry: initial 24-month history for primary, secondary and total residential agreement counts and values; old observations are retained on each refresh. Registration month can lag the transaction date.

HKMA: monthly mortgage survey plus explicitly stated mortgage lending rates from half-yearly reports. The rate is not imputed for missing months. Pricing-method shares are never used as interest rates.

P means provisional; Z means fewer than 20 cases. Sale-price statistics exclude primary residential sales. Average prices/rents may shift with transaction mix. Market yields are not property-specific net rental yields.

Sources: [RVD](https://www.rvd.gov.hk/en/publications/property_market_statistics.html), [Land Registry](https://www.landreg.gov.hk/en/monthly/agt-primary.htm), [HKMA](https://www.hkma.gov.hk/eng/data-publications-and-research/publications/half-yearly-monetary-financial-stability-report/).
