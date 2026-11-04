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
import posixpath
import re
import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

API = 'https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/banking/residential-mortgage-survey'
API_URL = API + '?segment=new&sortby=end_of_month&sortorder=desc&pagesize=1000'
SURVEY_XLSX = 'https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T0307.xlsx'
SURVEY_RELEASES = 'https://www.hkma.gov.hk/eng/news-and-media/press-releases/monthly-residential-mortgage-survey-results/'
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
COFINANCING_FIELDS = {
    'new_loans_approved_cofin_amt': ('hk_mortgage_cofinancing_approved_amount', 'Approved mortgage loans involving co-financing: amount', 'HKD million'),
    'new_loans_approved_cofin': ('hk_mortgage_cofinancing_approved_count', 'Approved mortgage loans involving co-financing: count', 'loans'),
    'outstanding_loans_cofin_gf_amt': ('hk_mortgage_cofinancing_government_outstanding_amount', 'Outstanding co-financed mortgages: government-funded schemes, amount', 'HKD million'),
    'outstanding_loans_cofin_gf': ('hk_mortgage_cofinancing_government_outstanding_count', 'Outstanding co-financed mortgages: government-funded schemes, count', 'loans'),
    'outstanding_loans_cofin_ps_amt': ('hk_mortgage_cofinancing_private_outstanding_amount', 'Outstanding co-financed mortgages: private-sector schemes, amount', 'HKD million'),
    'outstanding_loans_cofin_ps': ('hk_mortgage_cofinancing_private_outstanding_count', 'Outstanding co-financed mortgages: private-sector schemes, count', 'loans'),
}
COFINANCING_COLUMNS = {
    'AK': 'new_loans_approved_cofin_amt', 'AL': 'new_loans_approved_cofin',
    'H': 'outstanding_loans_cofin_gf_amt', 'I': 'outstanding_loans_cofin_gf',
    'K': 'outstanding_loans_cofin_ps_amt', 'L': 'outstanding_loans_cofin_ps',
}
COFINANCING_SCOPE = (
    'Residential mortgage loans involving co-financing; only the portions advanced by '
    'reporting authorized institutions are included (HKMA survey note 6). '
    'Developer or other co-financier top-up lending is excluded; these are not non-bank lending totals.'
)
TRANSACTION_FIELDS = {
    'new_loans_approved_pt_amt_pri': ('hk_mortgage_approved_primary_amount', 'Approved primary-market residential mortgages: amount', 'HKD million'),
    'new_loans_approved_pt_amt_sec': ('hk_mortgage_approved_secondary_amount', 'Approved secondary-market residential mortgages: amount', 'HKD million'),
    'new_loans_approved_pt_amt_refin': ('hk_mortgage_approved_refinancing_amount', 'Approved residential mortgage refinancing: amount', 'HKD million'),
    'new_loans_approved_pt_primkt': ('hk_mortgage_approved_primary_count', 'Approved primary-market residential mortgages: count', 'loans'),
    'new_loans_approved_pt_secmkt': ('hk_mortgage_approved_secondary_count', 'Approved secondary-market residential mortgages: count', 'loans'),
    'new_loans_approved_pt_refin': ('hk_mortgage_approved_refinancing_count', 'Approved residential mortgage refinancing: count', 'loans'),
}
TRANSACTION_COLUMNS = {
    'AN':'new_loans_approved_pt_amt_pri', 'AO':'new_loans_approved_pt_amt_sec', 'AP':'new_loans_approved_pt_amt_refin',
    'AR':'new_loans_approved_pt_primkt', 'AS':'new_loans_approved_pt_secmkt', 'AT':'new_loans_approved_pt_refin',
}
PURCHASE_COMPONENTS = {
    'amount': ('new_loans_approved_pt_amt_pri', 'new_loans_approved_pt_amt_sec'),
    'count': ('new_loans_approved_pt_primkt', 'new_loans_approved_pt_secmkt'),
}
TRANSACTION_SCOPE = (
    'New residential mortgage loans approved by surveyed authorized institutions during the month, '
    'classified by primary market, secondary market or refinancing; not drawdowns and not non-bank lending totals. '
    'Loans to private individuals, excluding the specified subsidized housing schemes; '
    'the survey covers about 99% of banking-sector residential mortgage lending, not 99% of all lenders.'
)
PURCHASE_SCOPE = (
    'Derived bank purchase-purpose residential mortgage approvals: primary-market plus secondary-market approvals, '
    'excluding refinancing. Monthly approval flows, not drawdowns, completed sales or unique properties; '
    'not non-bank or money-lender mortgage totals. The HKMA survey population and exclusions apply; '
    'bank loans involving co-financing remain included.'
)
SURVEY_DETAIL_GROUPS = {
    'Co-financing': {v[0] for v in COFINANCING_FIELDS.values()},
    'Approved transaction-type': {v[0] for v in TRANSACTION_FIELDS.values()} |
        {'hk_mortgage_approved_purchase_' + suffix for suffix in PURCHASE_COMPONENTS},
}


