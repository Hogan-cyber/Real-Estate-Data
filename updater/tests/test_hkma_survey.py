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
ANNEX = '''Residential Mortgage Survey
Results of Survey for September 2026
(Value in HK$ million)
Sep 2026 Aug 2026
1. New applications received during the month
a. Number 7,560 8,446
2. New loans approved during the month
a. Value 31,835 32,191
(M-o-M % change) (-1.1%) (-28.2%)
b. Number 6,240 6,090
3. New loans drawn down during the month
a. Value 25,291 32,768
(M-o-M % change) (-22.8%) (11.6%)
b. Number 4,788 6,233
(Value in HK$ million)
Sep 2026 Aug 2026
4. Outstanding loans
a. Value 1,980,257 1,975,355
c. Delinquency ratio (%)
- More than 3 months 0.11 0.11
5. Loans written off
'''

def workbook(overrides=None):
    cells={'A1':'Table 3.7  Residential mortgage survey results1,2',
        'D4':'As at end of period','T4':'During the period',
        'D6':'Outstanding loans','T6':'New applications received','W6':'New loans drawn down','AC6':' New loans approved3',
        'D9':'Value','N9':'Delinquency ratio4','T9':'Number','W9':'Value','Z9':'Number','AC9':'Value','AF9':'Number',
        'N11':'More than 3 months','D15':'(HK$ Mn)','N15':'(%)','T15':'(No.)','W15':'(HK$ Mn)',
        'Z15':'(No.)','AC15':'(HK$ Mn)','AF15':'(No.)','A17':2026,'B17':'August',
        'D17':1975355,'N17':0.11,'T17':8446,'W17':32768,'Z17':6233,'AC17':32191,'AF17':6090}
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
            self.assertEqual(len(rows),7)
            self.assertEqual({r['metric_id']:r['value'] for r in rows},{c.FIELDS[k][0]:v for k,v in VALUES.items()})
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
            self.assertEqual(len(latest),7)
            self.assertTrue(all(r['source_url']==PDF and r['fetch_mode']=='automatic_pdf' for r in latest))
            self.assertTrue((Path(temp)/'hkma_survey_2026-09.pdf').exists())

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

if __name__=='__main__':unittest.main()
