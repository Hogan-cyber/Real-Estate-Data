import test from 'node:test';
import assert from 'node:assert/strict';
import {macroSeries, latestMacro, changeInPoints, moneyInTrillions, latestPublishedRate} from '../src/content/dashboard/money-rates.js';
test('latest rate cards use daily rates independently of selected historical month',()=>{
 const rows=[{metric_id:'hk_hibor_1m_daily',date:'2026-09-30',value:3.00518},
 {metric_id:'hk_hibor_1m_daily',date:'2026-10-30',value:2.70923},
 {metric_id:'hk_hibor_1m_daily',date:'2026-11-03',value:2.68},
 {metric_id:'hk_hibor_3m_daily',date:'2026-11-03',value:3.21399}];
 assert.equal(latestPublishedRate(rows,'hk_hibor_1m_daily').date,'2026-11-03');
 assert.equal(latestPublishedRate(rows,'hk_hibor_3m_daily').value,3.21399);
 assert.equal(latestPublishedRate(rows,'hk_prime_rate_hsbc_effective'),undefined);
 assert.equal(macroSeries(rows,'hk_hibor_1m','2020-01-01..2026-09-30').length,0);
});
test('M3 growth uses exact prior year outside selected display window',()=>{
 const rows=[{metric_id:'hk_m3_hkd',period:'2025-01',date:'2025-01-31',value:100,unit:'HKD million'},{metric_id:'hk_m3_hkd',period:'2026-01',date:'2026-01-31',value:110,unit:'HKD million'}];
 const result=macroSeries(rows,'hk_m3_hkd','2026-01-01..2026-01-31');
 assert.equal(result.length,1);assert.ok(Math.abs(result[0].yoy-10)<1e-10);
 assert.equal(macroSeries(rows,'hk_m3_hkd','2026-02-01..2026-02-28').length,0);
 assert.equal(moneyInTrillions({value:1000000,unit:'HKD million'}),1);
 assert.equal(moneyInTrillions({value:1000,unit:'HKD billion'}),1);
 assert.equal(moneyInTrillions({value:1000,unit:'unknown'}),null);
});
test('latest null stays missing and rate changes are percentage points',()=>{
 const rows=[{metric_id:'rate',period:'2026-01',value:5},{metric_id:'rate',period:'2026-02',value:4.75},{metric_id:'rate',period:'2026-03',value:null}];
 assert.equal(latestMacro(rows).value,null);assert.equal(changeInPoints(rows[1],rows),-0.25);
 assert.equal(changeInPoints(rows[2],rows),null);assert.equal(changeInPoints(rows[1],[rows[1]]),null);
});