def _valid_survey_value(value, field):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid or missing survey value: ' + field)
    definition = {**FIELDS, **COFINANCING_FIELDS, **TRANSACTION_FIELDS}.get(field)
    if definition and definition[2] in ('loans', '宗') and not float(value).is_integer():
        raise ValueError('Non-integer mortgage count: ' + field)
    return value


def _validate_transaction_totals(record):
    # Amounts in HKD million are independently rounded; account counts are exact.
    for total, parts, tolerance in (
        ('new_loans_approved', ('new_loans_approved_pt_primkt', 'new_loans_approved_pt_secmkt', 'new_loans_approved_pt_refin'), 0),
        ('new_loans_approved_amt', ('new_loans_approved_pt_amt_pri', 'new_loans_approved_pt_amt_sec', 'new_loans_approved_pt_amt_refin'), 2),
    ):
        if total in record:
            values = [_valid_survey_value(record[key], key) for key in parts if key in record]
            difference = sum(values) - _valid_survey_value(record[total], total)
            if difference > tolerance or (len(values) == len(parts) and abs(difference) > tolerance):
                raise ValueError('Mortgage transaction-type components do not reconcile: ' + total)

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

def _survey_rows(records, as_of, url=API_URL, mode='automatic_api', include_cofinancing=True, include_transaction_types=True):
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
        if _month_end(period) > as_of.isoformat():
            continue
        fields = dict(FIELDS)
        if include_cofinancing and any(key in record for key in COFINANCING_FIELDS):
            fields.update(COFINANCING_FIELDS)
        if include_transaction_types:
            fields.update({key: value for key, value in TRANSACTION_FIELDS.items() if key in record})
            _validate_transaction_totals(record)
        for key, (metric_id, name, unit) in fields.items():
            value = _valid_survey_value(record.get(key), key)
            if key == 'delinquency_ratio' and value > 100:
                raise ValueError('Invalid delinquency percentage')
            row = _base(metric_id, name, period, value, unit, url, as_of)
            row.update(scope='香港住宅按揭调查；覆盖约99%银行业住宅按揭贷款；包括转按，排除指定资助房屋计划',
                       fetch_mode=mode,
                       note='月度调查。金额单位为百万港元；新批与提取为当月流量，未偿余额与拖欠率为月末存量。拖欠率数值已是百分数，勿再乘100。新批贷款可能于以后月份提取。')
            row.update(source_field=key, source_table='HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7',
                       source_frequency='monthly', source_period=period)
            if key in COFINANCING_FIELDS:
                row.update(scope=COFINANCING_SCOPE, source_note='6',
                           note='Approved loans are monthly flows; outstanding loans are month-end stocks. Amounts are HKD million; counts are loans. ' + COFINANCING_SCOPE)
                if mode == 'automatic_excel':
                    row['source_column'] = next(col for col, field in COFINANCING_COLUMNS.items() if field == key)
            elif key in TRANSACTION_FIELDS:
                row.update(scope=TRANSACTION_SCOPE, source_note='1,2,3,6', observation_type='official',
                           note='Approved loans may be drawn in the same month or later. ' + TRANSACTION_SCOPE)
                if mode == 'automatic_excel':
                    row['source_column'] = next(col for col, field in TRANSACTION_COLUMNS.items() if field == key)
            rows.append(row)
        if include_transaction_types:
            for suffix, components in PURCHASE_COMPONENTS.items():
                if not all(key in fields for key in components):
                    continue
                unit = 'loans' if suffix == 'count' else 'HKD million'
                formula = ' + '.join(components)
                row = _base('hk_mortgage_approved_purchase_' + suffix,
                            'Derived bank purchase-purpose mortgage approvals: ' + suffix,
                            period, sum(record[key] for key in components), unit, url, as_of)
                row.update(scope=PURCHASE_SCOPE, fetch_mode=mode, observation_type='derived',
                           source_field=formula, derivation=formula,
                           derived_from=[TRANSACTION_FIELDS[key][0] for key in components],
                           source_table='HKMA Residential Mortgage Survey / Monthly Statistical Bulletin Table 3.7',
                           source_note='1,2,3,6', source_frequency='monthly', source_period=period,
                           note='Calculated only when both official component values are available; no missing value is replaced by zero. ' + PURCHASE_SCOPE)
                if mode == 'automatic_excel':
                    row['source_column'] = ' + '.join(next(col for col, key in TRANSACTION_COLUMNS.items() if key == component) for component in components)
                rows.append(row)
    if not rows:
        raise ValueError('No API observations on or before as_of')
    return rows


