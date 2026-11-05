# HK Property Data — read the residential GitHub dataset

GitHub stores the dataset and refreshes official sources daily at **18:00 Hong Kong
time**. The Python package reads the latest successful publication. It neither runs
the collectors nor creates local dataset, database, Excel or cache files. No AI,
API key, account or third-party runtime dependency is required. Python 3.10+.

## Install code once

In macOS, Linux or Windows Terminal:

```bash
python -m pip install --upgrade "https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/hk_property_data-0.3.0-py3-none-any.whl"
```

In a Jupyter cell use `%pip` instead of `python -m pip`. Restart the kernel after
upgrading an already-imported version. The wheel contains code, not the dataset.
Data updates do not require reinstalling the package; call the reader again.

## Read selected records

```python
from hk_property_data import fetch_residential, fetch_residential_status

print(fetch_residential_status())  # Small metadata request only.
rows = fetch_residential(
    series=["hk_m3_hkd", "hk_mortgage_approved_amount"],
    start="2020-01", end="2026-09",
)
print(rows[-3:])
```

`series` accepts one metric ID, an iterable of IDs, or `None` for all. Find IDs in
the Excel `Data_Dictionary`. An unknown ID returns no rows. `start` and `end` are
inclusive **observation dates**; `YYYY-MM` includes the full boundary month, and
`YYYY-MM-DD` selects exact dates. Omitted dates leave that boundary unrestricted.
Values are numbers or `None`; source dates, frequencies, units and flags remain.

Optional pandas conversion, if pandas is already installed:

```python
import pandas as pd
df = pd.DataFrame(rows)
```

## SQL without saving a database

```python
from hk_property_data import connect_residential

conn = connect_residential(series="hk_mortgage_approved_amount", start="2020-01")
try:
    result = conn.execute("""
        SELECT date, value, unit
        FROM observations
        WHERE value IS NOT NULL
        ORDER BY date DESC LIMIT 12
    """).fetchall()
    print(result)
finally:
    conn.close()
```

This reads selected GitHub records into **in-memory SQLite**, then executes SQL in
Python. It does not download/save a `.sqlite` file. GitHub itself does not execute
SQL. The returned connection is read-only. Use `pd.read_sql_query(sql, conn)` when
you want a pandas DataFrame. Close the connection to release its memory.

## CSV, Excel and SQLite files

```python
from hk_property_data import residential_url

csv_url = residential_url("csv")
excel_url = residential_url("excel")
sqlite_url = residential_url("sqlite")
```

All formats are generated from the same observation records. SQLite contains the
`observations` table and a `metadata` table with the publication's collection status.
The files remain available for an explicit download, Excel use or external tools.
For example, pandas can read `pd.read_excel(excel_url, sheet_name="Mortgage_Monthly")`
with its optional Excel engine installed. That loads the workbook into memory;
use the filtered record reader for smaller analytical requests. Ordinary SQLite
clients need a local database file; use `connect_residential()` to avoid one.

## Memory and network behavior

The reader streams `observations.csv.gz` from GitHub and decompresses incrementally.
Filters run on the client: a filtered request still transfers the compressed
stream, but does not retain the entire dataset. `fetch_residential()` stores only
the matching rows; `connect_residential()` stores only the selected SQL table.
Both use RAM proportional to the selection. For bounded-memory row processing:

```python
from contextlib import closing
from hk_property_data import iter_residential

with closing(iter_residential(series="hk_hibor_1m_daily", start="2026-01")) as rows:
    for row in rows:
        print(row["date"], row["value"])
```

Each call reads again; an existing list/DataFrame/connection never changes by itself.
There is no persistent local data cache. Package installation uses a small amount
of disk space. Status and observations are separate requests, so a publication can
occur between them. Per-record source-check dates remain in the returned records.

## Errors and compatibility

Network failures, corrupt compressed data and unsupported CSV layouts raise
`CloudDataError`; nothing silently falls back to an older local file. Streaming
consumers can receive some rows before a later network/corruption error; treat that
iteration as incomplete. A failed SQL load closes its partial database and raises.
Bad filter arguments raise `ValueError`. All readers accept a timeout in seconds.

Version 0.3.0 adds these residential interfaces. The older `fetch_dataset()` and
`fetch_status()` still read the **legacy dashboard** snapshots for compatibility;
that pipeline is suspended. Use the `*_residential` readers for the current dataset.
Legacy collection/export commands remain available for their older schema. To run
the current collector yourself, follow [RESIDENTIAL_DATA.md](RESIDENTIAL_DATA.md).
