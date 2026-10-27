"""RVD monthly commercial statistics. No LLM, OCR, interpolation or district averaging."""
import calendar
import csv
import io
import math
import re

DISTRICTS = ['Sheung Wan', 'Central', 'Wan Chai / Causeway Bay', 'North Point / Quarry Bay', 'Tsim Sha Tsui', 'Yau Ma Tei / Mong Kok', 'Kowloon Bay / Kwun Tong']
REGIONS = ['Hong Kong', 'Kowloon', 'New Territories']
TABLES = {
    '2.1': ('Office', 'average_rent', 'PRIVATE OFFICES - AVERAGE RENTS', [f'Grade {g} {d}' for g in 'ABC' for d in DISTRICTS]),
    '2.2': ('Office', 'average_price', 'PRIVATE OFFICES - AVERAGE PRICES', [f'Grade {g} {d}' for g in 'ABC' for d in DISTRICTS]),
    '2.3': ('Office', 'rental_index', 'PRIVATE OFFICES - RENTAL INDICES', ['Grade A', 'Grade B', 'Grade C', 'Overall']),
    '2.4': ('Office', 'price_index', 'PRIVATE OFFICES - PRICE INDICES', ['Grade A', 'Grade B', 'Grade C', 'Overall']),
    '3.1': ('Retail', 'average', 'PRIVATE RETAIL - AVERAGE RENTS AND PRICES', [f'{m} ({r})' for m in ['Rents', 'Prices'] for r in REGIONS]),
    '3.2': ('Retail', 'index', 'PRIVATE RETAIL - RENTAL AND PRICE INDICES', ['Rents', 'Prices']),
    '4.1': ('Industrial', 'average', 'PRIVATE FLATTED FACTORIES - AVERAGE RENTS AND PRICES', [f'{m} ({r})' for m in ['Rents', 'Prices'] for r in REGIONS]),
    '4.2': ('Industrial', 'index', 'PRIVATE FLATTED FACTORIES - RENTAL AND PRICE INDICES', ['Rents', 'Prices']),
    '5.2': ('Commercial', 'yield', 'PROPERTY MARKET YIELDS - PRIVATE NON-DOMESTIC', ['Offices - Grade A', 'Offices - Grade B', 'Flatted Factories', 'Retail']),
}
LABELS = {'average_rent': 'Average rent', 'average_price': 'Average price', 'rental_index': 'Rental index', 'price_index': 'Price index', 'yield': 'Market yield'}

def parse(table, raw, as_of):
    sector, measure, expected_title, columns = TABLES[table]
    data = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    if len(data) < 3 or expected_title not in ' '.join(data[0][0].split()):
        raise ValueError(f'{table}: publication title changed')
    expected = ['Month'] + [item for column in columns for item in (column, column + ' - Remarks')]
    if data[1] != expected:
        raise ValueError(f'{table}: column names or order changed')
    result = []
    for cells in data[2:]:
        if not cells or not any(cell.strip() for cell in cells): continue
        if not re.fullmatch(r'\d{2}-\d{4}', cells[0]) or len(cells) != len(expected):
            raise ValueError(f'{table}: malformed monthly record')
        mm, year = map(int, cells[0].split('-'))
        date = f'{year:04d}-{mm:02d}-{calendar.monthrange(year, mm)[1]:02d}'
        if date < '1999-01-01' or date > as_of: continue
        record = dict(zip(expected, cells))
        for column in columns:
            text = record[column].strip(); flags = record[column + ' - Remarks'].strip()
            value = None if text.upper() in ('', '-', '^', '~', 'N.A.', 'N/A') else float(text.replace(',', ''))
            if value is not None and (not math.isfinite(value) or value < 0): raise ValueError(f'{table}: invalid value')
            kind = measure
            if measure in ('average', 'index'):
                kind = ('average_rent' if column.startswith('Rents') else 'average_price') if measure == 'average' else ('rental_index' if column == 'Rents' else 'price_index')
            property_type = ('Office' if column.startswith('Offices') else 'Industrial' if column == 'Flatted Factories' else 'Retail') if measure == 'yield' else sector
            grade_match = re.search(r'Grade ([ABC])', column)
            grade = grade_match[1] if grade_match else 'All'
            if sector == 'Office' and measure.startswith('average'): region = column[8:]
            elif measure == 'average': region = column.split('(', 1)[1].rstrip(')')
            else: region = 'All Hong Kong'
            if region == 'Hong Kong': region = 'Hong Kong Island'
            unit = 'HKD / sq m / month' if kind == 'average_rent' else 'HKD / sq m' if kind == 'average_price' else '%' if kind == 'yield' else '1999=100'
            result.append(dict(market='HK', property_type=property_type, measure=kind,
                metric_id='rvd_' + table.replace('.', '_') + '_' + re.sub('[^a-z0-9]+', '_', column.lower()).strip('_'),
                metric_name=property_type + ' ' + LABELS[kind].lower(), category='yield' if kind == 'yield' else 'rent' if 'rent' in kind else 'price',
                period=date[:7], date=date, value=value, unit=unit, frequency='M', grade=grade, class_name=grade, region=region,
                area_basis='internal floor area', source_name='Rating and Valuation Department', source_url=f'https://www.rvd.gov.hk/datagovhk/{table}M.csv',
                source_table=table, source_field=column, flags=flags, status='Provisional' if 'P' in flags else 'Published',
                small_sample=any(flag in flags for flag in 'XYZ'), missing_reason='No published value; see source notes' if value is None else None,
                fetch_mode='automatic_csv', note='Office grades describe building quality, not dwelling size. Industrial covers private flatted factories. Missing values are not zero; averages are transaction-mix sensitive. X/Y/Z indicate fewer than 5/10/20 cases.'))
    if not result or len({(r['metric_id'], r['period']) for r in result}) != len(result):
        raise ValueError(f'{table}: empty or duplicate source')
    return result

def collect(table, cache, as_of, fetch):
    raw = fetch(f'https://www.rvd.gov.hk/datagovhk/{table}M.csv')
    if len(raw) > 30_000_000: raise ValueError('Commercial CSV exceeds size limit')
    rows = parse(table, raw, as_of)
    (cache / f'{table}M.csv').write_bytes(raw)
    return rows
