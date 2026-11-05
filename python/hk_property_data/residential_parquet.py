"""Typed Parquet contract. Imported only when reading or writing data."""
import datetime as dt
import io

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .cloud import CloudDataError
from .residential_schema import COLUMNS, SCHEMA_VERSION


def schema():
    return pa.schema([(name, pa.float64() if name == 'value' else pa.date32() if name == 'date' else pa.string())
                      for name in COLUMNS],
                     metadata={b'hk_property_data.schema_version': str(SCHEMA_VERSION).encode()})


def validate(payload, metric=None):
    try:
        file = pq.ParquetFile(pa.BufferReader(payload), page_checksum_verification=True)
        actual = file.schema_arrow
        expected = schema()
        if len(actual.names) != len(set(actual.names)) or not set(COLUMNS) <= set(actual.names):
            raise CloudDataError('Unsupported residential Parquet columns')
        if any(actual.field(name).type != expected.field(name).type for name in COLUMNS):
            raise CloudDataError('Unsupported residential Parquet column types')
        if (actual.metadata or {}).get(b'hk_property_data.schema_version') != str(SCHEMA_VERSION).encode():
            raise CloudDataError('Unsupported residential Parquet schema version')
        for batch in file.iter_batches(batch_size=4096, columns=COLUMNS):
            for name in COLUMNS:
                if name != 'value' and batch.column(name).null_count:
                    raise CloudDataError('Missing required Parquet field')
            if pc.any(pc.equal(batch.column('metric_id'), '')).as_py():
                raise CloudDataError('Residential record lacks a metric')
            if not pc.all(pc.starts_with(batch.column('source_url'), 'https://')).as_py():
                raise CloudDataError('Residential record lacks a source')
            if not pc.all(pc.fill_null(pc.is_finite(batch.column('value')), True)).as_py():
                raise CloudDataError('Non-finite residential value')
            dates = batch.column('date')
            if not pc.all(pc.and_(pc.greater_equal(dates, dt.date.min), pc.less_equal(dates, dt.date.max))).as_py():
                raise CloudDataError('Invalid residential observation date')
            if metric is not None and not pc.all(pc.equal(batch.column('metric_id'), metric)).as_py():
                raise CloudDataError('Indicator file contains a different metric')
        return pq.read_table(pa.BufferReader(payload), columns=COLUMNS,
                             read_dictionary=[c for c in COLUMNS if c not in ('date','value')],
                             page_checksum_verification=True, use_threads=False)
    except (pa.ArrowException, OSError, ValueError) as exc:
        raise CloudDataError(f'Invalid residential Parquet: {exc}') from exc


def read_rows(table, selected, first, last):
    try:
        mask = pc.and_(pc.greater_equal(table['date'], dt.date.fromisoformat(first)),
                       pc.less_equal(table['date'], dt.date.fromisoformat(last)))
        if selected is not None:
            mask = pc.and_(mask, pc.is_in(table['metric_id'], value_set=pa.array(sorted(selected))))
        filtered = table.filter(mask)
        for batch in filtered.to_batches(max_chunksize=1024):
            for row in batch.to_pylist():
                row['date'] = row['date'].isoformat()
                yield row
    except (pa.ArrowException, OSError, ValueError) as exc:
        raise CloudDataError(f'Could not filter residential Parquet: {exc}') from exc


def table_from_rows(rows):
    clean = []
    for row in rows:
        record = {name: '' if row.get(name) is None else str(row[name]) for name in COLUMNS}
        record['date'] = dt.date.fromisoformat(row['date'])
        record['value'] = row['value']
        clean.append(record)
    return pa.Table.from_pylist(clean, schema=schema())


def write_table(table, path):
    pq.write_table(table, path, compression='zstd', use_dictionary=True, row_group_size=4096,
                   write_page_checksum=True, version='2.6')
