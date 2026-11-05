# Source collection audit — 5 November 2026

**All 72,142 observations in the audited publication match the official source values checked. Historical coverage is incomplete for some HKMA indicators, and the audit identified source-definition and provenance metadata that needed correction.** Numerical agreement does not establish that every available historical observation has been collected.

The audit pinned data commit `b19b9e9ed145ac99ead544f70ad35bb847cdd7bb`, generated at `2026-11-05T04:06:38.346856+00:00`. It also ran the collector from an empty output directory with an observation cutoff of 5 November 2026. That independent run generated the same values and observation keys, with no collection failures. Later daily publications can supersede this snapshot.

## What was checked

| Source family | Indicators | Published observations checked | Independent comparison |
| --- | ---: | ---: | --- |
| RVD sales prices, rents, indices and annual supply | 82 | 16,989 | All CSV cells against published records; all values also compared with separately downloaded official XLS tables; selected PDF tables checked |
| Land Registry sales and mortgage documents | 10 | 2,976 | Official current/historical JSON fields and the latest release annex; residential totals kept separate from all-property totals |
| HKMA mortgage survey, money supply and negative equity | 49 | 8,421 | Workbook cells and separately transcribed latest PDF annexes, including overlapping periods |
| HIBOR and HSBC Prime | 11 | 43,756 | Daily/effective/monthly workbook cells; HSBC's five displayed rate changes; three dated daily monetary releases |
| **Total** | **152** | **72,142** | **No numeric mismatch found** |

The source comparisons use independent extraction/checking code rather than simply rerunning the production parsers. They verify extraction from official publications, not the authorities' underlying transaction-level compilation.

Dataset checks found zero duplicate indicator/date keys, missing required identifiers or source URLs, non-finite non-missing numbers, out-of-range observation dates, or changes in an indicator's unit/frequency/name. All 5,260 null values were labelled `Missing`; none was replaced by zero. Monthly records had month-end observation dates and no unexplained internal missing months within each collected series.

The published Parquet, compressed CSV, SQLite and Excel values reconcile for all 72,142 observations. Empty optional text in CSV/Parquet and SQL `NULL` were treated as equivalent missing metadata. Excel contains an additional 4,789 structural blank cells to align coverage. The fresh collection also reproduced the published values, units, dates and flags.

## Findings and corrections

### RVD annual coverage notes

The old note stated that village houses were excluded from annual supply statistics from 2002. RVD's table-specific data dictionary and supply workbook say 2003, while its general technical notes say 2002. The corrected metadata identifies this discrepancy and warns against interpreting the 2002–2003 boundary as a like-for-like change.

Annual notes also identify the source's 2004 conversions from subsidised to private flats, the specific 2015 and 2019 completions exceptions, and the inclusion of Starter Homes subsidised sale flats in completions from 2025. These qualifications affect interpretation; the published numeric values, observation dates and original CSV flags are preserved. Sources: [RVD data dictionary](https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf), [annual private domestic tables](https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls), [technical notes](https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf).

The 2023 net take-up value of **−1,837 dwellings** for units of at least 100 square metres is valid: take-up measures the net change in occupied units and can be negative. The independent source check confirms the value. Vacancy fractions also remain in their source scale: `0.043` means `4.3%`.

### HKMA source locations

The raw collector retained workbook cell references, but the public 16-field export omitted the internal `source_cell` and `source_sheet` fields. In the audited publication, 8,383 of the 8,421 HKMA records therefore had empty `source_table`/`source_field` values, although their source URL and scope notes were present.

The collector now maps workbook sheet/cell information and PDF table/field labels into the existing public `source_table` and `source_field` fields. The data schema and numeric values are unchanged. Use `Residential().observations(...)` to inspect these fields for a specific indicator and date.

### Historical HKMA coverage — still incomplete

| Indicator group | Current collected history | Remaining limitation |
| --- | --- | --- |
| Nine core mortgage survey measures, including total approvals and drawdowns | January 2002 onward | Old/new workbook groups are joined only within the expanded survey population |
| Additional mortgage details, including applications and primary/secondary/refinancing breakdowns | December 2016 onward | Earlier official announcements exist and have not been backfilled |
| Six core negative-equity measures | 2016 Q4 onward | Earlier quarterly announcements exist and have not been backfilled |
| Negative-equity delinquency ratio | 2026 Q1–Q3 in this snapshot | Only the three periods in the latest annex are collected |

For example, the [September 2016 mortgage release](https://www.info.gov.hk/gia/general/201610/31/P2016103100674.htm) reports 13,536 applications and provides an [annex with detailed approvals](https://gia.info.gov.hk/general/201610/31/P2016103100674_246487_1_1477906113468.pdf). The [September 2016 negative-equity annex](https://gia.info.gov.hk/general/201610/31/P2016103100666_246485_1_1477905387180.pdf) provides figures for three quarters before the current workbook coverage begins. These establish a collection gap, not an absence of official historical data. Archive backfill remains outstanding.

## Coverage and interpretation that must remain visible

- **Bank lending and money lenders:** `hk_mortgage_approved_amount` is HKMA's residential mortgage survey of authorised institutions. December 2025 is HKD 31,201 million, recorded at `T0307.xlsx`, sheet `T3.7`, cell `AC134`. It includes primary-market, secondary-market and refinancing approvals. Co-financed mortgages include only the reporting institutions' portion. There is no separate licensed-money-lender mortgage series in the dataset. [HKMA definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey/)
- **Land Registry:** October 2026 residential totals are 4,512 agreements and HKD 42,346 million. October primary/secondary cells are blank in the official source, so these four component series stop in September. Mortgage/charge/discharge document counts cover all property types and cannot be subtracted from bank approvals to infer money-lender lending. The reference month is registration, not necessarily the transaction month. [Official October release](https://www.info.gov.hk/gia/general/202611/03/P2026110300276.htm)
- **Rates:** All seven HIBOR tenor columns match the official daily workbook through 30 October 2026. The one-month series additionally has verified 2–4 November releases. Overnight and one-week numeric history starts in 2006; nine-month fixing ends on 31 March 2014. Remaining blank source cells are preserved. [HKMA fixing definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily/)
- **HSBC Prime:** The source page still quotes 5.00%, effective 31 October 2025. An unchanged effective rate is not a missing daily observation. Monthly averages are separate published series. [HSBC rate history](https://www.hsbc.com.hk/investments/market-information/hk/lending-rate/)
- **Partial annual data and revisions:** 2026 completions retain their actual provisional cutoff rather than a fabricated full-year date. A collection cutoff does not recreate a historical publication vintage; revised official history replaces older values on refresh.

No interpolation, inferred non-bank lending, or archive backfill was introduced by these metadata corrections. Source availability, collection completeness and numerical fidelity are separate checks.