def parse_survey_xlsx(data, include_cofinancing=True, include_transaction_types=True):
    """Read only the reviewed Table 3.7 schema; no formula execution or old series."""
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        if sum(i.file_size for i in book.infolist()) > 30_000_000:
            raise ValueError('Mortgage workbook exceeds expanded size limit')
        strings = [''.join(t.text or '' for t in cell.findall('.//s:t', ns))
                   for cell in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('s:si', ns)] if 'xl/sharedStrings.xml' in book.namelist() else []
        sheets = [s for s in ET.fromstring(book.read('xl/workbook.xml')).findall('s:sheets/s:sheet', ns) if s.get('name') == 'T3.7']
        if len(sheets) != 1:
            raise ValueError('Mortgage workbook T3.7 sheet missing or ambiguous')
        rid = sheets[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        links = ET.fromstring(book.read('xl/_rels/workbook.xml.rels'))
        targets = [x.get('Target') for x in links if x.get('Id') == rid and x.get('TargetMode') != 'External']
        if len(targets) != 1:
            raise ValueError('Mortgage worksheet reference invalid')
        target = posixpath.normpath(posixpath.join('xl', targets[0])) if not targets[0].startswith('/') else targets[0].lstrip('/')
        if not target.startswith('xl/worksheets/'):
            raise ValueError('Unexpected mortgage worksheet location')
        cells = {}
        for cell in ET.fromstring(book.read(target)).findall('s:sheetData/s:row/s:c', ns):
            value = cell.find('s:v', ns)
            kind = cell.get('t')
            if kind == 'inlineStr':
                cells[cell.get('r')] = ''.join(t.text or '' for t in cell.findall('.//s:t', ns))
            elif value is not None:
                cells[cell.get('r')] = strings[int(value.text)] if kind == 's' else float(value.text) if kind in (None, 'n') else value.text
    expected = {'A1':'Table 3.7 Residential mortgage survey results1,2', 'D4':'As at end of period','T4':'During the period',
        'D6':'Outstanding loans','T6':'New applications received','W6':'New loans drawn down','AC6':'New loans approved3',
        'D9':'Value','N9':'Delinquency ratio4','T9':'Number','W9':'Value','Z9':'Number','AC9':'Value','AF9':'Number',
        'N11':'More than 3 months','D15':'(HK$ Mn)','N15':'(%)','T15':'(No.)','W15':'(HK$ Mn)',
        'Z15':'(No.)','AC15':'(HK$ Mn)','AF15':'(No.)'}
    if include_cofinancing:
        expected.update({'H9':'Loans associated with co-financing schemes6',
            'H11':'Government-funded schemes:', 'K11':'Schemes offered by the private sector:',
            'H13':'Value', 'I13':'Number', 'K13':'Value', 'L13':'Number',
            'AK8':'Loans associated with', 'AK9':'co-financing schemes', 'AK11':'Value', 'AL11':'Number',
            'H15':'(HK$ Mn)', 'I15':'(No.)', 'K15':'(HK$ Mn)', 'L15':'(No.)',
            'AK15':'(HK$ Mn)', 'AL15':'(No.)'})
    if include_transaction_types:
        expected.update({'AN9':'Type of property transaction', 'AN11':'Value', 'AR11':'Number',
            'AN13':'Primary market', 'AO13':'Secondary market', 'AP13':'Refinancing',
            'AR13':'Primary market', 'AS13':'Secondary market', 'AT13':'Refinancing',
            'AN15':'(HK$ Mn)', 'AO15':'(HK$ Mn)', 'AP15':'(HK$ Mn)',
            'AR15':'(No.)', 'AS15':'(No.)', 'AT15':'(No.)'})
    for address, text in expected.items():
        if ' '.join(str(cells.get(address, '')).split()) != text:
            raise ValueError('Mortgage workbook schema changed at ' + address)
    columns = {'AC':'new_loans_approved_amt','W':'new_loans_drawn_amt','AF':'new_loans_approved','Z':'new_loans_drawn',
               'T':'new_loans_app_received','N':'delinquency_ratio','D':'outstanding_loans_amt'}
    if include_cofinancing:
        columns.update(COFINANCING_COLUMNS)
    if include_transaction_types:
        columns.update(TRANSACTION_COLUMNS)
    records, seen, year = [], set(), None
    for index in sorted({int(re.search(r'\d+$', key)[0]) for key in cells if re.fullmatch(r'[A-Z]+\d+',key)}):
        value, month = cells.get(f'A{index}'), str(cells.get(f'B{index}', '')).strip().lower()
        if isinstance(value, (int, float)) and float(value).is_integer() and 1900 <= value <= 2200:
            year = int(value)
        if month not in MONTHS:
            continue
        if year is None:
            raise ValueError('Mortgage workbook month lacks a year')
        period = f'{year:04d}-{MONTHS[month]:02d}'
        if period in seen:
            raise ValueError('Duplicate mortgage workbook month')
        seen.add(period)
        record = {'end_of_month': period}
        for column, field in columns.items():
            value = cells.get(f'{column}{index}')
            record[field] = _valid_survey_value(value, field)
        if include_transaction_types:
            _validate_transaction_totals(record)
        records.append(record)
    if not records:
        raise ValueError('No mortgage workbook observations')
    return records


class _Links(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links, self.current = [], None
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), '']
    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data
    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(self.current)
            self.current = None


