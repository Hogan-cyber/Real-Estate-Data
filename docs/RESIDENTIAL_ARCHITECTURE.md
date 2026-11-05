# A small, stable residential dataset

GitHub is the publication/storage location. The package is a read-only consumer.
The system uses Python modules and files rather than a server or framework.

| Responsibility | Code | Change when |
|---|---|---|
| Official source collection | `python/hk_property_data/simple/{rvd,landreg,hkma,rates}.py` | A source changes or publishes a new field |
| Shared observation contract | `python/hk_property_data/residential_schema.py` | The common schema changes |
| Collection and machine exports | `scripts/collect_residential.py` | Publication formats change |
| Excel presentation | `python/hk_property_data/simple/export.py` | Workbook layout changes |
| Reader and in-memory SQL | `python/hk_property_data/residential.py` | Storage location or access method changes |
| Schedule and publication | `.github/workflows/residential-data.yml` | Refresh time or release process changes |

## Rules worth keeping

- One observation is identified by `(metric_id, period, frequency)`. `date` is the
  observation/cutoff date, not the download date. Keep source-check dates separate.
- Numbers remain numeric, missing values remain null/blank, units and source scope
  stay explicit. Never merge series whose definitions or frequencies differ.
- New indicators normally mean new rows/metric IDs, not new table columns. Reusing
  an ID for a different definition or unit corrupts history; introduce a new ID.
- Generate CSV, gzip CSV, SQLite and Excel from the same validated rows. Never fix
  one export by hand. SQLite and CSV share `COLUMNS`; Excel pivots those records.
- Keep reader function names/arguments stable. Changing the publication host should
  not require notebook users to change their analysis code.
- `SCHEMA_VERSION = 1` is stored in publication status and SQLite metadata. Adding
  optional fields can remain compatible; removing/renaming required fields or
  changing their meaning needs a new schema version and a client migration.
- Package version and dataset publication date are separate: data refreshes do not
  require a new wheel version. Changes to the reader do require a version bump.

## Safe, efficient changes

Change the smallest owning module. Add a focused regression fixture for a source
layout change, run the relevant tests, then the Python suite. For export changes,
re-export saved source records to check format equality without repeated crawling.
Before release, run one clean cloud collection and read the published result through
the package. Failed collection does not replace the previous successful Release.

The latest Release is a mutable current snapshot. Actions artifacts retain raw
sources and run snapshots for 30 days; this is **not** permanent revision history.
If research later needs historical publication vintages, add dated snapshots and
retention explicitly. When size or query traffic warrants it, replace file storage
with object storage or a database behind the same reader interfaces. Avoid adding
those operational dependencies merely to prepare for hypothetical scale.
