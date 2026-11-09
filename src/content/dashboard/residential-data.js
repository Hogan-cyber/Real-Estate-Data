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
