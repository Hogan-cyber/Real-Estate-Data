# Residential dashboard

The public dashboard is [Hong Kong Property Monitor](https://hogan-cyber.github.io/Real-Estate-Data/).
It has two English pages: **Overview** and **Mortgage**. Time trends use lines; category comparisons use horizontal bars.

## Data contract

The dashboard reads the same published Parquet dataset used by `hk_property_data`. It does not crawl official sites, call an AI model, or recalculate mortgage estimates. All 16 fields of every observation are retained, including nulls, negative estimates, original source labels, flags and reference dates. English presentation labels and definitions are separate from those original fields.

- Both pages open with the latest published HSBC effective Prime rate, daily 1-month and 3-month HIBOR fixings, and HK-dollar M3. These headline observations explicitly retain their own dates and are independent of the chart-period filter.
- Overview: daily HIBOR and money supply first, then prices, rents, residential transactions and annual supply. Monthly-average HIBOR is not displayed or offered in the indicator browser; those series remain unchanged in the full dataset.
- Mortgage: bank approvals and drawdowns, approval purposes, all-property registration documents, existing residential / bank / money-lender estimates, and quarterly negative equity.
- The indicator browser exposes the other published indicators, including those not featured in the opening charts. Choose a category and indicator, and optionally a second indicator with the same unit and frequency.
- The reference-period control applies to historical charts and market/mortgage cards across both pages. Those cards show the latest non-missing observation within that range and its own period. The top macro cards retain the latest published snapshot. Bars use one common observed period for every compared category.
- The existing money-lender series are model residuals, not observed pure licensed money-lender lending. Their assumptions and limitations remain visible. Quarterly and annual data retain their original grain.
- Chart source menus and selected CSV exports use the current chart/table selection. Footer workbook/database downloads contain the complete latest published dataset; their release may be newer than a dashboard left open in a browser.

## Automatic updates, without AI

1. `Residential Excel collection` collects official data at 18:00 Hong Kong time and publishes the dataset. GitHub schedules can start later than the nominal time.
2. .github/workflows/monthly.yml also runs after an unsuccessful collection to show the failed attempt while retaining the last valid data. On a successful collection, `.github/workflows/monthly.yml` (`Residential dashboard`) reads one immutable commit of the `residential-data` branch.
3. `prepare_snapshot.py` binds that dataset to the dashboard and records its URL, SHA-256, coverage and collection time. It adds no observations or calculations.
4. The workflow verifies the UI logic, builds static HTML using the pinned Node dependencies, and deploys the existing GitHub Pages site.

No OpenAI key, ChatGPT subscription, AI service or local computer is needed for scheduled updates. Ask / Publish / AI conversion controls are removed. Local chart editing, themes, data source inspection, copy actions, CSV export, full-data downloads and browser print remain available.

The **Updated** menu checks the same website's `data/refresh_status.json`. It reloads only if a newer dataset is already published; it does not start a collector or silently claim old data was refreshed. The GitHub action link is provided for an owner-triggered source update. A failed collection retains the last published dataset and adds a visible failure note. A failed website build leaves the previously deployed website available; the failure remains recorded in GitHub Actions.

## Run locally

Requirements: Python 3.10+ and Node.js 22.12+ (GitHub uses Node 24). From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-residential.txt
npm ci
python src/content/dashboard/prepare_snapshot.py --published --build-status complete
npm run build
python src/content/dashboard/export_status.py
python -m http.server 8000 --directory dist
```

Open `http://localhost:8000/`. On Windows, activate with `.venv\Scripts\activate` instead. `prepare_snapshot.py` must run before building: the source checkout's bundled snapshot is not the live data endpoint.

To use an existing local collector output instead of fetching GitHub:

```bash
python src/content/dashboard/prepare_snapshot.py --input outputs/residential_2002 --build-status complete
npm run build
python src/content/dashboard/export_status.py
```

The source URL remains the dataset's publication reference; the recorded checksum identifies the exact local input. Original observations remain unchanged.

For development after preparing data, use `npm run dev`. Edit app-specific UI and helpers in `src/content/dashboard/`. Keep the collector and reader package separate. The scoped runtime changes for this dashboard remove AI handoffs; integrity checks remain enabled.
