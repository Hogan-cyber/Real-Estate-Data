"""Land Registry monthly exports using the repository's existing official parser.

Residential sale registrations and all-property mortgage deeds are separate
series. The latest press release can supply residential totals before the
primary/secondary table is updated; unpublished components are never inferred.
"""
from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import json
from pathlib import Path

from hk_property_data.collectors import hk_landreg_collector as lr


def collect(output_dir: Path, as_of: str, start: str = '2002-01') -> list[dict]:
    """Fetch official tables, retain raw responses and return common-schema rows.

    ``as_of`` bounds observation months, not the revision vintage. Historical
    instrument archives retain their real check timestamps when reused within
    the existing collector's 30-day cache policy. Latest tables are revalidated.
    """
    cutoff = lr._as_date(as_of)
    year, month = map(int, start.split('-'))
    start_date = dt.date(year, month, calendar.monthrange(year, month)[1])
    cache = Path(output_dir) / 'raw' / 'landreg'
    cache.mkdir(parents=True, exist_ok=True)
    sales = lr._collect_sales(cache, cutoff)
    latest = max((row['period'] for row in sales if row.get('value') is not None), default=None)
    try:
        instruments = lr._collect_instruments(cache, cutoff, start=start_date, latest_sales_period=latest)
    except Exception as error:
        warning = f'Land Registry instrument history could not be verified: {error}'
        for row in sales:
            row['refresh_warning'] = '; '.join(filter(None, (row.get('refresh_warning'), warning)))
            if isinstance(error, lr.InstrumentCollectionError):
                row['refresh_failed_periods'] = error.failed_periods
                row['refresh_failed_metric_ids'] = list(lr.INSTRUMENT_METRIC_IDS)
        instruments = []

    result = []
    checked = dt.datetime.now(dt.timezone.utc).isoformat()
    for original in sales + instruments:
        if original['period'] < start or original['date'] > cutoff.isoformat():
            continue
        row = dict(original, frequency='M', source_id='landreg',
                   status='Unavailable' if original.get('value') is None else 'Published',
                   flags='SOURCE_CHECK_WARNING' if original.get('refresh_warning') else '')
        if not row.get('source_checked_at'):
            key = hashlib.sha256(row['source_url'].encode()).hexdigest()
            path = cache / (key + '.json')
            if path.exists():
                metadata = json.loads(path.read_text(encoding='utf-8'))
                if metadata.get('url') == row['source_url']:
                    row['source_checked_at'] = metadata.get('checked_at')
            elif row.get('fetch_mode') == 'automatic_pdf' and (cache / (key + '.pdf')).exists():
                # The existing PDF collector revalidates the annex on each run.
                row['source_checked_at'] = checked
        result.append(row)
    return sorted(result, key=lambda row: (row['metric_id'], row['period']))
