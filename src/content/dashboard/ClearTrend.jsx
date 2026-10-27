import React, { useEffect, useRef, useState } from 'react';
import { EvidenceChart, ChartMark, ChartTooltip, useDataApp } from '../../data-app-public.jsx';
import { niceScale, spreadLabels, monthlySegments, TREND_COLORS } from './clear-trend.js';

const month = date => new Date(date).toLocaleDateString('en-GB', { month: 'short', year: '2-digit', timeZone: 'UTC' });
const number = (v, decimals = 1) => v.toLocaleString('en-GB', { maximumFractionDigits: decimals, minimumFractionDigits: decimals });

function ClearPlot({ rows, spec, height, id, interactions }) {
  const ref = useRef(null); const drag = useRef(null); const [width, setWidth] = useState(1000); const [active, setActive] = useState(null);
  useEffect(() => { const node = ref.current; const observer = new ResizeObserver(() => setWidth(node.clientWidth)); observer.observe(node); setWidth(node.clientWidth); return () => observer.disconnect(); }, []);
  const { x = 'date', y, series, colors = {}, legend = {} } = spec;
  const names = [...new Set(rows.map(r => series ? String(r[series]) : y))].sort();
  const selected = interactions.visibleSeries ?? names;
  const visible = names.filter(name => selected.includes(name));
  const color = name => colors[name] || TREND_COLORS[names.indexOf(name) % TREND_COLORS.length];
  const label = name => legend.labels?.[name] || name;
  const dates = [...new Set(rows.map(r => r[x]))].sort();
  const scale = niceScale(rows.filter(r => visible.includes(series ? String(r[series]) : y)).map(r => r[y]), spec.startAtZero);
  const left = 64, right = width - 158, top = 22, bottom = height - 48;
  const first = Date.parse(dates[0]), last = Date.parse(dates.at(-1));
  const px = date => dates.length === 1 ? (left + right) / 2 : left + (Date.parse(date) - first) / (last - first) * (right - left);
  const py = value => bottom - (value - scale.min) / (scale.max - scale.min) * (bottom - top);
  const data = visible.map(name => ({ name, rows: rows.filter(r => (series ? String(r[series]) : y) === name).sort((a, b) => a[x].localeCompare(b[x])) }));
  const hasValues = data.some(group => group.rows.some(row => Number.isFinite(row[y])));
  const ends = spreadLabels(data.flatMap(group => { const row = group.rows.filter(r => Number.isFinite(r[y])).at(-1); return row ? [{ name: group.name, row, x: px(row[x]), y: py(row[y]) }] : []; }), top + 15, bottom - 10, 34);
  const stride = Math.max(1, Math.ceil(dates.length / Math.max(3, Math.floor((right - left) / 100))));
  const ticks = dates.filter((_, i) => i % stride === 0);
  function toggle(name, isolate = false) { interactions.onVisibleSeriesChange(isolate ? [name] : selected.includes(name) ? selected.filter(n => n !== name) : [...selected, name]); }
  return <div className="housing-clear-chart" data-chart-interaction-root data-reviewed-rows>
    <div className="housing-clear-legend" aria-label="Chart legend">{names.map(name => <button type="button" key={name} aria-label={`Toggle ${label(name)}`} aria-pressed={visible.includes(name)} onClick={() => toggle(name)} onDoubleClick={() => toggle(name, true)} onKeyDown={event => { if (event.shiftKey && event.key === 'Enter') { event.preventDefault(); toggle(name, true); } }}><i style={{ background: color(name) }} />{label(name)}</button>)}</div>
    <div className="housing-chart-scroll" tabIndex={0} aria-label="Scrollable chart">
      <div className="housing-chart-canvas" ref={ref} style={{ height }}>
        <svg width={width} height={height} role="img" aria-label={`${spec.y}; ${month(dates[0])} to ${month(dates.at(-1))}`} data-temporal-axis-start={dates[0]} data-temporal-axis-end={dates.at(-1)}>
          {hasValues && scale.ticks.map(v => <g key={v}><line x1={left} x2={right} y1={py(v)} y2={py(v)} stroke="var(--border)" /><text x={left - 12} y={py(v) + 4} textAnchor="end" fill="var(--secondary)" fontSize="13">{number(v, v % 1 === 0 ? 0 : 1)}</text></g>)}
          {ticks.map(date => <text key={date} x={px(date)} y={bottom + 27} textAnchor="middle" fill="var(--secondary)" fontSize="13">{month(date)}</text>)}
          {!hasValues && <text x={(left+right)/2} y={(top+bottom)/2} textAnchor="middle" fill="var(--secondary)" fontSize="14">{visible.length ? 'No published values in this period' : 'Select a series in the legend'}</text>}
          {data.map(group => <g key={group.name} data-series={group.name}>{monthlySegments(group.rows, y).map((segment, i) => segment.length === 1 ? <circle key={i} cx={px(segment[0][x])} cy={py(segment[0][y])} r="3" fill={color(group.name)} /> : <polyline key={i} data-series-path={group.name} points={segment.map(row => `${px(row[x])},${py(row[y])}`).join(' ')} fill="none" stroke={color(group.name)} strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round" />)}</g>)}
          {active && <line x1={px(active)} x2={px(active)} y1={top} y2={bottom} stroke="var(--secondary)" strokeDasharray="3 4" />}
          {ends.map(end => <g key={end.name} data-end-label={end.name}><circle cx={end.x} cy={end.y} r="3" fill={color(end.name)} /><path d={`M${end.x + 5},${end.y} L${right + 13},${end.labelY} L${right + 23},${end.labelY}`} fill="none" stroke={color(end.name)} strokeWidth="1" opacity=".65" /><text x={right + 29} y={end.labelY - 3} fill={color(end.name)} fontSize="14" fontWeight="650">{series && end.name.length <= 3 ? end.name + '  ' : ''}{number(end.row[y], spec.valueDecimals ?? 1)}</text><text x={right + 29} y={end.labelY + 13} fill="var(--secondary)" fontSize="11">{month(end.row[x])}{end.row.flags?.includes('P') ? ' · P' : ''}{end.row.flags?.includes('X') ? ' · X' : end.row.flags?.includes('Y') ? ' · Y' : end.row.flags?.includes('Z') ? ' · Z' : ''}</text></g>)}
        </svg>
        {dates.map((date, i) => {
          const selectedRows = rows.filter(r => r[x] === date && visible.includes(series ? String(r[series]) : y));
          const start = i ? (px(dates[i - 1]) + px(date)) / 2 : left, end = i < dates.length - 1 ? (px(date) + px(dates[i + 1])) / 2 : right;
          return <ChartMark key={date} className="housing-trend-hit" style={{ left: start, width: Math.max(1, end - start), top, height: bottom - top }} aria-label={`${month(date)}. View values`} context={{ kind: 'chart', chartType: 'line', label: month(date), row: selectedRows[0], value: selectedRows[0]?.[y] }} onPointerDown={event => { if (event.pointerType === 'mouse') drag.current = date; }} onPointerUp={() => { if (drag.current && drag.current !== date) { const [start,end]=[drag.current,date].sort(); interactions.onZoomChange({start,end}); } drag.current=null; }} onPointerEnter={() => setActive(date)} onPointerLeave={() => setActive(null)} onFocus={() => setActive(date)} onBlur={() => setActive(null)} tooltip={<ChartTooltip active label={`${month(date)} · ${y}`} details={selectedRows.map(row => ({ label: label(series ? String(row[series]) : y), value: Number.isFinite(row[y]) ? number(row[y], spec.valueDecimals ?? 1) + (row.flags ? ` (${row.flags})` : '') : 'Not published' }))} />} />;
        })}
      </div>
    </div>
    <div className="housing-chart-footnote">{dates.length ? `${month(dates[0])} – ${month(dates.at(-1))} · Monthly observations` : ''} · Hover or focus for values; drag to zoom. <span className="housing-mobile-note">Swipe the chart to see the full timeline.</span></div>
  </div>;
}

export function ClearTrend({ id, rows, sourceRows = rows, spec, height = 440, ...props }) {
  const shell = useDataApp();
  const interactions = shell.chartProps(id);
  return <EvidenceChart {...props} id={id} rows={rows} sourceRows={sourceRows} spec={spec} height={height}
    renderPlot={(plot, chart) => !rows.length || shell.chartOverrides[id] || interactions.zoomRange || chart.type !== 'line' ? plot : <ClearPlot rows={rows} spec={chart} height={height} id={id} interactions={interactions} />} />;
}
