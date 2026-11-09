"""Publish the same snapshot's freshness; never timestamp old data as new."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
snapshot = json.loads((ROOT / 'src/data.json').read_text())
target = ROOT / 'dist/data'
target.mkdir(parents=True, exist_ok=True)
status = {
    'market': 'HK', 'checked_at': snapshot['generatedAt'],
    'source_status': snapshot['refresh']['sourceRuns'],
    'errors': snapshot['refresh']['errors'], 'warnings': snapshot['refresh']['warnings'],
    'dataset': snapshot['dataset'],
}
(target / 'refresh_status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'dist/.nojekyll').touch()
print('Wrote dashboard freshness from the displayed dataset:', status['checked_at'])
