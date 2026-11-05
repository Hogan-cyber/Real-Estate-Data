"""Direct official RVD residential CSVs. No interpolation or PDF reconstruction."""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re

from ..pipeline import fetch

BASE = 'https://www.rvd.gov.hk/datagovhk/'
CLASSES = ['Class A', 'Class B', 'Class C', 'Class D', 'Class E']
AVERAGES = [f'{c} {region}' for c in CLASSES for region in ['Hong Kong', 'Kowloon', 'New Territories']]
INDICES = CLASSES + ['Classes A, B & C', 'Classes D & E', 'All Classes']
POPULAR = [f'{c} {region}' for c in ['Classes A, B & C', 'Classes D & E', 'Overall']
           for region in ['Urban', 'New Territories', 'All']]
# filename: (source table ID, label, unit, value columns, has remarks)
FILES = {
    '1.1M.csv': ('1.1', 'Average rent', 'HKD / sq m / month', AVERAGES, True),
    '1.2M.csv': ('1.2', 'Average price', 'HKD / sq m', AVERAGES, True),
    '1.3M.csv': ('1.3', 'Rental index', '1999=100', INDICES, True),
    '1.4M.csv': ('1.4', 'Price index', '1999=100', INDICES, True),
    '1.5M.csv': ('1.5', 'Selected popular development price index', '1999=100', POPULAR, True),
    'Private_Domestic-Stock.csv': ('stock', 'Year-end stock', 'dwellings',
        [f'{c} (Stock)' for c in CLASSES + ['Total']], False),
    'Private_Domestic-Completions.csv': ('completions', 'Completions', 'dwellings',
        [f'{c} (Completions)' for c in CLASSES + ['Total']], True),
    'Private_Domestic-Vacancy.csv': ('vacancy', 'Year-end vacancy', 'dwellings',
        [f'{c} (Vacancy) - {unit}' for c in CLASSES + ['Total'] for unit in ['Unit', '%']], False),
    'Private_Domestic-Take-up.csv': ('takeup', 'Net take-up', 'dwellings',
        ['Take Up (SA Less than 100 m2)', 'Take up (SA 100 m2 or above)', 'Take up (Total)'], False),
}


def _supply_note(table: str, period: str) -> str:
    note = ('Official RVD CSV. Supply definitions follow the table-specific data dictionary '
            '(https://www.rvd.gov.hk/datagovhk/Data_Dic.pdf) and historical table footnotes '
            '(https://www.rvd.gov.hk/doc/en/statistics/private_domestic.xls): figures from 2003 '
            'onwards exclude village houses. The generic Technical Notes '
            '(https://www.rvd.gov.hk/doc/en/statistics/15_technotes.pdf) instead state 2002; '
            'do not treat 2002 and 2003 as safely like-for-like coverage.')
    if period == '2004':
        note += ' The 2004 figures include private flats converted from subsidised sale flats during the year.'
    if table == 'completions':
        if period == '2015':
            note += (' The 2015 completion-table figures include 16 Class B units completed and designated '
                     'as subsidised sale flats in 2015 but sold at prevailing market prices in 2017.')
        elif period == '2019':
            note += (' The 2019 completion-table figures include 9 Class A and 34 Class B units intended '
                     'for open-market sale in 2019 but converted to subsidised sale flats in 2020.')
        if period >= '2025':
            note += (' Completion figures from 2025 onwards include subsidised sale flats under the '
                     'Starter Homes for Hong Kong Residents (SH) projects.')
    return note


