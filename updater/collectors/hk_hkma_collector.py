"""HKMA public-source collector. collect(cache_dir, as_of) returns observation rows.

Runtime: Python 3.10 or newer. The monthly API uses the standard library only.
For PDF reports install pdfplumber (preferred), with pypdf as an optional fallback:
    python3 -m pip install pdfplumber pypdf
If neither PDF dependency is available, rate refresh fails safely and preserves
the last verified rate. No machine-specific filesystem paths are required.

Freshness: new-mortgage rate observations have explicit calendar months, but
their public source is a semiannual report (normally March and September).
Judge source freshness against the latest available report, not a monthly
release deadline or the age of its latest explicitly reported observation.
No HIBOR/BLR or mortgage-pricing shares are used as a mortgage lending rate.
Each source is cached atomically and independently; failed refreshes retain old rows.
"""
from __future__ import annotations
import calendar
import datetime as dt
import http.client
import io
import json
import math
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

API = 'https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey'
API_URL = API + '?segment=new&sortby=end_of_month&sortorder=desc&pagesize=1000'
CATALOG = 'https://www.hkma.gov.hk/eng/data-publications-and-research/publications/half-yearly-monetary-financial-stability-report/'
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTH_RE = '(?:' + '|'.join(calendar.month_name[1:]) + ')'
FIELDS = {
    'new_loans_approved_amt': ('hk_mortgage_approved_amount', '新批住宅按揭贷款金额', '百万港元'),
    'new_loans_drawn_amt': ('hk_mortgage_drawn_amount', '新提取住宅按揭贷款金额', '百万港元'),
    'new_loans_approved': ('hk_mortgage_approved_count', '新批住宅按揭贷款宗数', '宗'),
    'new_loans_drawn': ('hk_mortgage_drawn_count', '新提取住宅按揭贷款宗数', '宗'),
    'new_loans_app_received': ('hk_mortgage_applications', '住宅按揭申请宗数', '宗'),
    'delinquency_ratio': ('hk_mortgage_delinquency', '住宅按揭逾期超过三个月比率', '%'),
    'outstanding_loans_amt': ('hk_mortgage_outstanding', '未偿还住宅按揭贷款余额', '百万港元'),
}

def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'HKHousingDashboard/1.0 (public statistics)'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                data = response.read(30_000_001)
            if len(data) > 30_000_000:
                raise ValueError('Source exceeds 30 MB safety limit')
            return data
        except urllib.error.HTTPError as exc:
            if attempt == 2 or not (exc.code == 429 or 500 <= exc.code <= 599):
                raise
            exc.close()
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                ssl.SSLError, http.client.IncompleteRead):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)

def _as_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])

def _month_end(period):
    year, month = map(int, period.split('-'))
    return dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat()

def _save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)

def _base(metric_id, name, period, value, unit, url, as_of):
    return dict(market='HK', category='mortgage', metric_id=metric_id,
                metric_name=name, period=period, date=_month_end(period), value=value,
                unit=unit, frequency='M', seasonal_adjustment='NSA',
                source_name='香港金融管理局', source='香港金融管理局', source_url=url,
                published_date=None, status='updated', checked_at=as_of.isoformat())

def _survey(as_of):
    payload = json.loads(_get(API_URL))
    if payload.get('header', {}).get('success') is not True:
        raise ValueError('HKMA API did not report success')
    records = payload.get('result', {}).get('records')
    if not isinstance(records, list) or not records:
        raise ValueError('HKMA API returned no records')
    rows, seen = [], set()
    for record in records:
        period = record.get('end_of_month', '')
        if not re.fullmatch(r'\d{4}-\d{2}', period):
            raise ValueError('Invalid API period')
        if period in seen:
            raise ValueError('Duplicate API month')
        seen.add(period)
        if period < '2015-01' or _month_end(period) > as_of.isoformat():
            continue
        for key, (metric_id, name, unit) in FIELDS.items():
            value = record.get(key)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid or missing {key} in {period}')
            if key == 'delinquency_ratio' and value > 100:
                raise ValueError('Invalid delinquency percentage')
            row = _base(metric_id, name, period, value, unit, API_URL, as_of)
            row.update(scope='香港住宅按揭调查；覆盖约99%银行业住宅按揭贷款；包括转按，排除指定资助房屋计划',
                       fetch_mode='automatic_api',
                       note='月度调查。金额单位为百万港元；新批与提取为当月流量，未偿余额与拖欠率为月末存量。拖欠率数值已是百分数，勿再乘100。新批贷款可能于以后月份提取。')
            rows.append(row)
    if not rows:
        raise ValueError('No API observations on or before as_of')
    return rows

