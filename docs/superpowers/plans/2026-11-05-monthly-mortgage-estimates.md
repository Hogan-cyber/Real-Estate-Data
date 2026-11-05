# Monthly mortgage estimates implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish the user's month-by-month allocation trial with traceable inputs and adjacent count/amount columns in the existing Mortgage_Monthly sheet.

**Architecture:** Add the all-building agreement count to the existing LR table extraction. A pure calculation module derives monthly estimates after collection and before the existing shared exports. Keep the reader and official observations unchanged.

**Tech Stack:** Python 3.10+, existing standard-library collector, openpyxl, Arrow.

**Spec:** [Monthly formulas and scope](../../MORTGAGE_ESTIMATES.md).

## Global constraints

- Use each month's own shares; remove refinancing only from the bank side as requested.
- Mark residuals as estimates, not observed pure money-lender loans; preserve negative residuals and blanks.
- Count and amount shares are distinct. All amount inputs and results are HKD million.
- Keep the public reader API, original observations, schema and 18:00 HKT schedule.

## Review focus

- Old/new LR schemas must count agreements, not units involved.
- Missing or zero denominators must not become zeros or borrow other months.
- Count ratios must never be reused for monetary ratios.
- Provenance and uncertainty must survive all four export formats.
- Adding data must stay within the reader's bounded snapshot capacity.

## Tasks

- [x] Add meaningful tests for LR counts, hand-calculated monthly estimates, missing/invalid input, negative residuals and export/readback.
- [x] Implement LR count extraction and `mortgage_estimates.build(rows)`; wire into every publisher run.
- [x] Add ordered three-column count/amount groups in the existing sheet, with source/formula comments; update README/local instructions.
- [x] Run collector/export tests, live local collection, format reconciliation and reader checks; review the patch.
- [x] Publish the authorized repository change; verify GitHub workflow and public reader output.

## Execution notes

User explicitly selected this trial and requested integration, sources, local execution and separate columns. Proceed directly within that authorization.

Ruling: Keep all new fields in the original Mortgage_Monthly sheet, following the user's subsequent clarification; no new estimate worksheet.

Additional authorized scope: generated indicator guide covering all 163 IDs,
expanded Python tutorials and downloadable/local-run instructions.

Local validation: 218 tests passed; clean live collection returned 75,420 rows
and zero source errors; CSV/Parquet/SQLite reconciled and Excel columns/comments
checked. The 118 complete residual months include six retained negative results.
Reader snapshot uses about 6.42 MB, below its 8 MiB limit. Independent code review
found no blocking issues; duplicate URL truncation in Excel was corrected.

Remote validation: source commit `086d3c51d32b9064dc20ec9cc3d9e182333088af`; GitHub Actions run `41986853050` succeeded, including Release and direct Parquet publication. Public package 0.5.0 read back all 163 indicators / 75,420 rows from snapshot `2026-11-05T07:25:27.213748+00:00`. Public Excel download verified the six adjacent result columns, complete source comments and 163 dictionary entries. The generated indicator guide is published on the residential-data branch and in the Release.
