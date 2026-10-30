"""Build the downloadable SQLite snapshot from the reviewed dataset, without network access."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import tempfile

SCHEMA_VERSION = 2
# Keep the original seven columns first for existing consumers. New columns expose
# source fields directly; payload remains the complete, unchanged source record.
OBSERVATION_COLUMNS = {
    'metric_id': 'TEXT NOT NULL', 'period': 'TEXT NOT NULL', 'date': 'TEXT NOT NULL',
    'value': 'REAL', 'unit': 'TEXT NOT NULL', 'source_id': 'TEXT NOT NULL', 'payload': 'TEXT NOT NULL',
    **{name: 'TEXT' for name in (
        'market', 'category', 'metric_name', 'frequency', 'class_name', 'region',
        'property_type', 'measure', 'grade', 'area_basis', 'source_name', 'source',
        'source_url', 'source_table', 'source_field', 'source_period', 'source_frequency',
        'flags', 'status', 'missing_reason', 'seasonal_adjustment', 'observation_frequency',
        'freshness_basis', 'fetch_mode', 'checked_at', 'published_date', 'scope', 'note',
    )},
    'small_sample': 'INTEGER',
}

SCHEMA = """
CREATE TABLE dataset_info (
    id INTEGER PRIMARY KEY CHECK (id=1), schema_version INTEGER NOT NULL,
    market TEXT, as_of TEXT, checked_at TEXT, monthly_rows INTEGER,
    pdf_cells INTEGER, source_count INTEGER, errors_json TEXT NOT NULL, report_json TEXT NOT NULL
);
CREATE TABLE sources (
    source_id TEXT PRIMARY KEY, source_name TEXT, status TEXT, checked_at TEXT,
    last_success TEXT, latest_period TEXT, row_count INTEGER, source_url TEXT,
    change_summary TEXT, payload TEXT NOT NULL
);
CREATE TABLE pdf_observations (
    id INTEGER PRIMARY KEY, table_id TEXT NOT NULL, pdf_page INTEGER, period TEXT,
    frequency TEXT, row_label TEXT, column_name TEXT, value REAL, unit TEXT,
    observation_kind TEXT, raw_cell TEXT, provisional INTEGER,
    fewer_than_20_transactions INTEGER, missing INTEGER, source_pdf TEXT,
    source_edition TEXT, payload TEXT NOT NULL
);
CREATE TABLE revisions (
    id INTEGER PRIMARY KEY, metric_id TEXT NOT NULL, period TEXT NOT NULL,
    old_value REAL, new_value REAL, detected_at TEXT, payload TEXT NOT NULL
);
CREATE TABLE pdf_csv_checks (
    table_id TEXT PRIMARY KEY, status TEXT, csv_source TEXT, csv_sha256 TEXT,
    compared_cells INTEGER, mismatch_count INTEGER, payload TEXT NOT NULL
);
CREATE TABLE pdf_csv_differences (
    id INTEGER PRIMARY KEY, table_id TEXT REFERENCES pdf_csv_checks(table_id),
    period TEXT, column_name TEXT, pdf_value REAL, csv_value REAL, payload TEXT NOT NULL
);
"""

VIEWS_AND_INDEXES = """
CREATE INDEX observations_source_period ON observations(source_id, period);
CREATE INDEX observations_category_region_class ON observations(category, region, class_name, period);
CREATE INDEX observations_property_period ON observations(property_type, source_table, period);
CREATE INDEX observations_period ON observations(period);
CREATE INDEX pdf_table_period ON pdf_observations(table_id, frequency, period);
CREATE INDEX revisions_metric_period ON revisions(metric_id, period);
CREATE VIEW latest_observations AS
    SELECT o.* FROM observations o JOIN
    (SELECT metric_id, MAX(period) AS period FROM observations GROUP BY metric_id) latest
    USING (metric_id, period);
CREATE VIEW metric_catalog AS
    SELECT latest.metric_id, latest.metric_name, latest.market, latest.category,
           latest.property_type, latest.measure, latest.class_name, latest.grade,
           latest.region, latest.area_basis, latest.unit, latest.frequency,
           latest.observation_frequency, latest.source_id, latest.source_table,
           latest.source_url, latest.value AS latest_value, latest.status AS observation_status,
           history.first_period, history.last_period, history.observation_count, history.non_null_count
    FROM latest_observations latest JOIN (
        SELECT metric_id, MIN(period) AS first_period, MAX(period) AS last_period,
               COUNT(*) AS observation_count, COUNT(value) AS non_null_count
        FROM observations GROUP BY metric_id
    ) history USING (metric_id);
CREATE VIEW residential_sale_prices AS
    SELECT metric_id, period, date, region, class_name, value AS price_hkd_per_sqm,
           value * 0.09290304 AS price_hkd_per_sqft, flags, small_sample, status,
           source_id, source_url
    FROM observations WHERE source_id='rvd_1.2' AND unit='HKD / sq m';
