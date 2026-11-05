# Residential cloud reader implementation plan

> Execute inline using the executing-plans and test-driven-development skills.

**Goal:** GitHub stores and updates the residential dataset at 18:00 Hong Kong time; the package reads published data without saving local datasets.

**Design:** Keep one observation schema and generate Excel, CSV, gzip CSV and SQLite from it. Add a standard-library reader that streams gzip CSV, filters series and inclusive observation dates, returns records or an in-memory SQL connection. Keep legacy dashboard functions compatible but label them as legacy. Publish a small code-only wheel. GitHub hosts files; SQL runs in the caller's Python process.

**Constraints:** Python 3.10+, no new runtime dependencies for readers, no local data/cache writes, no scraper activity in readers, missing values preserved, no dashboard changes. Existing untracked duplicate files remain untouched. The user requested simple implementation and delegated routine choices; no additional design approval round.

**Approach:** A streamed compressed CSV is simpler than a new query server and avoids loading the full dataset into memory. Filtering is client-side and transfers the compressed stream. Per-series partitioning is deferred until scale warrants it.

## Task 1: Publisher and read interfaces
- [x] Add failing tests for filtering, numeric/null types, SQL results, transport/schema errors, bounded reads, and no disk writes.
- [x] Add `fetch_residential`, `iter_residential`, `connect_residential`, `fetch_residential_status`, and `residential_url` in `python/hk_property_data/residential.py`; expose them from the package.
- [x] Export gzip CSV and SQLite from the same observations in `scripts/collect_residential.py`; add schema version to status and SQLite metadata.
- [x] Verify scoped tests and saved-source export round-trip, including CSV/Excel/SQLite equality.

## Task 2: Schedule, distribution and documentation
- [x] Set workflow cron to `0 10 * * *` (18:00 HKT), publish all formats and version 0.3.0 wheel, and run reader tests before collection.
- [x] Update package documentation and README with current entry points, memory/network behavior, SQL usage and legacy boundaries.
- [ ] Run all Python tests and clean wheel installation without optional dependencies. Independently review the branch.
- [ ] Publish to GitHub, validate live workflow and query the actual published data from a clean temporary directory.

## Review focus
Malformed gzip/CSV must raise; empty and zero values must differ; date filters must include the full requested end month; stream iterators must close responses; partial downloads must not create a usable partial SQL connection. Existing `fetch_dataset` consumers must retain their old API and be directed to the new residential reader for current data.
