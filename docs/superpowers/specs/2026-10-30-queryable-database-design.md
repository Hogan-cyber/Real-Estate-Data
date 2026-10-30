# Downloadable property database

The user selected downloading the database for Python / SQL, retaining GitHub hosting. Extend the existing monthly SQLite export at the same public URL. No hosted SQL server, credentials or extra service is needed.

Alternatives considered: a hosted SQL/API database introduces another service and access policy; CSV/JSON alone retains the current query inconvenience. The selected SQLite approach works offline and is already supported by the monthly workflow.

Expose all current observation fields as typed SQL columns, retaining the existing seven columns and complete JSON payload. Keep monthly observations separate from PDF cells with mixed frequencies and forecasts. Include source statuses, dataset metadata, historical value revisions, PDF/CSV checks and their detailed differences. Provide latest-observation, metric-catalog and residential-sale-price views; do not replace missing latest values with older values or zero. Add indexes for common filtering.

Build a temporary database and atomically replace the exported file only after integrity/count checks. Every scheduled refresh invokes this same builder. Preserve all original units, values, flags, source dates and existing source warnings. Add a standard-library Python download/query example, SQL examples, a concise schema guide and dashboard download links. Re-downloading is explicit; a previously downloaded file cannot update itself.

Implementation choices: SQLite schema version 2, standard-library sqlite3 only, snake_case column names, exact HKD/sq m to HKD/sq ft multiplier 0.09290304, main observation key remains (metric_id, period) for this HK dataset. No change to chart calculations or filters.
