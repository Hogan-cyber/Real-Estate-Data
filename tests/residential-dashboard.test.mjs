import test from 'node:test';
import assert from 'node:assert/strict';
import {selectRows, latestCommonRows, compatibleIndicators, metricCatalogue, recentRows, monitorEstimateDetails} from '../src/content/dashboard/residential-data.js';
const rows=[
 {metric_id:'a',date:'2025-01-31',period:'2025-01',value:10,unit:'loans',frequency:'M'},
 {metric_id:'a',date:'2025-02-28',period:'2025-02',value:0,unit:'loans',frequency:'M'},
 {metric_id:'b',date:'2025-01-31',period:'2025-01',value:-4,unit:'loans',frequency:'M'},
 {metric_id:'b',date:'2025-02-28',period:'2025-02',value:null,unit:'loans',frequency:'M'},
 {metric_id:'c',date:'2025-03-31',period:'2025-Q1',value:20,unit:'loans',frequency:'Q'},
 {metric_id:'d',date:'2025-01-31',period:'2025-01',value:50,unit:'HKD million',frequency:'M'},
];
test('date filtering preserves zero, null and negative observations without mutating input',()=>{
 const original=structuredClone(rows);
 assert.deepEqual(selectRows(rows,['a','b'],'2025-02-01..2025-02-28').map(r=>r.value),[0,null]);
 assert.deepEqual(selectRows(rows,['b'],'all').map(r=>r.value),[-4,null]);
 assert.deepEqual(rows,original);
});
test('category bars use one common observed date, never mix latest months',()=>{
 assert.deepEqual(latestCommonRows(rows,['a','b']).map(r=>r.date),['2025-01-31','2025-01-31']);
 assert.deepEqual(latestCommonRows(selectRows(rows,['a','b'],'2025-02-01..2025-02-28'),['a','b']),[]);
 assert.equal(latestCommonRows(rows,['a'])[0].value,0);
});
test('comparison choice requires equal original units and frequency',()=>{
 const catalogue=metricCatalogue(rows);
 assert.deepEqual(compatibleIndicators(catalogue,'a').map(r=>r.metric_id),['b']);
});
test('daily chart windows preserve trading-day gaps and selected cutoff',()=>{
 const data=[{date:'2026-11-20',value:1},{date:'2026-11-23',value:2},{date:'2026-11-24',value:3}];
 assert.deepEqual(recentRows(data,3),data.slice(1));
 assert.deepEqual(recentRows(data.slice(0,2),3),[data[1]]);
 assert.deepEqual(recentRows(data,'all'),data);
});
test('Monitor estimate details use the previous bank month without shifting original records',()=>{
 const data=[
  {metric_id:'monitor_nonbank_residual_count',period:'2026-10',date:'2026-10-31',value:-10},
  {metric_id:'monitor_bank_purchase_drawn_count_estimate',period:'2026-09',date:'2026-09-30',value:120},
  {metric_id:'monitor_bank_purchase_drawn_count_estimate',period:'2026-10',date:'2026-10-31',value:null},
  {metric_id:'monitor_completed_count',period:'2026-10',date:'2026-10-31',value:100},
  {metric_id:'monitor_offplan_count',period:'2026-10',date:'2026-10-31',value:10},
 ];
 const result=monitorEstimateDetails(data.filter(r=>r.period==='2026-10'),data);
 assert.equal(result.displayRows[0].bank_month,'2026-09');
 assert.equal(result.displayRows[0].bank_purchase,120);
 assert.equal(result.displayRows[0].residual,-10);
 assert.equal(result.displayRows[0].registrations,110);
 assert.ok(result.sourceRows.includes(data[1]));
 assert.equal(data[1].date,'2026-09-30');
});
