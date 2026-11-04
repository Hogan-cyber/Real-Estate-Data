#!/usr/bin/env python3
"""Validate saved dataset; no external requests."""
import csv, json, math, sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse
from .database import validate_database
from .export_excel import validate_excel

def validate_official_sources(rows):
    for row in rows:
        url = row.get('source_url') or row.get('source_pdf')
        parsed = urlparse(url or '')
        if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.gov.hk'):
            raise ValueError('Non-government source excluded: '+str(url))


def validate_mortgage_reconciliations(rows):
    values = {(r['metric_id'],r['period']):r['value'] for r in rows}
    periods = {r['period'] for r in rows if r['metric_id'].startswith('hk_mortgage_approved_purchase_')}
    for period in periods:
        for measure, tolerance in [('count',0),('amount',2)]:
            if ('hk_mortgage_approved_purchase_'+measure,period) not in values:
                continue
            ids = ['hk_mortgage_approved_'+part+measure for part in ('','primary_','secondary_','refinancing_','purchase_')]
            numbers = [values.get((metric,period)) for metric in ids]
            if any(n is None for n in numbers):
                raise ValueError('Derived purchase approvals lack complete inputs: '+period)
            total,primary,secondary,refinancing,purchase = numbers
            if purchase != primary+secondary or abs(total-primary-secondary-refinancing)>tolerance:
                raise ValueError('Mortgage approvals do not reconcile: '+period)

def validate_csv(path, rows):
    """Check the full CSV against its JSON source, including source links."""
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        actual=list(csv.DictReader(stream))
    fields=list(dict.fromkeys(key for row in rows for key in row))
    expected=[{key:'' if row.get(key) is None else str(row[key]) for key in fields} for row in rows]
    if actual!=expected:
        raise ValueError(f'CSV does not match dataset: {Path(path).name}')


def validate_dashboard(snapshot, data):
    """Refuse a dashboard with older/different values, provenance or coverage."""
    for query,field in [('observations','observations'),('rates','rate_observations'),('pdf','pdf_observations')]:
        if snapshot.get('queries',{}).get(query,{}).get('rows')!=data.get(field,[]):
            raise ValueError(f'Dashboard {query} do not match dataset')
    if snapshot.get('generatedAt')!=data.get('checked_at') or snapshot.get('asOf')!=data.get('as_of'):
        raise ValueError('Dashboard refresh timestamp does not match dataset')
    dates=[r['date'] for r in data['observations']+data.get('rate_observations',[])]
    period=next((f for f in snapshot.get('filters',[]) if f.get('id')=='date'),{})
    if (not {'observations','rates'}.issubset(period.get('queryIds',[]))
            or dates and period.get('defaultValue','').split('..')[-1]!=max(dates)):
        raise ValueError('Reference period does not include the latest dataset date')


def validate(output='data', *, app=None):
    root = Path(output)
    data=json.loads((root/'hk_housing_dataset.json').read_text(encoding='utf-8'));rows=data['observations']
    assert len(rows)==len({(r['metric_id'],r['period']) for r in rows})
    assert all(r['market']=='HK' and r['date']<=data['as_of'] for r in rows)
    assert all(r['value'] is None or isinstance(r['value'],(float,int)) and math.isfinite(r['value']) for r in rows)
    rates=data.get('rate_observations',[])
    validate_official_sources(rows+rates+data['pdf_observations'])
    validate_mortgage_reconciliations(rows)
    assert len(rates)==len({(r['metric_id'],r['date']) for r in rates})
    assert all(r['date']<=data['as_of'] and r['frequency'] in ('D','E') and r['unit']=='% p.a.'
               and isinstance(r['value'],(float,int)) and not isinstance(r['value'],bool)
               and math.isfinite(r['value']) and 0<=r['value']<=100 for r in rates)
    index={(r['metric_id'],r['period']):r['value'] for r in rows}
    periods={r['period'] for r in rows if r['metric_id']=='hk_residential_sales_count'}
    checked_periods=[]; incomplete_periods=[]
    for p in periods:
        complete=True
        for measure,tolerance in [('count',0),('value',1)]:
            values=[index.get((f'hk_residential_{kind}sales_{measure}',p)) for kind in ('','primary_','secondary_')]
            if any(value is None for value in values):
                complete=False
                continue  # A newer official total does not fabricate its unpublished components.
            assert abs(values[0]-values[1]-values[2])<=tolerance
        (checked_periods if complete else incomplete_periods).append(p)
    commercial=[r for r in rows if r.get('property_type') in ('Office','Retail','Industrial')]
    assert commercial, 'Commercial sources missing'
    assert {r['source_table'] for r in commercial}=={'2.1','2.2','2.3','2.4','3.1','3.2','4.1','4.2','5.2'}
    assert all(r['area_basis']=='internal floor area' for r in commercial)
    assert all(r['unit']=='1999=100' for r in commercial if r['measure'].endswith('_index'))
    pdf=data['pdf_observations'];assert len({r['table_id'] for r in pdf})==10
    assert all(r['frequency']=='annual' for r in pdf if r.get('observation_kind')=='forecast')
    assert not any('/Users/' in json.dumps(r) for r in pdf)
    assert all(r.get('observation_frequency')=='explicit_months_only' for r in rows if r['metric_id']=='hk_new_mortgage_rate')
    with closing(sqlite3.connect((root/'hk_housing.sqlite').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        validate_database(db, data)
    validate_excel(root/'hk_property_data.xlsx', data)
    validate_csv(root/'hk_observations.csv',rows)
    validate_csv(root/'hk_rate_observations.csv',rates)
    if app is not None:
        validate_dashboard(json.loads((Path(app)/'src/data.json').read_text(encoding='utf-8')),data)
    return {'validation':'passed','monthly_rows':len(rows),'rate_rows':len(rates),'pdf_cells':len(pdf),'dashboard_sync':'passed' if app is not None else 'not requested','sale_periods_checked':len(checked_periods),'sale_breakdown_unavailable_periods':sorted(incomplete_periods),'source_errors':data['errors'],'source_notes':data.get('warnings',[])}
