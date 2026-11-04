# HK Property Data — Python package

`hk-property-data` packages the same official-source collectors, validation rules and Excel/SQLite builders used by the Hong Kong Property Monitor. It does not need ChatGPT, an OpenAI key, or a running dashboard. Python **3.10 or newer** is required.

## Install

Choose **one** of the following environments. These commands install the package from GitHub, so Git must be installed. Do not paste a terminal command such as `pip install ...` into a Python editor or a `>>>` prompt: it is not Python syntax.

### Jupyter Notebook / JupyterLab

Run this installation cell. `%pip` installs into the current notebook kernel's environment:

```python
%pip install --upgrade "hk-property-data @ git+https://github.com/Hogan-cyber/Real-Estate-Data.git"
```

Then run this separate Python cell to download the data and produce Excel:

```python
from hk_property_data import refresh

status = refresh(output="company-data")
print("Completed" if status == 0 else "Exports saved; review company-data/refresh_status.json")
```

If you already imported the package before upgrading, restart the kernel after installation. `%pip` is notebook/IPython syntax; it does not belong in an ordinary `.py` file.

### macOS / Linux Terminal

Open **Terminal**, then paste this block. If you see `>>>`, exit Python with `exit()` first.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade "hk-property-data @ git+https://github.com/Hogan-cyber/Real-Estate-Data.git"
python -m hk_property_data refresh --output company-data
```

### Windows PowerShell

Open **PowerShell**, then paste this block. It uses the virtual environment directly, without changing PowerShell's activation policy:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade "hk-property-data @ git+https://github.com/Hogan-cyber/Real-Estate-Data.git"
.\.venv\Scripts\python.exe -m hk_property_data refresh --output company-data
```

### Normal Python editor / `.py` script

This is ordinary Python syntax and also works in a notebook. It runs installation and collection with the same Python interpreter as your editor. Your selected environment must allow package installation; a virtual environment is recommended. Run installation once or when upgrading:

```python
import subprocess
import sys

subprocess.run(
    [sys.executable, "-m", "pip", "install", "--upgrade",
     "hk-property-data @ git+https://github.com/Hogan-cyber/Real-Estate-Data.git"],
    check=True,
)
result = subprocess.run(
    [sys.executable, "-m", "hk_property_data", "refresh", "--output", "company-data"],
    check=False,
)
if result.returncode == 2:
    print("Exports saved; review company-data/refresh_status.json")
else:
    result.check_returncode()
```

After installation, future updates only need the `refresh` call or command; reinstalling is unnecessary for new data. The Excel file is `company-data/hk_property_data.xlsx`, relative to your notebook/script/terminal's current working directory.

From a local checkout use `python -m pip install .`. An internally distributed wheel can be installed with `python -m pip install hk_property_data-0.1.4-py3-none-any.whl`; dependencies must already be installed or available to pip. The package is distributed through GitHub and wheel/source files; it has not been published on PyPI.

For reproducible company deployments, pin the Git URL to a reviewed full commit hash with `.git@<commit>`, or keep the reviewed wheel and its dependencies. Code upgrades are separate from data updates.

## Update data and generate Excel

```sh
hk-property-data refresh --output company-data
hk-property-data validate company-data
```

This retrieves the official sources and creates `company-data/hk_property_data.xlsx`, `hk_housing.sqlite`, CSV and JSON snapshots, raw-source caches, reference periods, source statuses and revision history. Each metric updates to its latest officially published period; a metric without a newer release retains its existing published month. Prime and HIBOR monthly observations come from official monthly publications, with no extra months calculated from daily or effective rates. Run from any working directory; the package writes under the chosen output directory, not its installation folder. Reusing that directory preserves prior history and source-specific fallback data.

Exit codes: **0** means completed without unresolved source errors (informational notes may remain); **2** means exports were generated but a source was retained or a comparison needs review; **1** means a fatal error. Read `errors`, `warnings` and `source_status` in `refresh_status.json`, and the Excel Source Checks sheet. Confirmed PDF/CSV revisions remain visible as notes; unexplained differences still require review. A successful download is not proof that every source has published a new reference month.

The first run has no fallback history. If a required source is unavailable, it fails rather than inventing observations. A dashboard checkout may supply its saved history with `--app /path/to/Real-Estate-Data`; that option also updates the dashboard snapshot and archives. It is not required for ordinary package use.

Installation itself does not create a schedule. The existing GitHub Actions workflow installs this package and runs the same command daily at 18:00 Hong Kong time. You may also run the command in your company's scheduler. Do not run two refreshes against the same output directory concurrently.

## Use from Python

```python
from hk_property_data import refresh, load_dataset, build_excel, build_database

status = refresh(output="company-data")
if status == 2:
    print("Review the source warnings in company-data/refresh_status.json")

snapshot = load_dataset("company-data/hk_housing_dataset.json")
print(snapshot["checked_at"], len(snapshot["observations"]))
build_excel(snapshot, "reports/hong_kong.xlsx")
build_database(snapshot, "reports/hong_kong.sqlite")
```

`refresh()` returns 0 or 2; fatal errors raise exceptions in the Python API. `load_dataset()` and the builders work offline from a saved snapshot. Dates, missing values, units and source warnings are preserved. PDF extraction uses deterministic Python parsers, not AI interpretation.

## Rebuild exports without downloading

```sh
hk-property-data export-excel --dataset company-data/hk_housing_dataset.json --output reports/hong_kong.xlsx
hk-property-data build-database --dataset company-data/hk_housing_dataset.json --output reports/hong_kong.sqlite
python -m hk_property_data --help
```

The previous commands such as `python updater/refresh.py --output data --app .` remain compatibility entry points in a checkout and call the same implementation.

## Build and test the package

```sh
python -m pip install build
python -m build --outdir package-dist
python -m unittest discover -s updater/tests
```

The wheel contains code only. The React dashboard, original PDFs, data snapshots and caches are not bundled. Package metadata and dependencies live in `pyproject.toml`; canonical implementation lives in `python/hk_property_data/`.
