"""Hong Kong property data. Importing the package never downloads or writes data."""
from argparse import Namespace
from importlib.util import find_spec
import json
from pathlib import Path
from .cloud import fetch_dataset, fetch_status, CloudDataError, SourceDataWarning
from .residential import (fetch_residential, iter_residential, connect_residential,
                          fetch_residential_status, residential_url)

__version__ = '0.3.0'
__all__ = ['fetch_dataset', 'fetch_status', 'CloudDataError', 'SourceDataWarning',
           'fetch_residential', 'iter_residential', 'connect_residential',
           'fetch_residential_status', 'residential_url',
           'refresh', 'load_dataset', 'build_excel', 'build_database', 'validate', '__version__']


def _require_collector(*modules):
    if any(find_spec(name) is None for name in modules):
        raise RuntimeError(
            'This operation requires optional collector tools. Install '
            '"hk-property-data[collector] @ '
            'https://github.com/Hogan-cyber/Real-Estate-Data/archive/refs/heads/main.zip". '
            'To read the published cloud dataset, use fetch_dataset() instead.')


def load_dataset(path):
    """Read a saved JSON snapshot, including its reference periods and warnings."""
    return json.loads(Path(path).read_text(encoding='utf-8'))


def refresh(output='data', *, app=None, as_of=None, pdf=None):
    """Collect official sources and exports; return 0, or 2 for retained-source warnings.

    Fatal errors raise an exception. Outputs and caches live under ``output``.
    ``app`` is optional: pass a dashboard repository only to update its snapshot.
    """
    _require_collector('pdfplumber', 'pypdf', 'xlsxwriter', 'xlrd')
    from .pipeline import run
    return run(Namespace(output=output, app=app, as_of=as_of, pdf=pdf))


def build_excel(dataset, destination):
    """Write validated, company-readable Excel from a snapshot dictionary."""
    _require_collector('xlsxwriter')
    from .export_excel import build_excel as build
    build(dataset, destination)
    return Path(destination)


def build_database(dataset, destination):
    """Write the SQLite database, preserving the previous file on validation failure."""
    from .database import build_database as build
    return build(dataset, destination)


def validate(output='data', *, app=None):
    """Validate JSON, CSV, SQLite and Excel; optionally check a dashboard snapshot."""
    _require_collector('xlsxwriter')
    from .validation import validate as check
    return check(output, app=app)
