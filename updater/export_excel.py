#!/usr/bin/env python3
"""Portable Excel export; runs in GitHub Actions without AI or private services."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import xlsxwriter

SQM_PER_SQFT = 0.09290304
MONTHLY_SHEETS = ('Residential Prices', 'Residential Rents', 'Indices & Yields',
                  'Commercial', 'Sales & Mortgages')
SHEETS = ('Overview',) + MONTHLY_SHEETS + ('PDF Tables', 'Source Checks', 'Revisions')
HEADER_ROW = 5
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
WEB = 'https://hogan-cyber.github.io/Real-Estate-Data/'


def sheet_for(row):
    if row.get('property_type') in ('Office', 'Retail', 'Industrial'):
        return 'Commercial'
    if row.get('source_table') == '1.2':
        return 'Residential Prices'
    if row.get('source_table') == '1.1':
        return 'Residential Rents'
    if row.get('source_id', '').startswith('rvd_'):
        return 'Indices & Yields'
    return 'Sales & Mortgages'


def monthly_groups(dataset):
    groups = {name: [] for name in MONTHLY_SHEETS}
    seen = set()
    for row in dataset['observations']:
        key = (row['metric_id'], row['period'])
        if key in seen:
            raise ValueError(f'Duplicate monthly observation: {key}')
        seen.add(key)
        value = row['value']
        if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value)):
            raise ValueError(f'Invalid numeric value: {key}')
        groups[sheet_for(row)].append(row)
    for rows in groups.values():
        rows.sort(key=lambda r: (r['period'], r['metric_id']), reverse=True)
    return groups


def hk_datetime(value):
    if not value:
        return None
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone(dt.timedelta(hours=8))).replace(tzinfo=None)


def notes_for(row):
    if row['metric_id'] == 'hk_new_mortgage_rate':
        return 'Only months explicitly reported by HKMA; gaps are not filled. Report date differs from reference month.'
    if row.get('source_id') == 'landreg':
        return 'Residential agreements lodged for registration; not contract-signing month. Monetary amounts are HKD million; counts are agreements.'
    if row.get('property_type') in ('Office', 'Retail', 'Industrial'):
        return 'Internal floor area. Office grades describe building quality, not flat size. Industrial means private flatted factories.'
    if row.get('source_table') in ('1.1', '1.2'):
        return 'Saleable floor area. Averages depend on transaction mix. Residential price statistics exclude primary sales.'
    return 'Keep the original unit and reference period; missing observations are not zero.'


def _write_workbook(dataset, destination, groups):
    with xlsxwriter.Workbook(str(destination), {'constant_memory': True,
            'strings_to_formulas': False, 'strings_to_urls': False}) as book:
        _populate_workbook(dataset, book, groups)


def _populate_workbook(dataset, book, groups):
    book.set_properties({'title': 'Hong Kong Property Monitor — Data',
                         'subject': 'Official residential and commercial property statistics',
                         'author': 'Hong Kong Property Monitor',
                         'comments': 'Generated automatically from the dashboard dataset.'})
    base = {'font_name': 'Arial', 'font_size': 10, 'font_color': '#24344A', 'valign': 'vcenter'}
    formats = {
        'title': book.add_format(base | {'font_size': 17, 'bold': True}),
        'subtitle': book.add_format(base | {'font_color': '#526479', 'text_wrap': True}),
        'header': book.add_format(base | {'bold': True, 'bg_color': '#153C56', 'font_color': '#FFFFFF', 'text_wrap': True}),
        'label': book.add_format(base | {'bold': True}),
        'warning': book.add_format(base | {'bg_color': '#FFF2CC', 'font_color': '#795500', 'text_wrap': True}),
        'link': book.add_format(base | {'font_color': '#087EA4', 'underline': 1}),
    }
    for band, color in enumerate(('#FFFFFF', '#F1F6F9')):
        for kind, number_format in (('text', None), ('number', '#,##0.00;[Red](#,##0.00);0.00'),
                                    ('integer', '#,##0'), ('month', 'mmm yyyy'),
                                    ('date', 'dd mmm yyyy'), ('datetime', 'dd mmm yyyy hh:mm'), ('factor', '0.00000000')):
            formats[kind, band] = book.add_format(base | {'bg_color': color} |
                ({'num_format': number_format} if number_format else {}))
    sheets = {name: book.add_worksheet(name) for name in SHEETS}

    def cell(ws, row, col, value, kind='text'):
        fmt = formats[kind, row % 2]
        if value is None:
            ws.write_blank(row, col, None, fmt)
        elif isinstance(value, (dict, list)):
            ws.write_string(row, col, json.dumps(value, ensure_ascii=False), fmt)
        else:
            ws.write(row, col, value, fmt)

    def prepare(name, subtitle, headers, widths, row_count):
        ws = sheets[name]
        ws.hide_gridlines(2)
        ws.set_default_row(19)
        ws.set_zoom(90)
        ws.write(0, 0, name, formats['title'])
        ws.set_row(0, 28)
        ws.merge_range(1, 0, 2, min(7, len(headers)-1), subtitle, formats['subtitle'])
        ws.merge_range(3, 0, 3, min(7, len(headers)-1), f'{row_count:,} records | Full history | Use the header filters to select periods and series.', formats['subtitle'])
        ws.set_row(3, 24)
        for col, (header, width) in enumerate(zip(headers, widths)):
            ws.set_column(col, col, width)
            ws.write(HEADER_ROW, col, header, formats['header'])
        ws.set_row(HEADER_ROW, 32)
        ws.freeze_panes(HEADER_ROW+1, 2)
        ws.autofilter(HEADER_ROW, 0, HEADER_ROW + row_count, len(headers)-1)
        ws.repeat_rows(HEADER_ROW)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
        return ws

    overview = sheets['Overview']
    overview.hide_gridlines(2)
    overview.set_column('A:A', 29)
    overview.set_column('B:B', 27)
    overview.set_column('C:H', 14)
    overview.set_default_row(23)
    overview.freeze_panes(2, 0)
    overview.write(0, 0, 'Hong Kong Property Monitor', formats['title'])
    overview.set_row(0, 32)
    overview.merge_range('A2:H2', 'Excel data download | Residential, commercial, sales and mortgages', formats['subtitle'])
    metadata = [(3, 'Checked at (Hong Kong)', hk_datetime(dataset['checked_at']), 'datetime'),
                (4, 'Snapshot date', dt.datetime.fromisoformat(dataset['as_of']), 'date'),
                (5, 'Latest monthly observation', max((r['period'] for r in dataset['observations']), default='None'), 'text'),
                (6, 'PDF edition / latest month', f"{dataset.get('report', {}).get('edition', 'Unknown')} / {dataset.get('report', {}).get('latest_period', 'Unknown')}", 'text'),
                (7, 'sq m per sq ft (exact)', SQM_PER_SQFT, 'factor')]
    for row, label, value, kind in metadata:
        overview.write(row, 0, label, formats['label']); cell(overview, row, 1, value, kind)
        if row == 5:
            overview.merge_range('C6:H6', 'Latest month varies by series; a recent download does not mean every source has new data.', formats['subtitle'])
            overview.set_row(row, 32)
    overview.merge_range('C8:H8', 'HKD per sq ft = HKD per sq m × this factor. Original values are retained.', formats['subtitle'])
    warnings = dataset.get('errors', [])
    overview.merge_range('A10:H11', ('SOURCE REVIEW: ' + ' | '.join(warnings)) if warnings else 'Source checks: no refresh errors reported in this snapshot.', formats['warning'] if warnings else formats['subtitle'])
    overview.merge_range('A12:H13', 'Blank means unavailable, not zero. P = provisional; X/Y/Z = fewer than 5/10/20 cases. Rates use displayed percent values (e.g. 3.26 with % p.a.). PDF/CSV differences are preserved for review.', formats['subtitle'])
    overview.write_row(14, 0, ['Worksheet', 'Records'], formats['header'])
    overview.merge_range('C15:H15', 'Contents', formats['header'])
    detail = [(name, len(groups[name]), description) for name, description in zip(MONTHLY_SHEETS,
        ('Average prices by size class and region; HKD/sq m and HKD/sq ft.',
         'Average monthly rents by size class and region; both floor-area units.',
         'Residential price/rental indices (1999=100) and market yields.',
         'Office, retail and industrial prices, rents, indices and yields.',
         'Residential registration counts/values and mortgage statistics.'))]
    detail += [('PDF Tables', len(dataset.get('pdf_observations', [])), 'Original PDF cells; annual, quarterly, monthly, YTD and forecasts kept separate.'),
               ('Source Checks', len(dataset.get('source_status', [])), 'Source status, freshness, PDF/CSV comparisons and differences.'),
               ('Revisions', len(dataset.get('revisions', [])), 'Previously observed values revised by official sources.')]
    for row, (name, count, description) in enumerate(detail, 15):
        overview.write_url(row, 0, f"internal:'{name}'!A1", formats['link'], name)
        cell(overview, row, 1, count, 'integer')
        overview.merge_range(row, 2, row, 7, description, formats['subtitle'])
        overview.set_row(row, 31)
    overview.write(24, 0, 'Total monthly observations', formats['label'])
    overview.write_formula(24, 1, '=SUM(B16:B20)', formats['integer', 0], len(dataset['observations']))
    overview.merge_range('A27:H28', 'Monthly code refresh: GitHub Actions checks official sources and regenerates this file on day 1 at 10:00 Hong Kong time. No ChatGPT session is required. This downloaded copy is static; download again to receive a newer snapshot.', formats['subtitle'])
    overview.write_url('A30', WEB, formats['link'], 'Open dashboard / download latest')
    overview.merge_range('A32:H33', 'Residential size classes (saleable floor area): A <40 sq m; B 40–69.9; C 70–99.9; D 100–159.9; E ≥160. Office A–C are building grades, not residential size classes.', formats['subtitle'])

    headers = ['Reference month', 'Series', 'Property type', 'Class / grade', 'Region', 'Original value', 'Original unit',
               'Value per sq ft', 'Per sq ft unit', 'Status', 'Flags', 'Source table', 'Series ID', 'Source ID', 'Source URL', 'Interpretation', 'Original source note']
    widths = [18, 35, 18, 15, 25, 19, 26, 19, 28, 23, 10, 14, 45, 17, 55, 75, 80]
    for name, rows in groups.items():
        ws = prepare(name, 'Original source values are retained. Per-square-foot values are formula-linked conversions where applicable. Percent and index series are not converted.', headers, widths, len(rows))
        for i, record in enumerate(rows, HEADER_ROW+1):
            unit = record['unit']; converted = unit in ('HKD / sq m', 'HKD / sq m / month')
            values = [dt.datetime.strptime(record['period'], '%Y-%m'), record.get('metric_name'), record.get('property_type', 'Residential'),
                record.get('grade') or record.get('class_name'), record.get('region') or 'All Hong Kong', record['value'], unit, None,
                unit.replace('sq m', 'sq ft') if converted else None, record.get('status'), record.get('flags'), record.get('source_table'),
                record['metric_id'], record.get('source_id'), record.get('source_url'), notes_for(record), record.get('note')]
            for col, value in enumerate(values):
                cell(ws, i, col, value, 'month' if col == 0 else 'number' if col in (5, 7) else 'text')
            if converted:
                ws.write_formula(i, 7, f'=IF(ISNUMBER(F{i+1}),F{i+1}*Overview!$B$8,"")', formats['number', i%2],
                                 record['value'] * SQM_PER_SQFT if record['value'] is not None else '')

    pdf = dataset.get('pdf_observations', [])
    fields = ['period','frequency','observation_kind','table_id','column','value','unit','provisional','fewer_than_20_transactions','missing','pdf_page','source_edition','raw_cell','source_pdf']
    ws = prepare('PDF Tables', 'Direct code extraction from the official PDF. Mixed frequencies and forecasts are separate observations: do not add them together or append them to the monthly series.',
        ['Period','Frequency','Observed / forecast','Table','Column','Value','Unit','Provisional','Under 20 cases','Missing','PDF page','Edition','Original cell','Source PDF'],
        [18,18,23,12,40,18,25,15,18,13,12,16,22,65], len(pdf))
    for i, record in enumerate(pdf, HEADER_ROW+1):
        for col, field in enumerate(fields):
            cell(ws, i, col, record.get(field), 'number' if field == 'value' else 'integer' if field == 'pdf_page' else 'text')

    statuses = dataset.get('source_status', [])
    ws = prepare('Source Checks', 'A successful download is not proof of a new reference month. Retained sources and PDF/CSV differences remain visible. Comparison details appear below the source status table.',
        ['Source ID','Source','Status','Latest period','Rows','Checked (Hong Kong)','Last success (Hong Kong)','Changes','Source URL'],
        [20,50,35,17,15,25,28,45,65], len(statuses))
    for i, record in enumerate(statuses, HEADER_ROW+1):
        values = [record.get(k) for k in ('source_id','source_name','status','latest_period','rows')]
        values += [hk_datetime(record.get(k)) for k in ('checked_at','last_success')]
        values += [record.get('change_summary'), record.get('source_url')]
        for col, value in enumerate(values):
            cell(ws, i, col, value, 'integer' if col == 4 else 'datetime' if col in (5,6) else 'text')
    pos = HEADER_ROW + len(statuses) + 4
    ws.write(pos, 0, 'PDF / CSV comparison', formats['title']); pos += 2
    ws.write_row(pos, 0, ['Table','Status','Compared cells','Differences','CSV URL','CSV SHA256'], formats['header']); pos += 1
    for record in dataset.get('report', {}).get('comparisons', []):
        for col, field in enumerate(('table_id','status','compared_cells','mismatch_count','csv_source','csv_sha256')):
            cell(ws, pos, col, record.get(field), 'integer' if col in (2,3) else 'text')
        pos += 1
    pos += 2
    ws.write_row(pos, 0, ['Table','Period','Column','PDF value','CSV value'], formats['header']); pos += 1
    for comparison in dataset.get('report', {}).get('comparisons', []):
        for record in comparison.get('mismatches', []):
            for col, value in enumerate([comparison['table_id'], record.get('period'), record.get('column'), record.get('pdf'), record.get('csv')]):
                cell(ws, pos, col, value, 'number' if col in (3,4) else 'text')
            pos += 1

    revisions = dataset.get('revisions', [])
    ws = prepare('Revisions', 'Historical value revisions detected during refresh. Old and new values use the original series unit; a blank is not zero.',
        ['Series ID','Period','Previous value','Revised value','Detected (Hong Kong)','Original unit'], [50,18,22,22,26,28], len(revisions))
    units = {r['metric_id']: r['unit'] for r in dataset['observations']}
    for i, record in enumerate(reversed(revisions), HEADER_ROW+1):
        values = [record['metric_id'], record['period'], record.get('old'), record.get('new'), hk_datetime(record.get('detected_at')), units.get(record['metric_id'])]
        for col, value in enumerate(values):
            cell(ws, i, col, value, 'number' if col in (2,3) else 'datetime' if col == 4 else 'text')


def _sheet_rows(archive, number):
    """Read the writer's inline-string XML without a second production dependency."""
    with archive.open(f'xl/worksheets/sheet{number}.xml') as file:
        for _, element in ET.iterparse(file, events=('end',)):
            if element.tag != '{'+NS['s']+'}row':
                continue
            values = {}
            for cell in element.findall('s:c', NS):
                column = ''.join(c for c in cell.attrib['r'] if c.isalpha())
                raw = cell.find('s:v', NS)
                if cell.attrib.get('t') == 'inlineStr':
                    value = ''.join(cell.itertext())
                elif raw is None or raw.text is None:
                    value = None
                elif cell.attrib.get('t') in ('str','e'):
                    value = raw.text
                else:
                    value = float(raw.text)
                if cell.attrib.get('t') == 'e':
                    raise ValueError(f'Excel cell error: {cell.attrib["r"]}={value}')
                values[column] = value
            yield int(element.attrib['r']), values
            element.clear()


