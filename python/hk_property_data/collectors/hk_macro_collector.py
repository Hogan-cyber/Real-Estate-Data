"""Official HKMA money/rate series; API with same-table Excel fallback, no AI.

M3 uses the adjusted new series from April 1997. HSBC prime and HKAB HIBOR
use published monthly averages, supplemented by explicitly labelled calculations
from complete official daily fixings or HSBC effective-rate history.
"""
from __future__ import annotations
import calendar
import datetime as dt
import json
import math
from pathlib import Path
import re
from urllib.parse import urlencode

API_ROOT = 'https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/'
XLS_ROOT = 'https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/'
DOC_ROOT = 'https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/'
SOURCES = {
    'hkma_m3': dict(path='money/supply-adjusted', segment='new', table='2.2.1', file='T020201.xls', sheet='T2.2.1 (new series)', start='1997-04',
        fields={'m3_hkd': ('hk_m3_hkd', 'Hong Kong dollar M3', 11), 'm3_total': ('hk_m3_total', 'All-currency M3', 13)},
        unit='HKD million', basis='End of month',
        note='Adjusted for foreign currency swap deposits: HKD M3 includes these deposits. All-currency M3 includes HKD and foreign currencies expressed in HKD. New series begins April 1997; earlier old-series data are not spliced across the methodology break. Not seasonally adjusted.'),
    'hkma_prime': dict(path='er-ir/hkd-ir-periodaverage', segment=None, table='6.4.2', file='T060402.xls', sheet='T6.4.2', start='1980-01',
        fields={'best_lending_rate': ('hk_prime_rate_hsbc', 'HSBC prime rate (monthly average)', 10)},
        unit='% p.a.', basis='Monthly average',
        note='Official monthly average of the best lending rate quoted by HSBC (Hongkong and Shanghai Banking Corporation Limited). Not the current effective rate or an actual mortgage borrowing rate.'),
    'hkma_hibor': dict(path='er-ir/hk-interbank-ir-periodaverage', segment='hibor.fixing', table='6.3.2', file='T060302.xls', sheet='T6.3.2 (HIBOR Fixing)', start='1996-07',
        fields={'ir_1m': ('hk_hibor_1m', '1-month HIBOR (monthly average)', 6), 'ir_3m': ('hk_hibor_3m', '3-month HIBOR (monthly average)', 7)},
        unit='% p.a.', basis='Monthly average',
        note='Official monthly average of HKAB Hong Kong dollar Interest Settlement Rates (HIBOR fixing). A market benchmark, not an HSBC-specific quote or actual mortgage rate. The discontinued Standard Chartered HIBOR segment is excluded.'),
}
PAGE_SIZE = 500
MONTHS = {name: i for i, name in enumerate(calendar.month_abbr) if i}


def _number(value):
    if value is None or isinstance(value, str) and value.strip().upper() in ('', 'N.A.', 'N.A', 'N/A', '-', '--'):
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'Invalid macro value: {value!r}')
    return value


def _month_end(period):
    if not isinstance(period, str) or not re.fullmatch(r'\d{4}-\d{2}', period):
        raise ValueError(f'Invalid monthly reference period: {period!r}')
    year, month = map(int, period.split('-'))
    return dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def parse_records(key, records, as_of, source_url=None, fetch_mode='automatic_api'):
    config = SOURCES[key]
    as_of = str(as_of)[:10]
    dt.date.fromisoformat(as_of)
    rows, seen = [], set()
    for record in records:
        period = record.get('end_of_month')
        date = _month_end(period)
        if period in seen:
            raise ValueError(f'Duplicate {key} month: {period}')
        seen.add(period)
        if period < config['start'] or date > as_of:
            continue
        for field, (metric_id, name, _) in config['fields'].items():
            if field not in record:
                raise ValueError(f'Missing macro source field: {field}')
            value = _number(record[field])
            rows.append(dict(market='HK', category='macro', property_type='Macro', measure='money_supply' if key=='hkma_m3' else 'interest_rate',
                metric_id=metric_id, metric_name=name, period=period, date=date, value=value, unit=config['unit'], frequency='M',
                region='All Hong Kong', scope='Hong Kong dollars' if field=='m3_hkd' else 'All currencies' if field=='m3_total' else 'Hong Kong dollar interest rates',
                observation_basis=config['basis'], seasonal_adjustment='NSA', source_id=key,
                source_name='Hong Kong Monetary Authority', source_table=config['table'], source_field=field,
                source_url=source_url or API_ROOT+config['path']+(('?segment='+config['segment']) if config['segment'] else ''),
                source_documentation=DOC_ROOT+config['path']+'/', status='Published', flags='', small_sample=False,
                missing_reason='No published value' if value is None else None, fetch_mode=fetch_mode, note=config['note']))
    if not rows:
        raise ValueError(f'No eligible monthly observations for {key}')
    return sorted(rows, key=lambda r: (r['metric_id'], r['period']))


