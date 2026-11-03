#!/usr/bin/env python3
"""Compatibility entry point for hk_property_data.collectors.hk_commercial_collector."""
import importlib
from pathlib import Path
import runpy
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
if __name__ == '__main__':
    runpy.run_module('hk_property_data.collectors.hk_commercial_collector', run_name='__main__')
else:
    sys.modules[__name__] = importlib.import_module('hk_property_data.collectors.hk_commercial_collector')
