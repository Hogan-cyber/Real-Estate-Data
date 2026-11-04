# Latest rate cards correction

The user expects latest published Prime and HIBOR cards above monthly trends. Current cards incorrectly use monthly-average observations. Keep the existing monthly series and charts unchanged, while collecting source-published HSBC effective rates and HKAB/HKMA daily fixings separately. Latest rate cards are explicitly independent of the historical Reference period; show fixing date or effective date plus check date. Keep 1M/3M selection. Never relabel daily fixings as monthly averages or derive unpublished monthly figures.

Approaches: source-published latest cards plus official monthly trends fits the clarified intent. Calculating monthly averages would alter the selected monthly methodology and is excluded. Only retaining monthly cards fails the requested freshness.

Use the existing Python package and daily GitHub Actions job. Persist separately in JSON, CSV, SQLite and Excel with original sources and status. Per-source failures retain last valid daily data with a visible warning. Backfill available recent daily history, including October 1M fixings. Preserve existing code, archives, app identity, layout and monthly data.
