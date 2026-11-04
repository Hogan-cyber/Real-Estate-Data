import test from 'node:test';
import assert from 'node:assert/strict';
import {macroSeries, latestMacro, changeInPoints, moneyInTrillions, latestPublishedRate} from '../src/content/dashboard/money-rates.js';
import * as moneyRates from '../src/content/dashboard/money-rates.js';
const dailyFixtures=[
 {metric_id:'hk_prime_rate_hsbc_effective',date:'2025-10-31',value:5,frequency:'E',checked_at:'2026-11-04T03:30:00Z'},
 {metric_id:'hk_prime_rate_hsbc_effective',date:'2026-10-05',value:4.75,frequency:'E',checked_at:'2026-11-04T03:30:00Z'},
 ...[['2026-10-02',2.96839],['2026-10-05',2.9],['2026-10-30',2.70923],['2026-11-04',2.63982]].map(([date,value])=>({metric_id:'hk_hibor_1m_daily',date,value,frequency:'D'})),
 {metric_id:'hk_hibor_3m_daily',date:'2026-11-04',value:3.18601,frequency:'D'},
];
test('daily rate chart shows October fixings and the Prime rate in force without altering monthly data',()=>{
 const original=structuredClone(dailyFixtures);
 const result=moneyRates.dailyRateSeries(dailyFixtures,'1m','2020-01-01..2026-10-31');
 const hibor=result.rows.filter(r=>r.frequency==='D'),prime=result.rows.filter(r=>r.frequency==='E');
 assert.deepEqual(hibor.map(r=>r.date),['2026-10-02','2026-10-05','2026-10-30']);
 assert.equal(prime[0].value,5); assert.equal(prime.at(-1).value,4.75);
 assert.equal(prime[0].effective_date,'2025-10-31');
 assert.ok(result.sourceRows.some(r=>r.date==='2025-10-31'));
 assert.deepEqual(dailyFixtures,original);
 assert.deepEqual(macroSeries(dailyFixtures,'hk_hibor_1m','2020-01-01..2026-11-04'),[]);
});
test('daily scope honors historical filters and does not invent missing 3-month HIBOR history',()=>{
 assert.deepEqual(moneyRates.dailyRateSeries(dailyFixtures,'1m','2020-01-01..2026-09-30').rows,[]);
 assert.deepEqual(moneyRates.dailyRateSeries(dailyFixtures,'3m','2026-10-01..2026-10-31').rows,[]);
 const result=moneyRates.dailyRateSeries(dailyFixtures,'3m','2026-11-01..2026-11-04');
 assert.deepEqual(result.rows.filter(r=>r.frequency==='D').map(r=>r.date),['2026-11-04']);
});
test('Prime history ends at its last successful confirmation even if HIBOR is newer',()=>{
 const rows=dailyFixtures.map(r=>r.frequency==='E'?{...r,checked_at:'2026-10-30T10:00:00Z'}:r);
 const prime=moneyRates.dailyRateSeries(rows,'1m','2020-01-01..2026-11-04').rows.filter(r=>r.frequency==='E');
 assert.equal(prime.at(-1).date,'2026-10-30');
});
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
