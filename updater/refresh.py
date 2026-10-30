#!/usr/bin/env python3
"""Repeatable HK housing refresh. Public sources only; preserves last good source on error."""
from __future__ import annotations
import argparse, calendar, csv, datetime as dt, hashlib, io, json, math, re, shutil, subprocess, sys, tempfile, urllib.request
from database import build_database
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'collectors'))
import hk_landreg_collector, hk_hkma_collector, hk_commercial_collector
RVD = 'https://www.rvd.gov.hk/datagovhk/'
REPORT = 'https://www.rvd.gov.hk/doc/en/statistics/full.pdf'
TABLES = {'1.1': ('rent','平均租金','港元/平方米/月'), '1.2': ('price','平均售价','港元/平方米'),
          '1.3': ('rent','租金指数','1999=100'), '1.4': ('price','售价指数','1999=100'),
          '1.5': ('price','热门屋苑售价指数','1999=100'), '5.1': ('yield','市场回报率','%')}

METRIC_EN={
 '平均租金':'Average rent','平均售价':'Average price','租金指数':'Rental index','售价指数':'Price index','热门屋苑售价指数':'Popular development price index','市场回报率':'Market yield',
 'hk_residential_sales_count':'All residential sales','hk_residential_sales_value':'All residential sale value',
 'hk_residential_primary_sales_count':'Primary sales','hk_residential_primary_sales_value':'Primary sale value',
 'hk_residential_secondary_sales_count':'Secondary sales','hk_residential_secondary_sales_value':'Secondary sale value',
 'hk_mortgage_approved_amount':'New mortgage approvals','hk_mortgage_drawn_amount':'New mortgage drawdowns',
 'hk_mortgage_approved_count':'Approved mortgages','hk_mortgage_drawn_count':'Mortgage drawdown count','hk_mortgage_applications':'Mortgage applications',
 'hk_mortgage_delinquency':'Mortgage delinquency over 3 months','hk_mortgage_outstanding':'Outstanding residential mortgages','hk_new_mortgage_rate':'Average new mortgage lending rate'}
SOURCE_EN={'差饷物业估价署':'Rating and Valuation Department','香港土地注册处':'Land Registry','香港金融管理局':'Hong Kong Monetary Authority'}
REGION_EN={'港岛':'Hong Kong Island','九龙':'Kowloon','新界':'New Territories','市区':'Urban','全港':'All Hong Kong'}
UNIT_EN={'港元/平方米/月':'HKD / sq m / month','港元/平方米':'HKD / sq m','百万港元':'HKD million','宗':'loans','份':'agreements'}
def english_rows(rows):
    for r in rows:
        r['metric_name']=METRIC_EN.get(r['metric_id'],METRIC_EN.get(r['metric_name'],r['metric_name']))
        r['source_name']=SOURCE_EN.get(r['source_name'],r['source_name'])
        r['unit']=UNIT_EN.get(r['unit'],r['unit'])
        if r.get('class_name')=='全体':r['class_name']='All'
        if 'region' in r:r['region']=REGION_EN.get(r['region'],r['region'])
        if r.get('status')=='暂定':r['status']='Provisional'
        if r.get('status')=='已发布':r['status']='Published'
    return rows

