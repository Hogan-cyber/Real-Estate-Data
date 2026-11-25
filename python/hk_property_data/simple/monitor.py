"""One-way, verified copy of Monitor data. Never runs or writes its repository."""
from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor

from openpyxl import load_workbook
from ..pipeline import fetch
from ..monitor_schema import REPOSITORY, WORKBOOK, LAYOUTS, MODEL_NOTE

FILES = (WORKBOOK, 'HK_Mortgage_Dashboard.html', 'collection_report.json', 'source_evidence.json')


def _period(value, frequency):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.strftime('%Y-%m' if frequency == 'M' else '%Y-%m-%d')
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}' if frequency=='M' else r'\d{4}-\d{2}-\d{2}',value):
        raise ValueError(f'Invalid Monitor period: {value!r}')
    dt.date.fromisoformat(value+'-01' if frequency=='M' else value)
    return value


def read_verified_snapshot(raw, html):
    """Require exact worksheet headers, finite numbers and dashboard/workbook parity."""
    matches=re.findall(r'<script id="workbook-data" type="application/json">(.*?)</script>',html,re.S)
    if len(matches)!=1:raise ValueError('Monitor dashboard data block missing or duplicated')
    payload=json.loads(matches[0])
    if payload.get('schemaVersion')!=1:raise ValueError('Unsupported Monitor snapshot schema')
    if payload.get('revision')!=hashlib.sha256(raw).hexdigest():raise ValueError('Monitor workbook hash mismatch')
    if set(payload.get('series',{}))!=set(LAYOUTS):raise ValueError('Monitor series schema changed')
    series={}
    book=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
    try:
        for key,(sheet_name,date_header,freq,_,fields) in LAYOUTS.items():
            sheet=book[sheet_name]
            # The model sheet has presentation notes beside its three data columns.
            values=sheet.iter_rows(max_col=len(fields)+1,values_only=True)
            expected=(date_header,*(field[1] for field in fields))
            if tuple(next(values))!=expected:raise ValueError(f'Monitor headers changed: {sheet_name}')
            records={}
            for row in values:
                if all(cell is None for cell in row):continue
                period=_period(row[0],freq)
                if period in records:raise ValueError(f'Duplicate Monitor period: {sheet_name} {period}')
                cells=[None if value in (None,'') else value for value in row[1:]]
                if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v)) for v in cells):
                    raise ValueError(f'Invalid Monitor number: {sheet_name} {period}')
                records[period]=[period,*cells]
            series[key]=[records[p] for p in sorted(records)]
            if not series[key]:raise ValueError(f'Empty Monitor sheet: {sheet_name}')
            if series[key]!=payload['series'][key]:raise ValueError(f'Monitor workbook values do not match dashboard: {sheet_name}')
    finally:
        book.close()
    validate_model(series)
    return series


def validate_model(series):
    """Check saved results using the agreed formula; never replace the saved cells."""
    banks={row[0]:row for row in series['bank']}
    registrations={row[0]:row for row in series['registrations']}
    model={row[0]:row for row in series['nonbank']}
    for period,_,purchase in series['nonbank']:
        row=banks.get(period)
        expected=None
        if row and all(type(row[i]) in (int,float) and row[i]>=0 for i in (2,4,5,10)):
            if row[2]>0 and row[4]+row[5]<=row[2]:expected=(row[4]+row[5])/row[2]*row[10]
        if (purchase is None)!=(expected is None) or (purchase is not None and not math.isclose(purchase,expected,rel_tol=1e-10,abs_tol=1e-7)):
            raise ValueError(f'Monitor bank model mismatch: {period}')
    for period,residual,_ in series['nonbank']:
        prior=(dt.date.fromisoformat(period+'-01')-dt.timedelta(days=1)).strftime('%Y-%m')
        bank=model.get(prior,[None,None,None])[2]
        regs=registrations.get(period)
        expected=None
        if bank is not None and regs and all(type(regs[i]) in (int,float) and regs[i]>=0 for i in (1,2)):
            expected=regs[1]+regs[2]-bank
        if (residual is None)!=(expected is None) or (residual is not None and not math.isclose(residual,expected,rel_tol=1e-10,abs_tol=1e-7)):
            raise ValueError(f'Monitor residual model mismatch: {period}')


