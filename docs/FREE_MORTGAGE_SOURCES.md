# Free Land Registry and mortgage sources

Checked 9 November 2026. These are public downloads and reports; no paid search
or subscription has been purchased. Existing official series remain in the
published dataset. Research reports below are leads, not new production inputs.

| Free source | Available information | Limitation for money-lender calculations |
| --- | --- | --- |
| [LR residential sales counts, t1 JSON](https://www.landreg.gov.hk/json/monthly_agt-pri/agt-primary/t1.json) | Monthly primary, secondary and total residential sale agreements | Sales include cash purchases; these are not mortgage counts. |
| [LR residential sales consideration, t2 JSON](https://www.landreg.gov.hk/json/monthly_agt-pri/agt-primary/t2.json) | Corresponding sale consideration, HKD million | Property sale value is not loan principal or drawdown. |
| [LR monthly instruments, JSON](https://www.landreg.gov.hk/json/monthly_stat/monthly/t1.json) and [monthly tables](https://www.landreg.gov.hk/en/monthly/monthly.htm) | Mortgage/charge and discharge document counts, with urban/New Territories totals | No residential/lender/refinancing split. Mortgage consideration fields contain `-`, not aggregate loan amounts. |
| [DATA.GOV.HK monthly LR archive example](https://data.gov.hk/en-data/dataset/hk-lr-data4-landreg/resource/5ad81535-a93e-4f8d-ac77-5c159facf8ae) | Historical monthly instrument JSON files | The same aggregate definitions and amount gaps apply. |
| [Centaline licensed-money-lender report, May 2025](https://hk.centanet.com/info/property-news/研究報告/放債人承辦住宅現樓樓按將連跌5年-料累計大減逾半-2025年首4個月一按比例向上迫近六成-二按則跌穿四成/183469) | Annual residential completed-property mortgage counts and January-April 2025 cumulative counts, by mortgage rank | No complete monthly amount series. Includes refinancing; first/second mortgages refer to lien rank, not primary/secondary property sales. Developer-linked licensed lenders can be included. |
| [HKMA March 2022 research, Box 4](https://www.hkma.gov.hk/media/eng/publication-and-research/quarterly-bulletin/qb202203/Chapter4.pdf) | Public analysis of bank/non-bank mortgages using individual LR records | Research charts and sample findings, not a released monthly money-lender count-and-amount dataset. Non-bank scope includes developer financing. |

The current residential t1/t2 JSON blocks begin in 2022; the existing collector
also follows older official archive blocks and already publishes residential
sales from 2002. On this check, the split reaches September 2026, while the
newer official release supplies October residential totals. Empty future rows
and annual `Total` rows are not monthly observations.

Examples checked directly: September 2026 t1 contains 1,502 primary and 3,259
secondary agreements, total 4,761. t2 contains HKD 46,808 million of combined
sale consideration. October 2026 instrument JSON contains 1 building mortgage /
building legal charge and 5,715 other mortgages/legal charges; both monetary
fields are `-`.

The dedicated Centaline reports inspected provide annual money-lender counts
for 2011-2014 and 2020-2024, plus selected cumulative 2024/2025 periods. This does
not establish a continuous monthly history. The ordinary monthly bank mortgage
market-share report has a different scope and must not be substituted for an
all-lender total.

No complete, freely downloadable monthly series satisfying all of residential
scope, licensed money lenders only, refinancing exclusion, count and actual
loan amount was located in this review. This is a search finding, not proof
that no additional public report exists.

The one-month registration lag and bank refinancing-share calculation are
explicit assumptions described in [MORTGAGE_ESTIMATES.md](MORTGAGE_ESTIMATES.md).
They do not fill the missing LR mortgage amounts or identify lender types.
