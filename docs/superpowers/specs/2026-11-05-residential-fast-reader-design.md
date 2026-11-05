# Faster GitHub residential reads

The user requested a yfinance.Ticker-style experience, then explicitly chose Parquet
for Python and clarified that first-load delay is acceptable: the priority is fast
exploration after loading. Keep GitHub storage, deterministic cloud updates, the
existing fetch_residential call, and CSV/Excel/SQLite as optional manual downloads.

Download one full Parquet snapshot from the direct raw GitHub data branch. Validate
its typed 16-column contract and page checksums, then decode dictionary columns into
one immutable Arrow table. Repeated indicator/date filters run against this same
table before converting selected rows into independent Python dictionaries. Do not
write local data/cache files. PyArrow is installed once and imported lazily.

Keep one snapshot for the process session, with no timer replacing data mid-analysis.
refresh=True evicts and reloads, bypassing HTTP caches; failure cannot silently return
the old snapshot. cache=False bypasses memory reuse without replacing a prior snapshot.
clear_residential_cache releases it; cache_info reports retained bytes, source, loaded
time and snapshot generation time. The decoded table is cached only up to 8 MiB;
larger tables can be read but are not retained. The downloaded file is limited to 8 MiB.
Current retained Arrow size is about 5.6 MB; compressed bytes are discarded after decode.

The collector writes Parquet, manifest and status to generated api/. After successful
collection, Actions commits those files atomically to residential-data. Release assets
remain available for manual downloads and old 0.3 clients. A direct endpoint availability
failure can visibly fall back to the Release. Successful malformed responses fail;
unknown indicators produce an empty selection. Data formats must agree exactly.

Alternatives considered: compressed-byte caching still reparses each query; per-indicator
files repeat network work when switching indicators; a database/API service adds unnecessary
operations. Following the user's clarification, one decoded session snapshot is the simplest
fit. This supersedes the initial per-indicator/five-minute-cache proposal. A stable analysis
snapshot does not update automatically when the daily GitHub publication changes; explicitly
refresh it or restart the kernel. Existing independent Python lists also remain unchanged.
