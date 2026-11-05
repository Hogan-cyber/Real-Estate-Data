#!/usr/bin/env python3
"""Download official tables and export an Excel dataset. No AI services required."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
from pathlib import Path
import sys
import shutil
import sqlite3

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from hk_property_data.simple import rvd,landreg,hkma,rates,export
from hk_property_data.residential_schema import COLUMNS, SCHEMA_VERSION, populate_database


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('outputs/residential_2002'))
    parser.add_argument('--start',default='2002-01',help='First month, YYYY-MM')
    parser.add_argument('--as-of',default=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat())
    parser.add_argument('--from-saved',action='store_true',help='Re-export saved source parts without fetching; original check timestamps remain unchanged')
    args=parser.parse_args(argv)
    dt.date.fromisoformat(args.start+'-01');dt.date.fromisoformat(args.as_of)
    out=args.output.resolve();parts=out/'parts';parts.mkdir(parents=True,exist_ok=True)
    rows=[];errors=[];source_runs=[]
    for name,module in [('rvd',rvd),('landreg',landreg),('hkma',hkma),('rates',rates)]:
        path=parts/(name+'.json')
        print(f'{name}: '+('reading saved observations' if args.from_saved else 'fetching official sources'),flush=True)
        try:
            data=json.loads(path.read_text()) if args.from_saved else module.collect(out,args.as_of,args.start)
            if not data:raise ValueError('No observations returned')
            if not args.from_saved:
                tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.replace(path)
            problems=sorted({r['refresh_warning'] for r in data if r.get('refresh_warning')})
            errors.extend(name+': '+p for p in problems)
            rows.extend(data)
            source_runs.append(dict(source=name,observations=len(data),status='Warnings' if problems else 'Collected'))
            print(f'{name}: {len(data):,} observations',flush=True)
        except Exception as exc:
            errors.append(name+': '+str(exc));source_runs.append(dict(source=name,status='Failed',error=str(exc)))
            print(name+': FAILED: '+str(exc),file=sys.stderr,flush=True)
    for r in rows:
        if r.get('frequency')=='Q' and '-Q' not in r['period']:
            r['source_period']=r['period'];year,month=map(int,r['period'].split('-'))
            r['period']=f'{year}-Q{(month-1)//3+1}'
    rows=[r for r in rows if args.start<=r['date'][:7] and r['date']<=args.as_of]
    rows.sort(key=lambda r:(r['metric_id'],r['date']))
    # A failed source is reported explicitly. Never present a previous part as a fresh download.
    if not rows:raise RuntimeError('All sources failed: '+'; '.join(errors))
    workbook=out/'HK_Residential_Data.xlsx'
    dictionary=export.build_excel(rows,workbook,args.start,args.as_of,errors)
    temporary=out/'observations.tmp.csv'
    with temporary.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=COLUMNS,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    temporary.replace(out/'observations.csv')
    rate_warnings=out/'raw/rates/warnings.json'
    summary=dict(schema_version=SCHEMA_VERSION,start=args.start,as_of=args.as_of,mode='saved export' if args.from_saved else 'live collection',
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),observations=len(rows),series=len(dictionary),
        workbook=workbook.name,source_runs=source_runs,errors=errors,
        rate_release_notes=json.loads(rate_warnings.read_text()) if rate_warnings.exists() else [])
    # All formats share the same observations and metadata. Readers never invoke this publisher.
    compressed=out/'observations.tmp.csv.gz'
    with (out/'observations.csv').open('rb') as source, gzip.open(compressed,'wb') as target:
        shutil.copyfileobj(source,target)
    compressed.replace(out/'observations.csv.gz')
    database=out/'observations.tmp.sqlite'
    database.unlink(missing_ok=True)
    connection=sqlite3.connect(database)
    try:
        populate_database(connection,rows)
        with connection:
            connection.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            connection.execute('INSERT INTO metadata VALUES (?,?)',('collection_status',json.dumps(summary)))
    finally:
        connection.close()
    database.replace(out/'observations.sqlite')
    (out/'collection_status.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    print(f'Excel: {workbook}',flush=True)
    return 1 if errors else 0


if __name__=='__main__':
    raise SystemExit(main())
