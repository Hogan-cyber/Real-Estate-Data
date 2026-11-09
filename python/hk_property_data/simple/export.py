"""Business-grouped Excel, with official observations and labelled trial estimates."""
from __future__ import annotations

import calendar
import datetime as dt
import math
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
from .mortgage_estimates import COUNT_COLUMNS, AMOUNT_COLUMNS, REGISTRATION_LAG_MONTHS

FUNCTION_URL = ('https://github.com/Hogan-cyber/Real-Estate-Data/blob/main/'
                'python/hk_property_data/simple/mortgage_estimates.py')
FORMULAS = [
    ('Timing assumption', f'LR registration month = t. HKMA input month = t - {REGISTRATION_LAG_MONTHS}. Fixed registration lag is an assumption; official dates are unchanged.'),
    ('Residential count', 'LR mortgage deeds * (residential sale agreements / all building sale agreements)'),
    ('Bank count', f'HKMA drawn count[t-{REGISTRATION_LAG_MONTHS}] * (1 - refinancing approved count[t-{REGISTRATION_LAG_MONTHS}] / total approved count[t-{REGISTRATION_LAG_MONTHS}])'),
    ('Residual count', 'Residential count estimate - bank count excluding refinancing estimate'),
    ('Amounts', f'Bank amount uses drawn amount and refinancing AMOUNT share from t-{REGISTRATION_LAG_MONTHS}. Total/residual amounts = respective count * estimated bank average loan size.'),
    ('Function', 'mortgage_estimates.build — view calculation code'),
    ('Interpretation', 'Allocation estimates. Negative residuals signal proxy/timing mismatch. LR refinancing remains included.'),
]

MODEL_METRICS = set(COUNT_COLUMNS + AMOUNT_COLUMNS) | {
    'hk_residential_sales_share','hk_bank_mortgage_refinancing_count_share',
    'hk_bank_mortgage_refinancing_amount_share','hk_bank_mortgage_purchase_average_amount_estimate',
}

ORDER = ['Transactions','Price_Indices','Prices','Rent_Indices','Rents','Popular_Developments',
         'Supply_Annual','Mortgage_Monthly',
         'Mortgage_Registrations','Negative_Equity_Quarterly','Money_Supply','HIBOR_Daily',
         'Prime_Rate','Rates_Monthly']


def sheet_for(row):
    metric=row['metric_id'].lower()
    if metric in MODEL_METRICS:return 'Mortgage_Monthly'
    if metric.startswith('rvd_'):
        for prefix,sheet in [('rvd_1_1_','Rents'),('rvd_1_2_','Prices'),('rvd_1_3_','Rent_Indices'),
                             ('rvd_1_4_','Price_Indices'),('rvd_1_5_','Popular_Developments')]:
            if metric.startswith(prefix):return sheet
        return 'Supply_Annual'
    if metric.startswith('hk_residential_') or metric=='hk_all_building_sales_count':return 'Transactions'
    if metric.startswith('hk_all_property_'):return 'Mortgage_Registrations'
    if 'negative_equity' in metric or row.get('frequency')=='Q':return 'Negative_Equity_Quarterly'
    if metric.startswith('hk_mortgage_'):return 'Mortgage_Monthly'
    if 'hibor' in metric and row['frequency']=='D':return 'HIBOR_Daily'
    if 'prime' in metric and row['frequency']=='E':return 'Prime_Rate'
    if 'hibor' in metric or 'prime' in metric:return 'Rates_Monthly'
    if any(x in metric for x in ('m1_','m2_','m3_','money_supply','monetary_base','aggregate_balance')):return 'Money_Supply'
    return 'Mortgage_Monthly'


def group_for(sheet):
    if sheet in ORDER[:7]:return 'Sales & Rent'
    if sheet in ('Mortgage_Monthly','Mortgage_Registrations','Negative_Equity_Quarterly'):return 'Mortgage'
    return 'Macro'


def validate(rows,start,as_of):
    if not rows:raise ValueError('Empty dataset')
    seen=set()
    for r in rows:
        key=(r['metric_id'],r['period'],r['frequency'])
        if key in seen:raise ValueError(f'Duplicate observation: {key}')
        seen.add(key)
        date=dt.date.fromisoformat(r['date'])
        if r['date'][:7]<start or r['date']>as_of:
            raise ValueError(f'Observation outside requested period: {key}')
        if r['value'] is not None and (isinstance(r['value'],bool) or not isinstance(r['value'],(int,float)) or not math.isfinite(r['value'])):
            raise ValueError(f'Invalid numeric observation: {key}')
        if not r.get('source_url','').startswith('https://'):
            raise ValueError(f'Missing source: {key}')


def _months(start,end):
    year,month=map(int,start[:7].split('-'));output=[]
    while f'{year:04}-{month:02}'<=end[:7]:
        output.append(f'{year:04}-{month:02}')
        month+=1
        if month==13:year,month=year+1,1
    return output


