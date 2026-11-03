#!/usr/bin/env python3
"""Validate saved dataset; no external requests."""
import json, math, sqlite3
from contextlib import closing
from pathlib import Path
from .database import validate_database
from .export_excel import validate_excel

def validate(output='data'):
    root = Path(output)
    data=json.loads((root/'hk_housing_dataset.json').read_text(encoding='utf-8'));rows=data['observations']
    assert len(rows)==len({(r['metric_id'],r['period']) for r in rows})
    assert all(r['market']=='HK' and r['date']<=data['as_of'] for r in rows)
    assert all(r['value'] is None or isinstance(r['value'],(float,int)) and math.isfinite(r['value']) for r in rows)
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
    return {'validation':'passed','monthly_rows':len(rows),'pdf_cells':len(pdf),'sale_periods_checked':len(checked_periods),'sale_breakdown_unavailable_periods':sorted(incomplete_periods),'source_errors':data['errors'],'source_notes':data.get('warnings',[])}
