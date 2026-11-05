"""Read the residential GitHub Release without local dataset or cache files."""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import gzip
import io
import json
import math
import re
import sqlite3
import urllib.request
import warnings
import zlib

from .cloud import CloudDataError, SourceDataWarning
from .residential_schema import COLUMNS, SCHEMA_VERSION, populate_database

RELEASE_URL = 'https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/'
FORMATS = {'csv': 'observations.csv', 'csv.gz': 'observations.csv.gz',
           'excel': 'HK_Residential_Data.xlsx', 'sqlite': 'observations.sqlite',
           'status': 'collection_status.json'}


def residential_url(format='csv'):
    """Return a published file URL for CSV, Excel, SQLite or collection status."""
    if format not in FORMATS:
        raise ValueError('format must be one of: ' + ', '.join(FORMATS))
    return RELEASE_URL + FORMATS[format]


def _validate_timeout(timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be a positive finite number of seconds')


def _open(format, timeout):
    _validate_timeout(timeout)
    request = urllib.request.Request(residential_url(format), headers={
        'User-Agent': 'hk-property-data/residential-client', 'Cache-Control': 'no-cache'})
    return urllib.request.urlopen(request, timeout=timeout)


def _date_bound(value, *, end=False):
    if value is None:
        return '9999-12-31' if end else '0001-01-01'
    if not isinstance(value, str):
        raise ValueError('Dates must be YYYY-MM or YYYY-MM-DD strings')
    if re.fullmatch(r'\d{4}-\d{2}', value):
        year, month = map(int, value.split('-'))
        day = calendar.monthrange(year, month)[1] if end else 1
        return dt.date(year, month, day).isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Dates must be YYYY-MM or YYYY-MM-DD strings')
    return dt.date.fromisoformat(value).isoformat()


def iter_residential(*, series=None, start=None, end=None, timeout=90):
    """Stream current observations, retaining only selected series/dates.

    ``series`` is one metric ID or an iterable of IDs. Bounds are inclusive
    observation dates; YYYY-MM selects the full boundary month. The compressed
    CSV is transferred and filtered on the client, with bounded decompression
    buffers. No collector or local cache runs. Exhaust or close the iterator to
    release the HTTP connection; callers retaining rows consume their own RAM.
    """
    if isinstance(series, str):
        series = [series]
    try:
        selected = None if series is None else frozenset(series)
    except TypeError as exc:
        raise ValueError('series must be a metric ID or iterable of IDs') from exc
    if selected is not None and (not selected or any(not isinstance(s, str) or not s.strip() for s in selected)):
        raise ValueError('series must contain at least one nonempty metric ID')
    first, last = _date_bound(start), _date_bound(end, end=True)
    if first > last:
        raise ValueError('start must not be after end')
    _validate_timeout(timeout)
    try:
        with _open('csv.gz', timeout) as response, gzip.GzipFile(fileobj=response) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8-sig', newline='') as text:
                reader = csv.DictReader(text, strict=True)
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not set(COLUMNS) <= set(reader.fieldnames):
                    raise CloudDataError('Unsupported residential CSV columns')
                for row in reader:
                    if None in row or any(row[c] is None for c in COLUMNS):
                        raise CloudDataError('Incomplete residential CSV record')
                    if not row['metric_id'] or not row['source_url'].startswith('https://'):
                        raise CloudDataError('Residential record lacks a metric or source')
                    dt.date.fromisoformat(row['date'])
                    raw = row['value'].strip()
                    row['value'] = None if not raw else float(raw)
                    if row['value'] is not None and not math.isfinite(row['value']):
                        raise CloudDataError('Non-finite residential value')
                    if (selected is None or row['metric_id'] in selected) and first <= row['date'] <= last:
                        yield row
    except (OSError, EOFError, UnicodeError, csv.Error, zlib.error) as exc:
        raise CloudDataError(f'Could not read the published residential CSV: {exc}') from exc
    except ValueError as exc:
        raise CloudDataError(f'Invalid residential CSV value: {exc}') from exc


def fetch_residential(*, series=None, start=None, end=None, timeout=90):
    """Return selected records as a list. Only returned rows are held in memory."""
    return list(iter_residential(series=series, start=start, end=end, timeout=timeout))


def connect_residential(*, series=None, start=None, end=None, timeout=90):
    """Return a SQLite connection containing selected GitHub records in RAM.

    Query the ``observations`` table with SQL, then call ``connection.close()``.
    This is local in-memory SQL, not a remote GitHub query server. No .sqlite
    file is downloaded or saved. Full-table reads still require memory.
    """
    connection = sqlite3.connect(':memory:')
    try:
        populate_database(connection, iter_residential(series=series, start=start, end=end, timeout=timeout))
        connection.execute('PRAGMA query_only=ON')
        return connection
    except Exception:
        connection.close()
        raise


def fetch_residential_status(*, timeout=30):
    """Read small publication metadata without observations; a separate request."""
    try:
        with _open('status', timeout) as response:
            status = json.load(response)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CloudDataError(f'Could not read residential publication status: {exc}') from exc
    if (not isinstance(status, dict) or status.get('schema_version') != SCHEMA_VERSION
            or not isinstance(status.get('generated_at'), str)
            or not isinstance(status.get('source_runs'), list) or not isinstance(status.get('errors'), list)):
        raise CloudDataError('Unsupported residential status schema')
    if status['errors']:
        warnings.warn('Residential publication issues: ' + '; '.join(map(str, status['errors'])),
                      SourceDataWarning, stacklevel=2)
    return status
