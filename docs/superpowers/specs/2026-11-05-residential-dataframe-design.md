# Pandas-first residential analysis

The user finds the record/metadata table too textual and wants the usability of
yfinance history. Diagnosis: version 0.4 returns 15 text columns and one float
column; the typed Arrow date is converted back to text for record compatibility.

Use the user's standing authorization to change the code efficiently. The chosen
implementation is an additive `Residential` object; changing the existing record
return type would break their existing loops, while notebook-only conversions
would keep making every user repair the same presentation problem.

## Interface

- `hk.Residential(series=None)` is lazy and may select one or several metric IDs.
- `.history(series=None, start=None, end=None, labels='name', timeout=90,
  refresh=False, cache=True)` returns a pandas DataFrame: sorted timezone-naive
  observation DatetimeIndex named `Date`; one float64 column per indicator;
  NaN for missing values. Friendly names are the default; `labels='id'` provides
  stable programmatic IDs. Duplicate friendly names are disambiguated with IDs.
- `.catalog(series=None, timeout=90, refresh=False, cache=True)` returns one row
  per metric, indexed by metric_id, with name, unit, frequency, all source names
  and URLs, first/last observation dates, row count and non-missing count.
- `.observations(...)` has the history filters, but returns the complete long
  record table with datetime observation dates, float values and categorical
  metadata. Per-observation flags, status and notes remain inspectable here.
- Method series overrides the constructor selection; omitted means the object
  selection. Unknown IDs raise ValueError. Empty date selections retain known
  numeric history columns. Dates are inclusive, as in existing readers.

## Constraints

Keep current collection, publication schema, record readers, SQL and downloads
compatible. Reuse the existing bounded session Arrow cache; no new disk cache or
network calls on warm reads. Convert Arrow directly to pandas after selection,
without converting the entire snapshot to dictionaries. Returned DataFrames may
be edited without changing cached data. Preserve zero, missingness, original
observation dates, units and frequencies; no resampling or automatic filling.

Pandas >=2.2,<4 becomes a dependency, imported lazily alongside PyArrow. Retain
Python >=3.10 (pip selects compatible library versions). Bump reader to 0.5.0.
History attrs carry a plain metadata mapping and snapshot generation time; the
catalogue collects multiple sources, rather than selecting an arbitrary first.
Duplicate metric/date observations or inconsistent name/unit/frequency for an ID
must fail visibly rather than be silently averaged. No dashboard work.

## Verification

Test types, missing and zero values, inclusive bounds, multiple/unknown metrics,
empty date slices, label collisions, conflicting units and duplicate observations,
metadata variants, mutation isolation, explicit refresh, shared-cache reuse and
lazy imports. Reconcile live numeric values with published rows; install and test
the released wheel and provide a short Jupyter example.
