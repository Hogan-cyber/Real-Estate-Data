"""Small deterministic HKMA workbook + latest-release collectors.

The old survey tab supplies core series before December 2016; collected
detail starts with the current workbook's December 2016 coverage. Older
official press-release history is not yet included. No filling, annual-to-
monthly conversion, or bank/non-bank residual estimates are made.
"""
from __future__ import annotations

import calendar
import datetime as dt
import io
import json
import math
import re
from pathlib import Path
from urllib.parse import urljoin

import openpyxl
import requests
import xlrd

from ..collectors import hk_hkma_collector as legacy

ROOT = 'https://www.hkma.gov.hk'
MSB = ROOT + '/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/'
PRESS = ROOT + '/eng/news-and-media/press-releases/'
MONTHS = {name.lower(): i for i in range(1, 13) for name in (calendar.month_name[i], calendar.month_abbr[i])}
SURVEY_NOTE = ('HKMA residential mortgage survey: loans to individuals, including refinancing, excluding specified subsidized housing schemes. '
               'Amounts are HKD million; approvals and drawdowns are separate monthly flows; outstanding amounts are month-end stocks. '
               'Co-financing includes only reporting institutions\' portions, not developer/non-bank top-up loans. '
               'LTV and contractual life are weighted by loan amount. Missing values are not filled. ')
MONEY_NOTE = ('End-month money supply, not seasonally adjusted, new series since April 1997. '
              'M2/M3 HKD includes foreign-currency swap deposits; foreign currency excludes them. '
              'Foreign currency and all-currency totals are expressed in HKD million. ')

# column, metric id suffix, label, unit, numeric multiplier
SURVEY = {
    'D': ('outstanding', 'Outstanding residential mortgage loans', 'HKD million', 1),
    'H': ('cofinancing_government_outstanding_amount', 'Government co-financing: outstanding amount', 'HKD million', 1),
    'I': ('cofinancing_government_outstanding_count', 'Government co-financing: outstanding loans', 'loans', 1),
    'K': ('cofinancing_private_outstanding_amount', 'Private co-financing: outstanding amount', 'HKD million', 1),
    'L': ('cofinancing_private_outstanding_count', 'Private co-financing: outstanding loans', 'loans', 1),
    'N': ('delinquency', 'Mortgage delinquency ratio: more than 3 months', '%', 1),
    'O': ('delinquency_6m', 'Mortgage delinquency ratio: more than 6 months', '%', 1),
    'Q': ('rescheduled_ratio', 'Rescheduled mortgage loan ratio', '%', 1),
    'T': ('applications', 'New mortgage applications', 'applications', 1),
    'W': ('drawn_amount', 'New mortgage loans drawn down: amount', 'HKD million', 1),
    'Z': ('drawn_count', 'New mortgage loans drawn down: count', 'loans', 1),
    'AC': ('approved_amount', 'New mortgage loans approved: amount', 'HKD million', 1),
    'AF': ('approved_count', 'New mortgage loans approved: count', 'loans', 1),
    'AH': ('approved_average_size', 'Average size of new approved mortgages', 'HKD million', 1),
    'AI': ('approved_ltv', 'Loan-to-value ratio of new approved mortgages', '%', 1),
    'AJ': ('approved_tenor', 'Contractual life of new approved mortgages', 'months', 1),
    'AK': ('cofinancing_approved_amount', 'Approved co-financed mortgages: amount', 'HKD million', 1),
    'AL': ('cofinancing_approved_count', 'Approved co-financed mortgages: count', 'loans', 1),
    'AN': ('approved_primary_amount', 'Primary-market mortgage approvals: amount', 'HKD million', 1),
    'AO': ('approved_secondary_amount', 'Secondary-market mortgage approvals: amount', 'HKD million', 1),
    'AP': ('approved_refinancing_amount', 'Refinancing mortgage approvals: amount', 'HKD million', 1),
    'AR': ('approved_primary_count', 'Primary-market mortgage approvals: count', 'loans', 1),
    'AS': ('approved_secondary_count', 'Secondary-market mortgage approvals: count', 'loans', 1),
    'AT': ('approved_refinancing_count', 'Refinancing mortgage approvals: count', 'loans', 1),
    'AV': ('approved_undrawn_amount', 'Mortgages approved during month but not drawn: amount', 'HKD million', 1),
    'AW': ('approved_undrawn_count', 'Mortgages approved during month but not drawn: count', 'loans', 1),
    'AY': ('pricing_hibor_share', 'New approved mortgages priced with reference to HIBOR', '%', 100),
    'AZ': ('pricing_blr_share', 'New approved mortgages priced with reference to BLR', '%', 100),
    'BA': ('pricing_fixed_share', 'New approved mortgages with fixed rates', '%', 100),
    'BB': ('pricing_other_share', 'New approved mortgages with other pricing', '%', 100),
    'BD': ('written_off_amount', 'Mortgage loans written off during month', 'HKD million', 1),
    'BG': ('written_off_12m_amount', 'Mortgage loans written off over past 12 months', 'HKD million', 1),
    'BH': ('written_off_12m_ratio', 'Past-12-month write-offs as share of average outstanding', '%', 1),
}
OLD_COLUMNS = {'D':'D', 'E':'N', 'F':'Q', 'I':'Z', 'J':'W', 'K':'AF', 'L':'AC', 'M':'AW', 'N':'AV'}
NEGATIVE = {
    'D': ('count', 'Negative-equity mortgages: outstanding count', 'loans', 1),
    'E': ('borrower_share', 'Negative-equity mortgages: share of total borrowers', '%', 1),
    'G': ('amount', 'Negative-equity mortgages: outstanding value', 'HKD million', 1),
    'H': ('amount_share', 'Negative-equity mortgages: share of outstanding value', '%', 1),
    'I': ('unsecured_amount', 'Negative-equity mortgages: unsecured portion', 'HKD million', 1),
    'J': ('ltv', 'Negative-equity mortgages: loan-to-value ratio', '%', 100),
}


