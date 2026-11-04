# Sales and mortgages: what can be measured

Scope reviewed on 4 November 2026. All current inputs are downloaded from Hong Kong government or regulator websites. The public dataset does **not** contain an estimate of total non-bank mortgage originations.

## Units, events and coverage

| Data product | Official source | What one count means | Amount means |
|---|---|---|---|
| Residential total / primary / secondary sales | [Land Registry](https://www.landreg.gov.hk/en/monthly/agt-primary.htm) | A residential sale and purchase agreement lodged for registration during the month | Total consideration, HKD million; not average flat price and not financing |
| Mortgage / legal-charge registrations | [Land Registry monthly instruments](https://www.landreg.gov.hk/en/monthly/monthly.htm) | A registered instrument, covering all property types and financing purposes | No mortgage loan amount is inferred |
| Receipts / discharges / releases | Same Land Registry instrument tables | A registered discharge/release instrument; not an application withdrawal | Not used to infer new lending |
| New mortgage approvals | [HKMA Residential Mortgage Survey](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey/) | A loan approved during the month by surveyed authorized institutions | Approved loan amount, HKD million |
| New mortgage drawdowns | Same HKMA survey | A loan drawn down during the month | Loan amount drawn down, HKD million |
| Mortgage outstanding | Same HKMA survey | Where a count is published, outstanding loans at month end | Month-end stock, HKD million; not new monthly lending |

The HKMA survey includes loans to individuals for residential purchases, including refinancing, and excludes the specified HOS, PSPS and TPS properties. Its stated approximately 99% coverage concerns the **banking sector's residential mortgage loans**, not the combined bank/non-bank market or precise count coverage. No scaling by 1/0.99 is performed.

Registration month can lag contract signing. Approval month and drawdown month can differ. Multiple documents and multiple loans can relate to one property; a transaction can also have both bank and non-bank financing. These are not interchangeable units.

## Valid derived series

For a given reference month and the same HKMA survey definition:

```
bank purchase approvals = primary-market approvals + secondary-market approvals
                       = total approvals - refinancing approvals
```

Both count and amount are stored with `observation_type=derived`, component metric IDs and the formula. Official input rows remain separate. Count reconciliation is exact; HKD-million amount reconciliation allows the official tables' rounding tolerance. No value is derived when required components are missing or inconsistent.

September 2026 example, published on 30 October 2026:

| HKMA metric | Loans | HKD million |
|---|---:|---:|
| Total approvals | 6,240 | 31,835 |
| Primary market | 1,499 | 8,452 |
| Secondary market | 2,974 | 14,443 |
| Refinancing | 1,767 | 8,940 |
| **Derived purchase approvals** | **4,473** | **22,895** |
| Drawdowns, all purposes | 4,788 | 25,291 |

Evidence: [HKMA September 2026 annex](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf). The result `4,788 - 1,767` would mix actual drawdowns with approvals of a different cohort and has no valid purchase-drawdown interpretation.

## Missing information for non-bank inference

The free aggregate tables do not provide:

- The number of residential sales linked to a mortgage.
- Purchase-only bank drawdowns, excluding refinancing drawdowns.
- A bank/non-bank lender classification for all mortgage registrations.
- Deduplicated transactions with joint bank and non-bank financing.

`total sales - bank loans` also includes cash purchases, unmatched dates and scope differences. `all-property mortgage deeds - bank loans` mixes instruments, property coverage and loan events. Neither residual is reported as moneylender mortgages.

Even with matched sets of mortgaged residential purchases, `all mortgaged purchases - bank-financed purchases` identifies only purchases financed **solely** outside banks, not every purchase involving a non-bank lender. Joint financing requires a separate category.

The Land Registry's [Monthly Memorial Information on Mortgage Transactions](https://www.landreg.gov.hk/en/services/services_b_8.htm) is a paid official service with document dates, property identifiers/address and non-individual mortgagee names. It is not a ready-made free monthly count of mortgaged purchases. A future loan/property-level classification would require access, residential and sale-record linkage, lender classification, and explicit deduplication/refinancing rules. This application has not purchased or subscribed to the service.

HKMA's [March 2022 study, Box 4](https://www.hkma.gov.hk/media/eng/publication-and-research/quarterly-bulletin/qb202203/Chapter4.pdf) uses detailed Land Registry data. Its historical findings are not extrapolated into a 2026 official series.

## Co-financing is not non-bank lending

The HKMA co-financing series covers mortgages involving government/private-sector top-up arrangements. Per survey note 6, **only the reporting institution's portion** is included; developers' or other lenders' second mortgages are excluded. Outstanding series are stocks; new approvals are flows. Each observation preserves this scope, and the Excel Interpretation column states it.

## Deterministic refresh and common dataset

GitHub Actions runs Python daily at 18:00 Hong Kong time; no AI, prompt, ChatGPT account or manual spreadsheet upload participates. The workflow:

1. Download official structured CSV/JSON/API/Excel files; discover new releases from official catalogues.
2. Parse and validate fields, reference periods, units and reconciliations. Latest HKMA PDF annexes supplement lagging API/workbook months and revisions.
3. Merge by `(metric_id, period)`; retain history and record changed official values. Missing values are not zero; missing breakdowns are not estimated.
4. Save the master JSON dataset, then generate CSV, SQLite, Excel and the dashboard from those same records.
5. Publish the dataset and dashboard together. The dependency-free Python package fetches that published JSON; it does not independently generate different numbers.

PDF extraction uses `pdfplumber` text extraction plus explicit row labels, column positions/periods and numeric validation. It does not use GPT interpretation or OCR inference. Original source bytes are archived by SHA-256. If labels/layouts change or downloads fail, the affected source is flagged and last valid data is retained; code cannot guarantee future official websites never change.

Residential sales history is read from all discovered Land Registry archive blocks. Instrument counts backfill public monthly JSON files from April 1993, with older cache checked again after 30 days and recent months checked every run. Latest instrument tables are reconciled against the dated archive. Successful old-cache reuse preserves its actual check date. The current-definition HKMA series begins December 2016; the older-definition worksheet is not silently spliced across its breaks.

## Download / query

- [Excel workbook](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_property_data.xlsx)
- [Master JSON](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_housing_dataset.json)
- [SQLite database](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_housing.sqlite)
- [Python package guide](../PYTHON_PACKAGE.md)

Rows expose official source URLs, reference months, publication dates where available, source fields, scope and derived/official status. SQLite retains the complete row in `payload` in addition to queryable columns. The Excel Interpretation and Original source note columns retain those distinctions. A downloaded workbook is a static snapshot; download it again after a new release.
