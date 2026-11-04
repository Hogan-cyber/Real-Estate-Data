"""Published daily/effective rates, kept separate from monthly averages."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from urllib.parse import urlparse, urlencode
from .hk_hibor_supplement import API_URL, CALENDAR_URL, _calendar, _html_day

GOVERNMENT_RATE_URL = 'https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/'
_API_ROOT = 'https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/'
_XLS_ROOT = 'https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/'
PRIME_API_URL = _API_ROOT + 'hkd-ir-effdates'
HIBOR_API_URL = _API_ROOT + 'hk-interbank-ir-daily'
TABLES = {
    'prime': dict(api=PRIME_API_URL, date='effect_date', table='6.4.1', file='T060401.xls',
                  sheet='T6.4.1', fields={'best_lending_rate': ('hk_prime_rate_hsbc_effective', 'HSBC Prime rate', 10)},
                  source_id='hsbc_prime_effective', frequency='E'),
    'hibor': dict(api=HIBOR_API_URL, date='end_of_day', table='6.3.3', file='T060303.xls',
                  sheet='T6.3.3 (HIBOR Fixing)', fields={'ir_1m': ('hk_hibor_1m_daily', '1 Month HIBOR', 5),
                  'ir_3m': ('hk_hibor_3m_daily', '3 Months HIBOR', 6)}, source_id='hk_rates_hibor', frequency='D'),
}


def _date(value, as_of):
    date = dt.date.fromisoformat(value)
    if date > dt.date.fromisoformat(as_of[:10]):
        raise ValueError('Future published rate date')
    return date.isoformat()


def _value(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError('Invalid published interest rate')
    return value


def _row(metric, name, date, value, source_id, source_name, url, now, frequency='D'):
    return dict(metric_id=metric, metric_name=name, date=date, value=_value(value), unit='% p.a.',
                frequency=frequency, observation_basis='Effective rate' if frequency=='E' else 'Daily fixing',
                source_id=source_id, source_name=source_name, source_url=url, status='Published', checked_at=now)


def government_rows(rows):
    """Private-source legacy rows cannot survive an outage or successful merge."""
    return [r for r in rows if urlparse(r.get('source_url', '')).scheme == 'https'
            and urlparse(r.get('source_url', '')).hostname in ('www.hkma.gov.hk', 'api.hkma.gov.hk')]


def parse_records(kind, records, as_of, now, url, mode='automatic_api'):
    config = TABLES[kind]
    rows, dates = [], set()
    for record in records:
        date = _date(record[config['date']], as_of)
        if date in dates:
            raise ValueError('Duplicate official rate date: ' + date)
        dates.add(date)
        for field, (metric, name, _) in config['fields'].items():
            value = record[field]  # Missing columns are schema failures, not unpublished values.
            if value is None or isinstance(value, str) and value.strip() in ('', '-', 'N.A.', 'N/A'):
                continue
            row = _row(metric, name, date, value, config['source_id'], 'Hong Kong Monetary Authority',
                       url, now, config['frequency'])
            row.update(source_table=config['table'], source_field=field, fetch_mode=mode,
                       source_documentation=GOVERNMENT_RATE_URL + config['api'].rsplit('/', 1)[-1] + '/',
                       note=('HKMA-published HSBC best lending rate at its effective date; not a daily fixing or monthly average.'
                             if kind == 'prime' else 'HKMA-published HKAB fixing series, as at 11:15 am; not the discontinued closing-rate series or a monthly average.'))
            rows.append(row)
    if not rows:
        raise ValueError('No published official ' + kind + ' observations')
    return merge_rates([], rows)


def excel_rate_value(cell):
    """Preserve spreadsheet missingness before reading Excel's numeric error code."""
    import xlrd
    if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return None
    if cell.ctype == xlrd.XL_CELL_ERROR and cell.value == 42:  # #N/A
        return None
    if cell.ctype == xlrd.XL_CELL_TEXT and str(cell.value).strip() in ('', '-', 'N.A.', 'N/A'):
        return None
    if cell.ctype != xlrd.XL_CELL_NUMBER:
        raise ValueError('Unexpected official rate workbook cell type')
    return _value(cell.value)