def _number(value, multiplier=1):
    text = str(value).strip()
    if value is None or text.upper() in ('', 'N.A.', 'N/A', 'NA', '-', '--'):
        return None, 'not_available'
    if text == '*':
        return None, 'below_reporting_threshold'
    try:
        result = float(text.replace(',', '').replace('%', '')) * multiplier
    except (ValueError, TypeError) as exc:
        raise ValueError('Unexpected HKMA value: ' + repr(value)) from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError('Invalid HKMA numeric value: ' + repr(value))
    return result, ''


def _row(metric, name, period, value, unit, source, url, note, frequency='M', flags='', **extra):
    year, month = map(int, period.split('-'))
    return dict(metric_id=metric, metric_name=name, period=period,
                date=dt.date(year, month, calendar.monthrange(year, month)[1]).isoformat(),
                frequency=frequency, value=value, unit=unit, source_id=source,
                source_name='Hong Kong Monetary Authority', source_url=url,
                status='Published' if value is not None else 'Missing', flags=flags,
                note=note, **extra)


def _sheet_rows(sheet, max_col):
    return list(sheet.iter_rows(max_col=max_col, values_only=True))


def _period_rows(rows, quarterly=False):
    year = None
    for index, cells in enumerate(rows, 1):
        if isinstance(cells[0], (float, int)) and 1900 <= cells[0] <= 2200:
            year = int(cells[0])
        label = str(cells[1]).strip()
        month = (int(label[1])*3 if re.fullmatch('Q[1-4]', label) else None) if quarterly else MONTHS.get(label.lower())
        if month:
            if year is None:
                raise ValueError('HKMA observation has no year')
            yield index, f'{year:04d}-{month:02d}', cells


