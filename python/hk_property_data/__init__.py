"""Hong Kong property data. Importing the package never downloads or writes data."""
from argparse import Namespace
import json
from pathlib import Path

__version__ = '0.1.0'
__all__ = ['refresh', 'load_dataset', 'build_excel', 'build_database', 'validate', '__version__']


def load_dataset(path):
    """Read a saved JSON snapshot, including its reference periods and warnings."""
    return json.loads(Path(path).read_text(encoding='utf-8'))


def refresh(output='data', *, app=None, as_of=None, pdf=None):
    """Collect official sources and exports; return 0, or 2 for retained-source warnings.

    Fatal errors raise an exception. Outputs and caches live under ``output``.
    ``app`` is optional: pass a dashboard repository only to update its snapshot.
    """
    from .pipeline import run
    return run(Namespace(output=output, app=app, as_of=as_of, pdf=pdf))


def build_excel(dataset, destination):
    """Write validated, company-readable Excel from a snapshot dictionary."""
    from .export_excel import build_excel as build
    build(dataset, destination)
    return Path(destination)


def build_database(dataset, destination):
    """Write the SQLite database, preserving the previous file on validation failure."""
    from .database import build_database as build
    return build(dataset, destination)


def validate(output='data'):
    """Validate JSON plus its generated SQLite and Excel exports without network."""
    from .validation import validate as check
    return check(output)
