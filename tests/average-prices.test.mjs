import test from 'node:test';
import assert from 'node:assert/strict';
import {averagePriceRows, latestClassPrices} from '../src/content/dashboard/average-prices.js';
const price=(class_name,date,value,region='Hong Kong Island')=>({source_table:'1.2',class_name,date,period:date.slice(0,7),value,unit:'HKD / sq m',region,flags:'PZ',source_url:'https://www.rvd.gov.hk/datagovhk/1.2M.csv'});
const rows=[price('A','2024-01-31',100000),price('B','2024-01-31',150000),price('A','2024-02-29',110000),price('B','2024-02-29',null),price('A','2024-02-29',50000,'Kowloon'),{...price('A','2024-02-29',99000),source_table:'1.1'}];
test('converts official price per square metre to price per square foot without altering evidence',()=>{
 const before=JSON.stringify(rows);
 const result=averagePriceRows(rows,'2024-01-01..2024-01-31','Hong Kong Island');
 assert.equal(result.length,2);
 assert.equal(result[0].price_per_sq_ft,9290.304);
 assert.equal(result[0].value,100000);
 assert.equal(result[0].unit,'HKD / sq m');
 assert.equal(result[0].flags,'PZ');
 assert.equal(JSON.stringify(rows),before);
});
test('period and district apply together; rents and sale totals do not enter prices',()=>{
 const result=averagePriceRows(rows,'2024-02-01..2024-02-29','Kowloon');
 assert.equal(result.length,1);
 assert.equal(result[0].price_per_sq_ft,4645.152);
});
test('latest class comparison uses one month and preserves missing observations',()=>{
 const result=latestClassPrices(averagePriceRows(rows,'2024-01-01..2024-02-29','Hong Kong Island'));
 assert.deepEqual(result.map(r=>[r.class_name,r.period]),[['A','2024-02'],['B','2024-02']]);
 assert.equal(result[1].price_per_sq_ft,null);
});
test('a period without price releases stays empty rather than pulling in another month',()=>{
 assert.deepEqual(averagePriceRows(rows,'2024-03-01..2024-03-31','Hong Kong Island'),[]);
 assert.deepEqual(latestClassPrices([]),[]);
});