def validate_excel(path, dataset):
    groups = monthly_groups(dataset)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('Invalid XLSX archive')
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        names = [s.attrib['name'] for s in workbook.findall('s:sheets/s:sheet', NS)]
        if names != list(SHEETS):
            raise ValueError(f'Unexpected worksheets: {names}')
        for number, name in enumerate(MONTHLY_SHEETS, 2):
            expected = {(r['metric_id'], r['period']): r for r in groups[name]}
            seen = set()
            for row_number, cells in _sheet_rows(archive, number):
                if row_number <= HEADER_ROW+1:
                    continue
                period = (dt.datetime(1899, 12, 30) + dt.timedelta(days=cells['A'])).strftime('%Y-%m')
                key = (cells['M'], period)
                if key in seen or key not in expected:
                    raise ValueError(f'Unexpected Excel observation: {key}')
                seen.add(key); source = expected[key]
                original = source['value']; exported = cells.get('F')
                same_value = exported is None if original is None else exported is not None and math.isclose(exported, original, rel_tol=1e-14, abs_tol=1e-14)
                if not same_value or cells.get('G') != source['unit']:
                    raise ValueError(f'Excel value/unit mismatch: {key}')
                conversion = source['unit'] in ('HKD / sq m','HKD / sq m / month')
                derived = cells.get('H')
                if conversion and source['value'] is not None:
                    if derived is None or not math.isclose(derived, source['value']*SQM_PER_SQFT, rel_tol=1e-12, abs_tol=1e-10):
                        raise ValueError(f'Excel conversion mismatch: {key}')
                elif derived not in (None, ''):
                    raise ValueError(f'Unexpected converted value: {key}')
            if seen != set(expected):
                raise ValueError(f'Excel rows missing: {name}')
        for number, field in ((7,'pdf_observations'), (9,'revisions')):
            count = sum(row > HEADER_ROW+1 for row, cells in _sheet_rows(archive, number))
            if count != len(dataset.get(field, [])):
                raise ValueError(f'Excel row count mismatch: {field}')
    return {'monthly_rows': len(dataset['observations']), 'worksheets': len(SHEETS)}


def build_excel(dataset, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    groups = monthly_groups(dataset)
    fd, temporary = tempfile.mkstemp(suffix='.xlsx', dir=destination.parent)
    os.close(fd)
    try:
        _write_workbook(dataset, temporary, groups)
        validate_excel(temporary, dataset)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.dataset).read_text())
    build_excel(data, args.output)
    print(json.dumps({'output': args.output, **validate_excel(args.output, data)}))
