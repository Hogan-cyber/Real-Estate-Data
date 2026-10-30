# Queryable property database implementation plan

**Goal:** Make the existing downloadable SQLite database convenient and reliable for Python / SQL access.
**Architecture:** One deterministic builder consumes the existing dataset JSON and writes a versioned SQLite snapshot. The monthly workflow and local packaging share that builder. Keep the fixed public download URL.
**Tech stack:** Python standard library, SQLite, existing React dashboard and GitHub Actions.
**Spec:** ../specs/2026-10-30-queryable-database-design.md

## Constraints and review focus

- Preserve original values, nulls, flags, units and payloads; separate mixed-frequency PDF records.
- A failed build/download must preserve the prior local database.
- Latest means latest reference period, including a null value; preserve source warnings and revisions.
- Download examples must reject incomplete/unrelated SQLite files and use read-only parameterized queries.
- Keep the original observation columns, charts, update behavior and GitHub hosting.

## Tasks

- [x] Add failing tests in updater/tests/test_database.py for complete round-trip, duplicate/orphan rejection with atomic preservation, null latest values, metadata/warnings, separate PDF observations and price conversion.
- [x] Implement updater/database.py: build_database(dataset, destination), validate_database(connection, dataset); integrate in updater/refresh.py and updater/validate.py. Build twice and compare all records to the dataset.
- [x] Add examples/query_database.py and examples/queries.sql; test download failure/success and SQL parameter binding in updater/tests/test_database_client.py. Document schema and usage in DATABASE.md and README.md.
- [x] Add database and query-guide links in Data & Updates; update local delivery packaging to use the shared builder. Run Python/Node tests, build and browser-check download links.
- [ ] Review the scoped changes, upload through the existing authorized GitHub workflow, verify deployed SQLite and a real downloaded query, then package code/data and report any source warnings separately.

## Execution record

User chose the downloadable Python / SQL option. Existing state: 44,180 monthly rows, 1,896 PDF cells, 18 sources, 148 revisions; PDF/CSV vintage differences already surfaced by the pipeline. These are snapshot counts, not hard-coded schema expectations. Existing branch is a delivery checkout with previously published uncommitted files; preserve it and publish only scoped changed files atomically through GitHub.

Local verification: 12 Python tests, 23 Node tests, production build, all SQL examples, and desktop/mobile database links passed. Full monthly field/value/payload round-trip checked. UI contains a visible source warning inherited from official PDF/CSV vintage differences. The independent read-only final review found no actionable issues and confirmed all SQL examples plus PDF, source and revision round-trip consistency. Live download verification follows publication.
