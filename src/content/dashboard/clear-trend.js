export const CLASS_LABELS = { A: 'Class A · <40 sq m', B: 'Class B · 40–69.9 sq m', C: 'Class C · 70–99.9 sq m', D: 'Class D · 100–159.9 sq m', E: 'Class E · ≥160 sq m' };
export const CLASS_COLORS = { A: 'var(--housing-blue)', B: 'var(--housing-orange)', C: 'var(--housing-grey)', D: 'var(--housing-gold)', E: 'var(--housing-navy)' };
export const TREND_COLORS = ['var(--housing-blue)', 'var(--housing-orange)', 'var(--housing-grey)', 'var(--housing-gold)', 'var(--housing-navy)'];
export function niceScale(values, zero = false) {
  const finite = values.filter(Number.isFinite);
  if (!finite.length) return { min: 0, max: 1, ticks: [0, 1] };
  let min = Math.min(...finite), max = Math.max(...finite);
  const padding = (max - min || Math.abs(max) || 1) * 0.08;
  min = zero ? Math.min(0, min) : min - padding; max += padding;
  const raw = (max - min) / 5, power = 10 ** Math.floor(Math.log10(raw));
  const ratio = raw / power;
  const step = (ratio < 1.5 ? 1 : ratio < 3 ? 2 : ratio < 7 ? 5 : 10) * power;
  min = Math.floor(min / step) * step; max = Math.ceil(max / step) * step;
  const ticks = Array.from({ length: Math.round((max - min) / step) + 1 }, (_, n) => min + n * step);
  return { min, max, ticks };
}
export function spreadLabels(items, top, bottom, gap = 29) {
  const ordered = items.map(item => ({ ...item })).sort((a, b) => a.y - b.y);
  ordered.forEach((item, i) => { item.labelY = Math.max(item.y, i ? ordered[i - 1].labelY + gap : top); });
  for (let i = ordered.length - 1; i >= 0; i--) ordered[i].labelY = Math.min(ordered[i].labelY, i === ordered.length - 1 ? bottom : ordered[i + 1].labelY - gap);
  return ordered;
}
export function monthlySegments(rows, yField) {
  const result = []; let previous = null;
  for (const row of [...rows].sort((a, b) => a.date.localeCompare(b.date))) {
    const [year, month] = row.date.split('-').map(Number), index = year * 12 + month;
    if (!Number.isFinite(row[yField])) { previous = null; continue; }
    if (previous == null || index !== previous + 1) result.push([]);
    result.at(-1).push(row); previous = index;
  }
  return result;
}
export function exactChange(row, all, months = 12) {
  if (!row || !Number.isFinite(row.value)) return null;
  const [y, m] = row.period.split('-').map(Number);
  const priorPeriod = new Date(Date.UTC(y, m - 1 - months, 1)).toISOString().slice(0, 7);
  const prior = all.find(r => r.metric_id === row.metric_id && r.period === priorPeriod);
  return Number.isFinite(prior?.value) && prior.value !== 0 ? (row.value / prior.value - 1) * 100 : null;
}
