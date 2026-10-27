import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {referenceMonths, referenceRange, rowsInReferencePeriod} from '../src/content/dashboard/reference-period.js';
import {validFilterValue} from '../src/dashboard-url-state.js';
const rows=[{date:'1999-01-31'},{date:'2024-01-31'},{date:'2024-02-29'},{date:'2024-03-31'}];
test('month choices are unique, sorted and exclude unavailable future months',()=>{
 assert.deepEqual(referenceMonths([...rows,rows[2]]),['1999-01','2024-01','2024-02','2024-03']);
});
test('a full month range retains every monthly observation, including leap day',()=>{
 const range=referenceRange(rows,'2024-01','2024-03');
 assert.equal(range,'2024-01-01..2024-03-31');
 assert.deepEqual(rowsInReferencePeriod(rows,range),rows.slice(1));
 assert.deepEqual(rowsInReferencePeriod(rows,referenceRange(rows,'2024-02','2024-02')),[rows[2]]);
});
test('range links remain valid at both ends of reviewed coverage',()=>{
 const range=referenceRange(rows,'1999-01','2024-03');
 const filter={id:'date',field:'date',mode:'through',queryIds:['observations']};
 assert.equal(range,'1999-01-31..2024-03-31');
 assert.equal(validFilterValue({queries:{observations:{rows}}},filter,range),true);
});
test('reversed and unavailable ranges cannot be applied',()=>{
 assert.equal(referenceRange(rows,'2024-03','2024-01'),null);
 assert.equal(referenceRange(rows,'2024-01','2024-04'),null);
});
test('legacy date-only links retain their explicit single-month selection',()=>{
 assert.deepEqual(rowsInReferencePeriod(rows,'2024-02-29'),[rows[2]]);
 assert.deepEqual(rowsInReferencePeriod(rows,'all'),rows);
});
test('the saved dashboard declares a supported date range',()=>{
 const snapshot=JSON.parse(readFileSync(new URL('../src/data.json',import.meta.url)));
 const filter=snapshot.filters.find(f=>f.id==='date');
 assert.equal(filter.mode,'through');
 assert.equal(validFilterValue(snapshot,filter,filter.defaultValue),true);
});
