# Monthly mortgage allocation trial

This is the user-selected monthly trial, not an official money-lender survey.
Calculated rows use LR registration month t. The user-selected fixed lag is one month: bank drawdowns and refinancing approval shares both come from HKMA month t-1. Official observation dates and values stay unchanged.
Missing inputs stay blank; no interpolation, annual share, or zero clipping.

## Formulas

Let M be LR total mortgage/charge deeds (items 5 + 6), R residential sale
agreements, T all building-unit sale agreements, D bank drawdowns, A bank
approvals and F refinancing approvals. Subscripts n and a denote count and
amount (HKD million). LR inputs refer to t; D, A and F refer to t-1. This is a timing assumption, not a measured loan-level delay. For example, October 2026 LR registrations pair with September 2026 HKMA lending.

1. Residential sales share: s = R / T.
2. Residential mortgage count estimate: N = M * s.
3. Bank purchase drawdown count estimate: Bn[t] = Dn[t-1] * (1 - Fn[t-1] / An[t-1]).
4. Bank purchase drawdown amount estimate: Ba[t] = Da[t-1] * (1 - Fa[t-1] / Aa[t-1]).
5. Bank purchase average amount estimate: u = Ba / Bn.
6. Money-lender residual count estimate: Ln = N - Bn.
7. Residential mortgage amount scenario: V = N * u.
8. Money-lender residual amount scenario: La = V - Ba (= Ln * u).

Count and amount refinancing shares are separate. Amounts assume the allocated
non-bank loans have the same average size as estimated bank purchase drawdowns.
This assumption is not an observed money-lender average loan size.

## Interpretation

- The residential mix of mortgage documents is assumed to match the residential
  mix of sale agreements. Mortgage documents also cover land; the sales
  denominator covers building units. This allocation does not identify individual
  residential loans or fully remove non-residential properties.
- LR item 5, Building Mortgages/Building Legal Charges, means construction
  financing, not the total of ordinary building mortgages. The trial uses
  the published mortgage subtotal, items 5 + 6.
- Within the selected HKMA month t-1, approval purpose shares are proxies for drawdown purpose shares.
  Approvals, drawdowns and registrations may occur in different months, and
  documents need not correspond one-to-one to loans.
- As explicitly selected for this trial, refinancing is removed only from the
  bank side. LR's total is not stripped of refinancing. The residual therefore
  can contain bank refinancing, other lenders and timing/scope differences.
  It is **not a verified pure money-lender purchase-loan series**. Developer-related
  lending cannot be identified and excluded with these aggregates.
- Negative residuals remain visible with NEGATIVE_RESIDUAL; they indicate failure
  of the allocation assumptions for that month, not negative loan originations.
- Status and flags identify calculated shares, estimates and unavailable results.
  Every derived row records its input metric IDs, formula and original source URLs.
  Notes record `metric_id@t` or `metric_id@t-1`; `source_field` records the actual LR and HKMA source months. Join LR IDs at t and HKMA IDs at t-1. `REGISTRATION_LAG_ASSUMED_1M` identifies timing-aligned bank calculations and residuals. Missing preceding months stay blank; current or nearest months never substitute.

## Dataset and workbook

The existing `Mortgage_Monthly` sheet puts official observations first, followed
by three trial **counts**, three **amounts**, and the four supporting ratios / average
loan size. Each measure has its own column. The Contents and Mortgage_Monthly
opening views show the formulas and link to
[`mortgage_estimates.build`](../python/hk_property_data/simple/mortgage_estimates.py).
The calculated-data link jumps to the result columns.

The Excel data table retains numeric values for direct DataFrame reading; the
publisher performs the calculations in Python. Formula descriptions are visible
text, not an Excel calculation engine. Long per-observation notes and cell
comments are removed from Excel. Source URLs, source fields and indicator types
remain in `Data_Dictionary`; compact data statuses and negative-value formatting
identify exceptions. Full notes and flags remain in CSV, Parquet and SQLite.
No separate workbook or estimate worksheet is created.

## Interpreting a negative residual