def parse_survey_workbook(raw):
    book = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    out = {}
    for name, columns in [('T3.7 (old)', OLD_COLUMNS), ('T3.7', {c:c for c in SURVEY})]:
        sheet = book[name]
        data = _sheet_rows(sheet, 60)
        if 'Residential mortgage survey results' not in str(data[0][0]):
            raise ValueError('Survey workbook title changed')
        if name == 'T3.7' and (str(data[8][34]).strip() != 'Loan-to-value ratio7' or str(data[8][35]).strip() != 'Contractual life7'):
            raise ValueError('Survey LTV/tenor columns changed')
        for index, period, cells in _period_rows(data):
            if name.endswith('(old)') and not '2000-12' <= period < '2016-12':
                continue  # Exclude the different pre-expansion survey population.
            for col, mapped in columns.items():
                suffix, label, unit, factor = SURVEY[mapped]
                value, flags = _number(cells[openpyxl.utils.column_index_from_string(col)-1], factor)
                note = SURVEY_NOTE + ('Historical expanded survey group; workbook old tab, pre-Dec2016. ' if name.endswith('(old)') else
                                     'Collected detailed workbook coverage starts Dec2016; older official press-release history is not included. ')
                if flags == 'below_reporting_threshold':
                    note += 'Source reports *, not an exact numeric zero; no value imputed. '
                row = _row('hk_mortgage_'+suffix,label,period,value,unit,'hkma_survey',MSB+'T0307.xlsx',note,
                           flags=flags, source_table=name, source_field=f'{col}{index}: {label}',
                           source_sheet=name, source_cell=f'{col}{index}', source_raw_value=cells[openpyxl.utils.column_index_from_string(col)-1])
                out[row['metric_id'], period] = row
    book.close()
    return list(out.values())


def parse_survey_annex(text, period, url, published):
    records = legacy.parse_survey_annex(text, period)
    base = legacy._survey_rows(records, dt.date.max, url, 'automatic_pdf')
    out = []
    canonical = {'hk_mortgage_'+v[0]:v for v in SURVEY.values()}
    for r in base:
        if r.get('observation_type') == 'derived':
            continue
        r.update(source_id='hkma_survey', status='Published', flags='', published_date=published)
        _, r['metric_name'], r['unit'], _ = canonical[r['metric_id']]
        r['source_name'] = 'Hong Kong Monetary Authority'
        r['note'] = SURVEY_NOTE
        out.append(r)
    text = re.sub(r'[^\S\n]+', ' ', text)
    previous = (dt.date.fromisoformat(period+'-01')-dt.timedelta(days=1)).strftime('%Y-%m')
    token = r'(\d[\d,]*(?:\.\d+)?|\*)%?'
    patterns = {
        'AH': (r'c\. Average size ', '2.c. Average size'),
        'AI': (r'd\. Loan-to-value ratio \(%\) ', '2.d. Loan-to-value ratio (%)'),
        'AJ': (r'e\. Contractual life \(months\) ', '2.e. Contractual life (months)'),
        'O': (r'- More than 6 months ', '4.c. Delinquency ratio (%): More than 6 months'),
        'Q': (r'd\. Rescheduled loan ratio \(%\) ', '4.d. Rescheduled loan ratio (%)'),
        'BD': (r'a\. Value of loans written off during the month ', '5.a. Value of loans written off during the month'),
        'BG': (r'b\. Loans written off over the past 12 months\s+- Value ', '5.b. Loans written off over the past 12 months: Value'),
        'BH': (r'- As % of the average outstanding loans ', '5.b. Loans written off over the past 12 months: As % of the average outstanding loans'),
        'AV': (r'h\. New loans approved during the month but not yet drawn\s+- Value ', '2.h. New loans approved during the month but not yet drawn: Value'),
        'AW': (r'h\. New loans approved during the month but not yet drawn\s+- Value [\d,]+ [\d,]+\s+- Number ', '2.h. New loans approved during the month but not yet drawn: Number'),
        'AY': (r'a\. With reference to Hong Kong Interbank Offered Rate(?:\s*\(HIBOR\))?\s+', '6.a. With reference to Hong Kong Interbank Offered Rate (HIBOR)'),
        'AZ': (r'b\. With reference to Best Lending Rate \(BLR\) ', '6.b. With reference to Best Lending Rate (BLR)'),
        'BA': (r'c\. Fixed rate ', '6.c. Fixed rate'),
        'BB': (r'd\. Others ', '6.d. Others'),
    }
    for col, (prefix, field) in patterns.items():
        matches = re.findall(prefix+token+r'\s+'+token, text)
        if len(matches) != 1:
            raise ValueError('Latest survey annex detail missing/ambiguous: '+col)
        suffix, label, unit, _ = SURVEY[col]
        for p,v in zip((period,previous),matches[0]):
            value,flags = _number(v)
            note = SURVEY_NOTE + ('Source * means less than 0.05%; exact value unavailable. ' if flags == 'below_reporting_threshold' else '')
            out.append(_row('hk_mortgage_'+suffix,label,p,value,unit,'hkma_survey',url,note,
                            flags=flags,published_date=published,source_raw_value=v,
                            source_table='Residential Mortgage Survey annex',source_field=field))
    return out