def _style_table(ws,header_row,color):
    ws.freeze_panes=f'B{header_row+1}'
    ws.auto_filter.ref=f'A{header_row}:{get_column_letter(ws.max_column)}{ws.max_row}'
    ws.sheet_view.showGridLines=False
    for c in ws[header_row]:
        c.fill=PatternFill('solid',fgColor=color);c.font=Font(color='FFFFFF',bold=True,size=10)
        c.alignment=Alignment(wrap_text=True,vertical='center')
    ws.row_dimensions[header_row].height=62
    ws.column_dimensions['A'].width=16
    for col in range(2,ws.max_column+1):ws.column_dimensions[get_column_letter(col)].width=23
    for row in ws.iter_rows(min_row=header_row+1):
        for cell in row:cell.font=Font(name='Calibri',size=10)


def _formula_block(ws):
    """Put the method in view; numeric dataset cells remain directly readable."""
    for label, text in FORMULAS:
        ws.append([label, text])
        row=ws.max_row
        ws.merge_cells(start_row=row,start_column=2,end_row=row,end_column=6)
        ws.cell(row,1).font=Font(name='Calibri',bold=True,size=10)
        ws.cell(row,1).alignment=Alignment(wrap_text=True,vertical='center')
        ws.cell(row,2).alignment=Alignment(wrap_text=True,vertical='center')
        ws.cell(row,2).font=Font(name='Calibri',size=10)
        ws.row_dimensions[row].height=40 if label in ('Amounts','Timing assumption','Bank count') else 28
        if label=='Function':
            ws.cell(row,2).hyperlink=FUNCTION_URL
            ws.cell(row,2).style='Hyperlink'


def _data_status(records):
    """Compact exceptions, with full per-observation provenance in CSV/Parquet."""
    labels=set()
    model_labels={'MODEL_ESTIMATE','CALCULATED','SALES_MIX_PROXY','APPROVAL_MIX_PROXY',
                  'LR_REFINANCING_NOT_REMOVED','UNIDENTIFIED_LENDER_RESIDUAL',
                  'BANK_AVERAGE_LOAN_SIZE_ASSUMED'}
    readable={'NEGATIVE_RESIDUAL':'Negative residual','MISSING_INPUT':'Missing input',
              'INVALID_INPUT':'Invalid input','X':'X: fewer than 5 cases',
              'Y':'Y: fewer than 10 cases','Z':'Z: fewer than 20 cases',
              'BELOW_REPORTING_THRESHOLD':'Below reporting threshold'}
    for r in records:
        flags=set(filter(None,r.get('flags','').split(';')))
        for flag in flags-model_labels:
            if flag.startswith('REGISTRATION_LAG_ASSUMED_'):
                continue  # The shared assumption is visible above the table.
            labels.add(readable.get(flag.upper(),flag))
        status=r.get('status','').lower()
        if 'partial' in status or any('PARTIAL' in flag for flag in flags):labels.add('Partial coverage')
        if 'provisional' in status or any('PROVISIONAL' in flag for flag in flags):labels.add('Provisional')
        if r.get('value') is None and not flags:
            labels.add('Source blank')
    return '; '.join(sorted(labels))


