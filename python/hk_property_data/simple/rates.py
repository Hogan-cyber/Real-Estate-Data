"""Read official rate workbooks directly; keep fixing, effective and monthly data apart."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor

import xlrd
from bs4 import BeautifulSoup

from ..pipeline import fetch
from ..collectors import hk_latest_rates as legacy
from ..collectors import hk_macro_collector as macro

XLS_ROOT = 'https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/'
HSBC_URL = 'https://www.hsbc.com.hk/investments/market-information/hk/lending-rate/'
HKAB_API = 'https://www.hkab.org.hk/api/hibor'
TENORS = [('overnight','Overnight'),('1w','1 week'),('1m','1 month'),('3m','3 months'),
          ('6m','6 months'),('9m','9 months'),('12m','12 months')]


def daily_rows(cells, as_of, start='2002-01'):
    output = []
    for row in cells:
        if not isinstance(row[0], (dt.date,dt.datetime)):
            continue
        date = row[0].strftime('%Y-%m-%d')
        if date[:7] < start or date > as_of:
            continue
        for col,(tenor,label) in enumerate(TENORS,3):
            raw = row[col]
            value = None if str(raw).strip().upper() in ('','N.A.','N/A','-','NAN') else float(raw)
            if value is not None and not 0 <= value <= 100:
                raise ValueError('Invalid HIBOR fixing')
            output.append(dict(metric_id=f'hk_hibor_{tenor}_daily', metric_name=f'HIBOR {label}',
                period=date,date=date,frequency='D',value=value,unit='% p.a.',source_id='hk_rates_hibor',
                source_name='Hong Kong Monetary Authority',source_url=XLS_ROOT+'T060303.xls',
                source_table='6.3.3 (HIBOR Fixing)',source_field=label,status='Missing' if value is None else 'Published',
                flags='',note='HKAB fixing at 11:15; separate from discontinued closing quotes. '
                + ('9-month fixing discontinued from 1 April 2014.' if tenor=='9m' else '')))
    if not output:
        raise ValueError('No daily fixing observations')
    return output


def hkab_url(day):
    return f'{HKAB_API}?year={day.year}&month={day.month}&day={day.day}'


def hkab_daily_rows(data, day, checked_at):
    """Read HKAB's dated 11:15 fixings; never relabel another day's response."""
    if not isinstance(data,dict):raise ValueError('Invalid HKAB response')
    active=[(tenor,label.title()) for tenor,label in TENORS if tenor!='9m']
    if data.get('isHoliday') is True:
        if any(data.get(label) is not None for _,label in active):
            raise ValueError('HKAB holiday response contains rates')
        return []
    try:
        reference=dt.datetime.strptime(str(data.get('date')),'%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('HKAB reference date missing or invalid') from exc
    if reference!=day:raise ValueError(f'HKAB reference date {reference} does not match {day}')
    if day.weekday()>=5:raise ValueError('Unexpected weekend HKAB fixing')
    if str(data.get('time','')).replace(' ','').lower()!='11:15am':
        raise ValueError('HKAB fixing time is not 11:15am')
    rows=[]
    for tenor,label in active:
        value=data.get(label)
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not 0<=value<=100:
            raise ValueError(f'Invalid or missing HKAB {label} fixing for {day}')
        rows.append(dict(metric_id=f'hk_hibor_{tenor}_daily',metric_name=f'HIBOR {dict(TENORS)[tenor]}',
                         period=day.isoformat(),date=day.isoformat(),frequency='D',value=float(value),unit='% p.a.',
                         source_id='hk_rates_hibor',source_name='Hong Kong Association of Banks',
                         source_url=hkab_url(day),source_table='HKAB HKD Interest Settlement Rates at 11:15',
                         source_field=label,status='Published',
                         flags='OFFICIAL_FALLBACK' if data.get('ds_is_fb','N')!='N' else '',
                         note='Official HKAB 11:15 fixing for this business day; no weekend/holiday filling.',
                         checked_at=checked_at,source_checked_at=checked_at))
    return rows


def hsbc_rows(html, as_of, start='2002-01'):
    soup = BeautifulSoup(html,'html.parser')
    text = soup.get_text(' ',strip=True)
    current = re.search(r'Current Hong Kong Dollar Best Lending Rate:\s*(\d+(?:\.\d+)?)%',text)
    if not current:
        raise ValueError('HSBC current rate heading missing')
    output = {}
    for tr in soup.select('table tr'):
        cells = [x.get_text(' ',strip=True) for x in tr.select('td')]
        if len(cells)!=2 or not re.fullmatch(r'\d{1,2} [A-Za-z]{3} \d{4}',cells[0]):
            continue
        date=dt.datetime.strptime(cells[0],'%d %b %Y').date().isoformat()
        value=float(cells[1].strip().rstrip('%'))
        output[date]=dict(metric_id='hk_prime_rate_hsbc_effective',metric_name='HSBC Prime rate',
                date=date,period=date,frequency='E',value=value,unit='% p.a.',source_id='hsbc_prime_effective',
                source_name='HSBC',source_url=HSBC_URL,status='Published',flags='',
                note=f'Rate effective from this date. HSBC current rate checked {dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()}; unchanged dates are not new rate changes.')
    if not output or output[max(output)]['value']!=float(current[1]):
        raise ValueError('HSBC rate history does not reconcile with current rate')
    return [output[k] for k in sorted(output) if start <= k[:7] and k <= as_of]


def prime_rows(raw, as_of, now, start='2002-01'):
    # Validate the live workbook against today's date, then apply the requested
    # observation cutoff. Historical cutoffs are not publication vintages.
    checked_on=dt.datetime.fromisoformat(now).astimezone(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
    rows=legacy.parse_excel('prime',raw,checked_on,now)
    return [r for r in rows if start <= r['date'][:7] and r['date'] <= as_of]


def collect(output_dir, as_of, start='2002-01'):
    raw_dir=Path(output_dir)/'raw'/'rates';raw_dir.mkdir(parents=True,exist_ok=True)
    manifest=[]
    def download(url):
        raw=fetch(url)
        name=url.split('?')[0].rstrip('/').rsplit('/',1)[-1]
        if '?' in url:name += '-'+hashlib.sha256(url.encode()).hexdigest()[:16]+'.json'
        if '.' not in name:name += '.html'
        path=raw_dir/name;path.write_bytes(raw)
        manifest.append(dict(url=url,file=name,sha256=hashlib.sha256(raw).hexdigest(),
                             retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat()))
        return raw
    # Direct complete published workbooks avoid API pagination and access failures.
    urls=[XLS_ROOT+n for n in ['T060303.xls','T060401.xls','T060302.xls','T060402.xls']]+[HSBC_URL]
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloaded=dict(zip(urls,pool.map(download,urls)))
    book=xlrd.open_workbook(file_contents=downloaded[urls[0]])
    sheet=book.sheet_by_name('T6.3.3 (HIBOR Fixing)')
    if '1-month'!=sheet.cell_value(7,5) or '11:15' not in sheet.cell_value(7,0):
        raise ValueError('Daily HIBOR workbook header changed')
    cells=[]
    for i in range(sheet.nrows):
        row=sheet.row_values(i)
        if sheet.cell(i,0).ctype==xlrd.XL_CELL_DATE:
            row[0]=xlrd.xldate_as_datetime(row[0],book.datemode)
            # Preserve Excel #N/A instead of treating its error code 42 as a rate.
            for j in range(3,10):
                row[j]=legacy.excel_rate_value(sheet.cell(i,j))
                if row[j] is None:row[j]='N.A.'
        cells.append(row)
    rows=daily_rows(cells,as_of,start)
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    prime={r['date']:r for r in prime_rows(downloaded[urls[1]],as_of,now,start)}
    for r in hsbc_rows(downloaded[HSBC_URL].decode('utf-8'),as_of,start):
        if r['date'] in prime and prime[r['date']]['value']!=r['value']:
            raise ValueError('HSBC and HKMA effective rate conflict')
        prime[r['date']]=r
    rows.extend(prime.values())
    for key,index in [('hkma_hibor',2),('hkma_prime',3)]:
        rows.extend(r for r in macro.parse_excel(key,downloaded[urls[index]],as_of) if r['period']>=start)
    # HKMA's statistical workbook is monthly. HKAB, the benchmark publisher,
    # supplies all active tenors for each newer business day, including O/N.
    latest=max(r['date'] for r in rows if r['frequency']=='D')
    first=dt.date.fromisoformat(latest)+dt.timedelta(days=1)
    last=dt.date.fromisoformat(as_of)
    warnings=[]
    if (last-first).days>45:
        raise ValueError('Daily rate workbook is over 45 days behind; refusing to publish a silent history gap.')
    dates=[first+dt.timedelta(days=i) for i in range(max(0,(last-first).days+1))
           if (first+dt.timedelta(days=i)).weekday()<5]
    def recent(day):
        try:
            return hkab_daily_rows(json.loads(download(hkab_url(day))),day,now)
        except Exception as exc:
            raise ValueError(f'No verified HKAB daily release for {day}: {exc}') from exc
    with ThreadPoolExecutor(max_workers=3) as pool:
        for daily in pool.map(recent,dates):rows.extend(daily)
    for r in rows:
        r.setdefault('period',r['date']);r.setdefault('flags','');r.setdefault('checked_at',now)
    (raw_dir/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (raw_dir/'warnings.json').write_text(json.dumps(warnings,indent=2))
    return sorted(rows,key=lambda r:(r['metric_id'],r['date']))