def _api_records(key, fetch):
    config = SOURCES[key]
    records, pages, seen = [], [], set()
    # Continue until an explicitly empty page; datasize may describe a page or
    # the result total, and a server can cap pages below the requested size.
    for _ in range(100):
        params = dict(offset=len(records), pagesize=PAGE_SIZE, sortby='end_of_month', sortorder='asc')
        if config['segment']:
            params['segment'] = config['segment']
        url = API_ROOT + config['path'] + '?' + urlencode(params)
        raw = fetch(url)
        if len(raw) > 30_000_000:
            raise ValueError('Macro API response exceeds size limit')
        payload = json.loads(raw)
        if payload.get('header', {}).get('success') is not True:
            raise ValueError('HKMA macro API did not report success')
        page = payload.get('result', {}).get('records')
        if not isinstance(page, list):
            raise ValueError('HKMA macro API records changed shape')
        pages.append(dict(url=url, response=payload))
        if not page:
            if not records:
                raise ValueError('HKMA macro API returned no records')
            return records, pages
        for record in page:
            period = record.get('end_of_month')
            _month_end(period)
            if period in seen:
                raise ValueError('Repeated or overlapping macro API page')
            seen.add(period)
        records.extend(page)
    raise ValueError('Macro API pagination did not finish')


def parse_excel(key, raw, as_of):
    import xlrd
    config = SOURCES[key]
    book = xlrd.open_workbook(file_contents=raw)
    sheet = book.sheet_by_name(config['sheet'])
    top = ' '.join(str(c) for i in range(min(16, sheet.nrows)) for c in sheet.row_values(i))
    if 'Table '+config['table'] not in top or ('Adjusted for foreign currency swap deposits' if key=='hkma_m3' else 'Period average figures') not in top:
        raise ValueError('Macro workbook title/basis changed')
    if key == 'hkma_m3':
        if str(sheet.cell_value(7,11)).strip() != 'M3' or sheet.cell_value(9,11) != 'HK$2' or sheet.cell_value(9,13) != 'Total':
            raise ValueError('M3 workbook columns changed')
    elif key == 'hkma_hibor':
        if sheet.cell_value(7,6) != '1-month' or sheet.cell_value(7,7) != '3-month' or 'Interest Settlement Rates' not in top:
            raise ValueError('HIBOR fixing workbook columns changed')
    else:
        if 'lending rate' not in str(sheet.cell_value(10,10)).lower():
            raise ValueError('Prime workbook column changed')
        footnotes=' '.join(str(c) for i in range(max(0,sheet.nrows-15),sheet.nrows) for c in sheet.row_values(i))
        if 'Hongkong' not in footnotes or 'Shanghai Banking Corporation Limited' not in footnotes:
            raise ValueError('Prime workbook HSBC attribution changed')
    records, year = [], None
    for i in range(sheet.nrows):
        cells = sheet.row_values(i)
        month = MONTHS.get(str(cells[1]).strip())
        if not month:
            continue  # Annual totals, headings and footnotes are not monthly rows.
        label = str(cells[0]).strip()
        if label and label not in ('0', '0.0'):
            try:
                number=float(label)
            except ValueError as exc:
                raise ValueError('Invalid workbook year') from exc
            if not number.is_integer() or not 1900 <= number <= 2200:
                raise ValueError('Invalid workbook year')
            year=int(number)
        if year is None:
            raise ValueError('Macro workbook month has no year')
        record = {'end_of_month': f'{year:04d}-{month:02d}'}
        for field, (_, _, col) in config['fields'].items():
            record[field] = cells[col]
        records.append(record)
    return parse_records(key, records, as_of, XLS_ROOT+config['file'], 'automatic_excel')


def collect(key, cache, as_of, fetch):
    """Use a verified public API response or the same official Excel table.

    Both failures propagate to refresh.py, which independently retains the last
    good feed. Cached files never silently masquerade as a fresh collection.
    """
    config = SOURCES[key]
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    try:
        records, pages = _api_records(key, fetch)
        rows = parse_records(key, records, as_of)
        raw = json.dumps({'pages': pages}, ensure_ascii=False, indent=2).encode()
        suffix = '.json'
    except Exception as api_error:
        try:
            raw = fetch(XLS_ROOT+config['file'])
            if len(raw) > 30_000_000:
                raise ValueError('Macro workbook exceeds size limit')
            rows = parse_excel(key, raw, as_of)
            for row in rows:
                row['source_fallback_reason'] = f'{type(api_error).__name__}: {api_error}'[:500]
                row['note'] += ' The official Excel table was used because the API was unusable (' + row['source_fallback_reason'] + ').'
            suffix = '.xls'
        except Exception as excel_error:
            raise RuntimeError(f'{key}: API and official Excel both failed ({type(api_error).__name__}; {type(excel_error).__name__}: {excel_error})') from excel_error
    destination=cache/(key+suffix)
    temporary=destination.with_suffix(destination.suffix+'.tmp')
    temporary.write_bytes(raw); temporary.replace(destination)
    if key in ('hkma_prime', 'hkma_hibor'):
        if key == 'hkma_prime':
            from .hk_prime_supplement import supplement
        else:
            from .hk_hibor_supplement import supplement
        try:
            extra = supplement(rows, cache, as_of, fetch)
            official_keys = {(r['metric_id'], r['period']) for r in rows}
            if any((r['metric_id'], r['period']) in official_keys for r in extra):
                raise ValueError('Calculated rate would overwrite a published monthly observation')
            rows.extend(extra)
        except Exception as exc:
            # Keep the official monthly table, but expose an unsuccessful check
            # for newer daily/effective observations to the pipeline and UI.
            warning = f'Latest rate supplement unavailable: {type(exc).__name__}: {exc}'[:500]
            rows = [dict(row, refresh_warning=warning) for row in rows]
    return rows