def parse_excel(kind, raw, as_of, now):
    import xlrd
    config = TABLES[kind]
    book = xlrd.open_workbook(file_contents=raw)
    sheet = book.sheet_by_name(config['sheet'])
    top = ' '.join(str(c) for i in range(min(14, sheet.nrows)) for c in sheet.row_values(i))
    basis = 'Rates as at effective dates' if kind == 'prime' else 'Daily figures'
    if 'Table ' + config['table'] not in top or basis not in top:
        raise ValueError('Official rate workbook title/basis changed')
    if kind == 'hibor':
        if ('Interest Settlement Rates' not in top or '11:15 am' not in top
                or sheet.cell_value(7, 5) != '1-month' or sheet.cell_value(7, 6) != '3-month'):
            raise ValueError('Official HIBOR fixing workbook columns changed')
    else:
        heading = ' '.join(str(sheet.cell_value(i, 10)) for i in (7, 8, 9))
        notes = ' '.join(str(c) for i in range(max(0, sheet.nrows - 15), sheet.nrows) for c in sheet.row_values(i))
        if 'Best lending rate' not in heading or 'Hongkong' not in notes or 'Shanghai Banking Corporation Limited' not in notes:
            raise ValueError('Official Prime workbook attribution/column changed')
    records = []
    for i in range(sheet.nrows):
        if sheet.cell(i, 0).ctype != xlrd.XL_CELL_DATE:
            continue
        date = xlrd.xldate_as_datetime(sheet.cell_value(i, 0), book.datemode).date().isoformat()
        records.append({config['date']: date, **{field: excel_rate_value(sheet.cell(i, col))
                       for field, (_, _, col) in config['fields'].items()}})
    return parse_records(kind, records, as_of, now, _XLS_ROOT + config['file'], 'automatic_excel')


def collect_table(kind, cache, as_of, now, fetch):
    config = TABLES[kind]
    try:
        records, pages = [], []
        for _ in range(100):
            params = dict(sortby=config['date'], sortorder='desc', pagesize=1000, offset=len(records))
            if kind == 'hibor':
                params['segment'] = 'hibor.fixing'
            url = config['api'] + '?' + urlencode(params)
            raw = fetch(url); payload = json.loads(raw)
            part = payload.get('result', {}).get('records')
            if payload.get('header', {}).get('success') is not True or not isinstance(part, list):
                raise ValueError('Invalid official ' + kind + ' API response')
            if not part:
                break
            prior_dates = {x.get(config['date']) for x in records}
            if any(r.get(config['date']) in prior_dates for r in part):
                raise ValueError('Official rate pagination repeated dates')
            records.extend(part); pages.append((url, raw))
        else:
            raise ValueError('Official rate pagination limit')
        rows = parse_records(kind, records, as_of, now,
                             config['api'] + ('?segment=hibor.fixing' if kind == 'hibor' else ''))
        for index, (_, raw) in enumerate(pages):
            _archive(cache, 'hkma_' + kind + '_' + str(index) + '.json', raw)
        return rows
    except Exception as api_error:
        try:
            raw = fetch(_XLS_ROOT + config['file'])
            rows = parse_excel(kind, raw, as_of, now)
            for row in rows:
                row['source_fallback_reason'] = str(api_error)
            _archive(cache, config['file'], raw)
            return rows
        except Exception as excel_error:
            raise ValueError(f'Official {kind}: API {api_error}; Excel {excel_error}') from excel_error


def merge_rates(prior, fresh, check_conflicts=False):
    merged = {(r['metric_id'], r['date']):r for r in prior}
    seen = set()
    for row in fresh:
        key = (row['metric_id'], row['date'])
        if key in seen:
            raise ValueError('Duplicate published rate observation')
        seen.add(key)
        if check_conflicts and key in merged and not math.isclose(merged[key]['value'],row['value'],rel_tol=0,abs_tol=0.000005):
            raise ValueError('Official daily fixing conflict: '+str(key))
        merged[key] = row
    return sorted(merged.values(),key=lambda r:(r['metric_id'],r['date']))


def _archive(cache, name, raw):
    path = Path(cache)/(hashlib.sha256(raw).hexdigest()[:16]+'-'+name)
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        path.write_bytes(raw)


def verified_html_day(date, fetch):
    # HKMA occasionally returns a mismatched dated page on the first request.
    # Retry validation once; never accept that page or infer its requested date.
    try:
        return _html_day(date,fetch)
    except ValueError:
        return _html_day(date,fetch)


