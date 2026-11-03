import React from 'react';

export function SourceChecks({refresh = {}, observations = []}) {
  const report = refresh.report ?? {};
  const comparisons = (report.comparisons ?? []).filter(row => row.mismatch_count > 0);
  const differences = comparisons.reduce((sum, row) => sum + row.mismatch_count, 0);
  const confirmed = comparisons.reduce((sum, row) => sum + (row.confirmed_revision_count ?? 0), 0);
  const latestPeriod = metric => observations.filter(row => row.metric_id === metric && row.value != null).reduce((latest,row) => row.period > latest ? row.period : latest, '');
  const totalsPeriod = latestPeriod('hk_residential_sales_count');
  const primaryPeriod = latestPeriod('hk_residential_primary_sales_count');
  const secondaryPeriod = latestPeriod('hk_residential_secondary_sales_count');
  return <section className="housing-source-checks" aria-label="Source checks and comparison notes" data-reviewed-rows>
    {refresh.errors?.length > 0 && <div className="housing-warning"><strong>Source checks requiring attention</strong><ul>{refresh.errors.map(error => <li key={error}>{error}</li>)}</ul></div>}
    {refresh.warnings?.length > 0 && <div className="housing-source-notes"><strong>Source notes</strong><ul>{refresh.warnings.map(note => <li key={note}>{note}</li>)}</ul></div>}
    {totalsPeriod && (totalsPeriod > primaryPeriod || totalsPeriod > secondaryPeriod) && <p className="housing-small">Residential sales totals are available through {totalsPeriod}. Primary sales: {primaryPeriod || 'not available'}; secondary sales: {secondaryPeriod || 'not available'}. Unpublished breakdown values are not estimated.</p>}
    {comparisons.length > 0 && <details className="housing-comparison-details">
      <summary>PDF / CSV comparison · {differences} differences · {confirmed} confirmed revisions</summary>
      <p>PDF edition: {report.edition ?? 'Unknown'}; latest PDF reference month: {report.latest_period ?? 'Unknown'}. Monthly price and rental charts use the official CSV series. The PDF tables preserve the original printed values.</p>
      <p>A confirmed revision must match an earlier observed CSV value and its recorded change to the current CSV value. Unexplained differences remain flagged for review.</p>
      <div className="housing-comparison-scroll"><table><caption>Comparison by official table</caption><thead><tr><th>Table</th><th>Cells checked</th><th>Differences</th><th>Confirmed revisions</th><th>Still to review</th></tr></thead><tbody>{comparisons.map(row => <tr key={row.table_id}><td><a href={row.csv_source} target="_blank" rel="noreferrer">{row.table_id}</a></td><td>{row.compared_cells}</td><td>{row.mismatch_count}</td><td>{row.confirmed_revision_count ?? 0}</td><td>{row.unexplained_mismatch_count ?? row.mismatch_count}</td></tr>)}</tbody></table></div>
      <p>All original values and differences are included in the Excel workbook's Source Checks and PDF Tables sheets. <a href={report.source_url} target="_blank" rel="noreferrer">Open the official PDF</a>.</p>
    </details>}
  </section>;
}
