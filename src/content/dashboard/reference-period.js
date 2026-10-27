// Date-range values remain compatible with the dashboard's saved-view URLs.
export function referenceMonths(rows) {
  return [...new Set(rows.map(row => row.date?.slice(0, 7)).filter(Boolean))].sort();
}

export function referenceRange(rows, startMonth, endMonth) {
  const months = referenceMonths(rows);
  if (!months.includes(startMonth) || !months.includes(endMonth) || startMonth > endMonth) return null;
  const dates = rows.map(row => row.date).filter(Boolean).sort();
  const [year, month] = endMonth.split('-').map(Number);
  const monthEnd = new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10);
  const start = [startMonth + '-01', dates[0]].sort().at(-1);
  const end = [monthEnd, dates.at(-1)].sort()[0];
  return `${start}..${end}`;
}

export function rowsInReferencePeriod(rows, value) {
  if (!value || value === 'all') return rows;
  const [start, end = start] = value.split('..');
  return rows.filter(row => row.date >= start && row.date <= end);
}
