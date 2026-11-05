"""Shared residential observation contract for publishing and reading."""

SCHEMA_VERSION = 1
COLUMNS = ['metric_id', 'metric_name', 'period', 'date', 'frequency', 'value', 'unit',
           'status', 'flags', 'source_name', 'source_url', 'source_table', 'source_field',
           'note', 'checked_at', 'source_checked_at']


def populate_database(connection, rows):
    """Create the observation table from any iterable without copying it to a list."""
    columns = ', '.join(f'"{c}" {"REAL" if c == "value" else "TEXT"}' for c in COLUMNS)
    connection.execute('PRAGMA temp_store=MEMORY')
    connection.execute(f'CREATE TABLE observations ({columns}, PRIMARY KEY (metric_id, period, frequency))')
    with connection:
        connection.executemany('INSERT INTO observations VALUES (' + ','.join('?' for _ in COLUMNS) + ')',
                               (tuple(row.get(c) for c in COLUMNS) for row in rows))
        connection.execute('CREATE INDEX observations_metric_date ON observations(metric_id, date)')
