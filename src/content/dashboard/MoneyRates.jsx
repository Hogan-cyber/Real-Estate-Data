import React,{useState} from 'react';
import {DataComponent,DataTable,Dropdown,Button,Section,SortableRegion,SortableItem,useDataApp} from '../../data-app-public.jsx';
import {ClearTrend} from './ClearTrend.jsx';
import {macroSeries,latestMacro,changeInPoints} from './money-rates.js';
import {rowsInReferencePeriod} from './reference-period.js';

const fmt=(v,d=2)=>Number.isFinite(v)?v.toLocaleString('en-GB',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const signed=v=>Number.isFinite(v)?`${v>0?'+':''}${fmt(v)}`:'—';
const colors={'HSBC Prime rate':'var(--housing-navy)','HIBOR · 1 month':'var(--housing-orange)','HIBOR · 3 months':'var(--housing-blue)'};
function MacroCard({id,title,row,value,unit,change,changeLabel,sourceRows}){
 return <DataComponent id={id} queryId="observations" variant="card" kind="metric" title={title} sourceRows={sourceRows} displayRows={row?[row]:[]}>
  <div data-reviewed-rows><div className="housing-value">{fmt(value)}<small>{unit}</small></div><div className="housing-caption">{row?.period||'No observations in selected period'}</div><div className="housing-small">{signed(change)} {changeLabel}</div></div>
 </DataComponent>;
}
export function MoneyRates({onDownload}){
 const shell=useDataApp();const {queries,filters}=shell;const [currency,setCurrency]=useState('hkd');const[tenor,setTenor]=useState('1m');
 const all=queries.observations.rows;const selectedId=currency==='hkd'?'hk_m3_hkd':'hk_m3_total';const rateId=`hk_hibor_${tenor}`;
 const money=macroSeries(all,selectedId,filters.date);const prime=macroSeries(all,'hk_prime_rate_hsbc',filters.date);const hibor=macroSeries(all,rateId,filters.date);
 const moneyPlot=money.map(r=>({...r,'M3 (HKD trillion)':r.trillions,'YoY (%)':r.yoy}));
 const m=latestMacro(money),p=latestMacro(prime),h=latestMacro(hibor);const moneyLabel=currency==='hkd'?'Hong Kong dollar M3':'All-currency M3';
 const rates=[...prime.map(r=>({...r,line:'HSBC Prime rate'})),...hibor.map(r=>({...r,line:`HIBOR · ${tenor==='1m'?'1 month':'3 months'}`}))];
 const evidence=all.filter(r=>[selectedId,'hk_prime_rate_hsbc',rateId].includes(r.metric_id));
 const shown=rowsInReferencePeriod(evidence,filters.date);
 const bases=[...new Map([m,p,h].filter(Boolean).map(r=>[r.metric_id,r])).values()];
 return <><div className="housing-overview-heading"><p>MONEY & FINANCING CONDITIONS</p><h1>Hong Kong money supply & interest rates</h1><span>M3 tracks broad money. Prime and HIBOR provide lending-rate context; neither is a household's contracted mortgage rate.</span></div>
 <div className="housing-macro-controls"><Dropdown label="M3 currency coverage" showLabel value={currency} onChange={setCurrency} choices={['hkd','total']} formatChoice={v=>v==='hkd'?'Hong Kong dollars':'All currencies'}/><Dropdown label="HIBOR tenor" showLabel value={tenor} onChange={value=>{setTenor(value);shell.chartProps('macro-rates').onVisibleSeriesChange(undefined);}} choices={['1m','3m']} formatChoice={v=>v==='1m'?'1 month':'3 months'}/><Button onClick={()=>onDownload(shown)}>Download selected macro CSV</Button></div>
 <div className="housing-finance-kpis"><MacroCard id="macro-m3-latest" title={moneyLabel} row={m} value={m?.trillions} unit="HKD trillion equivalent" change={m?.yoy} changeLabel="% year on year" sourceRows={evidence.filter(r=>r.metric_id===selectedId)}/><MacroCard id="macro-prime-latest" title="HSBC Prime · monthly average" row={p} value={p?.value} unit="% p.a." change={changeInPoints(p,all)} changeLabel="percentage points vs prior month" sourceRows={all.filter(r=>r.metric_id==='hk_prime_rate_hsbc')}/><MacroCard id="macro-hibor-latest" title={`HIBOR monthly average · ${tenor==='1m'?'1 month':'3 months'}`} row={h} value={h?.value} unit="% p.a." change={changeInPoints(h,all)} changeLabel="percentage points vs prior month" sourceRows={all.filter(r=>r.metric_id===rateId)}/></div>
 <SortableRegion id="hk:money-rates" authoredRevision={1} variant="canvas" columns={12} spacing="standard" rows={[{id:'m3-level-row',items:['m3-level']},{id:'m3-growth-row',items:['m3-growth']},{id:'rates-row',items:['macro-rates']}]}>
 <SortableItem id="m3-level" label="M3 money supply level" kind="chart" span={12}><ClearTrend id="m3-level" queryId="observations" variant="card" title={`${moneyLabel} · total outstanding`} rows={moneyPlot} sourceRows={evidence.filter(r=>r.metric_id===selectedId)} height={350} spec={{type:'line',x:'date',y:'M3 (HKD trillion)',stackable:false,startAtZero:false,valueDecimals:2}} description="HKD trillion equivalent. Source: HKMA. Month-end; adjusted for foreign currency swap deposits. Currency coverage is stated below."/></SortableItem>
 <SortableItem id="m3-growth" label="M3 annual change" kind="chart" span={12}><ClearTrend id="m3-growth" queryId="observations" variant="card" title={`${moneyLabel} · year-on-year change`} rows={moneyPlot} sourceRows={evidence.filter(r=>r.metric_id===selectedId)} height={310} spec={{type:'line',x:'date',y:'YoY (%)',stackable:false,startAtZero:true,valueDecimals:2}} description="Percent change from the exact same month one year earlier. Calculated from the full series before applying Reference period; unavailable comparisons remain blank."/></SortableItem>
 <SortableItem id="macro-rates" label="Prime and HIBOR" kind="chart" span={12}><ClearTrend id="macro-rates" queryId="observations" variant="card" title="HSBC Prime rate & HIBOR · monthly average (% p.a.)" rows={rates} sourceRows={[...prime,...hibor]} height={390} spec={{type:'line',x:'date',y:'value',series:'line',colors,stackable:false,startAtZero:true,valueDecimals:2}} description="Official monthly averages, not live quotes or month-end interest rates. Prime is the bank's best lending rate; HIBOR is an interbank benchmark. M3 above is a month-end stock; the rate averages here describe the month."/></SortableItem>
 </SortableRegion>
 <Section id="macro-definitions" title="Definitions & sources" spacing="section"><div className="housing-macro-definitions" data-reviewed-rows>{bases.map(r=><div key={r.metric_id}><strong>{r.metric_name}</strong><p>{r.note||r.scope}</p><a href={r.source_url} target="_blank" rel="noreferrer">{r.source_name} · {r.source_table||'Official series'}</a></div>)}</div><p className="housing-small">Changes in money supply or rates do not, by themselves, establish what caused property prices to move. Source updates are checked on the existing monthly schedule.</p></Section>
 <DataComponent id="macro-monthly-table" queryId="observations" variant="card" kind="table" title="Monthly data · selected series" sourceRows={shown} displayRows={shown}><DataTable rows={[...shown].sort((a,b)=>b.period.localeCompare(a.period))} caption="Original values and units" columns={[{field:'period',label:'Reference month'},{field:'metric_name',label:'Series'},{field:'value',label:'Original value',renderCell:v=>fmt(v)},{field:'unit',label:'Original unit'},{field:'source_name',label:'Source'}]}/></DataComponent>
 </>;
}