def observations(series, commit, report, *, checked_at):
    """Convert unchanged source cells to the residential long-table contract."""
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Monitor commit must be a full SHA')
    source_checked=report.get('checked_at','')
    if not source_checked:raise ValueError('Monitor source check timestamp missing')
    dt.datetime.fromisoformat(source_checked)
    source_url=f'https://github.com/{REPOSITORY}/blob/{commit}/{WORKBOOK}'
    sources={'registrations':'Centaline','bank':'Hong Kong Monetary Authority',
             'registry':'Land Registry','m3':'Hong Kong Monetary Authority','prime':'HSBC',
             'hibor':'HKMA / Hong Kong Association of Banks','nonbank':'Mortgage Monitor workbook model'}
    output=[]
    for key,records in series.items():
        sheet,_,freq,_,fields=LAYOUTS[key]
        for period,*values in records:
            date=period if freq!='M' else period+f'-{calendar.monthrange(*map(int,period.split("-")))[1]:02}'
            for value,(suffix,heading,name,unit) in zip(values,fields):
                model=key=='nonbank'
                flags=['COPIED_MONITOR_SNAPSHOT']
                if model:flags+=['MODEL_ESTIMATE','REGISTRATION_LAG_ASSUMED_1_MONTH']
                if value is None:flags+=['MISSING_INPUT' if model else 'SOURCE_BLANK']
                if model and value is not None and value<0:flags+=['NEGATIVE_RESIDUAL']
                note=MODEL_NOTE if model else 'Copied unchanged from the Mortgage Monitor workbook; original reference period and missing cells preserved.'
                if key=='registrations':note+=' Completed-property total is broader than private residential; categories can overlap.'
                if key=='registry':note+=' Registered legal documents across property types, not unique residential purchase loans.'
                output.append(dict(metric_id='monitor_'+suffix,metric_name=name,period=period,date=date,
                    frequency=freq,value=value,unit=unit,status='Missing' if value is None else 'Estimate' if model else 'Published',
                    flags=';'.join(flags),source_name=sources[key]+' (via Mortgage Monitor)',source_url=source_url,
                    source_table=sheet,source_field=heading,note=note,checked_at=checked_at,source_checked_at=source_checked))
    return output


def collect(output_dir, as_of, start='2002-01', *, commit=None, snapshot_dir=None):
    """Read one pinned revision; save evidence only in this project's output directory."""
    if snapshot_dir is not None and commit is None:raise ValueError('--monitor-snapshot requires --monitor-commit for provenance')
    if commit is None:
        commit=json.loads(fetch(f'https://api.github.com/repos/{REPOSITORY}/commits/main'))['sha']
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Monitor commit must be a full SHA')
    receipt=None
    if snapshot_dir is not None:
        receipt_path=Path(snapshot_dir)/'diagnostics.json'
        if not receipt_path.is_file():raise ValueError('Local Monitor replay requires diagnostics.json from a commit-pinned collection')
        receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt.get('commit')!=commit:raise ValueError('Local Monitor receipt commit does not match --monitor-commit')
    def read(name):
        content=(Path(snapshot_dir)/name).read_bytes() if snapshot_dir is not None else fetch(f'https://raw.githubusercontent.com/{REPOSITORY}/{commit}/{name}')
        if receipt is not None and receipt.get('hashes',{}).get(name)!=hashlib.sha256(content).hexdigest():
            raise ValueError(f'Local Monitor file digest mismatch: {name}')
        return content
    with ThreadPoolExecutor(max_workers=4) as pool:
        files=dict(zip(FILES,pool.map(read,FILES)))
    checked_at=dt.datetime.now(dt.timezone.utc).isoformat()
    series=read_verified_snapshot(files[WORKBOOK],files['HK_Mortgage_Dashboard.html'].decode('utf-8'))
    report=json.loads(files['collection_report.json'])
    if report.get('issues'):raise ValueError('Monitor reported collection issues: '+json.dumps(report['issues'],ensure_ascii=False))
    rows=observations(series,commit,report,checked_at=checked_at)
    rows=[r for r in rows if start<=r['date'][:7] and r['date']<=as_of]
    coverage={}
    for key,layout in LAYOUTS.items():
        periods=sorted({row['period'] for row in rows if row['source_table']==layout[0]})
        coverage[key]=dict(first=periods[0] if periods else None,last=periods[-1] if periods else None,rows=len(periods))
    raw=Path(output_dir)/'raw'/'monitor';raw.mkdir(parents=True,exist_ok=True)
    for name,content in files.items():(raw/name).write_bytes(content)
    diagnostics=dict(repository=REPOSITORY,commit=commit,checked_at=checked_at,
        source_checked_at=report['checked_at'],upstream_status=report.get('status'),
        hashes={name:hashlib.sha256(content).hexdigest() for name,content in files.items()},
        coverage=coverage,
        upstream_coverage={key:dict(first=records[0][0],last=records[-1][0],rows=len(records)) for key,records in series.items()},
        upstream_feedback=report.get('update_feedback',{}),issues=report.get('issues',[]),
        validation='Workbook hash, headers, all saved values and non-bank formula results verified against the same commit.')
    (raw/'diagnostics.json').write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding='utf-8')
    return rows