def parse_csv(filename: str, raw: bytes, as_of: str, start: str = '2002-01') -> list[dict]:
    table, label, unit, columns, remarks = FILES[filename]
    monthly = filename[0].isdigit()
    frequency = 'M' if monthly else 'A'
    data = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    headers = ['Month' if monthly else 'Year'] + [item for column in columns
               for item in ((column, column + ' - Remarks') if remarks else (column,))]
    if len(data) < 3 or 'PRIVATE DOMESTIC' not in ' '.join(data[0][0].split()):
        raise ValueError(f'{filename}: missing residential data or wrong title')
    if data[1] != headers:
        raise ValueError(f'{filename}: CSV columns changed')
    output = []
    seen = set()
    for cells in data[2:]:
        if not cells or not any(c.strip() for c in cells):
            continue
        if len(cells) != len(headers):
            raise ValueError(f'{filename}: CSV row width changed')
        period_text = cells[0].strip()
        if monthly:
            if not re.fullmatch(r'\d{2}-\d{4}', period_text):
                raise ValueError(f'{filename}: invalid month {period_text!r}')
            month, year = map(int, period_text.split('-'))
            date = dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat()
            period = date[:7]
        else:
            if not re.fullmatch(r'\d{4}', period_text):
                raise ValueError(f'{filename}: invalid year {period_text!r}')
            period = period_text
            date = period + '-12-31'
        if period in seen:
            raise ValueError(f'{filename}: duplicate source period {period}')
        seen.add(period)
        record = dict(zip(headers, cells))
        for column in columns:
            flags = record.get(column + ' - Remarks', '').strip()
            cutoff = re.search(r'up to (\d{2}\.\d{2}\.\d{4})', flags, re.I)
            observation_date = dt.datetime.strptime(cutoff[1], '%d.%m.%Y').date().isoformat() if cutoff else date
            if cutoff and observation_date[:4] != period:
                raise ValueError(f'{filename}: partial-year cutoff differs from observation year')
            if observation_date[:7] < start[:7] or observation_date > as_of:
                continue
            text = record[column].strip()
            value = None if text.upper() in ('', '-', 'NA', 'N.A.', 'N/A') else float(text.replace(',', ''))
            if value is not None and (not math.isfinite(value) or (value < 0 and table != 'takeup')):
                raise ValueError(f'{filename}: invalid value {text!r}')
            fraction = column.endswith(' - %')
            if fraction and value is not None and not 0 <= value <= 1:
                raise ValueError(f'{filename}: vacancy fraction outside [0, 1]')
            status = ('Partial; Provisional' if cutoff else 'Provisional' if
                      'P' in flags or 'provisional' in flags.lower() else 'Published')
            if value is None:
                status = 'Missing'
            note = ('Official RVD CSV. Class sizes use saleable area; averages are transaction-mix sensitive. '
                    'P = provisional; Z = fewer than 20 cases. Primary residential sales are excluded from price analysis.'
                    if monthly else _supply_note(table, period))
            if cutoff:
                note += f' Year-to-date through {observation_date}; not a full-year total.'
            if fraction:
                note += ' Source percentage column is a fraction: 0.043 = 4.3%; retained without rescaling.'
            if value is None:
                note += f' Source missing marker: {text!r}; not zero.'
            metric = 'rvd_' + table.replace('.', '_') + '_' + re.sub('[^a-z0-9]+', '_', column.lower()).strip('_')
            output.append(dict(metric_id=metric, metric_name=f'{label} — {column}', period=period,
                date=observation_date, frequency=frequency, value=value, unit='fraction' if fraction else unit,
                source_id='rvd_' + table, source_name='Rating and Valuation Department',
                source_url=BASE + filename, source_table=table, source_field=column, status=status,
                flags=flags, note=note, raw_value=text, small_sample=any(f in flags for f in 'XYZ'),
                checked_at=as_of))
    if not output:
        raise ValueError(f'{filename}: no observations in requested period')
    return output


def collect(output_dir: Path, as_of: str, start: str = '2002-01') -> list[dict]:
    """Download nine small current CSVs and preserve their exact response bytes."""
    raw_dir = Path(output_dir) / 'raw' / 'rvd'
    raw_dir.mkdir(parents=True, exist_ok=True)
    output, manifest = [], []
    for filename in FILES:
        url = BASE + filename
        raw = fetch(url)
        if len(raw) > 30_000_000:
            raise ValueError(f'{filename}: response exceeds 30 MB')
        (raw_dir / filename).write_bytes(raw)
        rows = parse_csv(filename, raw, as_of, start)
        output.extend(rows)
        manifest.append(dict(file=filename, url=url, sha256=hashlib.sha256(raw).hexdigest(),
                             retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                             rows=len(rows), earliest=min(r['period'] for r in rows),
                             latest=max(r['period'] for r in rows)))
    (raw_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return output
