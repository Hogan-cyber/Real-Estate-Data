# Built-in residential groups implementation plan

> Execute inline using the executing-plans workflow; one independent final review.

**Goal:** Replace notebook grouping boilerplate with `Residential.overview()` and
group-aware DataFrame queries.

**Architecture:** A small standard-library group registry classifies IDs. The
existing Arrow reader applies selectors and retains the session cache. pandas
builds overview and catalogue metadata only on data access.

**Tech stack:** Python 3.10+, existing pandas / PyArrow, unittest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-09-residential-groups-design.md`.

## Constraints and review focus

- Preserve raw observations and legacy ID queries; do not relabel estimates as official.
- Unknown future IDs remain accessible; overlapping prefix shares belong to estimates.
- Validate bad selectors before HTTP; an empty filter must never load all series.
- Keep constructor/method override semantics and mixed-frequency selection predictable.
- Reuse cache across grouped methods and legacy methods; refresh updates other readers.

## Task 1: Reader API

- [x] Add failing tests in `updater/tests/test_residential_groups.py` for group
  coverage, overview counts/nulls, date filters, multiple groups, frequency,
  constructor overrides, invalid inputs, unknown IDs and cache refresh.
- [x] Add `python/hk_property_data/residential_groups.py`; update
  `residential_frame.py`; run the new tests and existing residential reader tests.

## Task 2: Release and examples

- [x] Set package version to 0.6.0 in `pyproject.toml` and `__init__.py`.
- [x] Add `.github/workflows/python-package.yml` to test/build/publish the wheel
  on relevant main-branch pushes without running collectors.
- [x] Simplify README, PYTHON_PACKAGE.md, notebook and standalone example to
  use built-in groups; build/install the wheel and run the examples locally.

## Task 3: Verify and publish

- [x] Request one scoped independent review; resolve substantive findings.
- [ ] Publish only the package feature, its tests/docs/workflow, and this plan.
- [ ] Observe successful wheel publication; install the public 0.6.0 wheel in
  an isolated environment and execute the complete notebook and short API calls.
- [ ] Verify remote files and report the exact usable installation/example.

## Execution record

Current worktree already isolated; existing dashboard edits remain out of scope.
Main before this change: `8319c5ba04c78a2a4d4927f11f5a486bb4adb1e5`.

Local validation: missing API observed before implementation; 46 residential
tests and 33 simple collector/export tests passed afterward. The built 0.6.0
wheel was installed separately and all 14 groups / 16 group-frequency selections
matched the original published DataFrame values (163 indicators, 6,216 dates;
snapshot `2026-11-08T16:33:31.994076+00:00`). All six README analysis blocks ran.
On this machine first overview took 1.773 seconds and cached two-group history
median was 9.74 ms over 12 reads; these are observations, not speed guarantees.

Independent review completed. Added the main-branch-only publication guard,
limited mortgage-estimate classification to known mortgage families (an unknown
future estimate stays in Other), and corrected the troubleshooting upgrade target
to 0.6.0. The new classification regression failed before the correction; all 47
residential tests passed after it. The public upload guard was checked before and
after adding the condition. No review findings remain deferred.
