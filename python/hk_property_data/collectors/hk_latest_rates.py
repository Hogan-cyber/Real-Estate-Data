"""Published daily/effective rates, kept separate from monthly averages."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor

from .hk_prime_supplement import HISTORY_URL, _parse_history
from .hk_hibor_supplement import API_URL, HTML_ROOT, CALENDAR_URL, _Text, _calendar, _html_day

HKAB_URL = 'https://www.hkab.org.hk/en/rates/hibor/'


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


def parse_hkab(raw, as_of, now):
    parser = _Text(); parser.feed(raw.decode('utf-8-sig'))
    text = ' '.join(' '.join(parser.parts).split())
    matches = re.findall(r'Rates as at 11:15a\.m\.\s*Hong Kong Time on (\d{4})-(\d{1,2})-(\d{1,2})\.', text)
    if len(matches) != 1 or 'HKD Interest Settlement Rates' not in text:
        raise ValueError('HKAB fixing date/table schema changed')
    date = _date(dt.date(*map(int, matches[0])).isoformat(), as_of)
    result = []
    for tenor, label in [('1m','1 Month'), ('3m','3 Months')]:
        values = re.findall(r'(?<!\w)'+label+r'\s+(\d+(?:\.\d+)?)(?!\w)', text)
        if len(values) != 1:
            raise ValueError('Missing or ambiguous HKAB '+label+' fixing')
        result.append(_row('hk_hibor_'+tenor+'_daily', label+' HIBOR', date, float(values[0]),
                           'hk_rates_hibor', 'Hong Kong Association of Banks', HKAB_URL, now))
    return result


def parse_prime(raw, as_of, now):
    return [_row('hk_prime_rate_hsbc_effective', 'HSBC Prime rate', _date(date.isoformat(), as_of),
                 float(value), 'hsbc_prime_effective', 'HSBC', HISTORY_URL, now, 'E')
            for date, value in _parse_history(raw)]


def merge_rates(prior, fresh, check_conflicts=False):
    merged = {(r['metric_id'], r['date']):r for r in prior}
    seen = set()
    for row in fresh:
        key = (row['metric_id'], row['date'])
        if key in seen:
            raise ValueError('Duplicate published rate observation')
        seen.add(key)
        if check_conflicts and key in merged and not math.isclose(merged[key]['value'],row['value'],rel_tol=0,abs_tol=0.000005):
            raise ValueError('HKAB / HKMA daily fixing conflict: '+str(key))
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
    warnings, daily, latest = [], [], []
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
    try:
        raw=fetch(HKAB_URL); latest=parse_hkab(raw,as_of,now)
        _archive(cache,'hkab_latest_hibor.html',raw)
    except Exception as exc:
        warnings.append('HKAB current fixings: '+str(exc))
    if not daily and not latest:
        raise ValueError('; '.join(warnings))
    return merge_rates(daily,latest,check_conflicts=True), warnings


def refresh(prior, old_statuses, cache, as_of, now, fetch):
    """Refresh feeds independently; outages never advance observation/check dates."""
    old_status={s['source_id']:s for s in old_statuses}
    rows, statuses, errors = [], [], []
    for source_id, name, url in [('hsbc_prime_effective','HSBC effective Prime rate',HISTORY_URL),
                                ('hk_rates_hibor','HKAB / HKMA daily HIBOR',HKAB_URL)]:
        previous=[r for r in prior if r.get('source_id')==source_id]
        warnings=[]
        try:
            if source_id=='hsbc_prime_effective':
                raw=fetch(url); fresh=parse_prime(raw,as_of,now)
                _archive(cache,'hsbc_prime_effective.html',raw)
            else:
                fresh,warnings=collect_hibor(cache,as_of,now,fetch)
            part=merge_rates(previous,fresh,check_conflicts=source_id=='hk_rates_hibor')
            state='Review: partial source refresh' if warnings else 'Verified'
            success=now
            errors.extend(source_id+': '+w for w in warnings)
        except Exception as exc:
            part=previous;state='Retained: refresh failed';success=old_status.get(source_id,{}).get('last_success')
            errors.append(source_id+': '+str(exc))
        rows.extend(part)
        statuses.append(dict(source_id=source_id,source_name=name,source_url=url,status=state,checked_at=now,
            last_success=success,latest_period=max((r['date'] for r in part),default=None),rows=len(part),
            change_summary=f'{len(part)-len(previous)} new daily/effective rate records'))
    return rows,statuses,errors
