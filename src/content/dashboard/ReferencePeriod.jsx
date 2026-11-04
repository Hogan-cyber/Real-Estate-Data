import React, { useEffect, useMemo, useState } from 'react';
import { Button, Dropdown, Filters, useDataApp } from '../../data-app-public.jsx';
import { referenceMonths, referenceRange } from './reference-period.js';

const monthLabel = month => new Intl.DateTimeFormat('en-GB', {
  month: 'short', year: 'numeric', timeZone: 'UTC',
}).format(new Date(`${month}-01T00:00:00Z`));

export function ReferencePeriod() {
  const { snapshot, queries, filters, setFilter } = useDataApp();
  const rows = useMemo(() => [...queries.observations.rows, ...(queries.rates?.rows || [])], [queries.observations.rows, queries.rates?.rows]);
  const months = useMemo(() => referenceMonths(rows), [rows]);
  const definition = snapshot.filters.find(filter => filter.id === 'date');
  const value = filters.date ?? definition.defaultValue;
  const selected = () => {
    const [from, to = from] = String(value).split('..').map(day => day.slice(0, 7));
    return [months.includes(from) ? from : months[0], months.includes(to) ? to : months.at(-1)];
  };
  const [[from, to], setDraft] = useState(selected);
  useEffect(() => { setDraft(selected()); }, [value, months]);
  const range = useMemo(() => referenceRange(rows, from, to), [rows, from, to]);
  const applied = selected();
  const latestDate = rows.map(row=>row.date).filter(Boolean).sort().at(-1);
  const selectedEnd = String(value).split('..').at(-1);
  return <>
    <Filters sticky filters={[]} queries={queries} values={filters} onChange={setFilter}
      ariaLabel="Hong Kong housing filters">
      <div className="housing-period-controls">
        <span className="housing-period-label">Reference period</span>
        <Dropdown label="From month" showLabel searchable value={from} choices={months}
          formatChoice={monthLabel} onChange={month => setDraft([month, to])} />
        <Dropdown label="To month" showLabel searchable value={to} choices={months}
          formatChoice={monthLabel} onChange={month => setDraft([from, month])} />
        <Button disabled={!range} onClick={() => setFilter('date', range)}>Apply period</Button>
        <Button onClick={() => { setFilter('date', definition.defaultValue); setDraft(
          definition.defaultValue.split('..').map(day => day.slice(0, 7))); }}>Reset filters</Button>
        {!range && <span className="housing-period-error" role="alert">Start month must not be after end month.</span>}
        {range && (from!==applied[0] || to!==applied[1]) && <span className="housing-small" role="status">Selection pending — click Apply period.</span>}
      </div>
    </Filters>
    <p className="housing-period-status" data-reviewed-rows>
      Showing {monthLabel(applied[0])} – {monthLabel(applied[1])}. Charts use available observations within these months. This period is shared across pages.
      {' '}A blank value means no published observation in the selected period.
      {selectedEnd < latestDate && <span> Newer data is available through {latestDate}.{' '}<Button onClick={()=>setFilter('date',referenceRange(rows,applied[0],months.at(-1)))}>Show latest data</Button></span>}
    </p>
  </>;
}
