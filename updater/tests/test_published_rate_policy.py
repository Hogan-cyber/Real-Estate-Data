"""Published monthly rates survive refresh; retired calculations cannot return."""
import argparse
import calendar
import copy
from contextlib import ExitStack, redirect_stdout
import datetime as dt
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data import pipeline
from hk_property_data.collectors import hk_macro_collector as macro
from hk_property_data.database import validate_database
from hk_property_data.export_excel import validate_excel, _sheet_rows, SHEETS, HEADER_ROW

RATE_IDS = {'hk_prime_rate_hsbc', 'hk_hibor_1m', 'hk_hibor_3m'}


def observation(metric, period, value, source, **fields):
    year, month = map(int, period.split('-'))
    return dict(market='HK', metric_id=metric, metric_name=metric, period=period,
                date=f'{period}-{calendar.monthrange(year, month)[1]:02}', value=value,
                unit='1999=100', frequency='M', source_id=source,
                source_name='Rating and Valuation Department',
                source_url='https://www.rvd.gov.hk/datagovhk/1.4M.csv',
                source_table='1.4', source_field='All Classes',
                status='Published', fetch_mode='automatic_csv', **fields)


class PublishedRatePolicyTests(unittest.TestCase):
    def run_refresh(self, *, storage='saved', offline=False, october_published=False,
                    only_calculated=False):
        prices = [observation('rvd_1_4_all_classes', f'{year}-{month:02}', 300, 'rvd_1.4')
                  for year in (2024, 2025) for month in range(1, 13)]
        sales = observation('hk_residential_sales_count', '2026-10', 4512, 'landreg')
        mortgage = observation('hk_mortgage_applications', '2026-09', 7560, 'hkma')
        # A calculated non-rate observation must not be removed by a rate-only policy.
        other = dict(observation('non_rate_comparison', '2026-10', 42, 'landreg'), status='Calculated')
        prime = macro.parse_records('hkma_prime', [dict(end_of_month='2026-09', best_lending_rate=5.0)], '2026-11-03')
        hibor = macro.parse_records('hkma_hibor', [dict(end_of_month='2026-09', ir_1m=2.904789090909091, ir_3m=3.10578)], '2026-11-03')
        older = dict(prime[0], period='2026-08', date='2026-08-31')
        calculated = [dict(row, period='2026-10', date='2026-10-31', status='Calculated',
                           fetch_mode='automatic_derived' if row['source_id']=='hkma_prime' else 'automatic_html_calculated',
                           observation_basis='Calculated monthly average', flags='calculated')
                      for row in prime + hibor]
        # A legacy mislabeled status must not conceal a known calculated fetch mode.
        calculated[-1].update(status='Published', fetch_mode='automatic_api_calculated')
        pdf = [dict(table_id='1.4', period='2025-12', frequency='monthly', column='All Classes',
                    value=300, provisional=False, source_pdf='https://www.rvd.gov.hk/doc/en/statistics/full.pdf',
                    pdf_page=8, unit='1999=100', raw_cell='300')]
        history = [dict(metric_id='rvd_1_4_all_classes', period='2025-12', old=299, new=300,
                        detected_at='2026-01-01T00:00:00+00:00')]
        previous = dict(observations=prices+[sales,mortgage,other]+calculated+([] if only_calculated else [older]+prime+hibor),
                        pdf_observations=pdf, revisions=history,
                        report={'status':'Extracted and checked','comparisons':[]},
                        source_status=[dict(source_id=source, status='Verified', latest_period='2026-10',
                                            last_success='2026-11-02T10:00:00+00:00')
                                       for source in ('hkma_prime','hkma_hibor')])
        fresh = {'hkma_prime':copy.deepcopy(prime), 'hkma_hibor':copy.deepcopy(hibor)}
        if october_published:
            fresh['hkma_prime'] += macro.parse_records('hkma_prime', [dict(end_of_month='2026-10',best_lending_rate=5.01)], '2026-11-03')

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            folder = Path(directory); out = folder/'data'; app = folder/'app'
            if storage == 'saved':
                pipeline.save(out/'hk_housing_dataset.json', previous)
                app_arg = None
            else:
                pipeline.save(app/'src/data.json', dict(
                    queries={'observations':{'rows':previous['observations']},'pdf':{'rows':pdf},'status':{'rows':previous['source_status']}},
                    refresh={'report':previous['report'],'revisions':history}))
                app_arg = app
            archive = out/'cache/macro/hkma_hibor_daily_supplement.json'
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(b'Historical calculation evidence; retain unchanged')

            def collect(source, *_):
                if offline:
                    raise OSError('Official API and workbook unavailable')
                return copy.deepcopy(fresh[source])

            def extract(command, **kwargs):
                target = Path(command[command.index('--output')+1])
                pipeline.save(target/'observations.json', pdf)
                pipeline.save(target/'manifest.json', {'comparisons':[],'edition':'2026-01','latest_month':'2025-12'})

            stack.enter_context(patch.object(pipeline,'TABLES',{'1.4':pipeline.TABLES['1.4']}))
            stack.enter_context(patch.object(pipeline,'rvd',return_value=copy.deepcopy(prices)))
            stack.enter_context(patch.object(pipeline.hk_commercial_collector,'TABLES',{}))
            stack.enter_context(patch.object(pipeline.hk_landreg_collector,'collect',return_value=copy.deepcopy([sales,other])))
            stack.enter_context(patch.object(pipeline.hk_hkma_collector,'collect',return_value=[copy.deepcopy(mortgage)]))
            stack.enter_context(patch.object(macro,'SOURCES',{key:macro.SOURCES[key] for key in fresh}))
            stack.enter_context(patch.object(macro,'collect',side_effect=collect))
            stack.enter_context(patch.object(pipeline,'fetch',return_value=b'%PDF-test'))
            stack.enter_context(patch.object(pipeline.subprocess,'run',side_effect=extract))
            with redirect_stdout(io.StringIO()):
                code = pipeline.run(argparse.Namespace(output=out,app=app_arg,as_of='2026-11-03',pdf=None))
            result = json.loads((out/'hk_housing_dataset.json').read_text())
            self.assertEqual(archive.read_bytes(), b'Historical calculation evidence; retain unchanged')
            retired=json.loads((out/'cache/macro/superseded_rate_calculations.json').read_text())
            self.assertEqual(retired['observations'],calculated)
            self.assertEqual(result['revisions'], history)
            with sqlite3.connect(out/'hk_housing.sqlite') as db:
                validate_database(db,result)
                database_rates = db.execute("SELECT metric_id,period,status,value FROM observations WHERE metric_id IN ('hk_prime_rate_hsbc','hk_hibor_1m','hk_hibor_3m') ORDER BY metric_id,period").fetchall()
            validate_excel(out/'hk_property_data.xlsx',result)
            excel_rates = []
            with zipfile.ZipFile(out/'hk_property_data.xlsx') as workbook:
                for number,cells in _sheet_rows(workbook,SHEETS.index('Money & Rates')+1):
                    if number > HEADER_ROW+1 and cells.get('M') in RATE_IDS:
                        period=(dt.datetime(1899,12,30)+dt.timedelta(days=cells['A'])).strftime('%Y-%m')
                        excel_rates.append((cells['M'],period,cells['J'],cells['F']))
            if app_arg:
                snapshot=json.loads((app/'src/data.json').read_text())
                self.assertEqual(snapshot['queries']['observations']['rows'],result['observations'])
            return code,result,database_rates,sorted(excel_rates)

    def assert_published_only(self, result):
        rates=[row for row in result['observations'] if row['metric_id'] in RATE_IDS]
        self.assertTrue(rates)
        self.assertTrue(all(row['status']=='Published' for row in rates))
        self.assertFalse(any('calculated' in row.get('fetch_mode','') or row.get('fetch_mode')=='automatic_derived' for row in rates))
        self.assertIn(('hk_prime_rate_hsbc','2026-08'),{(row['metric_id'],row['period']) for row in rates})
        for metric in ('hk_residential_sales_count','non_rate_comparison'):
            self.assertEqual(next(row['period'] for row in result['observations'] if row['metric_id']==metric),'2026-10')
        return rates

    def test_success_removes_retired_calculations_from_saved_and_seeded_history(self):
        for storage in ('saved','snapshot'):
            with self.subTest(storage=storage):
                code,result,database,excel=self.run_refresh(storage=storage)
                self.assertEqual(code,0)
                rates=self.assert_published_only(result)
                self.assertEqual(max(row['period'] for row in rates),'2026-09')
                for source in ('hkma_prime','hkma_hibor'):
                    status=next(row for row in result['source_status'] if row['source_id']==source)
                    self.assertEqual((status['status'],status['latest_period']),('Verified','2026-09'))
                self.assertEqual(database,excel)
                self.assertTrue(all(row[2]=='Published' and row[1]<='2026-09' for row in database))

    def test_offline_fallback_cannot_restore_calculations_from_either_history_path(self):
        for storage in ('saved','snapshot'):
            with self.subTest(storage=storage):
                code,result,database,excel=self.run_refresh(storage=storage,offline=True)
                self.assertEqual(code,2)
                self.assert_published_only(result)
                for source in ('hkma_prime','hkma_hibor'):
                    status=next(row for row in result['source_status'] if row['source_id']==source)
                    self.assertEqual((status['status'],status['latest_period']),('Retained: refresh failed','2026-09'))
                    self.assertEqual(status['last_success'],'2026-11-02T10:00:00+00:00')
                    self.assertTrue(any(source in error for error in result['errors']))
                self.assertEqual(database,excel)
                self.assertTrue(all(row[2]=='Published' and row[1]<='2026-09' for row in database))

    def test_new_published_october_is_accepted_without_forcing_other_series_forward(self):
        code,result,database,excel=self.run_refresh(october_published=True)
        self.assertEqual(code,0)
        rates=self.assert_published_only(result)
        prime=max((row for row in rates if row['metric_id']=='hk_prime_rate_hsbc'),key=lambda row:row['period'])
        self.assertEqual((prime['period'],prime['value'],prime['status']),('2026-10',5.01,'Published'))
        self.assertEqual(prime['observation_basis'],'Monthly average')
        self.assertIn('api.hkma.gov.hk',prime['source_url'])
        for metric in ('hk_hibor_1m','hk_hibor_3m'):
            self.assertEqual(max(row['period'] for row in rates if row['metric_id']==metric),'2026-09')
        self.assertEqual(database,excel)

    def test_offline_without_any_published_rate_history_fails_initial_load(self):
        with self.assertRaisesRegex(RuntimeError,'Initial load failed: hkma_prime'):
            self.run_refresh(offline=True,only_calculated=True)


if __name__=='__main__':
    unittest.main()
