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

## Fast Python access (0.4.0)

The collector produces one typed Parquet snapshot from the same observations as CSV,
Excel and SQLite. `residential_publish.py` builds the generated `api/` directory;
Actions commits it atomically to the `residential-data` branch after collection.
Release files remain available, including for older 0.3 clients.

`residential.py` downloads the direct Parquet URL once. `residential_parquet.py`
validates typed columns, null/finite values, source URLs, dates, checksums and schema,
then decodes dictionary columns. `residential_cache.py` holds one immutable Arrow
snapshot (8 MiB maximum) for the process session. Date/metric filters run in Arrow
before conversion to independent Python dictionaries. PyArrow is loaded lazily.

`refresh=True` evicts and reloads; a failed refresh does not return the old snapshot.
`cache=False` bypasses reads/writes to the session cache. `clear_residential_cache()`
releases it. Cache metadata exposes the loaded snapshot's generation time separately
from a new cloud status request. This stable-session policy follows the user's
explicit priority: first load may take time, subsequent exploration must be fast.

## Analysis DataFrames (0.5.0)

`residential_frame.py` owns the lazy `Residential` analysis object. `history()`
selects Arrow data before converting directly to pandas, with a DatetimeIndex and
float64 indicator columns. It preserves NaN, zero and original observation dates;
it never averages duplicate rows, fills gaps or resamples mixed frequencies.
`catalog()` separates indicator definitions and aggregates all observed sources;
`observations()` preserves per-record flags and notes in a typed categorical table.

Record readers and the analysis object share `_prepare_read` and the same bounded
snapshot. Return types of existing functions remain unchanged. New analysis
methods reject unknown IDs and conflicting definitions. Human labels can be
replaced by stable IDs; all-empty date slices retain known numeric columns.
DataFrame mutations cannot change cached Arrow values. Pandas is a required
dependency but is imported only on analysis access.