def parse_money_workbook(raw):
    sheet = xlrd.open_workbook(file_contents=raw).sheet_by_name('T2.2.1 (new series)')
    data = [sheet.row_values(i) for i in range(sheet.nrows)]
    if 'Adjusted for foreign currency swap deposits' not in str(data[3][0]):
        raise ValueError('Money workbook basis changed')
    expected = ['HK$', 'F.C.', 'Total', 'HK$2', 'F.C.3', 'Total', 'HK$2', 'F.C.3', 'Total']
    if data[9][5:14] != expected:
        raise ValueError('Money workbook columns changed')
    out=[]
    for index,period,cells in _period_rows(data):
        for group in range(1,4):
            for offset,(currency,label) in enumerate([('hkd','Hong Kong dollar'),('fc','Foreign currency'),('total','All-currency')]):
                col = 5+(group-1)*3+offset
                value,flags=_number(cells[col])
                out.append(_row(f'hk_m{group}_{currency}',f'{label} M{group}',period,value,'HKD million','hkma_money',MSB+'T020201.xls',MONEY_NOTE,
                                flags=flags,source_cell=f'{openpyxl.utils.get_column_letter(col+1)}{index}',
                                source_table=sheet.name,
                                source_field=f'{openpyxl.utils.get_column_letter(col+1)}{index}: M{group} - {data[9][col]}'))
    return out


def parse_money_annex(text, period, url, published):
    title = f'HONG KONG MONETARY STATISTICS - {calendar.month_name[int(period[5:])]} {period[:4]}'
    if title not in text or '(HK$ Million)' not in text:
        raise ValueError('Money annex title/units changed')
    block = text.split('Money Supply',1)[1].split('Notes and coins in circulation',1)[0]
    # PDF inserts spaces within digit groups. Lines are split at the first
    # parenthesized growth rate; the first two figures are current/prior levels.
    out=[]; group=None; currency=None
    for line in block.splitlines():
        if re.match(r'M[123] - HK\$',line):
            group=int(line[1]);currency='hkd';line=re.sub(r'^M[123] - HK\$2?\s+','',line)
        elif line.startswith('Foreign currency'):
            currency='fc';line=re.sub(r'^Foreign currency1?\s+','',line)
        elif line.startswith('Total '):
            currency='total';line=line[6:]
        else:continue
        # Each printed level has comma-separated thousands; whitespace inside
        # these digit groups is an extraction artifact, not a delimiter.
        match=re.match(r'([\d ]+,\s*\d{3},\s*\d{3})\s+([\d ]+,\s*\d{3},\s*\d{3})\s*\(',line)
        if not match:
            raise ValueError('Money annex level columns changed: '+line)
        value,_=_number(match[1].replace(' ',''))
        label={'hkd':'Hong Kong dollar','fc':'Foreign currency','total':'All-currency'}[currency]
        out.append(_row(f'hk_m{group}_{currency}',f'{label} M{group}',period,value,'HKD million','hkma_money',url,
                        MONEY_NOTE+'Latest press-release table rounds amounts to whole HKD million; historical workbook may retain decimals.',published_date=published,
                        source_table='Table 1A: Hong Kong Monetary Statistics',
                        source_field=f'Money Supply: M{group} - '+{'hkd':'HK$','fc':'Foreign currency','total':'Total'}[currency]))
    if len(out)!=9 or len({r['metric_id'] for r in out})!=9:
        raise ValueError('Money annex did not yield all nine money-supply fields')
    for g in range(1,4):
        values={r['metric_id'].split('_')[-1]:r['value'] for r in out if r['metric_id'].startswith(f'hk_m{g}_')}
        if abs(values['hkd']+values['fc']-values['total'])>2:
            raise ValueError('Money annex currency totals do not reconcile')
    return out


