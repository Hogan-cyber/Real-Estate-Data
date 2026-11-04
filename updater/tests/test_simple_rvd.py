"""Small official-format CSV examples, with hand-checked expected values."""
import csv
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
from hk_property_data.simple import rvd


def csv_bytes(title, columns, rows):
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow([title])
    writer.writerow(columns)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


INDEX_COLUMNS = ['Class A', 'Class B', 'Class C', 'Class D', 'Class E',
                 'Classes A, B & C', 'Classes D & E', 'All Classes']
INDEX_HEADERS = ['Month'] + [item for field in INDEX_COLUMNS
                             for item in (field, field + ' - Remarks')]
INDEX_TITLE = 'PRIVATE DOMESTIC - PRICE INDICES BY CLASS ( TERRITORY-WIDE ) [MONTHLY]'


class SimpleRVDTest(unittest.TestCase):
    def test_missing_is_not_zero_and_provisional_sample_flags_survive(self):
        raw = csv_bytes(INDEX_TITLE, INDEX_HEADERS, [
            ['09-2026', '340.4', 'PZ', '-', 'P', 'NA', '', 'N.A.', '',
             'N/A', '', '', '', '0', '', '320.8', 'P']])
        rows = rvd.parse_csv('1.4M.csv', raw, '2026-11-04')
        self.assertEqual(rows[0]['value'], 340.4)
        self.assertEqual(rows[0]['flags'], 'PZ')
        self.assertEqual(rows[0]['status'], 'Provisional')
        self.assertTrue(rows[0]['small_sample'])
        self.assertEqual([r['value'] for r in rows[1:6]], [None] * 5)
        self.assertEqual(rows[1]['status'], 'Missing')
        self.assertEqual(rows[6]['value'], 0.0)
        self.assertEqual(rows[-1]['metric_id'], 'rvd_1_4_all_classes')
        self.assertEqual(rows[-1]['unit'], '1999=100')
        self.assertEqual(rows[-1]['date'], '2026-09-30')

    def test_start_and_as_of_filter_actual_calendar_months(self):
        raw = csv_bytes(INDEX_TITLE, INDEX_HEADERS, [
            [period] + ['100', ''] * 8
            for period in ['12-2001', '01-2002', '09-2026', '10-2026']])
        rows = rvd.parse_csv('1.4M.csv', raw, '2026-10-02')
        self.assertEqual(sorted(set(r['period'] for r in rows)), ['2002-01', '2026-09'])
        earlier = rvd.parse_csv('1.4M.csv', raw, '2026-10-02', start='2001-01')
        self.assertIn('2001-12', [r['period'] for r in earlier])

    def test_vacancy_rates_preserve_source_fraction(self):
        columns = ['Year'] + [f'{c} (Vacancy) - {unit}'
                             for c in ['Class A', 'Class B', 'Class C', 'Class D', 'Class E', 'Total']
                             for unit in ['Unit', '%']]
        raw = csv_bytes('PRIVATE DOMESTIC - VACANCY AT YEAR END BY CLASS', columns,
                        [['2025', '18997', '0.044', '22378', '0.036', '6960', '0.045',
                          '4776', '0.067', '2970', '0.102', '56081', '0.043']])
        rows = rvd.parse_csv('Private_Domestic-Vacancy.csv', raw, '2026-11-04')
        self.assertEqual(rows[-2]['value'], 56081)
        self.assertEqual(rows[-2]['unit'], 'dwellings')
        self.assertEqual(rows[-1]['value'], 0.043)
        self.assertEqual(rows[-1]['unit'], 'fraction')
        self.assertIn('0.043 = 4.3%', rows[-1]['note'])
        self.assertEqual(rows[-1]['frequency'], 'A')
        self.assertEqual(rows[-1]['date'], '2025-12-31')

    def test_partial_completions_are_included_with_actual_cutoff(self):
        columns = ['Year'] + [item for c in ['Class A', 'Class B', 'Class C', 'Class D', 'Class E', 'Total']
                             for item in (f'{c} (Completions)', f'{c} (Completions) - Remarks')]
        flag = '# Provisional figures (up to 31.08.2026).'
        raw = csv_bytes('PRIVATE DOMESTIC - COMPLETIONS BY CLASS', columns,
                        [['2025'] + ['10', ''] * 6,
                         ['2026'] + [item for v in ['4557', '3400', '703', '286', '41', '8987']
                                     for item in (v, flag)]])
        rows = rvd.parse_csv('Private_Domestic-Completions.csv', raw, '2026-11-04')
        latest = rows[-1]
        self.assertEqual(latest['value'], 8987)
        self.assertEqual(latest['period'], '2026')
        self.assertEqual(latest['date'], '2026-08-31')
        self.assertEqual(latest['status'], 'Partial; Provisional')
        self.assertEqual(latest['flags'], flag)
        self.assertIn('2026-08-31', latest['note'])
        self.assertEqual(len(rvd.parse_csv('Private_Domestic-Completions.csv', raw, '2026-07-31')), 6)

    def test_negative_takeup_is_valid(self):
        raw = csv_bytes('PRIVATE DOMESTIC - TAKE-UP',
                        ['Year', 'Take Up (SA Less than 100 m2)', 'Take up (SA 100 m2 or above)', 'Take up (Total)'],
                        [['2023', '17507', '-1837', '15670']])
        rows = rvd.parse_csv('Private_Domestic-Take-up.csv', raw, '2026-11-04')
        self.assertEqual(rows[1]['value'], -1837)

    def test_schema_drift_and_non_finite_values_fail_clearly(self):
        for raw in [csv_bytes(INDEX_TITLE, INDEX_HEADERS[:-2], [['09-2026'] + ['100', ''] * 7]),
                    csv_bytes(INDEX_TITLE, INDEX_HEADERS, [['09-2026'] + ['inf', ''] * 8]),
                    csv_bytes(INDEX_TITLE, INDEX_HEADERS, [['13-2026'] + ['100', ''] * 8]),
                    csv_bytes(INDEX_TITLE, INDEX_HEADERS, [['09-2026'] + ['100', ''] * 7])]:
            with self.subTest(raw=raw[:100]), self.assertRaises(ValueError):
                rvd.parse_csv('1.4M.csv', raw, '2026-11-04')

    def test_duplicate_source_month_is_rejected(self):
        raw = csv_bytes(INDEX_TITLE, INDEX_HEADERS, [['09-2026'] + ['100', ''] * 8] * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            rvd.parse_csv('1.4M.csv', raw, '2026-11-04')
