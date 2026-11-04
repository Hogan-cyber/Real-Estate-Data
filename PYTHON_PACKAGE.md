# HK Property Data — cloud data package

`hk-property-data` is a Python interface to the dataset published by the Hong Kong Property Monitor. **Install the package once, then call `fetch_dataset()` to retrieve data for your own analysis.** It does not require ChatGPT, an API key or a running dashboard. Python **3.10+** is required.

The default package has **zero third-party runtime dependencies**. It does not install, upgrade or import pandas, NumPy, SciPy or python-dateutil. Crawling public sources and producing exports are optional `[collector]` tools used by GitHub Actions.

## Install

### Jupyter Notebook / JupyterLab

[Open the example notebook](examples/HK_Property_Data.ipynb) · [Download `.ipynb`](https://raw.githubusercontent.com/Hogan-cyber/Real-Estate-Data/main/examples/HK_Property_Data.ipynb)

Run this cell once, or when upgrading the package. `%pip` installs into the active notebook kernel. The small wheel contains code only and does not require Git:

```python
%pip install --upgrade "https://hogan-cyber.github.io/Real-Estate-Data/packages/hk_property_data-0.2.0-py3-none-any.whl"
```

If an older version was already imported, **restart the kernel after upgrading**. Then run this separate Python cell:

```python
from hk_property_data import fetch_dataset, __version__

data = fetch_dataset()
monthly = data["observations"]
rates = data["rate_observations"]

print("Package:", __version__)
print("Published source-check time:", data["checked_at"])
print("Monthly records:", len(monthly))
print("Daily/effective rate records:", len(rates))
```

The returned object is a normal Python dictionary; each table is a list of dictionaries. Data is transferred from the cloud into memory. This call creates **no local dataset, database, Excel or cache file**, and does not run the collectors. Reading the whole current snapshot transfers about 44 MB, so allow for your network speed.

### Terminal — macOS, Linux or Windows

Use `python` for your selected interpreter (`python3` on some Macs, or `py` on Windows). Run this outside Python or Jupyter:

```sh
python -m pip install --upgrade "https://hogan-cyber.github.io/Real-Estate-Data/packages/hk_property_data-0.2.0-py3-none-any.whl"
python -c "from hk_property_data import fetch_status; print(fetch_status()['checked_at'])"
```

After installation, the same Python examples work in `.py` files. `%pip` is Jupyter/IPython syntax only. The package wheel is published alongside the dashboard; source code is in GitHub. It is not published on PyPI.

## Use the dataset

```python
from hk_property_data import fetch_dataset

data = fetch_dataset()

# Original monthly M3 observations, including their source dates and missing values.
m3 = [row for row in data["observations"]
      if row["metric_id"] == "hk_m3_hkd"]

# Published daily fixings, kept separate from official monthly averages.
hibor = [row for row in data["rate_observations"]
         if row["metric_id"] == "hk_hibor_1m_daily"]

print(sorted(hibor, key=lambda row: row["date"])[-5:])
```

Available fields:

| Field | Contents |
|---|---|
| `observations` | Monthly property, commercial, mortgage, money and rate observations |
| `rate_observations` | Daily HIBOR and effective-date HSBC Prime records |
| `pdf_observations` | Extracted PDF cells with their original reporting frequencies |
| `source_status` | Source checks and latest available source periods |
| `revisions` | Retained changes to earlier monthly observations |
| `errors`, `warnings` | Source failures and informational comparison notes |
| `checked_at`, `as_of` | Publisher's source-check time and observation cutoff |

Values, missing values (`None`), original units and provenance are preserved. Prime dates are rate-change effective dates; HIBOR dates are fixing dates. A recent check is not evidence of a new monthly release. Historical coverage differs by series; daily 3M HIBOR is limited to the collected snapshots.

### Optional pandas conversion

If pandas already works in your analysis environment, convert the returned records:

```python
import pandas as pd

monthly_df = pd.DataFrame(data["observations"])
rates_df = pd.DataFrame(data["rate_observations"])
```

Pandas is optional and is never installed by this package. The supplied notebook works without it. Do not upgrade an existing Anaconda environment's numerical packages just to read this dataset.

### Check for a newer publication

```python
from hk_property_data import fetch_status

status = fetch_status()  # Small metadata request; does not transfer observations.
print(status["checked_at"])
print(status["errors"])
```

The existing GitHub Actions schedule refreshes official sources daily at 18:00 Hong Kong time and publishes the dataset, Excel, SQLite and dashboard together. Each `fetch_dataset()` call requests the latest **published** JSON snapshot; it does not trigger a new crawl or reuse a package-local cache. Call it again to update your in-memory variable. An already-returned dictionary does not change by itself. No package reinstall is needed when data changes.

`fetch_status()` and `fetch_dataset()` are separate requests; a publication can occur between them. Use `data["checked_at"]` to identify the exact snapshot in memory. This is read-only HTTP access to published files, not a remote SQL execution service.

## Errors and existing environment conflicts

- `CloudDataError`: the cloud file could not be fetched or its schema is unsupported. The call fails explicitly and does not silently fall back to an old local file. Both cloud functions accept a `timeout` in seconds.
- `SourceDataWarning`: the retrieved snapshot contains unresolved official-source refresh errors. Last valid observations may have been retained by the publisher. Inspect `data["errors"]` and `data["source_status"]`; the original published check time is preserved.
- Existing pip warnings mentioning `tables`, `gensim`, `numba`, `botocore` or `conda-repo-cli` concern requirements in the surrounding environment. The old notebook unnecessarily requested a pandas upgrade; that instruction has been removed. Version 0.2.0 neither needs those libraries nor repairs earlier version conflicts. It can read the cloud data without importing the numerical stack.

## Excel for colleagues

[Download the published Excel workbook](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_property_data.xlsx) · [Download SQLite](https://hogan-cyber.github.io/Real-Estate-Data/data/hk_housing.sqlite)

These are generated by the cloud update job. Click to save a file only when needed. Cloud reads through the Python package do not create these files locally.

## Optional collector tools — maintainers

The shared GitHub Actions workflow installs the extra below. Ordinary dataset users do not need it. It retains the existing deterministic official-site collection, PDF parsing, validation and Excel/SQLite builders.

```sh
python -m pip install "hk-property-data[collector] @ https://github.com/Hogan-cyber/Real-Estate-Data/archive/refs/heads/main.zip"
hk-property-data refresh --output company-data
hk-property-data validate company-data
```

Unlike `fetch_dataset()`, **`refresh()` crawls official sources and writes local files**. It returns 0 on successful refresh, or 2 when valid exports were generated with source issues requiring review; fatal failures raise exceptions. Reuse the output folder to retain history and caches. Installation does not schedule a local job. The `--app` argument additionally generates the dashboard snapshot; it is unnecessary for ordinary cloud reads.

The previous APIs `refresh`, `load_dataset`, `build_excel`, `build_database` and `validate` remain available. Refresh/PDF/Excel operations require the optional tools; missing dependencies produce an installation instruction. `load_dataset()` reads a saved JSON file offline. A full export consistency check is run by the cloud pipeline before publication.

For local development and tests:

```sh
python -m pip install ".[collector]"
python -m unittest discover -s updater/tests
python -m pip install build
python -m build --outdir package-dist
```

The wheel contains code only, never the dataset or archived PDFs. Company deployments may pin a reviewed commit or install a reviewed wheel. Code upgrades and cloud data updates are independent.
