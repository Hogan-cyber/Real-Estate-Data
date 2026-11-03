# Installable Hong Kong property data package

Goal: distribute the existing collectors and validated Excel/SQLite exporters as one portable Python package, usable by colleagues and the scheduled GitHub workflow.

Architecture: keep canonical code in python/hk_property_data. Existing updater scripts become compatibility entry points. Installation includes code only; all data and caches are written to a caller-selected directory. No AI service is used. The frontend and source definitions remain unchanged by packaging.

- [ ] Add package contract tests: imports must be side-effect free; CLI help works; refresh default is cwd/data; exports function from an unrelated directory.
- [ ] Move Python implementation once, repair relative imports and PDF subprocess paths, expose an API and CLI. Preserve source failure status 2 and fatal failure status 1.
- [ ] Build wheel/source distribution outside the dashboard dist directory. Install the wheel in a separate environment and run the contract plus existing collector/export tests.
- [ ] Make monthly workflow install and call the same package. Document exact commands and distinguish package installation from scheduling.

Checks: do not bundle observations or caches; missing values remain missing; bad rebuild retains prior exports; no writes to site-packages; legacy scripts resolve to the canonical implementation; monthly warnings remain visible.
