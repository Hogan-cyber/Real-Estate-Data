# Residential dashboard implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline implementation.

**Goal:** Publish the existing English Overview / Mortgage dashboard to the existing GitHub Pages site, with macro and rates prominent.

**Architecture:** Read one immutable published dataset commit. Retain original observations and provenance; chart selection never changes values. Existing standalone shell changes remove the AI controls the user previously requested removed.

**Tech stack:** Python / Parquet, React / shared Data app charts, GitHub Actions / Pages.

**Spec:** User's current two-page request and prior dataset-only, English, standalone, line / horizontal-bar requirements; docs/DASHBOARD.md records the resulting contract.

## Global constraints

- Preserve the existing app identity, GitHub repository and Pages URL.
- Latest macro cards have explicit scope independent of chart filters. Historical cards, charts and source rows share the selected range.
- Keep nulls, negative estimates and all original frequencies. Clearly distinguish model residuals from observed bank data.
- Preserve already published package work and unrelated local changes.

## Review focus

- Missing latest observations and comparisons without a common date remain empty.
- Rate-change dates are distinguishable from daily fixings and monthly averages.
- Source inspection and exported selections match plotted rows.
- Failed collections retain valid data and actual publication dates.
- Mobile controls, chart marks and English labels remain readable.

## Tasks

- [x] Update DashboardContent.jsx and residential.css: latest macro cards on both pages, prominent macro charts, selected-period market and mortgage charts. Verify rendered desktop and narrow views, period and indicator controls.
- [x] Verify prepare_snapshot.py and refresh status against immutable published data, existing selection tests and a full observation equality check. Build with the authorized source runtime; no collector or package changes.
- [ ] Update docs and workflow, review the dashboard-only diff against current main, publish, wait for Pages deployment and verify the live site.

## Validation record

- 37 JavaScript checks passed; current snapshot exactly matches all 75,422 published Parquet rows and all 16 fields.
- Two Python tests pass, including an API-outage regression reproduced before fixing it. Workflow-run events now pass the known collector conclusion directly.
- Browser: Overview / Mortgage, historical period selection and reset, common-period source preview, category-to-All reset, null-only series, negative residuals, and desktop / narrow daily-HIBOR charts checked.
- User refinement: daily HIBOR only in the dashboard; monthly HIBOR remains in the unchanged dataset.
- Source build is required by the previously authorized standalone AI-control removal. This runtime supports a single-file source build, not source mode with separate data.