def build_excel(rows,path,start,as_of,errors):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    validate(rows,start,as_of)
    grouped=defaultdict(list)
    for row in rows:grouped[sheet_for(row)].append(row)
    wb=Workbook();overview=wb.active;overview.title='Contents'
    overview.append(['Hong Kong residential dataset'])
    overview.append(['Start',start,'Checked as of',as_of])
    _formula_block(overview)
    overview.append(['Blank cells','Not published / outside source coverage / missing at source; never zero-filled.'])
    overview.append(['Collection warnings','; '.join(errors) if errors else 'None'])
    overview.append([])
    overview.append(['Group','Sheet','Frequency','Earliest observation','Latest observation','Series'])
    contents_header=overview.max_row
    dictionary=[]
    for name in ORDER:
        part=grouped.get(name,[])
        if not part:continue
        group=group_for(name);color={'Sales & Rent':'245B78','Mortgage':'28745A','Macro':'6D548C'}[group]
        frequencies={r['frequency'] for r in part}
        if len(frequencies)!=1:raise ValueError(f'Mixed frequencies in {name}: {frequencies}')
        frequency=next(iter(frequencies))
        series=defaultdict(list)
        for r in part:series[r['metric_id']].append(r)
        metrics=sorted(series)
        if name=='Mortgage_Monthly':
            official=[m for m in metrics if m not in MODEL_METRICS]
            results=[m for m in COUNT_COLUMNS+AMOUNT_COLUMNS if m in series]
            helpers=[m for m in metrics if m in MODEL_METRICS and m not in results]
            metrics=official+results+helpers
        headers=[]
        for m in metrics:
            s=series[m];latest=max(s,key=lambda r:r['date']);valid=[r for r in s if r['value'] is not None]
            units={r['unit'] for r in s}
            if len(units)!=1:raise ValueError(f'Conflicting units: {m}')
            label=latest['metric_name']
            if label in headers:label += ' '+m
            headers.append(label)
            dictionary.append([group,name,m,label,latest['unit'],frequency,
                min((r['date'] for r in valid),default=''),max((r['date'] for r in valid),default=''),
                len(valid),sum(r['value'] is None for r in s),latest.get('status',''),
                latest.get('source_name',''),latest.get('source_field',''),
                ' | '.join(sorted({url.strip() for r in s for url in r['source_url'].split(';') if url.strip()})),
                'Calculated / estimated' if m in MODEL_METRICS else 'Official source',
                FUNCTION_URL if m in MODEL_METRICS else ''])
        ws=wb.create_sheet(name);ws.sheet_properties.tabColor=color
        ws.append([group+' / '+name.replace('_',' ')])
        ws.append(['Frequency',frequency,'Start',start,'As of',as_of])
        if name=='Mortgage_Monthly':_formula_block(ws)
        ws.append(['Units']+[series[m][0]['unit'] for m in metrics])
        ws.append(['Period']+headers+['Data status'])
        header_row=ws.max_row
        by_key={(r['metric_id'],r['period']):r for r in part}
        periods=sorted({r['period'] for r in part})
        if frequency=='M':periods=_months(start,max(periods))
        elif frequency in ('A','Y'):periods=[str(y) for y in range(int(start[:4]),int(max(periods))+1)]
        elif frequency=='Q':
            periods=[f'{y}-Q{q}' for y in range(int(start[:4]),int(max(periods)[:4])+1) for q in range(1,5) if f'{y}-Q{q}'<=max(periods)]
        for period in periods:
            if frequency=='M':
                y,m=map(int,period.split('-'));date=dt.datetime(y,m,calendar.monthrange(y,m)[1])
            elif frequency in ('D','E'):date=dt.datetime.fromisoformat(period)
            elif frequency in ('A','Y'):date=int(period)
            else:date=period
            values=[];records=[]
            for metric in metrics:
                r=by_key.get((metric,period));values.append(r['value'] if r else None)
                if r:records.append(r)
            ws.append([date]+values+[_data_status(records)])
        _style_table(ws,header_row,color)
        for col,metric in enumerate(metrics,2):
            unit=series[metric][0]['unit']
            fmt='0.0%' if unit=='fraction' else '0.00000' if '% p.a.' in unit else '#,##0.00' if 'million' in unit else '#,##0.0' if unit=='1999=100' else '#,##0.00'
            for cells in ws.iter_rows(min_row=header_row+1,min_col=col,max_col=col):cells[0].number_format=fmt
            if metric in MODEL_METRICS:
                ws.cell(header_row,col).fill=PatternFill('solid',fgColor='365B83' if metric in COUNT_COLUMNS+AMOUNT_COLUMNS else '65727E')
                letter=get_column_letter(col)
                ws.conditional_formatting.add(f'{letter}{header_row+1}:{letter}{ws.max_row}',
                    CellIsRule(operator='lessThan',formula=['0'],font=Font(color='9C0006'),fill=PatternFill('solid',fgColor='FCE4D6')))
        if name=='Mortgage_Monthly' and any(m in MODEL_METRICS for m in metrics):
            first=next(i for i,m in enumerate(metrics,2) if m in MODEL_METRICS)
            ws['G7']='Calculated data';ws['G7'].hyperlink=f"#'{name}'!{get_column_letter(first)}{header_row}"
            ws['G7'].style='Hyperlink'
            ws['G8']='Official data';ws['G8'].hyperlink=f"#'{name}'!B{header_row}";ws['G8'].style='Hyperlink'
        for cells in ws.iter_rows(min_row=header_row+1,min_col=1,max_col=1):
            cells[0].number_format='yyyy-mm' if frequency=='M' else 'yyyy-mm-dd' if frequency in ('D','E') else '0'
        ws.column_dimensions[get_column_letter(ws.max_column)].width=32
        overview.append([group,name,frequency,min(r['date'] for r in part),max(r['date'] for r in part),len(metrics)])
        overview.cell(overview.max_row,2).hyperlink=f"#'{name}'!A1"
    ws=wb.create_sheet('Data_Dictionary')
    ws.append(['Group','Sheet','Series ID','Indicator label','Unit','Frequency','First value','Latest value',
               'Values','Source blanks','Latest status','Source','Source field','Source URLs','Data type','Function'])
    for row in dictionary:ws.append(row)
    _style_table(ws,1,'555555')
    for cells in ws.iter_rows(min_row=2,min_col=16,max_col=16):
        if cells[0].value:cells[0].hyperlink=cells[0].value;cells[0].style='Hyperlink'
    for col in ['C','D','M']:ws.column_dimensions[col].width=45
    ws.column_dimensions['N'].width=80
    ws.column_dimensions['P'].width=45
    _style_table(overview,contents_header,'243D4D');overview.column_dimensions['B'].width=42
    for i in range(1,contents_header-1):
        overview.cell(i,1).font=Font(bold=True)
        overview.row_dimensions[i].height=40 if overview.cell(i,1).value in ('Timing assumption','Bank count','Amounts') else 30
        if i>=3:
            overview.merge_cells(start_row=i,start_column=2,end_row=i,end_column=6)
            overview.cell(i,2).alignment=Alignment(wrap_text=True,vertical='center')
    tmp=path.with_name(path.stem+'.tmp.xlsx');wb.save(tmp);tmp.replace(path)
    return dictionary
