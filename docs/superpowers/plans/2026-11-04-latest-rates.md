# Latest rates correction implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline.

**Goal:** Correct latest Prime/HIBOR cards to show source-published effective/daily rates.
**Architecture:** Separate rate_observations from monthly observations. Collect HSBC effective history, HKMA recent daily 1M fixings and HKAB latest 1M/3M fixings. Merge with per-source retention; expose a separate reviewed query and downloadable outputs.
**Tech Stack:** Existing Python package, React, SQLite, XlsxWriter and GitHub Actions.
**Spec:** ../specs/2026-11-04-latest-rates-design.md

## Global constraints
Preserve official monthly averages, full provenance, existing layout and independent automatic operation. Daily/effective cards explicitly ignore historical Reference period. No future dates or fabricated observation dates.

## Review focus
Missing/new source failure must remain visible. Old selected September must not suppress the latest rate cards. Daily dates must not be monthly dates. Conflicting 1M source observations must not silently overwrite. Downloads must match reviewed data.

### Task 1: Source collection and persistence
- [ ] Write failing tests for date/basis/schema validation, October daily history, source conflict and outage retention.
- [ ] Implement collectors/hk_latest_rates.py and integrate pipeline.py with separately persisted rate_observations and rate source statuses.
- [ ] Extend database.py, export_excel.py and validate.py for separate rates; test output parity.

### Task 2: Latest cards
- [ ] Test latest rate choice independently of historical period and separately from monthly averages.
- [ ] Update MoneyRates.jsx and money-rates.js; keep monthly chart/filter code.
- [ ] Verify displayed dates, 1M/3M selection, October historical filter and sources in browser.

### Task 3: Publish and verify
- [ ] Update package/docs/workflow downloadable rate CSV. Run package, Python/JS tests and source refresh/build.
- [ ] Review changes, publish to existing repository, verify GitHub Actions and public webpage/downloads.
