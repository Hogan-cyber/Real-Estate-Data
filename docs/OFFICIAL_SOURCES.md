# Official data-source catalogue

All active dataset observations must have an HTTPS source URL on a Hong Kong government/regulator `.gov.hk` domain. HSBC and HKAB are benchmark originators for some rates; the collector now reads those rates only as published by HKMA. Direct HSBC/HKAB website records are excluded from the current dataset. Historical raw archives can retain earlier source vintages for audit; they are not active observations.

## Rating and Valuation Department

| Table | Dataset | Direct monthly file |
|---|---|---|
| 1.1 | Private residential average rents, class/district | [CSV](https://www.rvd.gov.hk/datagovhk/1.1M.csv) |
| 1.2 | Private residential average prices, class/district | [CSV](https://www.rvd.gov.hk/datagovhk/1.2M.csv) |
| 1.3 | Residential rental indices | [CSV](https://www.rvd.gov.hk/datagovhk/1.3M.csv) |
| 1.4 | Residential price indices | [CSV](https://www.rvd.gov.hk/datagovhk/1.4M.csv) |
| 1.5 | Popular residential development price indices | [CSV](https://www.rvd.gov.hk/datagovhk/1.5M.csv) |
| 2.1 | Office average rents | [CSV](https://www.rvd.gov.hk/datagovhk/2.1M.csv) |
| 2.2 | Office average prices | [CSV](https://www.rvd.gov.hk/datagovhk/2.2M.csv) |
| 2.3 | Office rental indices | [CSV](https://www.rvd.gov.hk/datagovhk/2.3M.csv) |
| 2.4 | Office price indices | [CSV](https://www.rvd.gov.hk/datagovhk/2.4M.csv) |
| 3.1 | Retail average rents and rental indices | [CSV](https://www.rvd.gov.hk/datagovhk/3.1M.csv) |
| 3.2 | Retail average prices and price indices | [CSV](https://www.rvd.gov.hk/datagovhk/3.2M.csv) |
| 4.1 | Private flatted factory rents and rental indices | [CSV](https://www.rvd.gov.hk/datagovhk/4.1M.csv) |
| 4.2 | Private flatted factory prices and price indices | [CSV](https://www.rvd.gov.hk/datagovhk/4.2M.csv) |
| 5.1 | Residential market yields | [CSV](https://www.rvd.gov.hk/datagovhk/5.1M.csv) |
| 5.2 | Commercial market yields | [CSV](https://www.rvd.gov.hk/datagovhk/5.2M.csv) |

The [rolling monthly supplement PDF](https://www.rvd.gov.hk/doc/en/statistics/full.pdf) supplies ten residential tables, including completions/forecast, with original frequency and page preserved. Tables 1.1–1.5 and 5.1 are compared with their CSVs; reported differences and confirmed revisions are retained. [Technical notes](https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) define prices, indices, yields and coverage. Residential price statistics exclude primary sales. Forecast, cumulative and monthly values remain separate.

## Land Registry

| Dataset | Official source | Collection |
|---|---|---|
| Total, primary and secondary residential agreements: counts and total consideration | [Series page](https://www.landreg.gov.hk/en/monthly/agt-primary.htm) | Discover all history blocks from the page's official JavaScript; read count/consideration JSONs; history begins January 2002 |
| Newer monthly residential totals | [Release catalogue](https://www.landreg.gov.hk/en/public/press.htm) | Follow official `info.gov.hk` release and `gia.info.gov.hk` annex links; parse Table 5 |
| All-property mortgage/charge/discharge instrument counts | [Monthly statistics](https://www.landreg.gov.hk/en/monthly/monthly.htm), [current Table 1 JSON](https://www.landreg.gov.hk/json/monthly_stat/monthly/t1.json) | Current/fixed-month JSON cross-check; monthly open-data archives from April 1993, e.g. [September 2026](https://www.landreg.gov.hk/datagovhk/202609_data.json) |

No free aggregate series here identifies residential sales with mortgages, the bank/non-bank lender sector, or purchase/refinancing purpose for each mortgage deed. [Measurement limits](MORTGAGE_METHOD.md).

## Hong Kong Monetary Authority

| Dataset | Official source / table | Basis |
|---|---|---|
| Residential mortgage applications, approvals, drawdowns, outstanding, delinquency, transaction-type splits and co-financing | [API definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey/), [T0307.xlsx](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T0307.xlsx), [monthly release catalogue](https://www.hkma.gov.hk/eng/news-and-media/press-releases/monthly-residential-mortgage-survey-results/) | Current-definition series from December 2016; latest annex supplements API/Excel and can revise the preceding month |
| Average new mortgage lending rate | [Half-yearly report catalogue](https://www.hkma.gov.hk/eng/data-publications-and-research/publications/half-yearly-monetary-financial-stability-report/) | Only explicit observation months in report text; not a continuously filled monthly series |
| HKD/all-currency M3 | [2.2.1 definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/money/supply-adjusted/), [T020201.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T020201.xls) | Adjusted new series from April 1997; month-end stock |
| HSBC Prime monthly average | [6.4.2 definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hkd-ir-periodaverage/), [T060402.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060402.xls) | Official monthly average |
| 1M/3M HIBOR monthly averages | [6.3.2 definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-periodaverage/), [T060302.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060302.xls) | HKAB fixing segment; not the discontinued alternative quotation segment |
| HSBC Prime effective-date history | [6.4.1 definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hkd-ir-effdates/), [T060401.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060401.xls) | Effective dates, not invented daily quotes or check dates |
| 1M/3M daily HIBOR | [6.3.3 definitions](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily/), [T060303.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T060303.xls) | Published daily fixings; each tenor keeps its own last observation |
| More recent 1M daily HIBOR | [Daily interbank liquidity API](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity/), [daily monetary statistics](https://www.hkma.gov.hk/eng/data-publications-and-research/data-and-statistics/daily-monetary-statistics/) | Dated published fixings; government [1823 calendar](https://www.1823.gov.hk/common/ical/en.json) supports dated-page discovery |
| Money and Credit: M3, domestic credit, nominal GDP YoY | [C01.xls](https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/C01.xls) | M3 and credit monthly; nominal GDP quarterly. Excel errors/blank cells are not values |

`source_url` on each record identifies the actual API, file or release used. `period`/`source_period` identify the observation period; `published_date`, when supplied by an official release, is separate; `checked_at` is the collector's check time. A successful check does not imply a new reference month has been published.
