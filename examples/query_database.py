#!/usr/bin/env python3
"""Download and query Hong Kong property data. Python 3.10+; no pip install needed."""
import argparse
import csv
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import urllib.request

DATABASE_URL = 'https://hogan-cyber.github.io/Real-Estate-Data/data/hk_housing.sqlite'


def open_database(path):
    """Open a downloaded snapshot read-only; never silently create an empty file."""
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def download_database(destination):
    """Fetch the latest published snapshot, validate it, then replace the local file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(DATABASE_URL + '?download=' + str(time.time_ns()),
                                     headers={'User-Agent': 'HKPropertyMonitor/2', 'Cache-Control': 'no-cache'})
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.housing-download-', suffix='.sqlite', delete=False) as file:
        temporary = Path(file.name)
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open('wb') as file:
            while chunk := response.read(1024 * 1024):
                file.write(chunk)
        with temporary.open('rb') as file:
            if file.read(16) != b'SQLite format 3\x00':
                raise ValueError('Download was not a SQLite database; local data was retained')
        db = open_database(temporary)
        try:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Incomplete or corrupt database download')
            if db.execute('PRAGMA user_version').fetchone()[0] != 2:
                raise ValueError('Database schema changed; download the matching query example')
            info = db.execute('SELECT market,monthly_rows,pdf_cells,source_count FROM dataset_info WHERE id=1').fetchone()
            if not info or info['market'] != 'HK':
                raise ValueError('Unexpected database identity')
            for table, count in [('observations', info['monthly_rows']), ('pdf_observations', info['pdf_cells']), ('sources', info['source_count'])]:
                if db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] != count:
                    raise ValueError('Incomplete database: ' + table)
        finally:
            db.close()
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def query_series(db, metric_id, start=None, end=None):
    """Return one series in original units. Months are inclusive YYYY-MM strings."""
    conditions, parameters = ['metric_id = ?'], [metric_id]
    if start:
        conditions.append('period >= ?')
        parameters.append(start)
    if end:
        conditions.append('period <= ?')
        parameters.append(end)
    sql = 'SELECT * FROM observations WHERE ' + ' AND '.join(conditions) + ' ORDER BY period'
    return [dict(row) for row in db.execute(sql, parameters)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=Path('hk_housing.sqlite'))
    parser.add_argument('--download', action='store_true', help='Replace the local file with the latest published database')
    parser.add_argument('--list-metrics', action='store_true', help='List series identifiers and coverage instead of observations')
    parser.add_argument('--metric', default='rvd_1_4_all_classes')
    parser.add_argument('--start', help='First month, e.g. 2020-01')
    parser.add_argument('--end', help='Last month, e.g. 2025-12')
    parser.add_argument('--format', choices=['json', 'csv'], default='json')
    args = parser.parse_args()
    if args.download:
        download_database(args.database)
    db = open_database(args.database)
    try:
        info = dict(db.execute('SELECT checked_at,errors_json FROM dataset_info').fetchone())
        print('Sources checked: ' + str(info['checked_at']), file=sys.stderr)
        warnings = json.loads(info['errors_json'])
        if warnings:
            print('Source warnings: ' + '; '.join(warnings), file=sys.stderr)
        rows = ([dict(r) for r in db.execute('SELECT * FROM metric_catalog ORDER BY metric_id')]
                if args.list_metrics else query_series(db, args.metric, args.start, args.end))
        if args.format == 'csv':
            fields = list(rows[0]) if rows else ['metric_id', 'period', 'value', 'unit']
            writer = csv.DictWriter(sys.stdout, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        else:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == '__main__':
    main()
