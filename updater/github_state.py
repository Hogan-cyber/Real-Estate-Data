"""Called only by the GitHub workflow after a validated data refresh."""
import json, os
from pathlib import Path
if os.environ.get('GITHUB_ACTIONS') != 'true':
    raise SystemExit('Run this state marker only within GitHub Actions.')
p=Path('src/data.json');s=json.loads(p.read_text())
s['refresh']['automationEnabled']=True
s['refresh']['automationStatus']='GitHub Actions monthly workflow configured; this snapshot was built in GitHub Actions.'
s['refresh']['runUrl']='https://github.com/'+os.environ['GITHUB_REPOSITORY']+'/actions/runs/'+os.environ['GITHUB_RUN_ID']
p.write_text(json.dumps(s,ensure_ascii=False,indent=2))