def parse_mortgage_text(text, report_period, as_of):
    """Accept only explicit rate/month/year in a sentence about new mortgages.

    Unknown wording, conflicting latest values, future dates, or no exact date fail.
    A flat Jan-Jul statement yields its endpoint only, never fabricated monthly data.
    """
    text = re.sub(r'\s+', ' ', text).replace('\u00ad', '')
    sentences = re.findall(r'average lending rate for new mortgages\b(.{0,650}?)(?:\.(?=\s+[A-Z])|$)', text, re.I)
    points = []
    for sentence in sentences:
        # Example: remained unchanged at 3.26% from January to July 2026.
        flat = re.search(r'(?:remained|was|stayed)\s+unchanged\s+at\s+(\d+(?:\.\d+)?)\s*%\s+from\s+' + MONTH_RE + r'(?:\s+\d{4})?\s+to\s+(' + MONTH_RE + r')\s+(\d{4})', sentence, re.I)
        if flat:
            points.append((int(flat[3]), MONTHS[flat[2].lower()], float(flat[1])))
        # Example: ... fell to 3.26% in January 2026.
        for match in re.finditer(r'(\d+(?:\.\d+)?)\s*%\s+in\s+(' + MONTH_RE + r')\s+(\d{4})', sentence, re.I):
            points.append((int(match[3]), MONTHS[match[2].lower()], float(match[1])))
    valid = []
    for year, month, value in points:
        period = f'{year:04d}-{month:02d}'
        if not 0 < value < 30 or period.replace('-', '') > report_period or _month_end(period) > as_of.isoformat():
            raise ValueError('Implausible or future mortgage-rate observation')
        valid.append((period, value))
    if not valid:
        raise ValueError('No unambiguous mortgage rate with explicit month/year')
    latest = max(p for p, _ in valid)
    values = {v for p, v in valid if p == latest}
    if len(values) != 1:
        raise ValueError('Conflicting mortgage rates for latest month')
    return latest, values.pop()

def _pdf_pages(data):
    if not data.startswith(b'%PDF'):
        raise ValueError('Report response is not a PDF')
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            # Reports use two columns; full-page extraction can insert chart labels
            # into the mortgage-rate sentence. Read columns independently.
            texts = []
            for page in pdf.pages:
                for box in [(0, 0, page.width / 2, page.height),
                            (page.width / 2, 0, page.width, page.height)]:
                    texts.append(page.crop(box).extract_text() or '')
            return texts
    except ImportError:
        from pypdf import PdfReader
        return [page.extract_text() or '' for page in PdfReader(io.BytesIO(data)).pages]