def collect_hibor(cache, as_of, now, fetch):
    warnings, daily, published = [], [], []
    try:
        published = collect_table('hibor', cache, as_of, now, fetch)
        present = {row['metric_id'] for row in published}
        for tenor in ('1m', '3m'):
            if 'hk_hibor_' + tenor + '_daily' not in present:
                warnings.append('Official HIBOR table has no published ' + tenor.upper()
                                + ' observations; any prior government observations retain their original dates.')
    except Exception as exc:
        warnings.append(str(exc))
    # Daily Monetary Statistics is refreshed more promptly than the monthly
    # bulletin's table named "Daily figures", which may stop at the prior month.
    url=API_URL+'?sortby=end_of_date&sortorder=desc&pagesize=100'
    try:
        raw=fetch(url); payload=json.loads(raw)
        records=payload.get('result',{}).get('records')
        if payload.get('header',{}).get('success') is not True or not isinstance(records,list) or not records:
            raise ValueError('Missing HKMA daily records')
        for record in records:
            daily.append(_row('hk_hibor_1m_daily','1 Month HIBOR',_date(record['end_of_date'],as_of),
                              record['hibor_fixing_1m'],'hk_rates_hibor','Hong Kong Monetary Authority',url,now))
        daily=merge_rates([],daily)
        _archive(cache,'hkma_recent_hibor.json',raw)
    except Exception as api_error:
        daily=[]
        try:
            cutoff=dt.date.fromisoformat(as_of)-dt.timedelta(days=1)
            current=dt.date.fromisoformat(as_of).replace(day=1)
            previous=(current-dt.timedelta(days=1)).replace(day=1)
            calendar_raw=fetch(CALENDAR_URL)
            expected,_=_calendar(calendar_raw,[previous,current])
            dates=sorted(day for values in expected.values() for day in values if day<=cutoff)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(lambda day:verified_html_day(day,fetch),dates))
            for record,evidence in results:
                row=_row('hk_hibor_1m_daily','1 Month HIBOR',record['end_of_date'],record['hibor_fixing_1m'],
                    'hk_rates_hibor','Hong Kong Monetary Authority',evidence['url'],now)
                row['source_fallback_reason']=str(api_error)
                daily.append(row)
                _archive(cache,'hkma_hibor_'+row['date']+'.html',evidence['html'].encode())
            _archive(cache,'hkma_hibor_holidays.json',calendar_raw)
        except Exception as exc:
            daily=[]; warnings.append('HKMA daily history: API '+str(api_error)+'; HTML '+str(exc))
    if not daily and not published:
        raise ValueError('; '.join(warnings))
    return merge_rates(published,daily,check_conflicts=True), warnings


def refresh(prior, old_statuses, cache, as_of, now, fetch):
    """Refresh feeds independently; outages never advance observation/check dates."""
    old_status={s['source_id']:s for s in old_statuses}
    rows, statuses, errors = [], [], []
    for source_id, name, url in [('hsbc_prime_effective','HKMA-published HSBC effective Prime rate',PRIME_API_URL),
                                ('hk_rates_hibor','HKMA-published daily HIBOR',HIBOR_API_URL+'?segment=hibor.fixing')]:
        previous=government_rows([r for r in prior if r.get('source_id')==source_id])
        warnings=[]
        try:
            if source_id=='hsbc_prime_effective':
                fresh=collect_table('prime',cache,as_of,now,fetch)
            else:
                fresh,warnings=collect_hibor(cache,as_of,now,fetch)
            part=merge_rates(previous,fresh,check_conflicts=source_id=='hk_rates_hibor')
            state='Review: partial source refresh' if warnings else 'Verified'
            success=now
            errors.extend(source_id+': '+w for w in warnings)
        except Exception as exc:
            part=previous;state='Retained: refresh failed'
            success=old_status.get(source_id,{}).get('last_success') if previous else None
            errors.append(source_id+': '+str(exc))
        rows.extend(part)
        statuses.append(dict(source_id=source_id,source_name=name,source_url=url,status=state,checked_at=now,
            last_success=success,latest_period=max((r['date'] for r in part),default=None),rows=len(part),
            change_summary=f'{len(part)-len(previous)} new daily/effective rate records'))
    return rows,statuses,errors