def _latest_survey_release(as_of):
    candidates = []
    for href, text in _Links(_get(SURVEY_RELEASES).decode('utf-8')).links:
        match = re.fullmatch(r'Residential Mortgage Survey Results for (' + MONTH_RE + r') (\d{4})', ' '.join(text.split()), re.I)
        url = urljoin(SURVEY_RELEASES, href)
        dated = re.search(r'/press-releases/\d{4}/\d{2}/(\d{8})-\d+/$', url)
        if not match or not dated or urlparse(url).netloc != 'www.hkma.gov.hk':
            continue
        published = dt.datetime.strptime(dated[1], '%Y%m%d').date()
        period = f'{int(match[2]):04d}-{MONTHS[match[1].lower()]:02d}'
        if published <= as_of and _month_end(period) <= as_of.isoformat():
            candidates.append((period, published.isoformat(), url))
    if not candidates:
        raise ValueError('No dated monthly survey releases discovered in official catalog')
    return max(candidates)


def _survey_annex_text(data):
    if not data.startswith(b'%PDF'):
        raise ValueError('Monthly survey annex is not a PDF')
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        if len(pdf.pages) < 2:
            raise ValueError('Monthly survey annex lacks two data pages')
        return '\n'.join(p.extract_text() or '' for p in pdf.pages[:2])