"""


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _insert_records(db, table, fields, rows, renamed=None):
    """Identifiers are module-owned constants; every source value is bound."""
    renamed = renamed or {}
    names = ','.join('"' + name + '"' for name in fields)
    placeholders = ','.join('?' for _ in fields)
    db.executemany(f'INSERT INTO {table} ({names}) VALUES ({placeholders})', (
        tuple(_json(row) if name == 'payload' else row.get(renamed.get(name, name)) for name in fields)
        for row in rows
    ))


def validate_database(db, dataset):
    """Check database integrity and lossless monthly values before publication."""
    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('SQLite integrity check failed')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Database source references are invalid')
    expected_counts = {
        'observations': len(dataset['observations']),
        'pdf_observations': len(dataset.get('pdf_observations', [])),
        'sources': len(dataset.get('source_status', [])),
        'revisions': len(dataset.get('revisions', [])),
        'pdf_csv_checks': len(dataset.get('report', {}).get('comparisons', [])),
        'pdf_csv_differences': sum(len(c.get('mismatches', [])) for c in dataset.get('report', {}).get('comparisons', [])),
    }
    for table, count in expected_counts.items():
        if db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] != count:
            raise ValueError(f'Row count mismatch: {table}')
    expected = sorted((r['metric_id'], r['period'], r['value'], r['unit'], r['source_id']) for r in dataset['observations'])
    actual = db.execute('SELECT metric_id,period,value,unit,source_id FROM observations ORDER BY metric_id,period').fetchall()
    if [tuple(row) for row in actual] != expected:
        raise ValueError('SQLite values differ from the dataset')
    if db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION:
        raise ValueError('Unexpected database schema version')


def build_database(dataset, destination):
    """Atomically replace destination after a complete valid build; preserve it on error."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.housing-', suffix='.sqlite', delete=False) as f:
        temporary = Path(f.name)
    db = None
    try:
        db = sqlite3.connect(temporary)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
        db.executescript(SCHEMA)
        columns = ','.join(f'"{name}" {kind}' for name, kind in OBSERVATION_COLUMNS.items())
        db.execute(f'CREATE TABLE observations ({columns}, PRIMARY KEY(metric_id,period), FOREIGN KEY(source_id) REFERENCES sources(source_id))')
        _insert_records(db, 'sources', ['source_id','source_name','status','checked_at','last_success','latest_period','row_count','source_url','change_summary','payload'], dataset.get('source_status', []), {'row_count':'rows'})
        _insert_records(db, 'observations', list(OBSERVATION_COLUMNS), dataset['observations'])
        _insert_records(db, 'pdf_observations', ['table_id','pdf_page','period','frequency','row_label','column_name','value','unit','observation_kind','raw_cell','provisional','fewer_than_20_transactions','missing','source_pdf','source_edition','payload'], dataset.get('pdf_observations', []), {'column_name':'column'})
        _insert_records(db, 'revisions', ['metric_id','period','old_value','new_value','detected_at','payload'], dataset.get('revisions', []), {'old_value':'old','new_value':'new'})
        checks = dataset.get('report', {}).get('comparisons', [])
        _insert_records(db, 'pdf_csv_checks', ['table_id','status','csv_source','csv_sha256','compared_cells','mismatch_count','payload'], checks)
        for check in checks:
            differences = [dict(row, table_id=check['table_id']) for row in check.get('mismatches', [])]
            _insert_records(db, 'pdf_csv_differences', ['table_id','period','column_name','pdf_value','csv_value','payload'], differences, {'column_name':'column','pdf_value':'pdf','csv_value':'csv'})
        db.execute('INSERT INTO dataset_info VALUES (1,?,?,?,?,?,?,?,?,?)', (
            SCHEMA_VERSION, dataset.get('market'), dataset.get('as_of'), dataset.get('checked_at'),
            len(dataset['observations']), len(dataset.get('pdf_observations', [])), len(dataset.get('source_status', [])),
            _json(dataset.get('errors', [])), _json(dataset.get('report', {})),
        ))
        db.executescript(VIEWS_AND_INDEXES)
        db.commit()
        validate_database(db, dataset)
        db.close()
        db = None
        temporary.replace(destination)
    finally:
        if db is not None:
            db.close()
        temporary.unlink(missing_ok=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=Path('data/hk_housing_dataset.json'))
    parser.add_argument('--output', type=Path, default=Path('data/hk_housing.sqlite'))
    args = parser.parse_args()
    path = build_database(json.loads(args.dataset.read_text()), args.output)
    print(_json({'database': str(path), 'schema_version': SCHEMA_VERSION, 'bytes': path.stat().st_size}))
