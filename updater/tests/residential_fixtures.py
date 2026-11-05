"""Independent typed fixtures for the published observation contract."""
import datetime as dt
import io
import pyarrow as pa
import pyarrow.parquet as pq

FIELDS = ['metric_id', 'metric_name', 'period', 'date', 'frequency', 'value', 'unit',
          'status', 'flags', 'source_name', 'source_url', 'source_table', 'source_field',
          'note', 'checked_at', 'source_checked_at']


def payload(rows=None):
    if rows is None:
        rows=[('m3','2026-08-31','0'),('m3','2026-09-30',''),
              ('hibor','2026-09-01','2.5'),('m3','2026-10-31','123.45')]
    schema=pa.schema([(name,pa.float64() if name=='value' else pa.date32() if name=='date' else pa.string()) for name in FIELDS],
                     metadata={b'hk_property_data.schema_version':b'1'})
    records=[]
    for metric,date,value in rows:
        row={name:'' for name in FIELDS}
        row.update(metric_id=metric,metric_name=metric,period=date[:7],date=dt.date.fromisoformat(date),
                   frequency='M',value=None if value=='' else float(value),unit='HKD million',status='Published',
                   source_name='Official',source_url='https://example.org/source',note='Original, source\nnotes',checked_at='2026-11-04')
        records.append(row)
    target=io.BytesIO()
    pq.write_table(pa.Table.from_pylist(records,schema=schema),target,compression='zstd',write_page_checksum=True)
    return target.getvalue()
