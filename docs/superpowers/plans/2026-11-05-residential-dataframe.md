# Residential DataFrame Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to execute inline.

**Goal:** Return a ready-to-analyse numeric DataFrame without repeated metadata.
**Architecture:** A lazy Residential facade over the existing Arrow session cache.
**Tech Stack:** Python >=3.10, PyArrow >=18,<27, pandas >=2.2,<4.
**Spec:** ../specs/2026-11-05-residential-dataframe-design.md

## Global Constraints
- Preserve all existing record/SQL interfaces and public dataset fields.
- No interpolation/resampling, disk cache, import-time network or eager pandas.
- Use DatetimeIndex plus float64 values for history; expose metadata separately.

## Review Focus
- NaN/zero, empty date ranges and all-missing series must preserve columns/types.
- Duplicate dates and metadata/name collisions must not lose or average data.
- Multiple source names for one indicator must remain visible.
- Mutating returned DataFrames must not corrupt the shared Arrow cache.
- Old readers, bad inputs and failed forced refresh keep their existing behaviour.

### Task 1: Numeric DataFrame interface
**Files:** residential.py, residential_parquet.py, new residential_frame.py,
__init__.py, pyproject.toml, requirements-residential.txt,
new updater/tests/test_residential_frame.py; existing reader/package tests.
**Interfaces:** Residential.history/catalog/observations as specified in the spec.
- [x] Write failing behaviour tests for the new interface and run them (RED).
- [x] Share query validation/snapshot loading with the record reader; implement
  Arrow selection and lazy pandas conversion; export Residential and bump 0.5.0.
- [x] Run focused tests and the complete Python suite; compare real data types,
  values, cache reuse and cold/warm timing.

### Task 2: Documentation and delivery
**Files:** README.md, PYTHON_PACKAGE.md, RESIDENTIAL_DATA.md,
docs/RESIDENTIAL_ARCHITECTURE.md.
- [x] Make history the primary analysis example; document catalogue, typed
  observations, cache/refresh, inclusive dates, original frequencies and units.
- [x] Execute examples; build a clean wheel excluding unrelated local files;
  verify minimum supported dependency family and import-time behaviour.
- [x] Obtain one independent whole-change review and resolve material findings.
- [ ] Publish the code and wheel; verify live collection and a clean public
  installation, value equality, typed DataFrames, and no data files written.
