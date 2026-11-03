"""Command-line entry point shared by installed packages and legacy scripts."""
import argparse
import json
from pathlib import Path
import sys
from . import __version__, build_database, build_excel, load_dataset, refresh, validate


def main(argv=None):
    parser = argparse.ArgumentParser(prog='hk-property-data', description='Collect official Hong Kong data and export Excel/SQLite. No AI service is required.')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    commands = parser.add_subparsers(dest='command', required=True)
    collect = commands.add_parser('refresh', help='Fetch official sources, retain history, and generate all exports')
    collect.add_argument('--output', default='data', help='Writable data directory (default: ./data)')
    collect.add_argument('--app', help='Optional dashboard repository to update')
    collect.add_argument('--as-of', help='Observation cutoff YYYY-MM-DD; default today')
    collect.add_argument('--pdf', help='Optional supplied RVD PDF; normally downloads the official latest PDF')
    for name, extension in [('export-excel','xlsx'), ('build-database','sqlite')]:
        command = commands.add_parser(name, help='Build a validated export from a saved JSON snapshot')
        command.add_argument('--dataset', type=Path, default=Path('data/hk_housing_dataset.json'))
        command.add_argument('--output', type=Path, default=Path('data/hk_property_data.xlsx' if extension=='xlsx' else 'data/hk_housing.sqlite'))
    check = commands.add_parser('validate', help='Check the dataset and both generated exports without network access')
    check.add_argument('output', nargs='?', default='data')
    args = parser.parse_args(argv)
    try:
        if args.command == 'refresh':
            return refresh(args.output, app=args.app, as_of=args.as_of, pdf=args.pdf)
        if args.command == 'validate':
            result = validate(args.output)
        else:
            dataset = load_dataset(args.dataset)
            path = (build_excel if args.command == 'export-excel' else build_database)(dataset, args.output)
            result = {'output': str(path), 'monthly_rows': len(dataset['observations'])}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as error:
        print(f'hk-property-data: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