def parse_negative_workbook(raw):
    book=openpyxl.load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
    data=_sheet_rows(book['T3.16'],10)
    if 'Negative Equity' not in str(data[0][0]) or data[5][3]!='Total outstanding number':
        raise ValueError('Negative equity workbook schema changed')
    out=[]
    for index,period,cells in _period_rows(data,quarterly=True):
        for col,(suffix,label,unit,factor) in NEGATIVE.items():
            value,flags=_number(cells[openpyxl.utils.column_index_from_string(col)-1],factor)
            out.append(_row('hk_negative_equity_'+suffix,label,period,value,unit,'hkma_negative_equity',MSB+'T0316.xlsx',
                            'Quarterly extrapolated residential mortgage negative-equity survey. Bank first mortgages only. No monthly interpolation. '
                            'Collected workbook coverage starts Q4 2016; older official press-release history is not included.',
                            frequency='Q',flags=flags,source_cell=f'{col}{index}',
                            source_table='T3.16',source_field=f'{col}{index}: {label}'))
    book.close()
    return out


def parse_negative_annex(text, period, url, published):
    title=f'End of {calendar.month_name[int(period[5:])]} {period[:4]}'
    if title not in text:raise ValueError('Negative equity annex period mismatch')
    headers=re.findall(r'([A-Z][a-z]{2})-(\d{4})',text)
    periods=[f'{y}-{MONTHS[m.lower()]:02d}' for m,y in headers]
    if len(periods)!=3 or periods[0]!=period:raise ValueError('Negative equity annex headers changed')
    patterns={
        'count':r'Total outstanding number', 'borrower_share':r'As % of total mortgage borrowers',
        'amount':r'Total outstanding value \(HK\$ million\)', 'amount_share':r'As % of total outstanding value',
        'unsecured_amount':r'Value of unsecured portion \(HK\$ million\)', 'ltv':r'Loan-to-value ratio',
        'delinquency':r'Delinquency ratio \(more than 3 months\)',
    }
    definitions={v[0]:v for v in NEGATIVE.values()}
    definitions['delinquency']=('delinquency','Negative-equity mortgages: delinquency over 3 months','%',1)
    out=[]
    for suffix,label in patterns.items():
        match=re.search(r'(?m)^'+label+r'\s+([\d,.]+%?|\*)\s+([\d,.]+%?|\*)\s+([\d,.]+%?|\*)\s*$',text)
        if not match:raise ValueError('Negative equity annex field missing: '+suffix)
        _,name,unit,_=definitions[suffix]
        for p,v in zip(periods,match.groups()):
            value,flags=_number(v)
            out.append(_row('hk_negative_equity_'+suffix,name,p,value,unit,'hkma_negative_equity',url,
                            'Quarterly extrapolated negative-equity survey of first mortgages from authorized institutions; no monthly interpolation.',
                            frequency='Q',flags=flags,published_date=published,
                            source_table='Key Extrapolated Results of the Survey on Residential Mortgage Loans in Negative Equity',
                            source_field=label.replace(r'\(', '(').replace(r'\)', ')').replace(r'\$', '$')))
    return out


def _download(url, destination):
    response=requests.get(url,timeout=35,headers={'User-Agent':'HKPropertyData/1.0 public statistics'})
    response.raise_for_status()
    raw=response.content
    if not raw or len(raw)>30_000_000:raise ValueError('Empty/oversized official source')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(raw)
    return raw