def parse_survey_annex(text, period, include_cofinancing=True, include_transaction_types=True):
    """Strict labeled rows from the two numeric pages; never headline rounding."""
    text = re.sub(r'[^\S\n]+', ' ', text)
    if '住宅按揭統計調查' in text:
        title = re.search(r'(\d{4})年(\d{1,2})月的調查結果', text)
        if not title or f'{int(title[1]):04d}-{int(title[2]):02d}' != period:
            raise ValueError('Monthly survey annex title period mismatch')
        text = text.replace(title[0], f'Results of Survey for {calendar.month_name[int(title[2])]} {title[1]}')
        def header(match):
            return ' '.join(f'{calendar.month_abbr[int(month)]} {year}' for year, month in
                            ((match[1], match[2]), (match[3], match[4])))
        text = re.sub(r'(?m)^\s*(\d{4})年(\d{1,2})月 (\d{4})年(\d{1,2})月\s*$', header, text)
        translations = {
            '(金額以百萬港元計)': '(Value in HK$ million)',
            '當月貸款申請': 'New applications received during the month',
            '當月新批出按揭貸款': 'New loans approved during the month',
            '當月新取用按揭貸款': 'New loans drawn down during the month',
            '未償還按揭貸款': 'Outstanding loans', '按揭貸款撇帳': 'Loans written off',
            '涉及第二按揭計劃的貸款': 'Loans associated with co-financing schemes',
            '政府資助計劃:': 'Government-funded schemes:',
            '私營機構提供的計劃:': 'Schemes offered by the private sector:',
            '物業交易類別': 'Type of property transaction',
            '一手市場': 'Primary market', '二手市場': 'Secondary market', '轉按': 'Refinancing',
            '拖欠比率 (%)': 'Delinquency ratio (%)', '超過3個月': 'More than 3 months',
            '貸款額': 'Value', '宗數': 'Number',
        }
        for original, english in translations.items():
            text = text.replace(original, english)
        text = re.sub(r'(?m)^([a-h])\.\s*', r'\1. ', text)
    title = re.search(r'Results of Survey for (' + MONTH_RE + r') (\d{4})', text, re.I)
    if not title or f'{int(title[2]):04d}-{MONTHS[title[1].lower()]:02d}' != period:
        raise ValueError('Monthly survey annex title period mismatch')
    if text.count('(Value in HK$ million)') != 2:
        raise ValueError('Monthly survey annex value units missing or changed')
    headers = re.findall(r'(?m)^\s*([A-Za-z]{3,9}) (\d{4}) ([A-Za-z]{3,9}) (\d{4})\s*$',text)
    names = {name.lower(): i for i in range(1,13) for name in (calendar.month_name[i],calendar.month_abbr[i])}
    parsed = [tuple(f'{int(y):04d}-{names[m.lower()]:02d}' for m,y in ((h[0],h[1]),(h[2],h[3]))) for h in headers]
    previous = (dt.date.fromisoformat(period+'-01') - dt.timedelta(days=1)).strftime('%Y-%m')
    if parsed != [(period,previous)] * 2:
        raise ValueError('Monthly survey annex columns missing or reordered')
    sections = {}
    for number, label in [(1,'New applications received during the month'),(2,'New loans approved during the month'),(3,'New loans drawn down during the month'),(4,'Outstanding loans')]:
        matches = re.findall(r'(?ms)^\s*' + str(number) + r'\. ' + re.escape(label) + r'\s*\n(.*?)(?=^\s*' + str(number+1) + r'\. |\Z)',text)
        if len(matches) != 1:
            raise ValueError('Monthly survey annex section missing or ambiguous: '+str(number))
        sections[number] = matches[0]
    if len(re.findall(r'(?m)^\s*c\. Delinquency ratio \(%\)\s*$',sections[4])) != 1:
        raise ValueError('Monthly survey annex delinquency percentage units changed')
    records = [dict(end_of_month=p) for p in (period,previous)]
    mapping = {'new_loans_app_received':(1,'a. Number'),'new_loans_approved_amt':(2,'a. Value'),
        'new_loans_approved':(2,'b. Number'),'new_loans_drawn_amt':(3,'a. Value'),'new_loans_drawn':(3,'b. Number'),
        'outstanding_loans_amt':(4,'a. Value'),'delinquency_ratio':(4,'- More than 3 months')}
    number = r'(\d[\d,]*(?:\.\d+)?)'
    for field,(section,label) in mapping.items():
        pairs = re.findall(r'(?m)^\s*'+re.escape(label)+r' '+number+r' '+number+r'\s*$',sections[section])
        if len(pairs) != 1:
            raise ValueError('Monthly survey annex row missing or ambiguous: '+field)
        for record, value in zip(records,pairs[0]):
            record[field] = float(value.replace(',',''))
    if include_cofinancing:
        labels = [
            (2, 'f. Loans associated with co-financing schemes', 'g. ', 'new_loans_approved_cofin'),
            (4, 'Government-funded schemes:', 'Schemes offered by the private sector:', 'outstanding_loans_cofin_gf'),
            (4, 'Schemes offered by the private sector:', 'c. ', 'outstanding_loans_cofin_ps'),
        ]
        if len(re.findall(r'(?m)^\s*b\. Loans associated with co-financing schemes\s*$', sections[4])) != 1:
            raise ValueError('Monthly survey outstanding co-financing section missing or ambiguous')
        for section, label, end, field in labels:
            blocks = re.findall(r'(?ms)^\s*' + re.escape(label) + r'\s*\n(.*?)(?=^\s*' + re.escape(end) + r')', sections[section])
            if len(blocks) != 1:
                raise ValueError('Monthly survey co-financing group missing or ambiguous: ' + field)
            for row_label, key in [('Value', field + '_amt'), ('Number', field)]:
                pairs = re.findall(r'(?m)^\s*- ' + row_label + r' ' + number + r' ' + number + r'\s*$', blocks[0])
                if len(pairs) != 1:
                    raise ValueError('Monthly survey co-financing row missing or ambiguous: ' + key)
                for record, value in zip(records, pairs[0]):
                    record[key] = _valid_survey_value(float(value.replace(',', '')), key)
    if include_transaction_types:
        blocks = re.findall(r'(?ms)^\s*g\. Type of property transaction\s*\n(.*?)(?=^\s*h\. )', sections[2])
        if len(blocks) != 1:
            raise ValueError('Monthly survey transaction-type section missing or ambiguous')
        # Match the complete labeled block to prevent swapping count/value columns.
        groups = [
            ('Value', [('Primary market','new_loans_approved_pt_amt_pri'),
                       ('Secondary market','new_loans_approved_pt_amt_sec'),
                       ('Refinancing','new_loans_approved_pt_amt_refin')]),
            ('Number', [('Primary market','new_loans_approved_pt_primkt'),
                        ('Secondary market','new_loans_approved_pt_secmkt'),
                        ('Refinancing','new_loans_approved_pt_refin')]),
        ]
        pattern, fields = r'\s*', []
        for label, entries in groups:
            pattern += re.escape(label) + r'\s*\n'
            for label, field in entries:
                pattern += r'\s*- ' + re.escape(label) + r' ' + number + r' ' + number + r'\s*\n?'
                fields.append(field)
        match = re.fullmatch(pattern, blocks[0])
        if not match:
            raise ValueError('Monthly survey transaction-type values missing, reordered or ambiguous')
        for index, field in enumerate(fields):
            for record, value in zip(records, match.groups()[index*2:index*2+2]):
                record[field] = _valid_survey_value(float(value.replace(',', '')), field)
        for record in records:
            _validate_transaction_totals(record)
    return records


