#!/usr/bin/env python3
"""Measure a fresh GitHub read and repeated exploration in one Python process."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--repeat',type=int,default=10)
    args=parser.parse_args()
    if args.repeat<1:parser.error('--repeat must be positive')
    started=time.perf_counter()
    import hk_property_data as hk
    import_seconds=time.perf_counter()-started
    from hk_property_data import residential
    hk.clear_residential_cache()
    data=hk.Residential()
    with patch.object(residential,'_open_url',wraps=residential._open_url) as network:
        started=time.perf_counter();frame=data.history();cold=time.perf_counter()-started
        first_requests=network.call_count
        tasks={
            'full_dataframe':lambda:data.history(),
            'overview':lambda:data.overview(),
            'two_indicators_dates':lambda:data.history(series=['rvd_1_4_all_classes','hk_mortgage_drawn_count'],start='2025-01',end='2026-09'),
            'records_dates':lambda:hk.fetch_residential(series='rvd_1_4_all_classes',start='2025-01',end='2026-09'),
        }
        timings={}
        for name,task in tasks.items():
            samples=[]
            for _ in range(args.repeat):
                started=time.perf_counter();task();samples.append(time.perf_counter()-started)
            timings[name]={'median_ms':round(statistics.median(samples)*1000,3),'max_ms':round(max(samples)*1000,3)}
        repeated_requests=network.call_count-first_requests
    report={'package_version':hk.__version__,'python':sys.version.split()[0],
            'import_seconds':round(import_seconds,4),'cold_full_dataframe_seconds':round(cold,4),
            'data_generated_at':frame.attrs.get('data_generated_at'),'shape':list(frame.shape),
            'first_network_requests':first_requests,'repeated_network_requests':repeated_requests,
            'repetitions':args.repeat,'warm':timings,'cache':hk.residential_cache_info()}
    text=json.dumps(report,indent=2,default=str);print(text)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text+'\n')
    if repeated_requests:
        raise SystemExit('Repeated exploration unexpectedly accessed the network')


if __name__=='__main__':main()
