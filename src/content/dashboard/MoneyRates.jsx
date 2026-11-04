import React,{useState} from 'react';
import {DataComponent,DataTable,Dropdown,Button,Section,SortableRegion,SortableItem,useDataApp} from '../../data-app-public.jsx';
import {ClearTrend} from './ClearTrend.jsx';
import {macroSeries,latestMacro,latestPublishedRate,dailyRateSeries} from './money-rates.js';
import {rowsInReferencePeriod} from './reference-period.js';

const fmt=(v,d=2)=>Number.isFinite(v)?v.toLocaleString('en-GB',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const signed=v=>Number.isFinite(v)?`${v>0?'+':''}${fmt(v)}`:'—';
const colors={'HSBC Prime rate':'var(--housing-navy)','HIBOR · 1 month':'var(--housing-orange)','HIBOR · 3 months':'var(--housing-blue)'};
function MacroCard({id,title,row,value,unit,change,changeLabel,sourceRows}){
 return <DataComponent id={id} queryId="observations" variant="card" kind="metric" title={title} sourceRows={sourceRows} displayRows={row?[row]:[]}>
  <div data-reviewed-rows><div className="housing-value">{fmt(value)}<small>{unit}</small></div><div className="housing-caption">{row?.period||'No observations in selected period'}</div><div className="housing-small">{signed(change)} {changeLabel}</div></div>
 </DataComponent>;
}
const readableDate=value=>value?new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'Asia/Hong_Kong'}).format(new Date(value.length===10?value+'T00:00:00+08:00':value)):'Unavailable';
function LatestRateCard({id,title,row,sourceRows,status}){
 return <DataComponent id={id} queryId="rates" variant="card" kind="metric" title={title} sourceRows={sourceRows} displayRows={row?[row]:[]}>
  <div data-reviewed-rows><div className="housing-value">{fmt(row?.value,row?.frequency==='D'?5:2)}<small>% p.a.</small></div>
   <div className="housing-caption" title={row?(row.frequency==='E'?`Rate confirmed ${readableDate(row.checked_at)}; effective since ${readableDate(row.date)}.`:`Published fixing for ${readableDate(row.date)}.`):undefined}>{row?(row.frequency==='E'?new Intl.DateTimeFormat('en-CA',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'Asia/Hong_Kong'}).format(new Date(row.checked_at)):row.date):'Unavailable'}</div>
   {status&&status.status!=='Verified'&&<div className="housing-small" role="status">{status.status} — showing the last available observation.</div>}
  </div>
 </DataComponent>;
}
export function MoneyRates({onDownload}){
 const shell=useDataApp();const {queries,filters}=shell;const [currency,setCurrency]=useState('hkd');const[tenor,setTenor]=useState('1m');const[rateView,setRateView]=useState('daily');
 const all=queries.observations.rows;const selectedId=currency==='hkd'?'hk_m3_hkd':'hk_m3_total';const rateId=`hk_hibor_${tenor}`;
 const money=macroSeries(all,selectedId,filters.date);const prime=macroSeries(all,'hk_prime_rate_hsbc',filters.date);const hibor=macroSeries(all,rateId,filters.date);
 const moneyPlot=money.map(r=>({...r,'M3 (HKD trillion)':r.trillions,'YoY (%)':r.yoy}));
 const m=latestMacro(money),p=latestMacro(prime),h=latestMacro(hibor);const moneyLabel=currency==='hkd'?'Hong Kong dollar M3':'All-currency M3';
 const rateRows=queries.rates?.rows||[];
 const latestPrime=latestPublishedRate(rateRows,'hk_prime_rate_hsbc_effective'),latestHibor=latestPublishedRate(rateRows,`hk_hibor_${tenor}_daily`);
 const rateStatus=id=>queries.status.rows.find(r=>r.source_id===id);
 const rates=[...prime.map(r=>({...r,line:'HSBC Prime rate'})),...hibor.map(r=>({...r,line:`HIBOR · ${tenor==='1m'?'1 month':'3 months'}`}))];
 const daily=dailyRateSeries(rateRows,tenor,filters.date);
 const dailyView=rateView==='daily';
 const dailyHistory=rateRows.filter(r=>r.metric_id===`hk_hibor_${tenor}_daily`).sort((a,b)=>a.date.localeCompare(b.date));
 const evidence=all.filter(r=>[selectedId,'hk_prime_rate_hsbc',rateId].includes(r.metric_id));
 const shown=rowsInReferencePeriod(evidence,filters.date);
 const moneyDefinition=latestMacro(all.filter(r=>r.metric_id===selectedId));
 const primeDefinition=latestMacro(all.filter(r=>r.metric_id==='hk_prime_rate_hsbc'));
 const hiborDefinition=latestMacro(all.filter(r=>r.metric_id===rateId));
 return <><div className="housing-overview-heading"><p>MONEY & FINANCING CONDITIONS</p><h1>Hong Kong money supply & interest rates</h1><span>M3 tracks broad money. Prime and HIBOR provide lending-rate context; neither is a household's contracted mortgage rate.</span></div>
 <div className="housing-macro-controls"><Dropdown label="M3 currency coverage" showLabel value={currency} onChange={setCurrency} choices={['hkd','total']} formatChoice={v=>v==='hkd'?'Hong Kong dollars':'All currencies'}/><Dropdown label="HIBOR tenor" showLabel value={tenor} onChange={value=>{setTenor(value);shell.chartProps('macro-rates').onVisibleSeriesChange(undefined);shell.chartProps('macro-rates').onZoomChange(undefined);}} choices={['1m','3m']} formatChoice={v=>v==='1m'?'1 month':'3 months'}/><Button onClick={()=>onDownload(shown)}>Download selected macro CSV</Button></div>
 
 <div className="housing-finance-kpis" title="Prime and HIBOR show latest available rates, independently of the historical Reference period."><MacroCard id="macro-m3-latest" title={moneyLabel} row={m} value={m?.trillions} unit="HKD trillion equivalent" change={m?.yoy} changeLabel="% year on year" sourceRows={evidence.filter(r=>r.metric_id===selectedId)}/><LatestRateCard id="macro-prime-latest" title="HSBC Prime" row={latestPrime} sourceRows={rateRows.filter(r=>r.metric_id==='hk_prime_rate_hsbc_effective')} status={rateStatus('hsbc_prime_effective')}/><LatestRateCard id="macro-hibor-latest" title={`HIBOR · ${tenor==='1m'?'1 month':'3 months'}`} row={latestHibor} sourceRows={rateRows.filter(r=>r.metric_id===`hk_hibor_${tenor}_daily`)} status={rateStatus('hk_rates_hibor')}/></div>
 <div className="housing-small" data-reviewed-rows><Button onClick={()=>onDownload(rateRows)}>Download daily &amp; effective rates CSV</Button></div>
 {p&&h&&p.period!==h.period&&<p className="housing-small" data-reviewed-rows>Latest available months differ: HSBC Prime {p.period}; {tenor==='1m'?'1-month':'3-month'} HIBOR {h.period}. No missing monthly rate is filled forward.</p>}
 <SortableRegion id="hk:money-rates" authoredRevision={1} variant="canvas" columns={12} spacing="standard" rows={[{id:'m3-level-row',items:['m3-level']},{id:'m3-growth-row',items:['m3-growth']},{id:'rates-row',items:['macro-rates']}]}>
 <SortableItem id="m3-level" label="M3 money supply level" kind="chart" span={12}><ClearTrend id="m3-level" queryId="observations" variant="card" title={`${moneyLabel} · total outstanding`} rows={moneyPlot} sourceRows={evidence.filter(r=>r.metric_id===selectedId)} height={350} spec={{type:'line',x:'date',y:'M3 (HKD trillion)',stackable:false,startAtZero:false,valueDecimals:2}} description="HKD trillion equivalent. Source: HKMA. Month-end; adjusted for foreign currency swap deposits. Currency coverage is stated below."/></SortableItem>
 <SortableItem id="m3-growth" label="M3 annual change" kind="chart" span={12}><ClearTrend id="m3-growth" queryId="observations" variant="card" title={`${moneyLabel} · year-on-year change`} rows={moneyPlot} sourceRows={evidence.filter(r=>r.metric_id===selectedId)} height={310} spec={{type:'line',x:'date',y:'YoY (%)',stackable:false,startAtZero:true,valueDecimals:2}} description="Percent change from the exact same month one year earlier. Calculated from the full series before applying Reference period; unavailable comparisons remain blank."/></SortableItem>
 <SortableItem id="macro-rates" label="Prime and HIBOR" kind="chart" span={12}><ClearTrend id="macro-rates" queryId={dailyView?'rates':'observations'} variant="card" title={`HSBC Prime rate & HIBOR · ${dailyView?'daily rates':'monthly averages'} (% p.a.)`} rows={dailyView?daily.rows:rates} sourceRows={dailyView?daily.sourceRows:[...prime,...hibor]} height={390} dateGrain={dailyView?'day':'month'} stepSeries={dailyView?['HSBC Prime rate']:[]} headerControls={<Dropdown label="Rate frequency" showLabel value={rateView} onChange={value=>{setRateView(value);shell.chartProps('macro-rates').onZoomChange(undefined);shell.chartProps('macro-rates').onVisibleSeriesChange(undefined);}} choices={['daily','monthly']} formatChoice={value=>value==='daily'?'Daily rates':'Monthly averages'}/>} spec={{type:'line',x:'date',y:'value',series:'line',colors,stackable:false,startAtZero:true,valueDecimals:2}} description={dailyView?'Published daily HIBOR fixings and the HSBC Prime rate in force on those dates. Prime changes on its effective date and is never extended beyond its last successful source check. Missing HIBOR weekdays break the line. Source inspection preserves the original effective dates.':'Officially published HKMA monthly averages. Each series updates when its monthly value is published; daily fixings are not substituted for monthly averages.'}>
  <p className="housing-small" data-reviewed-rows>{dailyView?`Daily HIBOR history available: ${dailyHistory[0]?.date||'unavailable'} – ${dailyHistory.at(-1)?.date||'unavailable'}. The chart follows Reference period.`:`Latest official monthly data in this period: Prime ${p?.period||'unavailable'} · HIBOR ${h?.period||'unavailable'}. Switch to Daily rates for more recent fixings.`}</p>
 </ClearTrend></SortableItem>
 </SortableRegion>
 <Section id="macro-definitions" title="Definitions & sources" spacing="section"><div className="housing-macro-definitions" data-reviewed-rows>
  <div><strong>{moneyLabel}</strong><p>Month-end money supply, adjusted for foreign currency swap deposits. Values are shown in HKD trillion equivalent; original HKD million values remain in the dataset.</p>{moneyDefinition&&<a href={moneyDefinition.source_documentation} target="_blank" rel="noreferrer">HKMA · M3 definition (Table 2.2.1)</a>}</div>
  <div><strong>HSBC Prime rate</strong><p>Daily view: HSBC's published rate in force. Monthly view: the official HKMA monthly average. Prime is a lending benchmark, not a contracted mortgage rate.</p>{latestPrime&&<a href={latestPrime.source_url} target="_blank" rel="noreferrer">HSBC · current Prime &amp; rate history</a>}{primeDefinition&&<p><a href={primeDefinition.source_documentation} target="_blank" rel="noreferrer">HKMA · Prime monthly definition (Table 6.4.2)</a></p>}</div>
  <div><strong>HIBOR · {tenor==='1m'?'1 month':'3 months'}</strong><p>Daily view: published HKAB interbank fixings. Monthly view: the official HKMA monthly average of those fixings. HIBOR is a market benchmark.</p>{latestHibor&&<a href={latestHibor.source_url} target="_blank" rel="noreferrer">{latestHibor.source_name==='Hong Kong Association of Banks'?'HKAB':'HKMA'} · daily HIBOR fixing</a>}{hiborDefinition&&<p><a href={hiborDefinition.source_documentation} target="_blank" rel="noreferrer">HKMA · HIBOR monthly definition (Table 6.3.2)</a></p>}</div>
 </div><p className="housing-small">Changes in money supply or rates do not, by themselves, establish what caused property prices to move. Source updates are checked daily at 18:00 Hong Kong time.</p></Section>
 <DataComponent id="macro-monthly-table" queryId="observations" variant="card" kind="table" title="Monthly data · selected series" sourceRows={shown} displayRows={shown}><DataTable rows={[...shown].sort((a,b)=>b.period.localeCompare(a.period))} caption="Original values and units" columns={[{field:'period',label:'Reference month'},{field:'metric_name',label:'Series'},{field:'value',label:'Original value',renderCell:v=>fmt(v)},{field:'unit',label:'Original unit'},{field:'status',label:'Status'},{field:'source_name',label:'Source'}]}/></DataComponent>
 </>;
}