def english_snapshot(snapshot):
    source=snapshot['queries']['observations']['source']
    source['metricDefinitions']=[{'label': 'YoY / MoM', 'definition': 'Change against the exact same month one year earlier / the previous month. Missing comparator months remain blank.'}, {'label': 'Price and rental indices', 'definition': 'RVD private residential indices, 1999=100. Sale-price statistics exclude primary residential sales.'}, {'label': 'Mortgage lending rate', 'definition': 'Explicit observation months reported in HKMA half-yearly reports. No interpolation or forward filling.'}]
    source['metricDefinitions'].append({'label': 'Average residential price per square foot', 'definition': 'RVD table 1.2 by saleable-area class A–E and district. HKD per square foot = official HKD per square metre × 0.09290304. Original values, units and flags are retained. Excludes primary residential sales. No averaging across districts or across months.'})
    source['metricDefinitions'].append({'label':'Commercial property','definition':'RVD office, retail and private flatted-factory CSVs. Office grades A–C reflect building quality. Commercial averages use internal floor area; no averaging across districts. Missing values are retained.'})
    source['caveats']=['P = provisional. X/Y/Z = fewer than 5/10/20 cases. Commercial floor area is internal floor area; residential classes use saleable area.', 'Averages are sensitive to transaction mix; statistical market yield is not property-specific net yield.', 'Sales are counted by registration month, which may lag the agreement date.']
    source['evidenceFlow']=[{'title': 'Refresh pipeline', 'detail': 'updater/refresh.py retrieves RVD CSV and the rolling monthly PDF, Land Registry JSON and HKMA API / half-yearly reports. Source-specific fallback, unique-key checks and revision logs are retained.'}]
    snapshot['queries']['pdf']['source']['caveats']=['Annual, quarterly, monthly, year-to-date and forecast observations are separate and must not be summed.']

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),encoding='utf-8'); tmp.replace(path)

def fetch(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'HKHousingObservatory/1.0'}),timeout=45) as r:
                return r.read(30_000_001)
        except Exception:
            if attempt==2: raise

def month_end(period):
    y,m=map(int,period.split('-')); return f'{period}-{calendar.monthrange(y,m)[1]:02d}'

def rvd(table, cache, as_of):
    url=RVD+table+'M.csv'; raw=fetch(url)
    if len(raw)>30_000_000: raise ValueError('RVD file too large')
    parsed=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    if len(parsed)<10 or parsed[1][0]!='Month': raise ValueError('RVD schema changed')
    headers=parsed[1]; values=[h for h in headers[1:] if not h.endswith(' - Remarks')]
    expected={'1.1':15,'1.2':15,'1.3':8,'1.4':8,'1.5':9,'5.1':5}[table]
    if len(values)!=expected: raise ValueError('RVD unexpected field count')
    category,label,unit=TABLES[table]; rows=[]
    for cells in parsed[2:]:
        if not cells or not re.fullmatch(r'\d{2}-\d{4}',cells[0]): continue
        mm,yy=cells[0].split('-'); period=f'{yy}-{mm}'; date=month_end(period)
        if period<'1999-01' or date>as_of: continue
        if len(cells)!=len(headers): raise ValueError('RVD row width changed')
        record=dict(zip(headers,cells))
        for field in values:
            raw_value=record[field].strip(); flags=record.get(field+' - Remarks','')
            if raw_value in ('','-','N.A.','N/A'): value=None
            else: value=float(raw_value.replace(',',''))
            cls='全体' if field in ('All Classes','Overall All') else 'A–C' if 'A, B & C' in field else 'D–E' if 'D & E' in field else next((c for c in 'ABCDE' if 'Class '+c in field),'全体')
            region='港岛' if 'Hong Kong' in field else '九龙' if 'Kowloon' in field else '新界' if 'New Territories' in field else '市区' if 'Urban' in field else '全港'
            metric='rvd_'+table.replace('.','_')+'_'+re.sub('[^a-z0-9]+','_',field.lower()).strip('_')
            rows.append(dict(market='HK',category=category,metric_id=metric,metric_name=label,period=period,date=date,value=value,unit=unit,
                frequency='M',class_name=cls,region=region,source_name='差饷物业估价署',source_url=url,source_table=table,source_field=field,
                flags=flags,status='暂定' if 'P' in flags else '已发布',small_sample='Z' in flags,fetch_mode='automatic_csv'))
    if not rows: raise ValueError('No RVD monthly observations')
    (cache/(table+'M.csv')).write_bytes(raw)
    return rows