def _survey_annex_url(landing):
    """Follow the release's language link; never guess a future PDF filename."""
    links = _Links(_get(landing).decode('utf-8')).links
    chinese = {urljoin(landing, href) for href, _ in links
               if urlparse(urljoin(landing, href)).netloc == 'www.hkma.gov.hk'
               and urlparse(urljoin(landing, href)).path == urlparse(landing).path.replace('/eng/', '/chi/', 1)}
    if len(chinese) == 1:
        chinese_landing = chinese.pop()
        chinese_links = _Links(_get(chinese_landing).decode('utf-8')).links
        urls = {urljoin(chinese_landing, href) for href, text in chinese_links if text.strip() == '附件'}
        documentation = chinese_landing
    else:
        urls = {urljoin(landing, href) for href, text in links if text.strip() == 'Annex'}
        documentation = landing
    if len(urls) != 1:
        raise ValueError('Monthly survey Annex link missing or ambiguous')
    url = urls.pop()
    parsed = urlparse(url)
    if parsed.netloc != 'www.hkma.gov.hk' or not re.fullmatch(r'/media/(?:eng|chi)/doc/key-information/press-release/\d{4}/[^/]+\.pdf', parsed.path):
        raise ValueError('Monthly survey Annex URL is not an official PDF')
    return url, documentation


