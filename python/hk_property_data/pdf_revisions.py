"""Explain PDF/CSV differences only through independently collected CSV revisions."""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import re


def _pdf_column(row):
    column = row['column'].replace(' | ', ' ').replace('N.T.', 'New Territories')
    if row['table_id'] == '1.5' and not column.startswith('Overall'):
        column = 'Classes ' + column
    return column


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def _revision_chain(records, old, new, checked_at):
    """Trace backwards through strictly older revisions, refusing circular paths."""
    if old is None or new is None or old == new:
        return []
    cutoff = _timestamp(checked_at) or datetime.now(timezone.utc)
    ordered = sorted(((stamp, r) for r in records
                      if (stamp := _timestamp(r.get('detected_at'))) is not None
                      and stamp <= cutoff), key=lambda item: item[0], reverse=True)
    value, seen, chain, last = new, {new}, [], None
    for stamp, record in ordered:
        if last is not None and stamp >= last:
            continue
        if record.get('new') != value or record.get('old') is None:
            continue
        previous = record['old']
        if previous in seen:
            return []
        chain.append({k: record[k] for k in ('metric_id', 'period', 'old', 'new', 'detected_at')})
        if previous == old:
            return list(reversed(chain))
        seen.add(previous)
        value, last = previous, stamp
    return []


def resolve_pdf_revisions(comparisons, pdf_rows, observations, revisions,
                          verified_sources, checked_at=None):
    """Return annotated copies; never change original PDF cells or comparison values."""
    result = deepcopy(comparisons)
    pdf = {(r['table_id'], r['period'], _pdf_column(r)): r
           for r in pdf_rows if r.get('frequency') == 'monthly'}
    current = {(r['metric_id'], r['period']): r for r in observations}
    history = defaultdict(list)
    for record in revisions:
        history[(record.get('metric_id'), record.get('period'))].append(record)
    for comparison in result:
        table = comparison.get('table_id')
        differences = comparison.get('mismatches', [])
        structurally_valid = (comparison.get('mismatch_count') == len(differences)
                              and comparison.get('compared_cells', 0) >= len(differences))
        confirmed = 0
        for difference in differences:
            # A previous classification must be proved again against this refresh.
            difference.pop('resolution', None)
            difference.pop('revision_evidence', None)
            column, period = difference.get('column'), difference.get('period')
            if not isinstance(table, str) or not isinstance(column, str):
                continue
            metric = 'rvd_' + table.replace('.', '_') + '_' + re.sub('[^a-z0-9]+', '_', column.lower()).strip('_')
            original, latest = pdf.get((table, period, column)), current.get((metric, period))
            source = 'rvd_' + table
            if not (structurally_valid and original and latest
                    and original.get('provisional') is True
                    and original.get('value') == difference.get('pdf')
                    and source in verified_sources and latest.get('source_id') == source
                    and latest.get('source_table') == table and latest.get('source_field') == column
                    and latest.get('fetch_mode') == 'automatic_csv'
                    and latest.get('status') != 'stale_cache'
                    and latest.get('value') == difference.get('csv')):
                continue
            records = [r for r in history[(metric, period)]
                       if r.get('source_id', source) == source]
            chain = _revision_chain(records, difference['pdf'], difference['csv'], checked_at)
            if chain:
                difference.update(resolution='recorded_csv_revision', revision_evidence=chain)
                confirmed += 1
        comparison['confirmed_revision_count'] = confirmed
        comparison['unexplained_mismatch_count'] = len(differences) - confirmed
        if differences:
            comparison['status'] = 'revisions_confirmed' if confirmed == len(differences) else 'review'
    return result
