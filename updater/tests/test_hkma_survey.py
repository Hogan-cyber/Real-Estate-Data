"""Survey API fallback and latest-release checks use original official values."""
import calendar
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import xlsxwriter

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.collectors import hk_hkma_collector as c

XLSX = 'https://www.hkma.gov.hk/media/eng/doc/market-data-and-statistics/monthly-statistical-bulletin/T0307.xlsx'
LIST = 'https://www.hkma.gov.hk/eng/news-and-media/press-releases/monthly-residential-mortgage-survey-results/'
LANDING = 'https://www.hkma.gov.hk/eng/news-and-media/press-releases/2026/10/20261030-5/'
PDF = 'https://www.hkma.gov.hk/media/eng/doc/key-information/press-release/2026/20261030e5a1.pdf'
VALUES = dict(new_loans_approved_amt=32191, new_loans_drawn_amt=32768,
    new_loans_approved=6090, new_loans_drawn=6233, new_loans_app_received=8446,
    delinquency_ratio=0.11, outstanding_loans_amt=1975355)
ANNEX = (Path(__file__).parent / 'fixtures/hkma_survey_202609_eng.txt').read_text()
CHINESE_ANNEX = (Path(__file__).parent / 'fixtures/hkma_survey_202609_chi.txt').read_text()
CHINESE_LANDING = LANDING.replace('/eng/', '/chi/')
CHINESE_PDF = PDF.replace('/eng/', '/chi/').replace('e5a1', 'c5a1')
COFIN_VALUES = {
    'new_loans_approved_cofin_amt': (193, 207),
    'new_loans_approved_cofin': (32, 38),
    'outstanding_loans_cofin_gf_amt': (2404, 2407),
    'outstanding_loans_cofin_gf': (1113, 1121),
    'outstanding_loans_cofin_ps_amt': (16067, 16188),
    'outstanding_loans_cofin_ps': (3893, 3920),
}
TRANSACTION_VALUES = {
    'new_loans_approved_pt_amt_pri': (8452, 9067),
    'new_loans_approved_pt_amt_sec': (14443, 15320),
    'new_loans_approved_pt_amt_refin': (8940, 7804),
    'new_loans_approved_pt_primkt': (1499, 1337),
    'new_loans_approved_pt_secmkt': (2974, 3167),
    'new_loans_approved_pt_refin': (1767, 1586),
}


def workbook(overrides=None):
    cells={'A1':'Table 3.7  Residential mortgage survey results1,2',
        'D4':'As at end of period','T4':'During the period',
        'D6':'Outstanding loans','T6':'New applications received','W6':'New loans drawn down','AC6':' New loans approved3',
        'D9':'Value','N9':'Delinquency ratio4','T9':'Number','W9':'Value','Z9':'Number','AC9':'Value','AF9':'Number',
        'N11':'More than 3 months','D15':'(HK$ Mn)','N15':'(%)','T15':'(No.)','W15':'(HK$ Mn)',
        'Z15':'(No.)','AC15':'(HK$ Mn)','AF15':'(No.)','A17':2026,'B17':'August',
        'D17':1975355,'N17':0.11,'T17':8446,'W17':32768,'Z17':6233,'AC17':32191,'AF17':6090}
    cells.update({'H9':'Loans associated with co-financing schemes6',
        'H11':'Government-funded schemes:', 'K11':'Schemes offered by the private sector:',
        'H13':'Value', 'I13':'Number', 'K13':'Value', 'L13':'Number',
        'AK8':'Loans associated with', 'AK9':'co-financing schemes', 'AK11':'Value', 'AL11':'Number',
        'H15':'(HK$ Mn)', 'I15':'(No.)', 'K15':'(HK$ Mn)', 'L15':'(No.)',
        'AK15':'(HK$ Mn)', 'AL15':'(No.)',
        'H17':2407,'I17':1121,'K17':16188,'L17':3920,'AK17':207,'AL17':38})
    cells.update({'AN9':'Type of property transaction','AN11':'Value','AR11':'Number',
        'AN13':'Primary market','AO13':'Secondary market','AP13':'Refinancing',
        'AR13':'Primary market','AS13':'Secondary market','AT13':'Refinancing',
        'AN15':'(HK$ Mn)','AO15':'(HK$ Mn)','AP15':'(HK$ Mn)',
        'AR15':'(No.)','AS15':'(No.)','AT15':'(No.)',
        'AN17':9067,'AO17':15320,'AP17':7804,'AR17':1337,'AS17':3167,'AT17':1586})
    cells.update(overrides or {})
    out=io.BytesIO();book=xlsxwriter.Workbook(out,{'in_memory':True});sheet=book.add_worksheet('T3.7')
    for cell,value in cells.items():
        if value is not None:sheet.write(cell,value)
    book.add_worksheet('T3.7 (old)').write('A1','wrong series')
    book.close();return out.getvalue()