def csvwrite(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    temp=path.with_suffix('.tmp')
    with temp.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    temp.replace(path)

def validate(rows,as_of):
    keys=[(r['metric_id'],r['period']) for r in rows]
    if len(keys)!=len(set(keys)): raise ValueError('Duplicate metric and period')
    for r in rows:
        if r['date']>as_of: raise ValueError('Future observation')
        if r['value'] is not None and (not isinstance(r['value'],(float,int)) or not math.isfinite(r['value'])): raise ValueError('Non numeric value')
    price=[r for r in rows if r['metric_id']=='rvd_1_4_all_classes']
    if len(price)<24: raise ValueError('Insufficient house price history')

def run(args):
    as_of=args.as_of or dt.date.today().isoformat(); now=dt.datetime.now(dt.timezone.utc).isoformat()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True);cache=out/'cache';cache.mkdir(exist_ok=True)
    prior_path=out/'hk_housing_dataset.json'; previous=json.loads(prior_path.read_text()) if prior_path.exists() else {}
    # A fresh cloud checkout seeds its history from the current hosted snapshot.
    if not previous and args.app:
        snapshot_file=Path(args.app)/'src/data.json'
        if snapshot_file.exists():
            seed=json.loads(snapshot_file.read_text()); q=seed.get('queries',{})
            if 'observations' in q and any(r.get('source_id') for r in q['observations']['rows']):
                previous=dict(observations=q['observations']['rows'],pdf_observations=q.get('pdf',{}).get('rows',[]),source_status=q.get('status',{}).get('rows',[]),report=seed.get('refresh',{}).get('report',{}),revisions=seed.get('refresh',{}).get('revisions',[]))
    prior=previous.get('observations',[]); old_status={s['source_id']:s for s in previous.get('source_status',[])}
    # Every hosted run starts without ignored caches, including later runs that
    # already have a committed dataset. Seed each HKMA feed independently so a
    # partial failure is visible and does not discard a successful sibling feed.
    for kind in ('survey','mortgage_rate'):
        cached=cache/'hkma'/('hkma_'+kind+'.json')
        old=[r for r in prior if r.get('source_id')=='hkma' and (r['metric_id']=='hk_new_mortgage_rate')==(kind=='mortgage_rate')]
        if old and not cached.exists():
            save(cached,{'last_success':old_status.get('hkma',{}).get('last_success'),'rows':old})
    rows=[];statuses=[];errors=[]
    sources=[('rvd_'+t,lambda t=t:rvd(t,cache,as_of)) for t in TABLES]
    sources += [('rvd_'+t,lambda t=t:hk_commercial_collector.collect(t,cache,as_of,fetch)) for t in hk_commercial_collector.TABLES]
    sources += [('landreg',lambda:hk_landreg_collector.collect(cache/'landreg',as_of)),('hkma',lambda:hk_hkma_collector.collect(cache/'hkma',as_of))]
    for source_id,collect in sources:
        try:
            collected=collect()
            if not collected: raise ValueError('Empty source')
            keys=[(r['metric_id'],r['period']) for r in collected]
            if len(keys)!=len(set(keys)): raise ValueError('Duplicate rows from source')
            # Retain history no longer included in rolling official downloads.
            merged={(r['metric_id'],r['period']):r for r in prior if r.get('source_id')==source_id}
            for r in collected:
                r=dict(r,source_id=source_id); merged[(r['metric_id'],r['period'])]=r
            part=list(merged.values()); stale=any(r.get('status')=='stale_cache' for r in collected)
            state='Retained: refresh failed' if stale else 'Verified'
            if stale: errors.append(source_id+': collector used stale cache')
            success=old_status.get(source_id,{}).get('last_success') if stale else now
        except Exception as exc:
            part=[r for r in prior if r.get('source_id')==source_id]
            errors.append(source_id+': '+str(exc));state='Retained: refresh failed';success=old_status.get(source_id,{}).get('last_success')
            if not part: raise RuntimeError(f'Initial load failed: {source_id}: {exc}') from exc
        old_values={(r['metric_id'],r['period']):r['value'] for r in prior if r.get('source_id')==source_id}
        added=sum((r['metric_id'],r['period']) not in old_values for r in part)
        changed=sum((r['metric_id'],r['period']) in old_values and old_values[(r['metric_id'],r['period'])]!=r['value'] for r in part)
        change_summary=f'{added} new rows; {changed} revised values' if added or changed else 'No new or revised values'
        rows.extend(part)
        statuses.append(dict(source_id=source_id,source_name=SOURCE_EN.get(part[0]['source_name'],part[0]['source_name']),status=state,checked_at=now,last_success=success,
                             latest_period=max(r['period'] for r in part),rows=len(part),source_url=part[0]['source_url'],change_summary=change_summary))
    english_rows(rows)
    validate(rows,as_of)
    # Every report is archived by content digest; never overwrite historical vintages.
    pdf_rows=[];report_path=None
    try:
        report=Path(args.pdf).read_bytes() if args.pdf else fetch(REPORT)
        if not report.startswith(b'%PDF') or len(report)>30_000_000: raise ValueError('Invalid report PDF')
        digest=hashlib.sha256(report).hexdigest(); folder=out/'source-tables'/digest[:12];folder.mkdir(parents=True,exist_ok=True)
        report_path=folder/'report.pdf';report_path.write_bytes(report)
        subprocess.run([sys.executable,str(ROOT/'collectors/hk_pdf_extract.py'),'--source',str(report_path),'--output',str(folder),'--rvd-dir',str(cache)],check=True,capture_output=True,text=True)
        pdf_rows=json.loads((folder/'observations.json').read_text())
        pdf_validation=json.loads((folder/'manifest.json').read_text())
        for check in pdf_validation.get('comparisons',[]):
            if 'csv_source' in check: check['csv_source']=RVD+check['table_id']+'M.csv'
        review_checks=[check for check in pdf_validation.get('comparisons',[]) if check.get('status')=='review']
        if review_checks: errors.append('pdf: CSV comparison needs review for tables '+', '.join(c['table_id'] for c in review_checks))
        for row in pdf_rows: row['source_pdf']=REPORT
        report_info=dict(sha256=digest,path=str(report_path.relative_to(out)),source_url=REPORT,status='Extracted and checked',checked_at=now,
                         edition=pdf_validation.get('edition'),latest_period=pdf_validation.get('latest_month'),comparisons=pdf_validation.get('comparisons',[]))
    except Exception as exc:
        errors.append('pdf: '+str(exc));pdf_rows=previous.get('pdf_observations',[]);report_info=previous.get('report',{})|{'status':'Retained: PDF refresh failed','checked_at':now}
        if not pdf_rows: raise RuntimeError('Initial PDF extraction failed') from exc
    pdf_failed=report_info.get('status','').startswith('Retained')
    pdf_review=any(c.get('status')=='review' for c in report_info.get('comparisons',[]))
    statuses.append(dict(source_id='rvd_pdf',source_name='Rating and Valuation Department — monthly PDF',source_url=REPORT,status='Retained: refresh failed' if pdf_failed else 'Review PDF / CSV differences' if pdf_review else 'Verified',checked_at=now,last_success=old_status.get('rvd_pdf',{}).get('last_success') if pdf_failed else now,latest_period=max((r['period'] for r in pdf_rows if r['frequency']=='monthly'),default=None),rows=len(pdf_rows),change_summary='Same PDF content' if report_info.get('sha256')==previous.get('report',{}).get('sha256') else 'New PDF content'))
    rows.sort(key=lambda r:(r['metric_id'],r['period']))
    prior_values={(r['metric_id'],r['period']):r['value'] for r in prior};revisions=[]
    for r in rows:
        key=(r['metric_id'],r['period'])
        if key in prior_values and prior_values[key]!=r['value']:
            revisions.append(dict(metric_id=key[0],period=key[1],old=prior_values[key],new=r['value'],detected_at=now))
    revision_history=previous.get('revisions',[])+revisions
    result=dict(schema_version=1,market='HK',as_of=as_of,checked_at=now,observations=rows,pdf_observations=pdf_rows,
                source_status=statuses,report=report_info,revisions=revision_history,errors=errors)
    save(prior_path,result);csvwrite(out/'hk_observations.csv',rows);csvwrite(out/'hk_pdf_observations.csv',pdf_rows)
    save(out/'refresh_status.json',{k:v for k,v in result.items() if k not in ('observations','pdf_observations')})
    build_database(result, out/'hk_housing.sqlite')
    if args.app:
        app=Path(args.app);snapshot_path=app/'src/data.json';snapshot=json.loads(snapshot_path.read_text())
        # These public source vintages travel with the cloud source repository.
        archive=app/'updater'/'archives';archive.mkdir(parents=True,exist_ok=True)
        raw_paths=([report_path] if report_path else [])+list(cache.glob('*M.csv'))+list((cache/'hkma').glob('*.pdf'))+list((cache/'landreg').glob('*.json'))
        for path in raw_paths:
            if path and path.exists():
                raw=path.read_bytes(); name=hashlib.sha256(raw).hexdigest()[:16]+'-'+path.name
                if not (archive/name).exists(): (archive/name).write_bytes(raw)
        save(archive/'latest_manifest.json',{'as_of':as_of,'report_sha256':report_info.get('sha256'),'source_status':statuses,'revisions':revisions})
        source=dict(label='Official Hong Kong residential and commercial statistics',executedAt=now,url='https://www.rvd.gov.hk/en/publications/property_market_statistics.html',
          coverage={'startDate':min(r['date'] for r in rows),'endDate':max(r['date'] for r in rows)},
          metricDefinitions=[{'label':'同比 / 环比','definition':'同一系列对精确12个月前 / 1个月前的数值计算百分比变化；没有同期就留空。'},
          {'label':'房价和租金指数','definition':'差饷物业估价署私人住宅指数，1999=100；售价统计排除一手住宅销售。'},
          {'label':'新批按揭平均利率','definition':'HKMA半年度报告明确披露的观察月份，非月度连续序列，不前向填补。'}],
          caveats=['P=暂定；Z=少于20宗，结果容易波动。','平均售价/租金受成交组合影响；市场回报率不是具体物业的净租金回报。','成交按送交登记月份；与实际签约月份有时间差。'],
          evidenceFlow=[{'title':'更新程序','detail':'housing-data/refresh.py：RVD官方CSV与滚动full.pdf，土地注册处JSON、HKMA API及半年度PDF。逐源保留旧值、内容哈希归档、唯一键验证及修订日志。'}])
        snapshot.update(title='Hong Kong Property Monitor',surface='dashboard',generatedAt=now,status='reviewed',buildStatus='complete',asOf=as_of,markets={'HK':'Hong Kong'},
          filters=[{'id':'date','field':'date','label':'Reference period','mode':'through','defaultValue':f"2020-01-01..{max(r['date'] for r in rows)}",'queryIds':['observations']}],
          queries={'observations':{'rows':rows,'source':source},'pdf':{'rows':pdf_rows,'source':dict(label='RVD residential report tables',url=REPORT,executedAt=now,caveats=['年度、季度、月度、年累计、全年预测独立保留；不能直接相加。'])},'status':{'rows':statuses,'source':dict(label='Source refresh log',executedAt=now)}},
          refresh={'cadence':'Monthly, day 1 at 10:00','timezone':'Asia/Hong_Kong','instruction':'MONTHLY_REFRESH.md','errors':errors,'report':report_info,'revisions':revision_history})
        english_snapshot(snapshot)
        save(snapshot_path,snapshot)
    print(json.dumps(dict(rows=len(rows),pdf_cells=len(pdf_rows),revisions=len(revisions),errors=errors,latest=max(r['period'] for r in rows)),ensure_ascii=False))
    return 2 if errors else 0

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT));parser.add_argument('--app');parser.add_argument('--as-of');parser.add_argument('--pdf',help='Optional initial supplied PDF; future runs download latest official report')
    sys.exit(run(parser.parse_args()))
