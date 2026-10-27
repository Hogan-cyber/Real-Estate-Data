import test from 'node:test';
import assert from 'node:assert/strict';
import { niceScale, spreadLabels, monthlySegments, exactChange } from '../src/content/dashboard/clear-trend.js';
test('monthly lines break at missing values and absent months', () => {
  const rows = [{date:'2026-01-31',value:1},{date:'2026-02-28',value:null},{date:'2026-03-31',value:3},{date:'2026-05-31',value:5},{date:'2026-06-30',value:6}];
  assert.deepEqual(monthlySegments(rows,'value').map(s=>s.map(r=>r.value)),[[1],[3],[5,6]]);
});
test('endpoint labels stay separated without moving their data coordinates', () => {
  const rows=[{y:100},{y:101},{y:102},{y:380},{y:390}];
  const result=spreadLabels(rows,20,400,34);
  assert.ok(result.every((r,i)=>!i||r.labelY-result[i-1].labelY>=34));
  assert.deepEqual(result.map(r=>r.y),rows.map(r=>r.y));
  assert.ok(result.at(-1).labelY<=400);
});
test('axis contains the data and handles a single constant observation', () => {
  for(const values of [[300,450],[340.5],[13000,37000],[-5,2]]){
    const s=niceScale(values);assert.ok(s.min<=Math.min(...values)&&s.max>=Math.max(...values));assert.ok(s.max>s.min);
  }
});
test('momentum uses exact comparable month, preserving a missing comparator', () => {
  const row={metric_id:'price',period:'2026-08',value:90};
  assert.equal(exactChange(row,[{metric_id:'price',period:'2025-07',value:100}]),null);
  assert.ok(Math.abs(exactChange(row,[{metric_id:'price',period:'2025-08',value:100}])+10)<1e-9);
});
