"""Business-grouped Excel, with official observations and labelled trial estimates."""
from __future__ import annotations

import calendar
import datetime as dt
import math
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter
from .mortgage_estimates import COUNT_COLUMNS, AMOUNT_COLUMNS

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


def build_excel(rows,path,start,as_of,errors):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    validate(rows,start,as_of)
    grouped=defaultdict(list)
    for row in rows:grouped[sheet_for(row)].append(row)
    wb=Workbook();overview=wb.active;overview.title='Contents'
    overview.append(['Hong Kong residential dataset'])
    overview.append(['Start',start,'Checked as of',as_of])
    overview.append(['Method','Official observations plus labelled monthly mortgage trial estimates; no interpolation or zero filling.'])
    overview.append(['Blank cells','Not published / outside source coverage / missing at source; never zero-filled.'])
    overview.append(['Rates','Daily HIBOR, HSBC effective rates and source-published monthly averages stay separate.'])
    overview.append(['Scope','Mortgage registrations cover all property types; HKMA survey covers its defined residential loans.'])
    overview.append(['Quarterly risk','Negative_Equity_Quarterly describes existing bank loan risk; not monthly new lending or a money-lender input.'])
    overview.append(['Collection warnings','; '.join(errors) if errors else 'None'])
    overview.append([])
    overview.append(['Group','Sheet','Frequency','Earliest observation','Latest observation','Series'])
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
            first=[m for m in COUNT_COLUMNS+AMOUNT_COLUMNS if m in series]
            metrics=first+[m for m in metrics if m not in first]
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
                ' | '.join(sorted({url.strip() for r in s for url in r['source_url'].split(';') if url.strip()})),latest.get('note','')])
        ws=wb.create_sheet(name);ws.sheet_properties.tabColor=color
        ws.append([group+' / '+name.replace('_',' ')])
        ws.append(['Frequency',frequency,'Start',start,'As of',as_of])
        ws.append(['Units']+[series[m][0]['unit'] for m in metrics])
        ws.append(['Period']+headers+['Source flags'])
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
            flags=[];values=[]
            for metric in metrics:
                r=by_key.get((metric,period));values.append(r['value'] if r else None)
                if r and r.get('flags'):flags.append(r.get('source_field',r['metric_name'])+': '+str(r['flags']))
                elif r and ('partial' in r.get('status','').lower()):flags.append(r['metric_name']+': '+r['status'])
            ws.append([date]+values+['; '.join(flags)])
            # Each estimate stays in the original monthly sheet; provenance is
            # available on the value itself as well as in the data dictionary.
            for column,metric in enumerate(metrics,2):
                r=by_key.get((metric,period))
                if r and metric in MODEL_METRICS:
                    ws.cell(ws.max_row,column).comment=Comment(
                        r.get('status','')+'\n'+r.get('flags','')+'\n'+r.get('note','')
                        +'\nSources: '+r.get('source_url',''),'Dataset calculation')
        _style_table(ws,4,color)
        for col,metric in enumerate(metrics,2):
            unit=series[metric][0]['unit']
            fmt='0.0%' if unit=='fraction' else '0.00000' if '% p.a.' in unit else '#,##0.00' if 'million' in unit else '#,##0.0' if unit=='1999=100' else '#,##0.00'
            for cells in ws.iter_rows(min_row=5,min_col=col,max_col=col):cells[0].number_format=fmt
        for cells in ws.iter_rows(min_row=5,min_col=1,max_col=1):
            cells[0].number_format='yyyy-mm' if frequency=='M' else 'yyyy-mm-dd' if frequency in ('D','E') else '0'
        ws.column_dimensions[get_column_letter(ws.max_column)].width=65
        overview.append([group,name,frequency,min(r['date'] for r in part),max(r['date'] for r in part),len(metrics)])
        overview.cell(overview.max_row,2).hyperlink=f"#'{name}'!A1"
    ws=wb.create_sheet('Data_Dictionary')
    ws.append(['Group','Sheet','Series ID','Indicator label','Unit','Frequency','First value','Latest value',
               'Values','Source blanks','Latest status','Source','Source field','Source URLs','Definition / scope'])
    for row in dictionary:ws.append(row)
    _style_table(ws,1,'555555')
    for col in ['C','D','M']:ws.column_dimensions[col].width=45
    for col in ['N','O']:ws.column_dimensions[col].width=80
    _style_table(overview,10,'243D4D');overview.column_dimensions['B'].width=42
    for i in range(1,9):
        overview.cell(i,1).font=Font(bold=True)
        overview.row_dimensions[i].height=30
        if i>=3:
            overview.merge_cells(start_row=i,start_column=2,end_row=i,end_column=6)
            overview.cell(i,2).alignment=Alignment(wrap_text=True,vertical='center')
    tmp=path.with_name(path.stem+'.tmp.xlsx');wb.save(tmp);tmp.replace(path)
    return dictionary
