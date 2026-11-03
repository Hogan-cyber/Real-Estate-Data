#!/usr/bin/env python3
"""Compatibility entry point; canonical implementation is hk_property_data.export_excel."""
import importlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
if __name__ == '__main__':
    from hk_property_data.cli import main
    sys.exit(main(['export-excel', *sys.argv[1:]]))
else:
    sys.modules[__name__] = importlib.import_module('hk_property_data.export_excel')
