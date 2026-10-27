import React, { useMemo, useState } from 'react';
import { Button, DataComponent, DataTable, Dropdown, EvidenceChart, Section, useDataApp } from '../../data-app-public.jsx';
import { ClearTrend } from './ClearTrend.jsx';
import { CLASS_LABELS, CLASS_COLORS } from './clear-trend.js';
import { averagePriceRows, latestClassPrices } from './average-prices.js';

const price = value => value == null ? '—' : value.toLocaleString('en-GB', { maximumFractionDigits: 0 });
const flags = value => [value?.includes('P') && 'Provisional', value?.includes('Z') && 'Fewer than 20 cases'].filter(Boolean).join(' · ') || '—';

export function AveragePrices({ onDownload }) {
  const { queries, filters } = useDataApp();
  const [region, setRegion] = useState('Hong Kong Island');
  const rows = useMemo(() => averagePriceRows(queries.observations.rows, filters.date, region), [queries.observations.rows, filters.date, region]);
  const latest = latestClassPrices(rows);
  const month = latest[0]?.period ?? 'No observations in selected period';
  const plotRows = rows.map(row => ({ ...row, 'HKD / sq ft': row.price_per_sq_ft }));
  return <Section id="average-price-heading" title="Average residential prices by size class"
    filters={<>
      <Dropdown label="Price district" showLabel value={region} onChange={setRegion}
        choices={['Hong Kong Island', 'Kowloon', 'New Territories']} />
      <Button disabled={!rows.length} onClick={() => onDownload(rows)}>Download prices CSV</Button>
    </>}>
    <p className="housing-small" data-editable-id="average-price-scope">
      Saleable area: A &lt;40 sq m · B 40–69.9 · C 70–99.9 · D 100–159.9 · E ≥160.
      {' '}RVD average prices exclude primary residential sales. Prices are converted from HKD per sq m to HKD per sq ft (× 0.09290304).
    </p>
    <ClearTrend id="average-price-history" queryId="observations" variant="card"
      title={`Average price trend · ${region} · HKD / sq ft`}
      rows={plotRows} sourceRows={rows} height={460}
      spec={{ type: 'line', x: 'date', y: 'HKD / sq ft', series: 'class_name', colors: CLASS_COLORS, legend: {labels: CLASS_LABELS}, stackable: false, startAtZero: false,
        valueDecimals: 0, showXAxisLabel: false, showYAxisLabel: false }}
      description="Each line is one saleable-area class, A–E. The chart and latest-price table use the shared Reference period and selected district. Transaction averages can change with the mix of properties sold; missing observations are not filled." />
    <DataComponent id="average-price-latest" queryId="observations" variant="card" kind="table"
      title={`Latest average prices · ${region} · ${month}`} sourceRows={latest} displayRows={latest}>
      <DataTable caption="Latest average prices by size class" searchable={false} rows={latest}
        columns={[
          { field: 'class_name', label: 'Size class' },
          { field: 'saleable_area', label: 'Saleable area' },
          { field: 'price_per_sq_ft', label: 'Average price (HKD / sq ft)', renderCell: price },
          { field: 'flags', label: 'Flags', renderCell: flags },
        ]} />
    </DataComponent>
  </Section>;
}
