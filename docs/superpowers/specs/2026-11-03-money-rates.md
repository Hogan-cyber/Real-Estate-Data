# Money & Rates dashboard addition

User-approved coverage: Hong Kong dollar M3 by default, all-currency toggle; HSBC Prime rate; 1-month HIBOR by default with 3-month toggle. Add a distinct Money & Rates tab immediately after Sales & Mortgages, preserving existing overview and chart identity.

Use HKMA official monthly series: adjusted M3 table 2.2.1, HSBC-referenced monthly-average best lending rate table 6.4.2, HKAB HIBOR fixing monthly-average table 6.3.2. Keep original levels and units. M3 change uses the exact same month twelve months earlier; rate changes use percentage points. All displays respect Reference period; computation may reference prior-year source rows outside the display interval. Never fill missing values or call a monthly rate a live quote.

One large M3 level line, one separate annual-change line and one Prime/HIBOR comparison keep units distinct. Top cards show latest reference months per series, preserving missing latest values. Excel receives a Money & Rates sheet with raw series, sources and linked change calculations. Existing GitHub schedule and newly packaged Python code collect and validate the same data without AI. API and official Excel fallback have explicit fetch-mode/source metadata.

Verify source parsing and pagination, basis/units, empty and missing periods, exact YoY and pp changes, Excel calculations, package installation, scheduled workflow and published browser interactions.
