"""Read the published dataset into memory using only Python's standard library."""
import json
import urllib.error
import urllib.request
import warnings

DATA_URL = 'https://hogan-cyber.github.io/Real-Estate-Data/data/'


class CloudDataError(RuntimeError):
    """The published dataset could not be retrieved or its schema is unsupported."""


class SourceDataWarning(UserWarning):
    """The published snapshot contains unresolved official-source refresh errors."""


def _fetch_json(filename, timeout):
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError('timeout must be a positive number of seconds')
    url = DATA_URL + filename
    request = urllib.request.Request(url, headers={
        'User-Agent': 'hk-property-data/cloud-client',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8-sig'))
    except (OSError, urllib.error.URLError, UnicodeError, ValueError) as error:
        raise CloudDataError(f'Could not read the published dataset at {url}: {error}') from error
    if (not isinstance(data, dict) or data.get('schema_version') != 1
            or not isinstance(data.get('checked_at'), str) or not data['checked_at']
            or not isinstance(data.get('source_status'), list)
            or not isinstance(data.get('errors'), list)):
        raise CloudDataError(f'Invalid or unsupported published dataset at {url}')
    return data


def fetch_dataset(*, timeout=90):
    """Return the latest published snapshot as a dictionary, without local files.

    Reads one complete cloud JSON snapshot per call. Monthly, daily/effective,
    and PDF records retain their original types, dates, units and provenance.
    ``checked_at`` remains the publisher's source-check time, not this request's
    time. No collectors run, no cache is saved, and no pandas/NumPy is imported.
    Network/schema failures raise CloudDataError instead of returning stale data.
    """
    data = _fetch_json('hk_housing_dataset.json', timeout)
    for field in ('observations', 'rate_observations', 'pdf_observations', 'revisions'):
        if not isinstance(data.get(field), list) or any(not isinstance(row, dict) for row in data[field]):
            raise CloudDataError(f'Invalid published dataset field: {field}')
    if data['errors']:
        warnings.warn('Published source refresh issues: ' + '; '.join(map(str, data['errors'])),
                      SourceDataWarning, stacklevel=2)
    return data


def fetch_status(*, timeout=30):
    """Read published source status without transferring the full observations.

    This is a separate request. Use fetch_dataset()['checked_at'] when comparing
    the data in that snapshot; publication can occur between two requests.
    """
    return _fetch_json('refresh_status.json', timeout)
