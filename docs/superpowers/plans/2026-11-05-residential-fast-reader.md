# Residential Fast Reader Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Speed up first and repeated GitHub reads without changing analysis calls or adding a server.
**Architecture:** One direct full Parquet file on a data branch; a bounded decoded Arrow session cache; existing Release compatibility.
**Tech Stack:** Python 3.10+, lazy PyArrow reader, existing GitHub Actions publication.
**Spec:** ../specs/2026-11-05-residential-fast-reader-design.md

## Global constraints
- Preserve the shared 16-column schema, values, provenance, missingness and inclusive observation date filters.
- No timer expiry; 8 MiB / one-snapshot bound; no persistent data cache; PyArrow loaded lazily for Parquet.
- Only data/client/publication files change. Dashboard migration remains separate.

## Review focus
- Force refresh failing while an old valid entry exists must raise and evict that entry.
- Partial/corrupt responses must never enter the cache.
- Changing indicators or dates must filter the same loaded snapshot without HTTP.
- Cache opt-out must fetch fresh data; returned dictionaries must not mutate cached Arrow buffers.
- Removed indicator files must not remain in the next published snapshot.

## Task 1: Direct reader and bounded caching
- [x] Add failing behavior tests in updater/tests/test_residential_fast.py for network-free repeat reads, date changes, session stability, refresh, corrupt transfers, fallback and caller mutations.
- [x] Implement the cache in python/hk_property_data/residential_cache.py and typed parsing in residential_parquet.py and route/validate responses in residential.py. Export cache controls in __init__.py; keep existing signatures compatible and bump to 0.4.0.
- [x] Run residential tests and fix regressions; exercise cache opt-out and concurrency.

## Task 2: Consistent fast publication
- [x] Extend updater/tests/test_residential_exports.py with Parquet/CSV equivalence, missing/zero values and removal of obsolete files.
- [x] Add export_fast_data(rows, status, directory) in residential_publish.py; invoke after exports from scripts/collect_residential.py.
- [x] Publish the generated directory atomically to the residential-data Git branch in the existing workflow after a successful collection.
- [x] Run the full Python suite, re-export saved sources, compare every fast observation against CSV/SQLite, and verify a clean CI collection. 195 tests passed; 72,142 observations reconciled (optional empty SQLite text normalized to empty strings).

## Task 3: Delivery and performance
- [x] Update README.md, PYTHON_PACKAGE.md, RESIDENTIAL_DATA.md and docs/RESIDENTIAL_ARCHITECTURE.md for 0.4.0, cache semantics and the direct endpoint.
- [x] Obtain an independent code review and address actionable issues. Corrected retained Arrow buffer accounting and stale descriptions; regression reproduced before the fix.
- [x] Merge/publish, install the public wheel in a clean environment, compare first/repeated/date-changed queries and values, verify no data files are written, and report measured limits. PR #5 merged; workflow 41962074442 succeeded. Public 0.4.0: cold 8.35 s, warm 1.48 ms, changed date 0.98 ms, rent/M3 1.09 ms. Warm reads were checked with HTTP forbidden; all 72,142 public rows matched CSV. Retained Arrow buffers: 5,618,641 bytes. Clean reader tests also passed on PyArrow 18.1.0.