The residual becomes negative when `M[t] * (R[t] / T[t]) < Dn[t-1] * (1 - Fn[t-1] / An[t-1])`.
This does not establish negative money-lender activity or an extraction error.
It shows that the allocation and timing assumptions fail to reconcile that month.

- Sale-agreement mix is not mortgage mix. Differences in mortgage use, property
  types and the timing of transactions can make the residential share of
  mortgage deeds higher than the residential share of sale agreements.
- HKMA approvals can be drawn in later months. The current month's approval
  refinancing share need not describe that month's drawdowns.
- LR measures documents received for registration; HKMA measures loans drawn.
  These are not matched loan cohorts. LR also documents a lag between execution
  and lodgement for registration.
- Keeping refinancing in LR while removing it from the bank estimate tends to
  increase the residual, all else equal. It does not explain a negative residual;
  removing it from LR as well would lower the residual further.
- The amount residual equals the count residual multiplied by the assumed bank
  average loan size. A negative amount is therefore not independent evidence.

For October 2026 comparisons, use September 2026 HKMA drawdowns of 4,788
loans and HKD 25,291 million. Refinancing approvals are 1,767 of 6,240 loans,
and HKD 8,940 million of HKD 31,835 million. The aligned bank non-refinancing
estimates are therefore 3,432.17 loans and HKD 18,188.71 million. These are
estimated drawdown-purpose splits, not reported drawdown breakdowns.

Official definitions: [HKMA survey notes](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey/),
[LR registration timing](https://www.landreg.gov.hk/pdf/en/aodp2022.pdf), and
[HKMA June 2024 survey](https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2024/20240731e6a1.pdf).

The six result IDs are:

| Measure | Count | Amount (HKD million) |
| --- | --- | --- |
| Residential total | `hk_residential_mortgage_count_estimate` | `hk_residential_mortgage_amount_estimate` |
| Bank excluding refinancing | `hk_bank_mortgage_purchase_drawn_count_estimate` | `hk_bank_mortgage_purchase_drawn_amount_estimate` |
| Money-lender residual | `hk_money_lender_mortgage_count_estimate` | `hk_money_lender_mortgage_amount_estimate` |

The reader does not run these calculations locally: the publisher saves them
alongside the official inputs in CSV, Excel, SQLite and Parquet. Use
`Residential(...).history(refresh=True)` once after publication to update a
previously loaded snapshot. The current detailed HKMA refinancing coverage starts
in December 2016; with the one-month registration alignment, dependent comparisons start no earlier than January 2017. Earlier dependent estimates stay blank.

## Sources

- [LR monthly tables](https://www.landreg.gov.hk/en/monthly/monthly.htm):
  Table 1 mortgage/charge subtotal and building-unit sale agreement counts;
  [residential registrations](https://www.landreg.gov.hk/en/monthly/agt-primary.htm).
- [HKMA residential mortgage survey](https://www.hkma.gov.hk/eng/news-and-media/press-releases/monthly-residential-mortgage-survey-results/):
  drawdown and approval counts/amounts, and refinancing approvals.
- [EAA definition of building mortgage](https://www.eaa.org.hk/en-us/Information-Centre/Publications/Monograph-Encumbrances/Interest-of-financier).

## Local modification

Run `python scripts/collect_residential.py` after installing
`requirements-residential.txt`. Change `REGISTRATION_LAG_MONTHS` in
`python/hk_property_data/simple/mortgage_estimates.py` to adjust this assumption. The default is 1; `build(rows, registration_lag_months=0)` reproduces a zero-lag comparison for inspection.
Then `python scripts/collect_residential.py --from-saved` recalculates it from
saved official inputs without downloading those inputs again. A normal run
refreshes the inputs and recalculates every month automatically.

## Why keep Negative_Equity_Quarterly?

This is a separate HKMA risk dataset: the quarter-end number and outstanding
balance of bank residential mortgages known to exceed collateral values, their
unsecured portion and reported delinquency. It measures the condition of existing
loans, not monthly new lending, and is not an input to this trial. Negative equity
does not itself mean a borrower has defaulted. HKMA's first-mortgage survey does
not measure all second-lien or money-lender risks.
