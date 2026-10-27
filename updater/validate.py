#!/usr/bin/env python3
"""Validate saved dataset; no external requests."""
import json, math, sqlite3, sys
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
data=json.loads((root/'hk_housing_dataset.json').read_text());rows=data['observations']
assert len(rows)==len({(r['metric_id'],r['period']) for r in rows})
assert all(r['market']=='HK' and r['date']<=data['as_of'] for r in rows)
assert all(r['value'] is None or isinstance(r['value'],(float,int)) and math.isfinite(r['value']) for r in rows)
index={(r['metric_id'],r['period']):r['value'] for r in rows}
periods={r['period'] for r in rows if r['metric_id']=='hk_residential_sales_count'}
for p in periods:
    assert index['hk_residential_sales_count',p]==index['hk_residential_primary_sales_count',p]+index['hk_residential_secondary_sales_count',p]
    assert abs(index['hk_residential_sales_value',p]-index['hk_residential_primary_sales_value',p]-index['hk_residential_secondary_sales_value',p])<=1
commercial=[r for r in rows if r.get('property_type') in ('Office','Retail','Industrial')]
assert commercial, 'Commercial sources missing'
assert {r['source_table'] for r in commercial}=={'2.1','2.2','2.3','2.4','3.1','3.2','4.1','4.2','5.2'}
assert all(r['area_basis']=='internal floor area' for r in commercial)
assert all(r['unit']=='1999=100' for r in commercial if r['measure'].endswith('_index'))
pdf=data['pdf_observations'];assert len({r['table_id'] for r in pdf})==10
assert all(r['frequency']=='annual' for r in pdf if r.get('observation_kind')=='forecast')
assert not any('/Users/' in json.dumps(r) for r in pdf)
assert all(r.get('observation_frequency')=='explicit_months_only' for r in rows if r['metric_id']=='hk_new_mortgage_rate')
with sqlite3.connect(root/'hk_housing.sqlite') as db:
    assert db.execute('SELECT COUNT(*) FROM observations').fetchone()[0]==len(rows)
print(json.dumps({'validation':'passed','monthly_rows':len(rows),'pdf_cells':len(pdf),'sale_periods_checked':len(periods),'source_errors':data['errors']},ensure_ascii=False))