def _mortgage_rate(as_of, cache_dir):
    html = _get(CATALOG).decode('utf-8')
    links = re.findall(r'href=[\"\']([^\"\']+half-yearly-monetary-financial-stability-report/(\d{6})/)[\"\']', html, re.I)
    available = {(p, urljoin(CATALOG, u)) for u, p in links if p <= as_of.strftime('%Y%m')}
    if not available:
        raise ValueError('No dated reports discovered in official catalog')
    rows = []
    for index, (report_period, landing) in enumerate(sorted(available, reverse=True)[:2]):
        try:
            page = _get(landing).decode('utf-8')
            pdfs = re.findall(r'href=[\"\']([^\"\']*E_Half-yearly_' + report_period + r'\.pdf)[\"\']', page, re.I)
            if len(set(pdfs)) != 1:
                raise ValueError('Full-report PDF link missing or ambiguous')
            url = urljoin(landing, pdfs[0])
            data = _get(url)
            pages = _pdf_pages(data)
            period, value = parse_mortgage_text(' '.join(pages), report_period, as_of)
            row = _base('hk_new_mortgage_rate', '新造按揭平均贷款利率', period, value, '% p.a.', url, as_of)
            row.update(scope='香港银行新造住宅按揭平均贷款利率；金管局半年度报告明确文字观察值',
                       published_date=report_period[:4] + '-' + report_period[4:],
                       source_period=report_period[:4] + '-' + report_period[4:],
                       source_frequency='semiannual', freshness_basis='latest_official_report',
                       observation_frequency='explicit_months_only',
                       seasonal_adjustment='NA', fetch_mode='automatic_pdf',
                       note='自动发现最新半年度报告，只采用明确的新造按揭平均贷款利率及观察月份；不以HIBOR、最优惠利率或定价占比替代。不填补未明确报告月份；报告发布月份不等于利率观察月份。')
            rows.append(row)
            (cache_dir / ('hkma_report_' + report_period + '.pdf')).write_bytes(data)
        except Exception:
            if index == 0:
                raise
    if not rows:
        raise ValueError('No parsed mortgage rates')
    return rows

def collect(cache_dir, as_of):
    as_of = _as_date(as_of)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    all_rows, diagnostics = [], {}
    for name, fetch in [('survey', lambda: _survey(as_of)),
                        ('mortgage_rate', lambda: _mortgage_rate(as_of, cache_dir))]:
        path = cache_dir / ('hkma_' + name + '.json')
        old = json.loads(path.read_text()) if path.exists() else {'rows': []}
        old_rows = [r for r in old.get('rows', []) if r['date'] <= as_of.isoformat()]
        if name == 'mortgage_rate':
            for row in old_rows:
                row.update(source_frequency='semiannual',
                           freshness_basis='latest_official_report',
                           observation_frequency='explicit_months_only')
                row.setdefault('source_period', row.get('published_date'))
        try:
            fresh = fetch()
            # Preserve history while accepting current official revisions.
            merged = {(r['metric_id'], r['period']): r for r in old_rows}
            merged.update({(r['metric_id'], r['period']): r for r in fresh})
            rows = sorted(merged.values(), key=lambda r: (r['metric_id'], r['date']))
            _save(path, {'last_success': as_of.isoformat(), 'rows': rows})
            diagnostics[name] = {'status': 'updated', 'latest_period': max(r['period'] for r in fresh), 'records': len(fresh)}
            if name == 'mortgage_rate':
                diagnostics[name].update(
                    source_frequency='semiannual',
                    freshness_basis='latest_official_report',
                    latest_source_period=max(r['source_period'] for r in fresh))
        except Exception as exc:
            rows = [dict(r, status='stale_cache', checked_at=as_of.isoformat(), refresh_error=str(exc)) for r in old_rows]
            diagnostics[name] = {'status': 'stale_cache' if rows else 'unavailable', 'error': str(exc), 'last_success': old.get('last_success')}
            if name == 'mortgage_rate':
                diagnostics[name].update(
                    source_frequency='semiannual',
                    freshness_basis='latest_official_report',
                    latest_source_period=max((r.get('source_period') or '' for r in rows), default=None))
        all_rows.extend(rows)
    _save(cache_dir / 'hkma_status.json', {'as_of': as_of.isoformat(), 'sources': diagnostics})
    if not all_rows:
        raise RuntimeError('Both HKMA sources unavailable; see hkma_status.json')
    return all_rows

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-dir', default=str(Path(__file__).parent / 'hkma_cache'))
    parser.add_argument('--as-of', default=dt.date.today().isoformat())
    args = parser.parse_args()
    observations = collect(args.cache_dir, args.as_of)
    print(json.dumps({'records': len(observations), 'latest': {r['metric_id']: {'period': r['period'], 'value': r['value'], 'status': r['status']} for r in sorted(observations, key=lambda r: r['date'])}}, ensure_ascii=False, indent=2))
