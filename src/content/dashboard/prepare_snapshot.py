"""Bind the existing residential dataset to the dashboard, without recalculation.

Run from the repository root:
  python src/content/dashboard/prepare_snapshot.py --published
  python src/content/dashboard/prepare_snapshot.py --input outputs/residential_2002
This is a reader/exporter. It does not call collectors or change source datasets.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
from urllib.request import Request, urlopen

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'python'))
from hk_property_data.simple.export import sheet_for
from english_labels import english_name, english_definition

REPO = 'Hogan-cyber/Real-Estate-Data'
MODEL_URL = f'https://github.com/{REPO}/blob/main/docs/MORTGAGE_ESTIMATES.md'


def get_bytes(url):
    headers = {'User-Agent': 'hk-property-dashboard/1.0'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token and url.startswith('https://api.github.com/'):
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        return response.read()


def build_snapshot(rows, status, original, source_url, checksum):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['metric_id']].append(row)
    catalogue = []
    for metric_id, records in sorted(grouped.items()):
        sample = records[-1]
        observed = [r for r in records if r['value'] is not None]
        group = sheet_for(sample)
        catalogue.append({
            'metric_id': metric_id, 'metric_name': sample['metric_name'],
            'unit': sample['unit'], 'frequency': sample['frequency'],
            'group': group, 'page': 'mortgage' if group.startswith(('Mortgage', 'Negative')) else 'overview',
            'display_name': english_name(sample), 'description': english_definition(sample), 'observations': len(records),
            'available': len(observed), 'first_date': min((r['date'] for r in observed), default=None),
            'last_date': max((r['date'] for r in observed), default=None),
            'source_name': sample['source_name'], 'source_url': sample['source_url'],
        })
    dates = [row['date'] for row in rows]
    checked = status['generated_at']
    snapshot = {key: original[key] for key in ('id', 'title', 'legacyPresentationTitle') if key in original}
    snapshot.update({
        'surface': 'dashboard', 'standalone': True, 'status': 'reviewed', 'buildStatus': 'updating',
        'asOf': status['as_of'], 'generatedAt': checked,
        'exportPreferences': original.get('exportPreferences', {'selected': None, 'destinations': []}),
        'filters': [{'id': 'date', 'field': 'date', 'label': 'Reference period', 'mode': 'through',
                     'defaultValue': f'2020-01-01..{max(dates)}', 'queryIds': ['observations']}],
        'refresh': {'cadence': 'Daily at 18:00', 'timezone': 'Asia/Hong_Kong',
                    'instruction': 'RESIDENTIAL_DATA.md', 'automationEnabled': True,
                    'errors': status.get('errors', []), 'warnings': status.get('rate_release_notes', []),
                    'sourceRuns': status.get('source_runs', [])},
        'dataset': {'url': source_url, 'sha256': checksum, 'observations': len(rows),
                    'indicators': len(catalogue), 'startDate': min(dates), 'endDate': max(dates)},
        'queries': {
            'observations': {'rows': rows, 'source': {
                'label': 'Published Hong Kong residential dataset', 'url': source_url,
                'executedAt': checked, 'coverage': {'startDate': min(dates), 'endDate': max(dates)},
                'evidenceFlow': [
                    {'title': 'Published dataset', 'detail': f'{source_url}; SHA-256 {checksum}. All 16 observation fields preserved.'},
                    {'title': 'Dashboard binding', 'detail': 'src/content/dashboard/prepare_snapshot.py reads Parquet. Dates are serialized as ISO strings. No values are recalculated, resampled, interpolated, filled, clipped or converted.'},
                    {'title': 'Selection', 'detail': 'Date and indicator filters select original records. Category comparisons use the latest date with observations for every selected series within the chosen range.'},
                ],
                'metricDefinitions': [
                    {'label': 'Reference dates and units', 'definition': 'Each series retains the published reference date, frequency, value, unit, status and source. Missing observations remain missing. Monthly, quarterly, annual, daily and effective-date records are separate.'},
                    {'label': 'Existing mortgage estimates', 'definition': 'The six total / bank purchase / money-lender residual series are the existing published monthly estimates. Residential allocation uses the LR residential sales share; bank purchase drawdowns use the approval refinancing share. Amount scenarios assume the bank purchase average loan size. The dashboard performs no new estimate. Negative residuals remain negative.',
                     'componentIds': ['res26-model-count', 'res26-model-amount']},
                ],
                'caveats': [
                    'Registration documents, bank approvals and bank drawdowns have different populations and timing; they are not a loan-level reconciliation.',
                    'Existing money-lender series are model residuals, not observed pure licensed money-lender lending. LR refinancing is not removed.',
                    'Each row links to the original publisher; source-checked dates differ from reference dates. An unavailable source value is never zero.',
                ],
            }, 'methods': [{'language': 'text', 'code': 'python src/content/dashboard/prepare_snapshot.py --published'}]},
            'catalogue': {'rows': catalogue, 'source': {
                'label': 'Complete published indicator dictionary',
                'url': f'https://github.com/{REPO}/blob/residential-data/INDICATORS.md',
                'executedAt': checked,
                'evidenceFlow': [{'title': 'Dictionary', 'detail': 'Groups match the published Excel. English display labels describe the original metrics without changing source fields or values. Counts and coverage describe existing records.'}],
            }},
        },
    })
    if not snapshot.get('id'):
        raise ValueError('Existing dashboard ID is required; never create a new identity on refresh.')
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published', action='store_true')
    parser.add_argument('--build-status', choices=['updating', 'complete'], default='updating')
    parser.add_argument('--collection-outcome', default='auto')
    parser.add_argument('--collection-run-url', default='')
    parser.add_argument('--published-ref', help='Optional immutable commit of the residential-data branch')
    parser.add_argument('--input', type=Path, default=ROOT / 'outputs/residential_2002')
    parser.add_argument('--output', type=Path, default=ROOT / 'src/data.json')
    args = parser.parse_args()
    if args.published:
        ref = args.published_ref or subprocess.check_output(
            ['git', 'ls-remote', '--exit-code', f'https://github.com/{REPO}.git', 'refs/heads/residential-data'],
            text=True, timeout=60).split()[0]
        if len(ref) != 40 or any(char not in '0123456789abcdef' for char in ref):
            raise ValueError('Expected an immutable 40-character Git commit.')
        base = f'https://raw.githubusercontent.com/{REPO}/{ref}'
        payload = get_bytes(base + '/observations.parquet')
        status = json.loads(get_bytes(base + '/collection_status.json'))
        source_url = base + '/observations.parquet'
    else:
        payload = (args.input / 'observations.parquet').read_bytes()
        status = json.loads((args.input / 'collection_status.json').read_text())
        source_url = f'https://raw.githubusercontent.com/{REPO}/residential-data/observations.parquet'
    rows = pq.read_table(io.BytesIO(payload)).to_pylist()
    for row in rows:
        for key, value in row.items():
            if isinstance(value, (date, datetime)):
                row[key] = value.isoformat()
    if len(rows) != status['observations'] or len({r['metric_id'] for r in rows}) != status['series']:
        raise ValueError('Dataset and collection status do not describe the same snapshot.')
    original = json.loads((ROOT / 'src/data.json').read_text())
    snapshot = build_snapshot(rows, status, original, source_url, hashlib.sha256(payload).hexdigest())
    snapshot['buildStatus'] = args.build_status
    if args.collection_outcome == 'auto':
        try:
            runs = json.loads(get_bytes(f'https://api.github.com/repos/{REPO}/actions/workflows/residential-data.yml/runs?branch=main&status=completed&per_page=1'))['workflow_runs']
            if not runs:
                raise ValueError('No completed collector run is available.')
            args.collection_outcome = runs[0]['conclusion']
            args.collection_run_url = runs[0]['html_url']
            snapshot['refresh']['latestCollectionRun'] = {'id': runs[0]['id'], 'outcome': args.collection_outcome, 'url': args.collection_run_url}
        except Exception:
            # Keep current dataset errors. The checkout snapshot is not the last deployment.
            args.collection_outcome = ''
            snapshot['refresh']['warnings'].append('Latest collector workflow status could not be verified. The dataset retains its actual publication time.')
    if args.collection_outcome and args.collection_outcome != 'success':
        snapshot['refresh']['errors'] = [*snapshot['refresh']['errors'],
            f'Latest collection ended with status {args.collection_outcome}. The previous valid published dataset is retained. Run: {args.collection_run_url}']
    temporary = args.output.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')
    temporary.replace(args.output)
    print(json.dumps({'output': str(args.output), **snapshot['dataset'], 'generatedAt': snapshot['generatedAt']}))


if __name__ == '__main__':
    main()
