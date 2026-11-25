# Monitor integration into the residential dataset

## Scope and invariants

Audit `Hogan-cyber/HK-Mortgage-Monitor` read-only. All implementation belongs to
`Hogan-cyber/Real-Estate-Data`. Never execute or modify the Monitor updater,
workflow, workbook, repository settings, or published website.

Copy the Monitor workbook into the residential collection by immutable commit.
Verify all workbook cells against its published dashboard snapshot. Preserve
the workbook's saved model results and original reference months. Use separate
`monitor_` indicator IDs; existing official and legacy-model IDs retain their
meaning and coverage. Preserve nulls and signed estimates. No estimated amount
is invented when the Monitor workbook only supplies counts.

The original package continues using its bounded memory/disk Parquet cache.
Add `Monitor()` as a convenient filtered reader of the same residential data;
constructing or importing the reader must not download data or run collection.

Bring the Monitor's Overview/Mortgage presentation into the existing Data app,
retaining RVD residential coverage, app identity, source inspection, theme and
filters. Display actual observation periods and refresh status. Do not replace
the protected app runtime with a static dashboard.

## Task 1 — Collection and data contract

Test and repair current-day HIBOR collection before its 11:15 HKT publication.
Keep strict date matching after release. Add commit-pinned Monitor downloads,
workbook/header/snapshot validation, original check timestamps, explicit model
metadata, and a local reproducible snapshot option. Retain upstream reports and
hashes. Integrate into the original all-format publisher and Excel sheets.

Verification: targeted collector tests; full snapshot equality; independent
format parity across Parquet, CSV, SQLite and workbook.

## Task 2 — Reader and documentation

Expose lazy `Monitor()` with the existing history/catalog/overview APIs and
groups. Bump the package version and document both dataset views, the one-way
copy, model meaning and the unchanged fast cache. Test existing reader APIs,
multi-indicator/date filters, cold import and warm reads.

## Task 3 — Dashboard presentation

Use original public React bindings for macro cards, daily HIBOR, M3 and Prime;
Monitor registration, approvals, drawdown and residual charts. Retain RVD
sections and all-indicator exploration. Keep original legacy estimates out of
the Monitor model charts without deleting their data. Build and visually check
Overview, Mortgage, date/measure/series controls, sources and narrow layout.

## Task 4 — Integration validation and delivery

Run collection and relevant regression suites; review the whole branch with a
fresh reviewer; address material findings. Package a wheel and full dataset,
commit only intended changes, and publish the integration branch for review.
Keep Mortgage Monitor unchanged. Report audited limits separately from the
new branch's measured results and publication state.

## Decisions

- Work in a clean managed worktree to preserve unrelated local edits.
- Monitor names use a distinct namespace because the old LR proxy is a
  different method; reusing IDs would silently change existing analyses.
- Initial delivery is a tested integration branch/preview: the request says
  to begin copying, so the original public dashboard is not replaced before
  the user can review the concrete result.

## Review focus

No Monitor writes; exact copied values; honest model/source definitions;
immutability and failure handling; preserved existing APIs and fast cache;
real visible charts and coherent filter/source scopes.
