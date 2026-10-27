import { rowsInReferencePeriod } from './reference-period.js';

// One international square foot is exactly 0.09290304 square metres.
export const SQ_METRES_PER_SQ_FOOT = 0.09290304;
export const SIZE_CLASSES = {
  A: '<40 sq m', B: '40–69.9 sq m', C: '70–99.9 sq m',
  D: '100–159.9 sq m', E: '≥160 sq m',
};

export function averagePriceRows(rows, period, region) {
  return rowsInReferencePeriod(rows, period)
    .filter(row => row.source_table === '1.2' && row.region === region && Object.hasOwn(SIZE_CLASSES, row.class_name))
    .map(row => ({
      ...row,
      price_per_sq_ft: row.value == null ? null : row.value * SQ_METRES_PER_SQ_FOOT,
      price_unit: 'HKD / sq ft',
      saleable_area: SIZE_CLASSES[row.class_name],
      conversion: 'HKD / sq m × 0.09290304',
    }));
}

export function latestClassPrices(rows) {
  const latest = rows.reduce((date, row) => row.date > date ? row.date : date, '');
  return rows.filter(row => row.date === latest).sort((a, b) => a.class_name.localeCompare(b.class_name));
}