def _latest_release(kind, as_of, directory):
    catalogs={'survey':'monthly-residential-mortgage-survey-results','money':'monetary-statistics','negative':'quarterly-residential-mortgage-loans-in-negative-equity'}
    prefixes={'survey':'Residential Mortgage Survey Results for ','money':'Monetary Statistics for ','negative':'Residential mortgage loans in negative equity: End of '}
    url=PRESS+catalogs[kind]+'/'
    html=_download(url,directory/f'{kind}_catalog.html').decode('utf-8')
    candidates=[]
    for href,label in legacy._Links(html).links:
        if not label.startswith(prefixes[kind]):continue
        match=re.fullmatch(r'([A-Za-z]+) (\d{4})',' '.join(label[len(prefixes[kind]):].split()))
        dated=re.search(r'/(\d{8})-\d+/$',href)
        if not match or not dated:continue
        published=dt.datetime.strptime(dated[1],'%Y%m%d').date().isoformat()
        period=f'{int(match[2]):04d}-{MONTHS[match[1].lower()]:02d}'
        if published<=as_of:candidates.append((period,published,urljoin(url,href)))
    if not candidates:raise ValueError('No eligible official '+kind+' release')
    period,published,landing=max(candidates)
    page=_download(landing,directory/f'{kind}_release.html').decode('utf-8')
    annex={urljoin(landing,href) for href,label in legacy._Links(page).links if label.strip()=='Annex'}
    if len(annex)!=1:raise ValueError('Official release annex missing/ambiguous')
    pdf_url=annex.pop()
    if not pdf_url.startswith(ROOT+'/media/') or not pdf_url.endswith('.pdf'):raise ValueError('Unexpected annex URL')
    raw=_download(pdf_url,directory/f'{kind}_{period}.pdf')
    import pdfplumber
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        text='\n'.join(p.extract_text() or '' for p in pdf.pages[:2])
    (directory/f'{kind}_{period}.txt').write_text(text,encoding='utf-8')
    return period,published,landing,pdf_url,text


def collect(output_dir: Path, as_of: str, start='2002-01') -> list[dict]:
    as_of=str(as_of)[:10];dt.date.fromisoformat(as_of)
    output_dir=Path(output_dir);directory=output_dir/'raw'/'hkma';directory.mkdir(parents=True,exist_ok=True)
    out=[];diagnostics={}
    for kind,filename,parser,annex_parser in [
        ('survey','T0307.xlsx',parse_survey_workbook,parse_survey_annex),
        ('money','T020201.xls',parse_money_workbook,parse_money_annex),
        ('negative','T0316.xlsx',parse_negative_workbook,parse_negative_annex),
    ]:
        rows=[];errors=[];latest=None
        try:rows=parser(_download(MSB+filename,directory/filename))
        except Exception as exc:errors.append('Workbook: '+str(exc))
        try:
            period,published,landing,url,text=_latest_release(kind,as_of,directory)
            latest=period
            newer=annex_parser(text,period,url,published)
            for r in newer:r['source_documentation']=landing
            # Prefer higher-precision workbook values when current; newest PDF
            # supplies missing periods and authoritative survey revisions.
            merged={(r['metric_id'],r['period']):r for r in rows}
            for r in newer:
                key=(r['metric_id'],r['period'])
                if kind!='money' or key not in merged:merged[key]=r
            rows=list(merged.values())
        except Exception as exc:errors.append('Latest release: '+str(exc))
        if not rows:raise RuntimeError(kind+': '+'; '.join(errors))
        eligible=[r for r in rows if r['period']>=start and r['date']<=as_of]
        for r in eligible:
            r['checked_at']=as_of
            if errors:r['refresh_warning']='; '.join(errors)
        out.extend(eligible)
        diagnostics[kind]={'latest_announced_period':latest,'first_period':min((r['period'] for r in eligible),default=None),
                           'last_period':max((r['period'] for r in eligible),default=None),'observations':len(eligible),'errors':errors}
    out.sort(key=lambda r:(r['metric_id'],r['period']))
    parts=output_dir/'parts';parts.mkdir(parents=True,exist_ok=True)
    (parts/'hkma.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    (directory/'diagnostics.json').write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding='utf-8')
    return out
