"""Calculate completed-month HSBC HKD prime averages from effective rates.

The public HSBC history is the source of the rate intervals. Calendar-day
weighting reproduces observable changing-month HKMA figures at their published
two-decimal precision. These supplemental rows remain explicitly Calculated;
they never replace a monthly observation published by the HKMA.
"""
from __future__ import annotations

import calendar
from collections import Counter
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re


HISTORY_URL = 'https://www.hsbc.com.hk/investments/market-information/hk/lending-rate/'
METRIC_ID = 'hk_prime_rate_hsbc'
RATE_LABEL = "HSBC's Hong Kong Dollar Best Lending Rate"


def _today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.table is not None:
                raise ValueError('Nested HSBC rate tables are ambiguous')
            self.table = {'class': dict(attrs).get('class', '').split(), 'text': [], 'rows': []}
        elif self.table is not None:
            if tag == 'tr':
                self.row = []
            elif tag in ('td', 'th'):
                self.cell = []

    def handle_data(self, data):
        if self.table is not None:
            self.table['text'].append(data)
            if self.cell is not None:
                self.cell.append(data)

    def handle_endtag(self, tag):
        if self.table is None:
            return
        if tag in ('td', 'th') and self.cell is not None:
            if self.row is not None:
                self.row.append(' '.join(' '.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table['rows'].append(self.row)
            self.row = None
        elif tag == 'table':
            self.tables.append(self.table)
            self.table = self.row = self.cell = None


def _parse_history(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > 5_000_000:
        raise ValueError('Invalid HSBC rate-history response')
    parser = _Tables()
    parser.feed(raw.decode('utf-8-sig'))
    parser.close()
    if parser.table is not None:
        raise ValueError('Incomplete HSBC rate-history HTML')
    candidates = [table for table in parser.tables if 'desktop' in table['class']
                  and RATE_LABEL in ' '.join(' '.join(table['text']).split())]
    if len(candidates) != 1:
        raise ValueError('Missing or ambiguous HSBC HKD rate-history table')
    table = candidates[0]
    text = ' '.join(' '.join(table['text']).split())
    current = re.findall(r"HSBC's Current Hong Kong Dollar Best Lending Rate:\s*(\d+(?:\.\d+)?)%", text)
    if len(current) != 1 or len(table['rows']) != 6 or table['rows'][0] != ['Effective Date', RATE_LABEL]:
        raise ValueError('HSBC current-rate/history schema changed')
    changes = []
    for cells in table['rows'][1:]:
        if len(cells) != 2 or not re.fullmatch(r'\d{1,2} [A-Z][a-z]{2} \d{4}', cells[0]) or not re.fullmatch(r'\d+(?:\.\d+)?%', cells[1]):
            raise ValueError('Invalid HSBC effective date or percentage')
        effective = dt.datetime.strptime(cells[0], '%d %b %Y').date()
        rate = Decimal(cells[1][:-1])
        if not 0 <= rate <= 100:
            raise ValueError('HSBC effective rate outside percentage range')
        changes.append((effective, rate))
    if any(newer[0] <= older[0] for newer, older in zip(changes, changes[1:])):
        raise ValueError('HSBC history dates must be unique and descending')
    if Decimal(current[0]) != changes[0][1]:
        raise ValueError('HSBC current rate disagrees with latest effective rate')
    return sorted(changes)


def _month_dates(period):
    if not isinstance(period, str) or not re.fullmatch(r'\d{4}-\d{2}', period):
        raise ValueError('Invalid monthly prime reference period')
    year, month = map(int, period.split('-'))
    return [dt.date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1)]


def _next_month(date):
    return dt.date(date.year + (date.month == 12), date.month % 12 + 1, 1)


def _average(changes, days):
    if days[0] < changes[0][0]:
        raise ValueError('Month predates complete HSBC effective-rate coverage')
    rates = [max((change for change in changes if change[0] <= day), key=lambda change: change[0])[1]
             for day in days]
    return sum(rates, Decimal(0)) / Decimal(len(days)), Counter(rates)


def _archive(cache, raw, changes):
    if cache is None:
        return
    folder = Path(cache)
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    stem = 'hsbc_prime_history_' + digest[:16]
    metadata = {'url': HISTORY_URL, 'sha256': digest, 'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'effective_rates': [{'effective_date': day.isoformat(), 'rate': str(rate)} for day, rate in changes]}
    for suffix, content in (('.html', raw), ('.json', json.dumps(metadata, indent=2).encode())):
        destination = folder / (stem + suffix)
        temporary = destination.with_suffix(suffix + '.tmp')
        temporary.write_bytes(content)
        temporary.replace(destination)


def supplement(rows, cache, as_of, fetch):
    """Return only new completed months covered by freshly fetched HSBC history.

    Fetch/schema failures propagate to the caller so its source status can show
    an explicit warning. Archived HTML is evidence and is never a fallback feed.
    """
    cutoff = min(dt.date.fromisoformat(str(as_of)[:10]), _today())
    official = [row for row in rows if row.get('metric_id') == METRIC_ID
                and row.get('status') != 'Calculated' and row.get('fetch_mode') != 'automatic_derived']
    if not official:
        raise ValueError('A published HKMA prime series is required before supplementation')
    for row in official:
        _month_dates(row['period'])
    latest = max(row['period'] for row in official)
    start = _next_month(_month_dates(latest)[0])
    # A date-only cutoff is reached during that day; its month is not closed.
    if _month_dates(start.strftime('%Y-%m'))[-1] >= cutoff:
        return []
    raw = fetch(HISTORY_URL)
    changes = _parse_history(raw)
    if changes[-1][0] > _today():
        raise ValueError('HSBC current rate has a future effective date')
    # A step-rate series is only complete from the first listed effective date.
    covered_start = changes[0][0].replace(day=1)
    if changes[0][0].day != 1:
        covered_start = _next_month(covered_start)
    start = max(start, covered_start)
    # Check available overlap at the precision of the published monthly series.
    for row in official:
        days = _month_dates(row['period'])
        if days[0] < changes[0][0] or days[-1] >= cutoff or row.get('value') is None:
            continue
        expected, _ = _average(changes, days)
        published = Decimal(str(row['value']))
        if expected.quantize(Decimal('.01'), rounding=ROUND_HALF_UP) != published.quantize(Decimal('.01'), rounding=ROUND_HALF_UP):
            raise ValueError(f"HSBC effective-rate history conflicts with published monthly overlap: {row['period']}")
    _archive(cache, raw, changes)
    result = []
    while True:
        period = start.strftime('%Y-%m')
        days = _month_dates(period)
        if days[-1] >= cutoff:
            break
        average, counts = _average(changes, days)
        calculation = '; '.join(f'{count} days at {rate}%' for rate, count in sorted(counts.items(), reverse=True))
        result.append(dict(market='HK', category='macro', property_type='Macro', measure='interest_rate',
            metric_id=METRIC_ID, metric_name='HSBC prime rate (monthly average)', period=period,
            date=days[-1].isoformat(), value=float(average), unit='% p.a.', frequency='M',
            region='All Hong Kong', scope='HSBC Hong Kong dollar best lending rate', seasonal_adjustment='NSA',
            observation_basis='Calculated monthly average — calendar-day weighted', source_id='hkma_prime',
            source_name='HSBC', source_table='HKD best lending rate effective-date history',
            source_field='Effective Date / HSBC Hong Kong Dollar Best Lending Rate',
            source_url=HISTORY_URL, source_documentation=HISTORY_URL, published_date=None,
            status='Calculated', flags='Calculated', small_sample=False, missing_reason=None,
            fetch_mode='automatic_derived', freshness_basis='Fresh HSBC effective-date history covers the completed calendar month',
            note=f'Calculated from HSBC published effective rates, weighted across all {len(days)} calendar days including weekends and holidays; '
                 f'the new rate applies on its effective date ({calculation}). '
                 'This is a calculated monthly average, not an HKMA-published monthly figure. '
                 'Effective dates are not publication dates; no monthly publication date is inferred. '
                 'Published HKMA monthly values take precedence when available.'))
        start = _next_month(start)
    return result
