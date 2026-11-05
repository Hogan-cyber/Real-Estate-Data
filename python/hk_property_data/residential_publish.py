"""Build one typed Parquet snapshot from the same validated export rows."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


from .residential_parquet import table_from_rows, validate, write_table


def export_fast_data(rows, status, directory):
    directory = Path(directory)
    directory.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(row['metric_id'] for row in rows)
    table = table_from_rows(rows)
    table = table.replace_schema_metadata({**(table.schema.metadata or {}),
        b'hk_property_data.generated_at': status['generated_at'].encode(),
        b'hk_property_data.as_of': status['as_of'].encode()})
    with tempfile.TemporaryDirectory(prefix='residential-api-', dir=directory.parent) as temporary:
        staging = Path(temporary)
        full = staging / 'observations.parquet'
        write_table(table, full)
        validate(full.read_bytes())
        manifest = dict(schema_version=status['schema_version'], generated_at=status['generated_at'],
                        observations=len(rows), format='parquet', series=dict(sorted(counts.items())),
                        bytes=full.stat().st_size, sha256=hashlib.sha256(full.read_bytes()).hexdigest())
        (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        (staging / 'collection_status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
        (staging / 'README.md').write_text(
            '# Generated residential data\n\n'
            'Published automatically after successful official-source collection.\n'
            'Python reads typed Parquet; CSV, Excel and SQLite downloads remain in the '
            '[latest Release](https://github.com/Hogan-cyber/Real-Estate-Data/releases/tag/residential-data-latest).\n',
            encoding='utf-8')
        # Only the generated api directory is replaced. Failed validation above
        # leaves the previous snapshot intact; publication uses an atomic Git ref.
        if directory.exists():
            shutil.rmtree(directory)
        shutil.copytree(staging, directory)
    return manifest
