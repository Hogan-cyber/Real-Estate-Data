import {rowsInReferencePeriod} from './reference-period.js';
import {exactChange} from './clear-trend.js';
export function latestMacro(rows){return [...rows].sort((a,b)=>a.period.localeCompare(b.period)).at(-1);}
export function latestPublishedRate(rows,id){return rows.filter(r=>r.metric_id===id).sort((a,b)=>a.date.localeCompare(b.date)).at(-1);}
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
