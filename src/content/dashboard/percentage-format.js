// Values are already percentages (3.26 means 3.26%, not 326%).
export function formatPercent(value, { signed = false, decimals = 2 } = {}) {
  if (!Number.isFinite(value)) return '—';
  const rounded = Number(value.toFixed(decimals));
  const normalized = rounded === 0 ? 0 : rounded;
  return `${signed && normalized > 0 ? '+' : ''}${normalized.toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}%`;
}
