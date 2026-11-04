"""Portable package contract independent of a cloned dashboard working directory."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP / 'python'))


class PackageTest(unittest.TestCase):
    def package(self):
        try:
            return importlib.import_module('hk_property_data')
        except ImportError:
            self.fail('Installable hk_property_data package must exist')

    def test_public_api_and_version(self):
        package = self.package()
        self.assertEqual(package.__version__, '0.2.0')
        for name in ('fetch_dataset', 'fetch_status', 'refresh', 'build_excel', 'build_database', 'load_dataset', 'validate'):
            self.assertTrue(callable(getattr(package, name, None)), name)

    def test_api_refresh_uses_explicit_output_and_retains_warning_status(self):
        package = self.package()
        pipeline = importlib.import_module('hk_property_data.pipeline')
        with patch.object(pipeline, 'run', return_value=2) as run:
            status = package.refresh(output='my data', as_of='2026-11-03')
        self.assertEqual(status, 2)
        args = run.call_args.args[0]
        self.assertEqual(str(args.output), 'my data')
        self.assertIsNone(args.app)
        self.assertEqual(args.as_of, '2026-11-03')

    def test_cli_can_export_from_unrelated_directory(self):
        self.package()
        cli = importlib.import_module('hk_property_data.cli')
        dataset = {'as_of':'2026-11-03','checked_at':'2026-11-03T00:00:00+00:00','observations':[],
                   'pdf_observations':[], 'source_status':[], 'revisions':[], 'errors':[], 'report':{}}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.json'; source.write_text(json.dumps(dataset))
            target = Path(directory) / 'nested' / 'data.xlsx'
            self.assertEqual(cli.main(['export-excel','--dataset',str(source),'--output',str(target)]), 0)
            self.assertTrue(target.read_bytes().startswith(b'PK'))

    def test_import_and_help_have_no_side_effects_in_a_clean_directory(self):
        self.package()
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ, PYTHONPATH=str(APP / 'python'))
            result = subprocess.run([sys.executable, '-m', 'hk_property_data', '--help'], cwd=directory,
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('export-excel', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_cli_default_writes_to_caller_directory_not_install_location(self):
        self.package()
        cli = importlib.import_module('hk_property_data.cli')
        pipeline = importlib.import_module('hk_property_data.pipeline')
        with patch.object(pipeline, 'run', return_value=0) as run:
            self.assertEqual(cli.main(['refresh']), 0)
        self.assertEqual(str(run.call_args.args[0].output), 'data')


if __name__ == '__main__':
    unittest.main()
