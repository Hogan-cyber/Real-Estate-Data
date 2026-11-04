"""Official HKMA C01 growth rates, preserving monthly/quarterly observation frequency.

Values are the published percentage-point numbers in the workbook, not fractions
to multiply by 100. Nominal GDP is a quarterly series laid out on a monthly axis;
Excel #N/A and empty cells never become zero, interpolations or carried values.
"""
from __future__ import annotations

import calendar
import datetime as dt
import math
from pathlib import Path

SOURCE_URL = 'https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/C01.xls'
SOURCE_TABLE = 'HKMA Monthly Statistical Bulletin C01: Money and Credit'
SERIES = {
    2: ('hk_money_credit_m3_yoy', 'Hong Kong dollar M3: year-on-year growth', 'HK dollar M3', 'M'),
    3: ('hk_domestic_credit_yoy', 'Domestic credit: year-on-year growth', 'Domestic credit', 'M'),
    4: ('hk_nominal_gdp_yoy', 'Nominal GDP: year-on-year growth', 'Nominal GDP', 'Q'),
}
MAX_SOURCE_BYTES = 30_000_000


def _as_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _value_or_missing(cell, address):
    # xlrd types: empty=0, text=1, number=2, date=3, boolean=4, error=5, blank=6.
    if cell.ctype in (0, 6) or (cell.ctype == 1 and not str(cell.value).strip()):
        return None
    if cell.ctype == 5 and cell.value == 42:  # Excel #N/A, used between GDP quarters.
        return None
    if cell.ctype != 2 or isinstance(cell.value, bool) or not isinstance(cell.value, (int, float)) or not math.isfinite(cell.value):
        raise ValueError('C01 unexpected nonnumeric value at ' + address)
    return cell.value


def parse(raw, as_of):
    """Read the reviewed Data sheet schema and fail on ambiguous/noncurrent data."""
    import xlrd

    as_of = _as_date(as_of)
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('C01 source must contain at most 30 MB of workbook bytes')
    workbook = xlrd.open_workbook(file_contents=raw)
    if workbook.sheet_names().count('Data') != 1:
        raise ValueError('C01 schema changed: Data sheet missing or ambiguous')
    sheet = workbook.sheet_by_name('Data')
    if sheet.nrows < 4 or sheet.ncols < 5:
        raise ValueError('C01 schema changed: missing data columns')
    headers = {(0, 2): 'Money and Credit'}
    headers.update({(1, column): definition[2] for column, definition in SERIES.items()})
    headers.update({(2, column): '(yoy %)' for column in SERIES})
    for (row, column), expected in headers.items():
        cell = sheet.cell(row, column)
        if cell.ctype != 1 or ' '.join(str(cell.value).split()) != expected:
            raise ValueError(f'C01 schema changed at {chr(65 + column)}{row + 1}')

    rows, seen = [], set()
    for index in range(3, sheet.nrows):
        values = {column: _value_or_missing(sheet.cell(index, column), f'{chr(65 + column)}{index + 1}')
                  for column in SERIES}
        date_cell = sheet.cell(index, 1)
        if date_cell.ctype in (0, 6) and all(value is None for value in values.values()):
            continue
        if date_cell.ctype != xlrd.XL_CELL_DATE:
            raise ValueError(f'C01 date column changed at B{index + 1}')
        try:
            source_date = xlrd.xldate_as_datetime(date_cell.value, workbook.datemode).date()
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f'C01 invalid date at B{index + 1}') from exc
        period = source_date.strftime('%Y-%m')
        if period in seen:
            raise ValueError('C01 duplicate observation month: ' + period)
        seen.add(period)
        # C01 uses the 15th as a monthly chart label, not as the observation date.
        date = dt.date(source_date.year, source_date.month,
                       calendar.monthrange(source_date.year, source_date.month)[1])
        if any(value is not None for value in values.values()) and date > as_of:
            raise ValueError('C01 future numeric observation: ' + period)
        for column, value in values.items():
            if value is None:
                continue
            metric_id, name, field, frequency = SERIES[column]
            if frequency == 'Q' and source_date.month not in (3, 6, 9, 12):
                raise ValueError('C01 nominal GDP is not at a quarter end: ' + period)
            source_period = f'{source_date.year}-Q{source_date.month // 3}' if frequency == 'Q' else period
            note = ('Published year-on-year percentage change; the numeric value is used directly, without multiplying by 100. '
                    'The workbook date labels identify months; observation dates are normalized to month-end. ')
            note += ('Nominal GDP is quarterly: period is the quarter-end month and source_period identifies the quarter. '
                     'Missing quarters and intervening months are not filled.' if frequency == 'Q' else
                     'Monthly observation. Missing source values are omitted, not zero.')
            rows.append(dict(market='HK', category='macro', property_type='Macro',
                metric_id=metric_id, metric_name=name, period=period, date=date.isoformat(),
                value=value, unit='% yoy', frequency=frequency, region='All Hong Kong',
                source_name='Hong Kong Monetary Authority', source='Hong Kong Monetary Authority',
                source_url=SOURCE_URL, source_table=SOURCE_TABLE, source_field=field,
                source_column=chr(65 + column), source_row=index + 1, source_period=source_period,
                source_date=source_date.isoformat(), published_date=None,
                publication_date_basis='The rolling C01 workbook does not supply a publication date',
                status='Published', checked_at=as_of.isoformat(), fetch_mode='automatic_excel',
                observation_type='official', scope='Hong Kong; official HKMA C01 Money and Credit growth-rate series',
                note=note))
    if {row['metric_id'] for row in rows} != {definition[0] for definition in SERIES.values()}:
        raise ValueError('C01 has no published observations for one or more required series')
    return rows


def collect(cache_dir, as_of, fetch=None):
    """Fetch and validate before replacing the raw archive; callers manage row caches."""
    if fetch is None:
        from .hk_hkma_collector import _get
        fetch = _get
    raw = fetch(SOURCE_URL)
    rows = parse(raw, as_of)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive = cache_dir / 'C01.xls'
    temporary = archive.with_suffix('.xls.tmp')
    temporary.write_bytes(raw)
    temporary.replace(archive)
    return rows
