import {rowsInReferencePeriod} from './reference-period.js';
import {exactChange} from './clear-trend.js';
export function latestMacro(rows){return [...rows].sort((a,b)=>a.period.localeCompare(b.period)).at(-1);}
export function latestPublishedRate(rows,id){return rows.filter(r=>r.metric_id===id).sort((a,b)=>a.date.localeCompare(b.date)).at(-1);}
export function dailyRateSeries(all,tenor,period){
 const fixings=rowsInReferencePeriod(all.filter(r=>r.metric_id===`hk_hibor_${tenor}_daily`),period).sort((a,b)=>a.date.localeCompare(b.date));
 if(!fixings.length)return {rows:[],sourceRows:[]};
 const history=all.filter(r=>r.metric_id==='hk_prime_rate_hsbc_effective').sort((a,b)=>a.date.localeCompare(b.date));
 const checked=history.at(-1)?.checked_at;
 const confirmedThrough=checked?new Intl.DateTimeFormat('en-CA',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'Asia/Hong_Kong'}).format(new Date(checked)):'';
 const start=fixings[0].date,end=fixings.at(-1).date;
 // Plot the effective rate in force, keeping the original effective date in
 // both the display rows and source evidence. Never carry past confirmation.
 const dates=[...new Set([...fixings.map(r=>r.date),...history.map(r=>r.date),confirmedThrough])].filter(date=>date>=start&&date<=end).sort();
 const used=new Set();
 const prime=dates.flatMap(date=>{
  const source=history.filter(r=>r.date<=date).at(-1);
  if(!source||date>confirmedThrough||!Number.isFinite(source.value))return [];
  used.add(source);
  return [{...source,effective_date:source.date,date,observation_basis:'Effective rate in force',line:'HSBC Prime rate'}];
 });
 return {rows:[...prime,...fixings.map(r=>({...r,line:`HIBOR · ${tenor==='1m'?'1 month':'3 months'}`}))],sourceRows:[...used,...fixings]};
}
export function moneyInTrillions(row){
 if(!Number.isFinite(row?.value))return null;
 const divisor={'HKD million':1e6,'HKD billion':1000,'HKD trillion':1}[row.unit];
 return divisor?row.value/divisor:null;
}
export function macroSeries(all,id,period){
 return rowsInReferencePeriod(all.filter(r=>r.metric_id===id),period).map(r=>({...r,trillions:moneyInTrillions(r),yoy:exactChange(r,all,12)}));
}
export function changeInPoints(row,all){
 if(!Number.isFinite(row?.value))return null;
 const[y,m]=row.period.split('-').map(Number);
 const p=new Date(Date.UTC(y,m-2,1)).toISOString().slice(0,7);
 const previous=all.find(r=>r.metric_id===row.metric_id&&r.period===p);
 return Number.isFinite(previous?.value)?row.value-previous.value:null;
}
