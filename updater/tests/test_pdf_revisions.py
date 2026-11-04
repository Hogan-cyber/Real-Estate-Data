"""Known source revisions are informative; unknown differences and outages still fail."""
import argparse
import copy
import io
import json
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data import pipeline


def row(metric, period, value, source):
    return dict(market='HK', metric_id=metric, metric_name=metric, period=period,
                date=period+'-28', value=value, unit='1999=100', frequency='M',
                source_id=source, source_name='Rating and Valuation Department',
                source_url='https://www.rvd.gov.hk/datagovhk/1.4M.csv',
                source_table='1.4', source_field='All Classes',
                fetch_mode='automatic_csv', status='Published')


class PdfRevisionIntegrationTest(unittest.TestCase):
    def run_refresh(self, *, pdf_value=320.5, prior_value=320.5, history=None,
                    extra_difference=False, pdf_outage=False, csv_outage=False,
                    provisional=True, collector_warning=None):
        prior=[row('rvd_1_4_all_classes', f'{y}-{m:02}', 300, 'rvd_1.4')
               for y in (2024, 2025) for m in range(1, 13)]
        prior[-1]['value']=prior_value
        others=[row('landreg_sample','2025-12',1,'landreg'),
                row('hkma_sample','2025-12',1,'hkma')]
        current=copy.deepcopy(prior);current[-1]['value']=320.2
        pdf=[dict(table_id='1.4', period='2025-12', frequency='monthly',
                  column='All Classes', value=pdf_value, provisional=provisional,
                  source_pdf='original', pdf_page=8, unit='1999=100', raw_cell=str(pdf_value))]
        differences=[dict(period='2025-12', column='All Classes',pdf=pdf_value,csv=320.2)]
        if extra_difference:
            pdf.append(dict(pdf[0],column='Class A',value=340))
            differences.append(dict(period='2025-12',column='Class A',pdf=340,csv=341))
            current.append(dict(row('rvd_1_4_class_a','2025-12',341,'rvd_1.4'),source_field='Class A'))
        comparisons=[dict(table_id='1.4',status='review',compared_cells=len(pdf),
                          mismatch_count=len(differences),mismatches=differences,
                          csv_source='1.4M.csv',csv_sha256='test')]
        previous=dict(observations=prior+others,pdf_observations=pdf,
                      source_status=[],revisions=history or [],
                      report=dict(status='Extracted and checked',comparisons=comparisons))
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            out=Path(temporary);pipeline.save(out/'hk_housing_dataset.json',previous)
            def extract(command, **kwargs):
                folder=Path(command[command.index('--output')+1])
                pipeline.save(folder/'observations.json',pdf)
                pipeline.save(folder/'manifest.json',dict(comparisons=comparisons,edition='2026-01',latest_month='2025-12'))
            stack.enter_context(patch.object(pipeline,'TABLES',{'1.4':pipeline.TABLES['1.4']}))
            stack.enter_context(patch.object(pipeline,'rvd',side_effect=OSError('CSV unavailable') if csv_outage else None,return_value=current))
            stack.enter_context(patch.object(pipeline.hk_commercial_collector,'TABLES',{}))
            stack.enter_context(patch.object(pipeline.hk_macro_collector,'SOURCES',{}))
            stack.enter_context(patch.object(pipeline.hk_latest_rates,'refresh',return_value=([],[],[])))
            stack.enter_context(patch.object(pipeline.hk_landreg_collector,'collect',return_value=[others[0]]))
            hkma=dict(others[1])
            if collector_warning: hkma['refresh_warning']=collector_warning
            stack.enter_context(patch.object(pipeline.hk_hkma_collector,'collect',return_value=[hkma]))
            stack.enter_context(patch.object(pipeline,'fetch',side_effect=OSError('PDF unavailable') if pdf_outage else None,return_value=b'%PDF-test'))
            stack.enter_context(patch.object(pipeline.subprocess,'run',side_effect=extract))
            # Exporters have independent reconciliation tests; this fixture isolates refresh semantics.
            stack.enter_context(patch.object(pipeline,'build_database'))
            stack.enter_context(patch.object(pipeline,'build_excel'))
            with redirect_stdout(io.StringIO()):
                code=pipeline.run(argparse.Namespace(output=out,app=None,as_of='2026-01-31',pdf=None))
            return code,json.loads((out/'hk_housing_dataset.json').read_text()),copy.deepcopy(pdf)

    def test_new_exact_revision_is_notice_without_mutating_pdf(self):
        code,result,original=self.run_refresh()
        self.assertEqual(code,0)
        self.assertEqual(result['errors'],[])
        self.assertTrue(result['warnings'])
        check=result['report']['comparisons'][0]
        self.assertEqual(check['status'],'revisions_confirmed')
        self.assertEqual(check['confirmed_revision_count'],1)
        self.assertEqual(check['mismatches'][0]['pdf'],320.5)
        self.assertEqual(result['pdf_observations'][0]['value'],original[0]['value'])

    def test_binary_serialization_noise_is_not_a_recorded_official_revision(self):
        _,result,_=self.run_refresh(prior_value=320.20000000000005, pdf_outage=True)
        self.assertEqual(result['revisions'],[])
        source=next(s for s in result['source_status'] if s['source_id']=='rvd_1.4')
        self.assertEqual(source['change_summary'],'No new or revised values')
        self.assertEqual(result['observations'][-1]['value'],320.2)
        for previous in (320.201, 0, None):
            with self.subTest(previous=previous):
                _,changed,_=self.run_refresh(prior_value=previous,pdf_outage=True)
                self.assertEqual(len(changed['revisions']),1)

    def test_unknown_difference_remains_error(self):
        code,result,_=self.run_refresh(pdf_value=319)
        self.assertEqual(code,2)
        self.assertEqual(result['report']['comparisons'][0]['status'],'review')
        self.assertTrue(any('CSV comparison' in e for e in result['errors']))

    def test_mixed_known_unknown_does_not_clear_error(self):
        code,result,_=self.run_refresh(extra_difference=True)
        self.assertEqual(code,2)
        check=result['report']['comparisons'][0]
        self.assertEqual(check['status'],'review')
        self.assertEqual(check.get('confirmed_revision_count'),1)
        self.assertEqual(check.get('unexplained_mismatch_count'),1)

    def test_retained_pdf_is_still_failure_even_with_known_revision(self):
        code,result,_=self.run_refresh(pdf_outage=True)
        self.assertEqual(code,2)
        self.assertTrue(result['report']['status'].startswith('Retained'))
        self.assertTrue(any('PDF unavailable' in e for e in result['errors']))

    def test_retained_csv_cannot_confirm_revision(self):
        code,result,_=self.run_refresh(csv_outage=True)
        self.assertEqual(code,2)
        self.assertEqual(result['report']['comparisons'][0]['status'],'review')

    def test_monotonic_recorded_chain_can_explain_older_provisional_snapshot(self):
        history=[dict(metric_id='rvd_1_4_all_classes',period='2025-12',old=320.5,new=320.4,detected_at='2026-01-01T00:00:00+00:00')]
        code,result,_=self.run_refresh(prior_value=320.4,history=history)
        self.assertEqual(code,0)
        self.assertEqual(len(result['report']['comparisons'][0]['mismatches'][0]['revision_evidence']),2)

    def test_nonprovisional_pdf_difference_remains_review(self):
        code,result,_=self.run_refresh(provisional=False)
        self.assertEqual(code,2)
        self.assertEqual(result['report']['comparisons'][0]['status'],'review')

    def test_wrong_series_or_period_history_cannot_clear_warning(self):
        for metric,period in [('rvd_1_4_class_a','2025-12'),('rvd_1_4_all_classes','2025-11')]:
            with self.subTest(metric=metric,period=period):
                history=[dict(metric_id=metric,period=period,old=320.5,new=320.2,detected_at='2026-01-01T00:00:00+00:00')]
                code,result,_=self.run_refresh(prior_value=320.2,history=history)
                self.assertEqual(code,2)
                self.assertEqual(result['report']['comparisons'][0]['status'],'review')

    def test_future_or_reverse_dated_chain_cannot_clear_warning(self):
        def revision(old,new,date):
            return dict(metric_id='rvd_1_4_all_classes',period='2025-12',old=old,new=new,detected_at=date)
        cases=[
            [revision(320.5,320.2,'2099-01-01T00:00:00+00:00')],
            [revision(320.5,320.4,'2026-01-02T00:00:00+00:00'),revision(320.4,320.2,'2026-01-01T00:00:00+00:00')],
            [revision(320.5,320.4,'2026-01-01T00:00:00+00:00'),revision(320.4,320.3,'2026-01-02T00:00:00+00:00'),
             revision(320.3,320.4,'2026-01-03T00:00:00+00:00'),revision(320.4,320.2,'2026-01-04T00:00:00+00:00')],
        ]
        for history in cases:
            with self.subTest(history=history):
                code,result,_=self.run_refresh(prior_value=320.2,history=history)
                self.assertEqual(code,2)
                self.assertEqual(result['report']['comparisons'][0]['status'],'review')

    def test_collector_warning_is_visible_without_mislabeling_base_data_stale(self):
        code,result,_=self.run_refresh(collector_warning='Latest release check unavailable; base data refreshed.')
        self.assertEqual(code,0)
        self.assertIn('hkma: Latest release check unavailable; base data refreshed.',result['warnings'])
        status=next(s for s in result['source_status'] if s['source_id']=='hkma')
        self.assertEqual(status['status'],'Review: latest release check unavailable')


if __name__=='__main__': unittest.main()
