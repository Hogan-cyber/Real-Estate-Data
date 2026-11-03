"""Calculate closed-month 1M HIBOR from complete official HKMA daily fixings.

The published monthly series always wins. The independent government holiday
calendar prevents partial daily coverage being presented as a monthly average.
No cached response is used when a live source or its validation fails.
"""
from __future__ import annotations

import calendar
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import statistics

API_URL = 'https://api.hkma.gov.hk/public/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity'
CALENDAR_URL = 'https://www.1823.gov.hk/common/ical/en.json'
HTML_ROOT = 'https://www.hkma.gov.hk/eng/data-publications-and-research/data-and-statistics/daily-monetary-statistics/'
DOC_URL = 'https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/daily-monetary-statistics/daily-figures-interbank-liquidity/'


def _today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()


def _json(raw):
    if len(raw) > 30_000_000:
        raise ValueError('HIBOR supplement source exceeds size limit')
    return json.loads(raw.decode('utf-8-sig'))


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Missing or invalid daily HIBOR fixing')
    return value


def _month_start(period):
    if not isinstance(period, str) or not re.fullmatch(r'\d{4}-\d{2}', period):
        raise ValueError('Invalid monthly HIBOR reference period')
    return dt.date.fromisoformat(period+'-01')


def _next_month(date):
    return (date.replace(day=28)+dt.timedelta(days=4)).replace(day=1)


def _calendar(raw, months):
    payload = _json(raw)
    calendars = payload.get('vcalendar', [])
    if len(calendars) != 1 or 'Hong Kong Public Holidays' not in calendars[0].get('prodid', ''):
        raise ValueError('Official Hong Kong holiday calendar identity changed')
    holidays = set()
    for event in calendars[0].get('vevent', []):
        value = event.get('dtstart', [])
        if not isinstance(value, list) or len(value) != 2 or value[1].get('value') != 'DATE':
            raise ValueError('Holiday calendar date format changed')
        date = dt.datetime.strptime(value[0], '%Y%m%d').date()
        if date in holidays:
            raise ValueError('Duplicate holiday calendar date')
        holidays.add(date)
    for year in {m.year for m in months}:
        dates = sorted(d for d in holidays if d.year == year)
        if not dates or dates[0].month != 1 or dates[-1].month != 12:
            raise ValueError(f'Official holiday calendar does not cover {year}')
    expected = {}
    for month in months:
        expected[month.strftime('%Y-%m')] = {
            month.replace(day=day) for day in range(1, calendar.monthrange(month.year, month.month)[1]+1)
            if month.replace(day=day).weekday() < 5 and month.replace(day=day) not in holidays
        }
    return expected, payload


def _api(fetch, first_date, as_of):
    records, pages, seen = [], [], set()
    for _ in range(12):
        url = API_URL+'?pagesize=100'+(f'&offset={len(records)}' if records else '')
        payload = _json(fetch(url))
        if payload.get('header', {}).get('success') is not True:
            raise ValueError('HKMA daily liquidity API did not report success')
        page = payload.get('result', {}).get('records')
        if not isinstance(page, list) or not page:
            raise ValueError('HKMA daily liquidity API has insufficient history')
        for row in page:
            date = dt.date.fromisoformat(row['end_of_date'])
            if date in seen or date > as_of:
                raise ValueError('Duplicate or future daily HIBOR observation')
            seen.add(date)
            records.append(row)
        pages.append({'url':url, 'response':payload})
        if min(seen) <= first_date:
            return records, pages
    raise ValueError('HKMA daily liquidity pagination did not reach required month')


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden-1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _html_day(date, fetch):
    url = HTML_ROOT+date.strftime('%Y/%m/ms-%Y%m%d/')
    raw = fetch(url)
    if len(raw) > 3_000_000:
        raise ValueError('HKMA daily monetary HTML exceeds size limit')
    html = raw.decode('utf-8-sig')
    parser = _Text()
    parser.feed(html)
    text = ' '.join(' '.join(parser.parts).split())
    dates = re.findall(r'Date and Time\s*(?:\([^)]*\))?\s*:\s*\d{2}:\d{2},\s*(\d{2}/\d{2}/\d{4})', text)
    if 'Daily Monetary Statistics' not in text or not dates or set(dates) != {date.strftime('%d/%m/%Y')}:
        raise ValueError(f'HKMA daily page reference date does not match {date}')
    values = re.findall(r'HKAB\s+1-Month HIBOR Fixing\s*:\s*(?:\([^)]*\))?\s*(\d+(?:\.\d+)?)\s*%', text)
    if len(values) != 1:
        raise ValueError(f'HKMA daily page 1M fixing is missing or ambiguous for {date}')
    return {'end_of_date':date.isoformat(), 'hibor_fixing_1m':_number(float(values[0]))}, {'url':url, 'html':html}


