import test from 'node:test';
import assert from 'node:assert/strict';
import {selectRows, latestCommonRows, compatibleIndicators, metricCatalogue} from '../src/content/dashboard/residential-data.js';
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
