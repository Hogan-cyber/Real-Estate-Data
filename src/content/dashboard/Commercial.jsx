import React, { useState } from 'react';
import { DataComponent, DataTable, Dropdown, Section, Button, useDataApp } from '../../data-app-public.jsx';
import { ClearTrend } from './ClearTrend.jsx';
import { exactChange, CLASS_COLORS } from './clear-trend.js';
import { rowsInReferencePeriod } from './reference-period.js';
import { SQ_METRES_PER_SQ_FOOT } from './average-prices.js';

const format = (n, d = 1) => Number.isFinite(n) ? n.toLocaleString('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d }) : '—';
const signed = n => Number.isFinite(n) ? `${n > 0 ? '+' : ''}${format(n)}%` : '—';
const latest = rows => rows.reduce((a, r) => !a || r.date > a.date ? r : a, null);
const flagLabel = flags => [flags?.includes('P') && 'Provisional', flags?.includes('X') && '<5 cases', flags?.includes('Y') && '<10 cases', flags?.includes('Z') && '<20 cases'].filter(Boolean).join(' · ') || '—';

function ChangeCard({ id, title, row, all }) {
  const evidence = all.filter(r => r.metric_id === row?.metric_id && r.date <= row.date);
  return <DataComponent id={id} queryId="observations" kind="metric" variant="card" title={title} sourceRows={evidence} displayRows={row ? [row] : []}><div data-reviewed-rows><div className="housing-change">{signed(exactChange(row, all, 12))}<small>YoY</small></div><div className="housing-caption">{signed(exactChange(row, all, 1))} month on month</div><div className="housing-momentum-meta">{row?.period || 'No observations'} · Index {format(row?.value)} (1999 = 100)</div></div></DataComponent>;
}

export function Commercial({ onDownload }) {
  const { queries, filters, chartProps } = useDataApp();
  const [sector, setSector] = useState('Office'), [district, setDistrict] = useState('Central');
  const all = queries.observations.rows;
  const rows = rowsInReferencePeriod(all, filters.date).filter(r => r.property_type === sector);
  const prices = rows.filter(r => r.measure === 'price_index');
  const rents = rows.filter(r => r.measure === 'rental_index');
  const overall = list => latest(list.filter(r => r.grade === 'All'));
  const districts = [...new Set(all.filter(r => r.property_type === sector && r.measure === 'average_price').map(r => r.region))];
  const region = districts.includes(district) ? district : districts[0];
  const averages = rows.filter(r => ['average_price', 'average_rent'].includes(r.measure) && (sector !== 'Office' || r.region === region));
  const priceRows = averages.filter(r => r.measure === 'average_price').map(r => ({ ...r, 'HKD / sq ft': r.value == null ? null : r.value * SQ_METRES_PER_SQ_FOOT }));
  const latestMonth = latest(averages)?.period;
  const table = averages.filter(r => r.period === latestMonth).map(r => ({ ...r, converted_value: r.value == null ? null : r.value * SQ_METRES_PER_SQ_FOOT, converted_unit: r.measure === 'average_rent' ? 'HKD / sq ft / month' : 'HKD / sq ft' }));
  const yields = rows.filter(r => r.measure === 'yield'); const yieldMonth = latest(yields)?.period;
  const yieldRows = yields.filter(r => r.period === yieldMonth);
  const indexSpec = { type: 'line', x: 'date', y: 'value', series: 'grade', colors: CLASS_COLORS, legend: { labels: { A: 'Grade A', B: 'Grade B', C: 'Grade C', All: 'All grades / all districts' } }, valueDecimals: 1, stackable: false, startAtZero: false, showXAxisLabel: false, showYAxisLabel: false };
  const indexRows = list => sector === 'Office' ? list.filter(r => r.grade !== 'All') : list;
  return <>
    <div className="housing-overview-heading"><p>COMMERCIAL PROPERTY</p><h1>Hong Kong commercial real estate</h1><span>Office, retail and industrial markets. Price indices, rental indices and transaction averages are kept separate.</span></div>
    <Section id="commercial-market" title="Market selection" filters={<><Dropdown label="Property sector" showLabel value={sector} onChange={value => { setSector(value); for (const id of ['commercial-price-trend','commercial-rent-trend','commercial-average-price']) { chartProps(id).onVisibleSeriesChange(undefined); chartProps(id).onZoomChange(null); } }} choices={['Office', 'Retail', 'Industrial']} /><Button disabled={!rows.length} onClick={() => onDownload(rows)}>Download sector CSV</Button></>}>
      <p className="housing-small">{sector === 'Office' ? 'Office grades A, B and C describe building quality, not residential size classes. Indices cover all districts.' : sector === 'Industrial' ? 'Industrial coverage is private flatted factories. It does not represent warehouses, logistics facilities or every industrial property.' : 'Private retail premises. Average prices and rents are published for Hong Kong Island, Kowloon and the New Territories.'} Commercial averages use internal floor area.</p>
      <div className="housing-commercial-kpis"><ChangeCard id="commercial-price-change" title={`${sector} prices · year on year`} row={overall(prices)} all={all} /><ChangeCard id="commercial-rent-change" title={`${sector} rents · year on year`} row={overall(rents)} all={all} /></div>
      <ClearTrend id="commercial-price-trend" queryId="observations" variant="card" title={`${sector} Property Price Index · 1999 = 100`} rows={indexRows(prices)} sourceRows={indexRows(prices)} spec={indexSpec} height={430} description="Official price indices. Office grades reflect quality; retail and industrial series cover all districts. Missing observations remain gaps." />
      <ClearTrend id="commercial-rent-trend" queryId="observations" variant="card" title={`${sector} Rental Index · 1999 = 100`} rows={indexRows(rents)} sourceRows={indexRows(rents)} spec={indexSpec} height={360} description="Official rental indices, shown separately from prices. Source: Rating and Valuation Department." />
    </Section>
    <Section id="commercial-averages" title={`${sector} average prices and rents`} filters={sector === 'Office' ? <Dropdown label="Office district" showLabel value={region} onChange={setDistrict} choices={districts} /> : undefined}>
      <ClearTrend id="commercial-average-price" queryId="observations" variant="card" title={`Average sale price · ${sector === 'Office' ? region : sector} · HKD / sq ft`} rows={priceRows} sourceRows={priceRows} height={400} spec={{ type: 'line', x: 'date', y: 'HKD / sq ft', series: sector === 'Office' ? 'grade' : 'region', colors: sector === 'Office' ? CLASS_COLORS : {}, legend: {labels:{A:'Grade A',B:'Grade B',C:'Grade C'}}, valueDecimals: 0, stackable: false, startAtZero: false }} description="Official HKD per square metre multiplied by 0.09290304. Transaction averages are sensitive to the mix of properties. No interpolation and no district averaging." />
      <DataComponent id="commercial-latest-averages" queryId="observations" kind="table" variant="card" title={`Latest published averages · ${latestMonth || 'No observations in selected period'}`} sourceRows={table} displayRows={table}><DataTable caption="Latest commercial prices and rents" searchable={false} rows={table} columns={[{field:'region',label:'District'},{field:'grade',label:'Grade'},{field:'metric_name',label:'Measure'},{field:'converted_value',label:'Value',renderCell:v=>format(v,1)},{field:'converted_unit',label:'Unit'},{field:'flags',label:'Flags',renderCell:flagLabel}]} /></DataComponent>
      <p className="housing-small">The table uses one reference month. A dash means no published value, never zero. P = provisional; X / Y / Z = fewer than 5 / 10 / 20 cases. Compare trends with indices; individual transaction averages can be volatile.</p>
    </Section>
    <Section id="commercial-yields" title={`Market yields · ${yieldMonth || 'No observations in selected period'}`}><DataComponent id="commercial-yield-table" queryId="observations" kind="table" variant="card" sourceRows={yieldRows} displayRows={yieldRows}><DataTable caption="Commercial market yields" searchable={false} rows={yieldRows} columns={[{field:'property_type',label:'Sector'},{field:'grade',label:'Grade'},{field:'value',label:'Market yield (%)',renderCell:v=>format(v,1)},{field:'period',label:'Reference month'},{field:'flags',label:'Flags',renderCell:flagLabel}]} /></DataComponent><p className="housing-small">Statistical market yields are broad indications, not property-specific net returns. Office yields are available for Grades A and B only.</p></Section>
  </>;
}