def _validate(records, expected, template):
    grouped = {period:{} for period in expected}
    for record in records:
        date = dt.date.fromisoformat(record['end_of_date'])
        period = date.strftime('%Y-%m')
        if period not in grouped:
            continue
        if date in grouped[period]:
            raise ValueError('Duplicate daily HIBOR observation')
        grouped[period][date] = _number(record.get('hibor_fixing_1m'))
    for period, dates in expected.items():
        if set(grouped[period]) != dates:
            missing = sorted(str(d) for d in dates-set(grouped[period]))
            extra = sorted(str(d) for d in set(grouped[period])-dates)
            raise ValueError(f'Incomplete daily HIBOR coverage for {period}: missing={missing}; unexpected={extra}')
    overlap = statistics.mean(grouped[template['period']].values())
    if not math.isclose(overlap, _number(template['value']), rel_tol=0, abs_tol=0.000005):
        raise ValueError('Daily HIBOR mean disagrees with the latest published monthly observation')
    return grouped


def supplement(rows, cache, as_of, fetch):
    """Return calculated 1M rows only; callers retain all official monthly rows."""
    today = min(dt.date.fromisoformat(str(as_of)[:10]), _today())
    published = [r for r in rows if r.get('metric_id') == 'hk_hibor_1m' and r.get('status') != 'Calculated']
    if not published:
        raise ValueError('A published monthly 1M HIBOR observation is required for validation')
    template = max(published, key=lambda r:r['period'])
    first = _month_start(template['period'])
    current = today.replace(day=1)
    months = [first]
    while _next_month(months[-1]) < current:
        months.append(_next_month(months[-1]))
    if len(months) == 1:
        return []
    if len(months) > 4:
        raise ValueError('HIBOR monthly source is more than three completed months behind')
    expected, calendar_payload = _calendar(fetch(CALENDAR_URL), months)
    first_fixing = min(expected[template['period']])
    archive = {'as_of':today.isoformat(), 'calendar':{'url':CALENDAR_URL,'response':calendar_payload}}
    api_error = None
    try:
        records, pages = _api(fetch, first_fixing, today)
        grouped = _validate(records, expected, template)
        archive['api_pages'] = pages
        mode = 'automatic_api_calculated'
    except Exception as error:
        api_error = f'{type(error).__name__}: {error}'[:500]
        try:
            dates = sorted(set().union(*expected.values()))
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(lambda date:_html_day(date, fetch), dates))
            grouped = _validate([r[0] for r in results], expected, template)
            archive['html_pages'] = [r[1] for r in results]
            archive['api_error'] = api_error
            mode = 'automatic_html_calculated'
        except Exception as html_error:
            raise RuntimeError(f'HIBOR daily supplement failed: API ({api_error}); HTML ({type(html_error).__name__}: {html_error})') from html_error
    extra = []
    for month in months[1:]:
        period = month.strftime('%Y-%m')
        observations = grouped[period]
        row = dict(template)
        row.pop('source_fallback_reason', None)
        row.update(period=period, date=( _next_month(month)-dt.timedelta(days=1)).isoformat(),
            value=statistics.mean(observations.values()), status='Calculated', flags='', missing_reason=None,
            source_url=API_URL if not api_error else HTML_ROOT+max(observations).strftime('%Y/%m/ms-%Y%m%d/'),
            source_documentation=DOC_URL, source_table='Daily Monetary Statistics', source_field='hibor_fixing_1m',
            fetch_mode=mode, observation_basis='Monthly average (calculated from daily fixings)',
            calculation_basis='Arithmetic mean of all published HKAB 1-month daily fixings on Hong Kong business days in the completed calendar month; no forward filling.',
            daily_observation_count=len(observations), daily_first_date=min(observations).isoformat(),
            daily_last_date=max(observations).isoformat(), calendar_source_url=CALENDAR_URL,
            note='Calculated from complete official HKMA Daily Monetary Statistics, with business-day coverage checked against the Hong Kong government holiday calendar. This is not yet the published HKMA monthly average; the official monthly release replaces it when available.')
        if api_error:
            row['source_fallback_reason'] = api_error
        extra.append(row)
    archive['calculated_rows'] = extra
    path = Path(cache)/'hkma_hibor_daily_supplement.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)
    return extra
