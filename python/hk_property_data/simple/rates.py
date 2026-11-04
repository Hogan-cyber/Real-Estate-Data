"""Read official rate workbooks directly; keep fixing, effective and monthly data apart."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
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
    # Newest daily HKMA releases may extend past the statistical workbook.
    # Only the explicitly published 1M fixing is added from this source.
    latest=max(r['date'] for r in rows if r['frequency']=='D')
    first=dt.date.fromisoformat(latest)+dt.timedelta(days=1)
    last=dt.date.fromisoformat(as_of)
    warnings=[]
    if (last-first).days>45:
        warnings.append('Daily rate workbook is over 45 days behind; recent HTML supplement limited to 45 days.')
        first=last-dt.timedelta(days=44)
    dates=[first+dt.timedelta(days=i) for i in range(max(0,(last-first).days+1))
           if (first+dt.timedelta(days=i)).weekday()<5]
    def recent(day):
        try:
            record,_=legacy.verified_html_day(day,download)
            r=legacy._row('hk_hibor_1m_daily','HIBOR 1 month',record['end_of_date'],
                record['hibor_fixing_1m'],'hk_rates_hibor','Hong Kong Monetary Authority',
                'https://www.hkma.gov.hk/eng/data-publications-and-research/data-and-statistics/daily-monetary-statistics/'+day.strftime('%Y/%m/ms-%Y%m%d/'),now)
            r.update(period=r['date'],flags='',note='HKAB 1-month fixing published in HKMA Daily Monetary Statistics.')
            return r
        except Exception as exc:
            warnings.append(f'No verified daily release for {day}: {exc}')
            return None
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows.extend(r for r in pool.map(recent,dates) if r is not None)
    for r in rows:
        r.setdefault('period',r['date']);r.setdefault('flags','');r.setdefault('checked_at',now)
    (raw_dir/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (raw_dir/'warnings.json').write_text(json.dumps(warnings,indent=2))
    return sorted(rows,key=lambda r:(r['metric_id'],r['date']))