def listing(month='September', year=2026):
    return f'<a href="{LANDING}" title="Residential Mortgage Survey Results for {month} {year}">Residential Mortgage Survey Results for {month} {year}</a>'.encode()

class SurveyTest(unittest.TestCase):
    def source_rows(self):
        as_of=dt.date(2026,11,3)
        return {
            'survey':c._base('hk_mortgage_applications','applications','2026-09',7560,'宗',c.API_URL,as_of),
            'mortgage_rate':dict(c._base('hk_new_mortgage_rate','mortgage rate','2026-07',3.26,'% p.a.',PDF,as_of),source_period='2026-09'),
        }

    def test_missing_required_feed_without_cache_cannot_publish_partial_success(self):
        for missing in ('survey','mortgage_rate'):
            with self.subTest(missing=missing),tempfile.TemporaryDirectory() as temp:
                rows=self.source_rows()
                with patch.object(c,'_survey',side_effect=OSError('survey unavailable') if missing=='survey' else None,return_value=[rows['survey']]), \
                     patch.object(c,'_mortgage_rate',side_effect=OSError('rate report unavailable') if missing=='mortgage_rate' else None,return_value=[rows['mortgage_rate']]):
                    with self.assertRaisesRegex(RuntimeError,missing + '.*unavailable'):
                        c.collect(temp,'2026-11-03')
                diagnostics=json.loads((Path(temp)/'hkma_status.json').read_text())['sources']
                self.assertEqual(diagnostics[missing]['status'],'unavailable')
                self.assertIn('unavailable',diagnostics[missing]['error'])

    def test_cached_failed_feed_is_preserved_while_its_sibling_updates(self):
        for missing in ('survey','mortgage_rate'):
            with self.subTest(missing=missing),tempfile.TemporaryDirectory() as temp:
                rows=self.source_rows();path=Path(temp)
                cached=dict(rows[missing],value=123 if missing=='survey' else 3.50)
                cache=path/f'hkma_{missing}.json'
                cache.write_text(json.dumps({'last_success':'2026-10-27','rows':[cached]}))
                with patch.object(c,'_survey',side_effect=OSError('survey unavailable') if missing=='survey' else None,return_value=[rows['survey']]), \
                     patch.object(c,'_mortgage_rate',side_effect=OSError('rate report unavailable') if missing=='mortgage_rate' else None,return_value=[rows['mortgage_rate']]):
                    result=c.collect(path,'2026-11-03')
                by_metric={r['metric_id']:r for r in result}
                retained=by_metric[cached['metric_id']]
                self.assertEqual(retained['value'],cached['value'])
                self.assertEqual(retained['status'],'stale_cache')
                self.assertIn('unavailable',retained['refresh_error'])
                sibling='mortgage_rate' if missing=='survey' else 'survey'
                self.assertEqual(by_metric[rows[sibling]['metric_id']]['value'],rows[sibling]['value'])
                self.assertEqual(by_metric[rows[sibling]['metric_id']]['status'],'updated')
                self.assertEqual(json.loads(cache.read_text())['last_success'],'2026-10-27')

    def test_empty_feed_does_not_advance_last_success_of_cached_data(self):
        with tempfile.TemporaryDirectory() as temp:
            rows=self.source_rows();path=Path(temp);cache=path/'hkma_survey.json'
            cache.write_text(json.dumps({'last_success':'2026-10-27','rows':[rows['survey']]}))
            with patch.object(c,'_survey',return_value=[]),patch.object(c,'_mortgage_rate',return_value=[rows['mortgage_rate']]):
                result=c.collect(path,'2026-11-03')
            self.assertEqual(json.loads(cache.read_text())['last_success'],'2026-10-27')
            self.assertEqual(next(r for r in result if r['metric_id']=='hk_mortgage_applications')['status'],'stale_cache')

    def test_api_405_uses_validated_official_workbook(self):
        def get(url):
            if url==c.API_URL:raise HTTPError(url,405,'Not Allowed',None,None)
            if url==XLSX:return workbook()
            if url==LIST:return listing('August')
            raise AssertionError(url)
        with tempfile.TemporaryDirectory() as temp,patch.object(c,'_get',side_effect=get):
            try:rows=c._survey(dt.date(2026,11,3),Path(temp))
            except Exception as exc:self.fail(f'Official workbook fallback must recover API failure: {exc}')
            self.assertEqual(len(rows),21)
            self.assertEqual({r['metric_id']:r['value'] for r in rows if r['metric_id'] in {v[0] for v in c.FIELDS.values()}},{c.FIELDS[k][0]:v for k,v in VALUES.items()})
            self.assertEqual({r['source_url'] for r in rows},{XLSX})
            self.assertEqual({r['fetch_mode'] for r in rows},{'automatic_excel'})
            self.assertTrue((Path(temp)/'hkma_survey.xlsx').exists())
            self.assertTrue(all('405' in r['source_fallback_reason'] for r in rows))

    def test_workbook_rejects_changed_units_missing_values_and_duplicate_months(self):
        for changes in [{'N15':'(fraction)'},{'AC17':None},{'B18':'August','D18':1,'N18':1,'T18':1,'W18':1,'Z18':1,'AC18':1,'AF18':1}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):c.parse_survey_xlsx(workbook(changes))

    def test_workbook_zero_is_preserved(self):
        records=c.parse_survey_xlsx(workbook({'N17':0}))
        self.assertEqual(records[0]['delinquency_ratio'],0)

    def test_annex_exact_values_and_explicit_months(self):
        records=c.parse_survey_annex(ANNEX,'2026-09')
        self.assertEqual([r['end_of_month'] for r in records],['2026-09','2026-08'])
        self.assertEqual(records[0]['new_loans_approved_amt'],31835)
        self.assertEqual(records[0]['new_loans_drawn'],4788)
        self.assertEqual(records[0]['outstanding_loans_amt'],1980257)
        self.assertEqual(records[0]['delinquency_ratio'],0.11)
        self.assertEqual({k:records[1][k] for k in VALUES},VALUES)

    def test_annex_refuses_wrong_period_units_missing_or_reordered_columns(self):
        for text in [ANNEX.replace('HK$ million','HK$ billion'),ANNEX.replace('ratio (%)','ratio (fraction)'),ANNEX.replace('Sep 2026 Aug 2026','Aug 2026 Sep 2026'),ANNEX.replace('0.11 0.11','N.A. 0.11')]:
            with self.subTest(text=text),self.assertRaises(ValueError):c.parse_survey_annex(text,'2026-09')
        with self.assertRaises(ValueError):c.parse_survey_annex(ANNEX,'2026-08')

    def test_successful_api_is_extended_by_newer_annex(self):
        def get(url):
            if url==c.API_URL:return json.dumps({'header':{'success':True},'result':{'records':[dict(VALUES,end_of_month='2026-08')]}}).encode()
            if url==LIST:return listing()
            if url==LANDING:return f'<a href="{PDF}">Annex</a>'.encode()
            if url==PDF:return b'%PDF-test'
            raise AssertionError(url)
        with tempfile.TemporaryDirectory() as temp,patch.object(c,'_get',side_effect=get),patch.object(c,'_survey_annex_text',return_value=ANNEX):
            rows=c._survey(dt.date(2026,11,3),Path(temp))
            latest=[r for r in rows if r['period']=='2026-09']
            self.assertEqual(len(latest),21)
            self.assertTrue(all(r['source_url']==PDF and r['fetch_mode']=='automatic_pdf' for r in latest))
            self.assertTrue((Path(temp)/'hkma_survey_2026-09.pdf').exists())

    def test_chinese_and_english_annex_six_values_and_scope(self):
        for text in (ANNEX, CHINESE_ANNEX):
            records = c.parse_survey_annex(text, '2026-09')
            for key, values in COFIN_VALUES.items():
                self.assertEqual(tuple(record.get(key) for record in records), values)
            rows = c._survey_rows(records, dt.date(2026, 11, 4), CHINESE_PDF, 'automatic_pdf')
            details = [r for r in rows if 'cofinancing' in r['metric_id']]
            self.assertEqual(len(details), 12)
            self.assertEqual({r['unit'] for r in details}, {'HKD million', 'loans'})
            self.assertTrue(all('reporting authorized institutions' in r['scope'] for r in details))
            self.assertTrue(all(r['source_field'] in COFIN_VALUES for r in details))
            self.assertTrue(all(r['source_table'] for r in details))

    def test_cofinancing_workbook_schema_and_values_are_validated(self):
        record = c.parse_survey_xlsx(workbook())[0]
        self.assertEqual({key: record.get(key) for key in COFIN_VALUES}, {key: values[1] for key, values in COFIN_VALUES.items()})
        for changes in ({'H15':'HK$ billion'}, {'AK17':None}, {'K11':'Other lenders'}, {'L17':1.5}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                c.parse_survey_xlsx(workbook(changes))
        self.assertEqual(c.parse_survey_xlsx(workbook({'AL17':0}))[0]['new_loans_approved_cofin'], 0)

    def test_cofinancing_annex_missing_or_reordered_details_fail_without_zero(self):
        for text in (ANNEX.replace('193 207','N.A. 207'),
                     ANNEX.replace('Government-funded schemes:', 'Unknown schemes:'),
                     CHINESE_ANNEX.replace('2026年9月 2026年8月', '2026年8月 2026年9月'),
                     CHINESE_ANNEX.replace('百萬港元', '十億港元'),
                     CHINESE_ANNEX.replace('- 宗數 32 38', '- 宗數 32.5 38')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                c.parse_survey_annex(text, '2026-09')

    def test_same_period_api_missing_details_gets_full_history_and_chinese_revisions(self):
        def get(url):
            if url == c.API_URL:
                return json.dumps({'header':{'success':True}, 'result':{'records':[dict(VALUES, end_of_month='2026-09')]}}).encode()
            if url == XLSX:
                return workbook({'A17':2012, 'B17':'December'})
            if url == LIST:return listing()
            if url == LANDING:return f'<a href="{CHINESE_LANDING}">繁體中文</a><a href="{PDF}">Annex</a>'.encode()
            if url == CHINESE_LANDING:return f'<a href="{CHINESE_PDF}">附件</a>'.encode()
            if url == CHINESE_PDF:return b'%PDF-test'
            raise AssertionError(url)
        with patch.object(c, '_get', side_effect=get), patch.object(c, '_survey_annex_text', return_value=CHINESE_ANNEX):
            rows = c._survey(dt.date(2026,11,4))
        self.assertEqual({r['period'] for r in rows}, {'2012-12','2026-08','2026-09'})
        self.assertEqual(len(rows),63)
        latest = [r for r in rows if r['period']=='2026-09']
        self.assertTrue(all(r['source_url']==CHINESE_PDF for r in latest))
        self.assertTrue(all(r['published_date']=='2026-10-30' for r in latest))
        self.assertEqual(next(r['value'] for r in latest if r['metric_id']=='hk_mortgage_approved_amount'),31835)
        self.assertEqual(next(r['value'] for r in rows if r['period']=='2026-08' and r['metric_id']=='hk_mortgage_cofinancing_private_outstanding_count'),3920)

    def test_api_cofinancing_values_refresh_without_workbook(self):
        record = dict(VALUES, end_of_month='2026-08', **{k:v[1] for k,v in COFIN_VALUES.items()})
        def get(url):
            if url == c.API_URL:
                return json.dumps({'header':{'success':True},'result':{'records':[record]}}).encode()
            if url == LIST:raise OSError('catalog unavailable')
            raise AssertionError(url)
        with patch.object(c,'_get',side_effect=get):
            rows = c._survey(dt.date(2026,11,4))
        self.assertEqual(len(rows),13)
        details = [r for r in rows if 'cofinancing' in r['metric_id']]
        self.assertEqual({r['source_field']:r['value'] for r in details}, {k:v[1] for k,v in COFIN_VALUES.items()})
        self.assertTrue(all(r['fetch_mode']=='automatic_api' for r in details))
        invalid = dict(record, new_loans_approved_cofin=None)
        with self.assertRaises(ValueError):c._survey_rows([invalid],dt.date(2026,11,4))

    def test_invalid_optional_api_detail_does_not_discard_valid_core(self):
        record=dict(VALUES,end_of_month='2026-08',new_loans_approved_cofin_amt=None)
        def get(url):
            if url==c.API_URL:
                return json.dumps({'header':{'success':True},'result':{'records':[record]}}).encode()
            raise OSError('fallback unavailable')
        with patch.object(c,'_get',side_effect=get):rows=c._survey(dt.date(2026,11,4))
        self.assertEqual(len(rows),7)
        self.assertTrue(all('API co-financing detail' in r['refresh_warning'] for r in rows))
        self.assertTrue(all(r['status']=='updated' for r in rows))

    def test_missing_detail_preserves_cached_values_but_marks_them_stale(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            prior=c._base('hk_mortgage_cofinancing_approved_amount','co-financing','2026-08',207,'HKD million',XLSX,dt.date(2026,10,27))
            (path/'hkma_survey.json').write_text(json.dumps({'last_success':'2026-10-27','rows':[prior]}))
            fresh=dict(self.source_rows()['survey'],period='2026-08',date='2026-08-31',refresh_warning='Co-financing detail unavailable')
            with patch.object(c,'_survey',return_value=[fresh]),patch.object(c,'_mortgage_rate',return_value=[self.source_rows()['mortgage_rate']]):
                rows=c.collect(path,'2026-11-04')
            retained=next(r for r in rows if r['metric_id']==prior['metric_id'])
            self.assertEqual(retained['value'],207)
            self.assertEqual(retained['status'],'stale_cache')
            self.assertIn('Co-financing',retained['refresh_error'])
            self.assertEqual(next(r for r in rows if r['metric_id']=='hk_mortgage_applications')['status'],'updated')

    def test_bad_detail_workbook_preserves_valid_core_and_warns(self):
        def get(url):
            if url==c.API_URL:raise HTTPError(url,405,'Not Allowed',None,None)
            if url==XLSX:return workbook({'AK17':None})
            if url==LIST:raise OSError('catalog unavailable')
            raise AssertionError(url)
        with patch.object(c,'_get',side_effect=get):rows=c._survey(dt.date(2026,11,4))
        self.assertEqual(len(rows),15)
        self.assertTrue(all('workbook co-financing detail' in r['refresh_warning'] for r in rows))
        self.assertEqual(next(r['value'] for r in rows if r['metric_id']=='hk_mortgage_approved_purchase_count'),4504)
        self.assertTrue(all('not zero' in r['refresh_warning'] for r in rows))

    def test_failed_latest_release_probe_remains_visible(self):
        def get(url):
            if url==c.API_URL:return json.dumps({'header':{'success':True},'result':{'records':[dict(VALUES,end_of_month='2026-08')]}}).encode()
            raise OSError('catalog unavailable')
        with patch.object(c,'_get',side_effect=get):
            rows=c._survey(dt.date(2026,11,3))
            self.assertEqual(len(rows),7)
            self.assertTrue(all('catalog unavailable' in r['refresh_warning'] for r in rows))

    def test_successful_release_check_clears_old_freshness_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);prior=c._base('hk_mortgage_applications','applications','2015-01',100,'宗',c.API_URL,dt.date(2026,10,27))
            prior['refresh_warning']='old catalog outage'
            (path/'hkma_survey.json').write_text(json.dumps({'last_success':'2026-10-27','rows':[prior]}))
            fresh=c._base('hk_mortgage_applications','applications','2026-08',8446,'宗',c.API_URL,dt.date(2026,11,3))
            with patch.object(c,'_survey',return_value=[fresh]),patch.object(c,'_mortgage_rate',return_value=[self.source_rows()['mortgage_rate']]):
                rows=c.collect(path,'2026-11-03')
            self.assertFalse(any(r.get('refresh_warning') for r in rows))

    def test_failed_api_and_workbook_preserve_last_good_survey(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);prior=c._base('hk_mortgage_applications','applications','2026-08',8446,'宗',c.API_URL,dt.date(2026,10,27))
            (path/'hkma_survey.json').write_text(json.dumps({'last_success':'2026-10-27','rows':[prior]}))
            with patch.object(c,'_get',side_effect=OSError('unavailable')),patch.object(c,'_mortgage_rate',return_value=[self.source_rows()['mortgage_rate']]):
                rows=c.collect(path,'2026-11-03')
            self.assertEqual(rows[0]['value'],8446)
            self.assertEqual(rows[0]['status'],'stale_cache')
            self.assertIn('unavailable',rows[0]['refresh_error'])
            self.assertEqual(json.loads((path/'hkma_survey.json').read_text())['last_success'],'2026-10-27')

    def test_transaction_types_and_purchase_derivation_match_bilingual_annex(self):
        for text in (ANNEX, CHINESE_ANNEX):
            records = c.parse_survey_annex(text, '2026-09')
            for key, values in TRANSACTION_VALUES.items():
                self.assertEqual(tuple(record.get(key) for record in records), values)
            rows = c._survey_rows(records, dt.date(2026,11,4), PDF, 'automatic_pdf')
            latest = {r['metric_id']: r for r in rows if r['period']=='2026-09'}
            for suffix, value in [('count',4473),('amount',22895)]:
                row = latest['hk_mortgage_approved_purchase_'+suffix]
                self.assertEqual(row['value'], value)
                self.assertEqual(row['observation_type'], 'derived')
                self.assertIn(' + ', row['source_field'])
                self.assertEqual(len(row['derived_from']), 2)
                self.assertIn('not drawdowns', row['scope'])
                self.assertIn('not non-bank', row['scope'])
            self.assertEqual(latest['hk_mortgage_drawn_count']['value'],4788)
            self.assertFalse(any('drawn_purchase' in metric or 'nonbank' in metric for metric in latest))

    def test_transaction_workbook_columns_units_and_integer_counts(self):
        records = c.parse_survey_xlsx(workbook())
        self.assertEqual({k:records[0].get(k) for k in TRANSACTION_VALUES}, {k:v[1] for k,v in TRANSACTION_VALUES.items()})
        rows = c._survey_rows(records, dt.date(2026,11,4), XLSX, 'automatic_excel')
        self.assertEqual(next(r['source_column'] for r in rows if r['metric_id']=='hk_mortgage_approved_refinancing_count'),'AT')
        for changes in ({'AT17':None},{'AR15':'(HK$ Mn)'},{'AN13':'Secondary market'},{'AT17':1586.5}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                c.parse_survey_xlsx(workbook(changes))

    def test_api_transaction_fields_and_derivation_preserve_provenance(self):
        record=dict(VALUES,end_of_month='2026-08',**{k:v[1] for k,v in TRANSACTION_VALUES.items()},
                    **{k:v[1] for k,v in COFIN_VALUES.items()})
        def get(url):
            if url==c.API_URL:return json.dumps({'header':{'success':True},'result':{'records':[record]}}).encode()
            if url==LIST:raise OSError('catalog unavailable')
            raise AssertionError('Complete API must not request historical workbook: '+url)
        with patch.object(c,'_get',side_effect=get):rows=c._survey(dt.date(2026,11,4))
        self.assertEqual(len(rows),21)
        official=[r for r in rows if r.get('source_field') in TRANSACTION_VALUES]
        self.assertEqual({r['source_field']:r['value'] for r in official},{k:v[1] for k,v in TRANSACTION_VALUES.items()})
        self.assertTrue(all(r['source_url']==c.API_URL and r['fetch_mode']=='automatic_api' for r in official))
        self.assertEqual(next(r['value'] for r in rows if r['metric_id']=='hk_mortgage_approved_purchase_amount'),24387)

    def test_invalid_transaction_api_values_do_not_discard_other_detail_family(self):
        record=dict(VALUES,end_of_month='2026-08',**{k:v[1] for k,v in TRANSACTION_VALUES.items()},
                    **{k:v[1] for k,v in COFIN_VALUES.items()})
        record['new_loans_approved_pt_refin']=None
        def get(url):
            if url==c.API_URL:return json.dumps({'header':{'success':True},'result':{'records':[record]}}).encode()
            raise OSError('fallback unavailable')
        with patch.object(c,'_get',side_effect=get):rows=c._survey(dt.date(2026,11,4))
        self.assertEqual(len(rows),13)
        self.assertTrue(all('API transaction-type detail' in r['refresh_warning'] for r in rows))

    def test_rounding_tolerance_applies_to_amounts_but_never_counts(self):
        record=dict(VALUES,end_of_month='2026-08',**{k:v[1] for k,v in TRANSACTION_VALUES.items()})
        record['new_loans_approved_pt_amt_sec']+=1
        c._survey_rows([record],dt.date(2026,11,4))
        record['new_loans_approved_pt_secmkt']+=1
        with self.assertRaisesRegex(ValueError,'do not reconcile'):
            c._survey_rows([record],dt.date(2026,11,4))

    def test_transaction_annex_rejects_missing_reordered_and_inconsistent_data(self):
        for text in (ANNEX.replace('- Refinancing 1,767 1,586','- Refinancing N.A. 1,586'),
                     ANNEX.replace('- Primary market 8,452 9,067','- Secondary market 8,452 9,067'),
                     ANNEX.replace('- Primary market 1,499 1,337','- Primary market 1,499.5 1,337'),
                     ANNEX.replace('- Refinancing 1,767 1,586','- Refinancing 1,768 1,586')):
            with self.subTest(text=text), self.assertRaises(ValueError):
                records = c.parse_survey_annex(text, '2026-09')
                c._survey_rows(records, dt.date(2026,11,4))

    def test_purchase_requires_available_components_and_preserves_zero(self):
        record = dict(VALUES, end_of_month='2026-08',new_loans_approved_pt_primkt=0)
        rows = c._survey_rows([record],dt.date(2026,11,4))
        self.assertFalse(any('purchase' in r['metric_id'] for r in rows))
        record['new_loans_approved_pt_secmkt']=0
        rows = c._survey_rows([record],dt.date(2026,11,4))
        derived=[r for r in rows if 'purchase' in r['metric_id']]
        self.assertEqual([(r['metric_id'],r['value']) for r in derived],[('hk_mortgage_approved_purchase_count',0)])
        record['new_loans_approved_pt_secmkt']=record['new_loans_approved']+1
        with self.assertRaisesRegex(ValueError,'do not reconcile'):
            c._survey_rows([record],dt.date(2026,11,4))

    def test_bad_transaction_detail_preserves_core_and_cofinancing(self):
        def get(url):
            if url==c.API_URL:raise HTTPError(url,405,'Not Allowed',None,None)
            if url==XLSX:return workbook({'AT17':None})
            raise OSError('catalog unavailable')
        with patch.object(c,'_get',side_effect=get):rows=c._survey(dt.date(2026,11,4))
        self.assertEqual(len(rows),13)
        self.assertEqual(len([r for r in rows if 'cofinancing' in r['metric_id']]),6)
        self.assertFalse(any('purchase' in r['metric_id'] for r in rows))
        self.assertTrue(all('transaction-type' in r['refresh_warning'] for r in rows))

    def test_only_missing_details_inside_current_coverage_are_stale(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp); prior=[]
            for metric in ('hk_mortgage_cofinancing_approved_amount','hk_mortgage_approved_primary_count','hk_mortgage_approved_purchase_count'):
                for period in ('2012-12','2026-08'):
                    row=c._base(metric,metric,period,123,'loans',XLSX,dt.date(2026,10,27))
                    row.update(status='stale_cache',refresh_error='Previous source failure')
                    prior.append(row)
            (path/'hkma_survey.json').write_text(json.dumps({'last_success':'2026-10-27','rows':prior}))
            fresh=dict(self.source_rows()['survey'],period='2026-08',date='2026-08-31')
            with patch.object(c,'_survey',return_value=[fresh]),patch.object(c,'_mortgage_rate',return_value=[self.source_rows()['mortgage_rate']]):
                rows=c.collect(path,'2026-11-04')
            old=[r for r in rows if r['period']=='2012-12']
            self.assertEqual(len(old),3)
            self.assertTrue(all(r['status']=='updated' and not r.get('refresh_error') for r in old))
            self.assertTrue(all(r['checked_at']=='2026-10-27' for r in old))
            missing=[r for r in rows if r['period']=='2026-08' and r['metric_id']!=fresh['metric_id']]
            self.assertTrue(all(r['status']=='stale_cache' and r['refresh_error'] for r in missing))

if __name__=='__main__':unittest.main()
