"""Read GitHub residential data from one bounded, reusable Arrow session snapshot."""
from __future__ import annotations

import calendar
import datetime as dt
from http.client import HTTPException
import io
import json
import math
import re
import sqlite3
import time
import urllib.error
import urllib.request
import warnings

from .cloud import CloudDataError, SourceDataWarning
from . import residential_cache as _cache
from .residential_schema import COLUMNS, SCHEMA_VERSION, populate_database

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
RELEASE_URL = 'https://github.com/Hogan-cyber/Real-Estate-Data/releases/download/residential-data-latest/'
FAST_URL = 'https://raw.githubusercontent.com/Hogan-cyber/Real-Estate-Data/residential-data/'
FORMATS = {'csv': 'observations.csv', 'csv.gz': 'observations.csv.gz',
           'excel': 'HK_Residential_Data.xlsx', 'sqlite': 'observations.sqlite',
           'status': 'collection_status.json', 'parquet': 'observations.parquet'}


def residential_url(format='csv'):
    """Return the full downloadable Release asset URL, unchanged for compatibility."""
    if format not in FORMATS:
        raise ValueError('format must be one of: ' + ', '.join(FORMATS))
    return RELEASE_URL + FORMATS[format]


def clear_residential_cache():
    """Release the cached session snapshot; the next read downloads again."""
    _cache.clear()


def residential_cache_info():
    """Return cache size, age and source URLs without downloading any data."""
    return _cache.info()


def _validate_timeout(timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be a positive finite number of seconds')


def _open_url(url, timeout, refresh=False):
    if refresh:
        url += '?refresh=' + str(time.time_ns())
    request = urllib.request.Request(url, headers={
        'User-Agent': 'hk-property-data/residential-client', 'Cache-Control': 'no-cache'})
    return urllib.request.urlopen(request, timeout=timeout)


def _open_source(path, format, timeout, refresh=False, metric=None):
    url = FAST_URL + path
    try:
        return _open_url(url, timeout, refresh), metric, url
    except (OSError, HTTPException) as exc:
        # Do not keep a failed HTTP response/socket alive while trying the fallback.
        if isinstance(exc, urllib.error.HTTPError):
            exc.close()
        warnings.warn('Direct GitHub data unavailable; reading the published Release instead.',
                      SourceDataWarning, stacklevel=3)
        url = residential_url(format)
        return _open_url(url, timeout, refresh), None, url


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


def _download(path, timeout, refresh, metric):
    response, expected, source = _open_source(path, 'parquet', timeout, refresh, metric)
    with response:
        output = io.BytesIO()
        while chunk := response.read(64 * 1024):
            if output.tell() + len(chunk) > MAX_RESPONSE_BYTES:
                raise CloudDataError('Parquet response exceeds the 8 MiB in-memory response limit')
            output.write(chunk)
        payload = output.getvalue()
    from .residential_parquet import validate
    table = validate(payload)
    return dict(table=table, source=source, downloaded_bytes=len(payload))


def _normalise_series(series):
    if isinstance(series, str):
        series = [series]
    try:
        selected = None if series is None else tuple(series)
    except TypeError as exc:
        raise ValueError('series must be a metric ID or iterable of IDs') from exc
    if selected is not None and (not selected or any(not isinstance(s, str) or not s.strip() for s in selected)):
        raise ValueError('series must contain at least one nonempty metric ID')
    if isinstance(series, (set, frozenset)):
        selected = tuple(sorted(selected))
    return None if selected is None else tuple(dict.fromkeys(selected))


def _prepare_read(*, series=None, start=None, end=None, timeout=90, refresh=False, cache=True):
    """Shared validation and snapshot loading; heavy libraries stay lazy."""
    selected = _normalise_series(series)
    first, last = _date_bound(start), _date_bound(end, end=True)
    if first > last:
        raise ValueError('start must not be after end')
    _validate_timeout(timeout)
    if not isinstance(refresh, bool) or not isinstance(cache, bool):
        raise ValueError('refresh and cache must be booleans')
    path = 'observations.parquet'
    key = FAST_URL + path
    try:
        if cache:
            snapshot = _cache.get_or_load(
                key, lambda: _download(path, timeout, refresh, None), refresh=refresh)
        else:
            if refresh:
                _cache.discard(key)
            snapshot = _download(path, timeout, refresh, None)
        return snapshot['table'], selected, first, last
    except (OSError, HTTPException, EOFError, UnicodeError) as exc:
        raise CloudDataError(f'Could not read the published residential Parquet: {exc}') from exc
    except ValueError as exc:
        raise CloudDataError(f'Invalid residential data: {exc}') from exc


def iter_residential(*, series=None, start=None, end=None, timeout=90, refresh=False, cache=True):
    """Yield independent record dictionaries from the shared Arrow snapshot.

    For analysis-ready numeric DataFrames use Residential.history(). This record
    interface retains ISO date strings and all original metadata for compatibility.
    """
    table, selected, first, last = _prepare_read(
        series=series, start=start, end=end, timeout=timeout, refresh=refresh, cache=cache)
    from .residential_parquet import read_rows
    yield from read_rows(table, selected, first, last)


def fetch_residential(*, series=None, start=None, end=None, timeout=90, refresh=False, cache=True):
    """Return selected records. Repeated reads filter the same bounded session snapshot until explicit refresh."""
    return list(iter_residential(series=series, start=start, end=end, timeout=timeout, refresh=refresh, cache=cache))


def connect_residential(*, series=None, start=None, end=None, timeout=90, refresh=False, cache=True):
    """Load selected records into read-only in-memory SQLite; close after use."""
    connection = sqlite3.connect(':memory:')
    try:
        populate_database(connection, iter_residential(series=series, start=start, end=end, timeout=timeout,
                                                       refresh=refresh, cache=cache))
        connection.execute('PRAGMA query_only=ON')
        return connection
    except Exception:
        connection.close()
        raise


def fetch_residential_status(*, timeout=30):
    """Read current publication status independently; do not cache metadata."""
    _validate_timeout(timeout)
    try:
        response, _, _ = _open_source('collection_status.json', 'status', timeout, refresh=True)
        with response:
            status = json.load(response)
    except (OSError, HTTPException, UnicodeError, json.JSONDecodeError) as exc:
        raise CloudDataError(f'Could not read residential publication status: {exc}') from exc
    if (not isinstance(status, dict) or status.get('schema_version') != SCHEMA_VERSION
            or not isinstance(status.get('generated_at'), str)
            or not isinstance(status.get('source_runs'), list) or not isinstance(status.get('errors'), list)):
        raise CloudDataError('Unsupported residential status schema')
    if status['errors']:
        warnings.warn('Residential publication issues: ' + '; '.join(map(str, status['errors'])),
                      SourceDataWarning, stacklevel=2)
    return status
