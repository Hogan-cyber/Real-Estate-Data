// Selection only: preserve published values, dates, nulls, units and statuses.
export function selectRows(rows, ids, range = 'all') {
  const selected = new Set(ids);
  const [start, end = start] = String(range || 'all').split('..');
  return rows.filter(row => selected.has(row.metric_id) &&
    (start === 'all' || (row.date >= start && row.date <= end)));
}

export function latestRow(rows) {
  return rows.reduce((latest, row) => Number.isFinite(row.value) &&
    (!latest || row.date > latest.date) ? row : latest, null);
}

export function recentRows(rows, days) {
  if (days === 'all' || !rows.length) return rows;
  const latest = rows.reduce((last,row)=>row.date>last?row.date:last,'');
  const start = new Date(latest+'T00:00:00Z');
  start.setUTCDate(start.getUTCDate()-Number(days)+1);
  return rows.filter(row=>row.date>=start.toISOString().slice(0,10));
}

export function monitorEstimateDetails(rows, allRows=rows) {
  const index = new Map(allRows.filter(row=>row.metric_id.startsWith('monitor_')).map(row=>[row.metric_id+'|'+row.period,row]));
  const source = new Set();
  const displayRows=selectRows(rows,['monitor_nonbank_residual_count']).map(residual=>{
    const prior = new Date(residual.period+'-01T00:00:00Z');
    prior.setUTCDate(0);
    const bankMonth=prior.toISOString().slice(0,7);
    const bank=index.get('monitor_bank_purchase_drawn_count_estimate|'+bankMonth);
    const completed=index.get('monitor_completed_count|'+residual.period);
    const offplan=index.get('monitor_offplan_count|'+residual.period);
    [residual,bank,completed,offplan].filter(Boolean).forEach(row=>source.add(row));
    return {registration_month:residual.period,bank_month:bankMonth,
      registrations:Number.isFinite(completed?.value)&&Number.isFinite(offplan?.value)?completed.value+offplan.value:null,
      bank_purchase:bank?.value??null,residual:residual.value};
  }).sort((a,b)=>b.registration_month.localeCompare(a.registration_month));
  return {sourceRows:[...source],displayRows};
}

export function latestCommonRows(rows, ids) {
  const wanted = new Set(ids);
  if (!wanted.size) return [];
  const dates = new Map();
  for (const row of rows) {
    if (!wanted.has(row.metric_id) || !Number.isFinite(row.value)) continue;
    if (!dates.has(row.date)) dates.set(row.date, new Map());
    dates.get(row.date).set(row.metric_id, row);
  }
  const date = [...dates.keys()].sort().reverse().find(key => dates.get(key).size === wanted.size);
  return date ? ids.map(id => dates.get(date).get(id)) : [];
}

export function metricCatalogue(rows) {
  return [...new Map(rows.map(row => [row.metric_id, row])).values()];
}

export function compatibleIndicators(catalogue, id) {
  const selected = catalogue.find(row => row.metric_id === id);
  return selected ? catalogue.filter(row => row.metric_id !== id &&
    row.unit === selected.unit && row.frequency === selected.frequency) : [];
}

export const frequencyNames = { M: 'Monthly', Q: 'Quarterly', A: 'Annual', D: 'Daily', E: 'Effective date' };
export const formatValue = (value, decimals = 2) => Number.isFinite(value)
  ? value.toLocaleString('en-GB', { maximumFractionDigits: decimals }) : '—';

export function downloadCsv(name, rows) {
  if (!rows.length) return;
  const fields = [...new Set(rows.flatMap(Object.keys))];
  const escape = value => '"' + String(value ?? '').replaceAll('"', '""') + '"';
  const text = '\uFEFF' + [fields.map(escape).join(','), ...rows.map(row =>
    fields.map(field => escape(row[field])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