def _verified_survey_rows(read_records, as_of, url, mode, warnings, source_label):
    """Validate detail families independently so a bad family cannot hide valid data."""
    merged = {}
    for cofinancing, transactions, label in (
        (False, False, None), (True, False, 'co-financing'), (False, True, 'transaction-type'),
    ):
        options = dict(include_cofinancing=cofinancing, include_transaction_types=transactions)
        try:
            records = read_records(**options)
            rows = _survey_rows(records, as_of, url, mode, **options)
            merged.update({(row['metric_id'], row['period']): row for row in rows})
        except ValueError as exc:
            if label is None:
                raise
            warnings.append(f'{source_label} {label} detail could not be verified: {exc}')
    return list(merged.values())


def _survey(as_of, cache_dir=None):
    fallback_reason, rows, warnings = None, [], []
    try:
        payload = json.loads(_get(API_URL))
        if payload.get('header',{}).get('success') is not True:
            raise ValueError('HKMA API did not report success')
        records = payload.get('result',{}).get('records')
        rows = _verified_survey_rows(lambda **options: records, as_of, API_URL,
                                     'automatic_api', warnings, 'API')
    except (OSError,ValueError,http.client.IncompleteRead) as exc:
        fallback_reason = f'{type(exc).__name__}: {exc}'
    detail_ids = set().union(*SURVEY_DETAIL_GROUPS.values())
    periods = {r['period'] for r in rows}
    if not rows or sum(r['metric_id'] in detail_ids for r in rows) != len(periods) * len(detail_ids):
        try:
            raw = _get(SURVEY_XLSX)
            historical = _verified_survey_rows(lambda **options: parse_survey_xlsx(raw, **options),
                as_of, SURVEY_XLSX, 'automatic_excel', warnings, 'Historical workbook')
            source_period = max(row['period'] for row in historical)
            for row in historical:
                row.update(source_period=source_period,
                           source_documentation=SURVEY_RELEASES,
                           publication_date_basis='Publication date is not supplied by the rolling Table 3.7 workbook')
                if fallback_reason:
                    row['source_fallback_reason'] = fallback_reason
            merged = {(r['metric_id'],r['period']):r for r in historical}
            merged.update({(r['metric_id'],r['period']):r for r in rows})
            rows = list(merged.values())
            if cache_dir is not None:
                (Path(cache_dir)/'hkma_survey.xlsx').write_bytes(raw)
        except Exception as excel_error:
            if not rows:
                raise ValueError(f'Mortgage survey API failed ({fallback_reason}); official workbook failed ({excel_error})') from excel_error
            warnings.append(f'Historical survey detail workbook could not be verified: {excel_error}')
    latest = None
    try:
        latest,published,landing = _latest_survey_release(as_of)
        # Both explicit months are authoritative revisions, even if API/core is current.
        url, documentation = _survey_annex_url(landing)
        raw = _get(url)
        text = _survey_annex_text(raw)
        newer = _verified_survey_rows(lambda **options: parse_survey_annex(text, latest, **options),
            as_of, url, 'automatic_pdf', warnings, 'Latest annex')
        for row in newer:
            row.update(published_date=published,source_period=latest,source_frequency='monthly',source_documentation=documentation)
            if fallback_reason:
                row['source_fallback_reason']=fallback_reason
        merged = {(r['metric_id'],r['period']):r for r in rows}
        merged.update({(r['metric_id'],r['period']):r for r in newer})
        rows = list(merged.values())
        if cache_dir is not None:
            (Path(cache_dir)/f'hkma_survey_{latest}.pdf').write_bytes(raw)
    except Exception as exc:
        detail = f'Latest announced survey {latest} annex could not be verified' if latest else 'HKMA latest monthly release could not be verified'
        warnings.append(f'{detail}: {exc}')
    newest = max(r['period'] for r in rows)
    for label, group_ids in SURVEY_DETAIL_GROUPS.items():
        if {r['metric_id'] for r in rows if r['period'] == newest and r['metric_id'] in group_ids} != group_ids:
            warnings.append(f'{label} detail is incomplete for {newest}; missing values are unavailable, not zero')
    if warnings:
        for row in rows:
            row['refresh_warning'] = '; '.join(warnings)
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
    for name, fetch in [('survey', lambda: _survey(as_of, cache_dir)),
                        ('mortgage_rate', lambda: _mortgage_rate(as_of, cache_dir))]:
        path = cache_dir / ('hkma_' + name + '.json')
        old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'rows': []}
        old_rows = [r for r in old.get('rows', []) if r['date'] <= as_of.isoformat()]
        if name == 'mortgage_rate':
            for row in old_rows:
                row.update(source_frequency='semiannual',
                           freshness_basis='latest_official_report',
                           observation_frequency='explicit_months_only')
                row.setdefault('source_period', row.get('published_date'))
        try:
            fresh = fetch()
            if not fresh:
                raise ValueError(f'No observations returned for required HKMA {name} feed')
            # Preserve history while accepting current official revisions.
            merged = {(r['metric_id'], r['period']): r for r in old_rows}
            merged.update({(r['metric_id'], r['period']): r for r in fresh})
            if name == 'survey':
                returned = {(r['metric_id'], r['period']) for r in fresh}
                coverage_start = min(r['period'] for r in fresh)
                coverage_end = max(r['period'] for r in fresh)
                detail_labels = {metric: label for label, metrics in SURVEY_DETAIL_GROUPS.items() for metric in metrics}
                for key, row in list(merged.items()):
                    if key[0] in detail_labels and key not in returned:
                        if coverage_start <= key[1] <= coverage_end:
                            merged[key] = dict(row, status='stale_cache', checked_at=as_of.isoformat(),
                                refresh_error=detail_labels[key[0]] + ' detail was not returned within the current verified source coverage; retaining the last valid observation')
                        elif key[1] < coverage_start:
                            # Rolling publications do not republish the whole archive.
                            # Retain original provenance/check time without treating absence as failure.
                            merged[key] = {k:v for k,v in row.items() if k != 'refresh_error'}
                            merged[key].update(status='updated', source_coverage_status='archived_outside_current_coverage')
            rows = sorted(merged.values(), key=lambda r: (r['metric_id'], r['date']))
            warning = next((r['refresh_warning'] for r in fresh if r.get('refresh_warning')),None)
            if warning:
                rows = [dict(r,refresh_warning=warning) for r in rows]
            elif name == 'survey':
                rows = [{k:v for k,v in r.items() if k != 'refresh_warning'} for r in rows]
            diagnostics[name] = {'status': 'updated', 'latest_period': max(r['period'] for r in fresh), 'records': len(fresh)}
            if warning:
                diagnostics[name]['refresh_warning'] = warning
            if name == 'mortgage_rate':
                diagnostics[name].update(
                    source_frequency='semiannual',
                    freshness_basis='latest_official_report',
                    latest_source_period=max(r['source_period'] for r in fresh))
            _save(path, {'last_success': as_of.isoformat(), 'rows': rows})
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
    unavailable = [f"{name}: {state.get('error', 'no valid observations')}"
                   for name, state in diagnostics.items() if state['status'] == 'unavailable']
    if unavailable:
        raise RuntimeError('Required HKMA feed unavailable without cached history: ' + '; '.join(unavailable))
    return all_rows

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-dir', default='data/cache/hkma')
    parser.add_argument('--as-of', default=dt.date.today().isoformat())
    args = parser.parse_args()
    observations = collect(args.cache_dir, args.as_of)
    print(json.dumps({'records': len(observations), 'latest': {r['metric_id']: {'period': r['period'], 'value': r['value'], 'status': r['status']} for r in sorted(observations, key=lambda r: r['date'])}}, ensure_ascii=False, indent=2))
