"""Extract original instrument columns with cell locations; never fit kinetics.

Standard-library only. Original XML numeric strings are kept in the CSV;
SI columns use decimal unit conversions, not clipping or curve smoothing.
"""
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

BASE = Path(__file__).resolve().parent
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
EXPECTED = '57de3dc8b44cc9dfb13c07fe83b2ae939939eac0ed87a1fc4fb122d8e98b2084'


def extract():
    original = BASE / 'tga-record.xlsx'
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise ValueError('original_workbook_hash_mismatch')
    with zipfile.ZipFile(original) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheet = workbook.find('s:sheets/s:sheet', NS)
        if sheet is None or sheet.attrib['name'] != 'Praveen_UPES':
            raise ValueError('unexpected_first_sheet')
        # The hash fixes workbook relationships; still check the expected mapping.
        rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        rid = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
        target = next(e.attrib['Target'] for e in rels if e.attrib['Id'] == rid)
        if target not in ('worksheets/sheet1.xml', '/xl/worksheets/sheet1.xml'):
            raise ValueError('unexpected_sheet_relationship')
        tree = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        strings = [ ''.join(e.itertext()) for e in ET.fromstring(archive.read('xl/sharedStrings.xml')) ]
    cells = {c.attrib['r']: c for c in tree.findall('.//s:sheetData/s:row/s:c', NS)}

    def value(address):
        cell = cells[address]
        raw = cell.find('s:v', NS).text
        return strings[int(raw)] if cell.attrib.get('t') == 's' else raw

    if [value(f'{c}27') for c in 'ABCDE'] != ['min', 'Cel', 'uV', 'ug', 'ug/min']:
        raise ValueError('unexpected_source_units')
    rows = []
    for row_number in range(28, 11603):
        raw = [value(f'{c}{row_number}') for c in 'ABCDE']
        numbers = list(map(Decimal, raw))
        if not all(n.is_finite() for n in numbers):
            raise ValueError(f'nonfinite_row:{row_number}')
        time, temperature, _, mass, _ = numbers
        rows.append((row_number, *raw, str(time*60), str(temperature+Decimal('273.15')),
                     str(mass*Decimal('1e-9'))))
    with (BASE/'tga-observations.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(('source_row','time_min','temperature_c','dta_uv','mass_ug','dtg_ug_min',
                         'time_s','temperature_k','mass_kg'))
        writer.writerows(rows)
    time = [Decimal(r[1]) for r in rows]
    temperature = [Decimal(r[2]) for r in rows]
    mass = [Decimal(r[4]) for r in rows]
    if not all(a < b for a, b in zip(time, time[1:])):
        raise ValueError('time_not_strictly_increasing')
    audit = {
        'source_doi': '10.17632/r4tb4nbsbc.1', 'original_sha256': digest,
        'original_sheet': 'Praveen_UPES', 'original_cells': 'A28:E11602',
        'observations': len(rows), 'independent_runs': 1,
        'time_range_min': [str(time[0]), str(time[-1])],
        'temperature_range_c': [str(min(temperature)), str(max(temperature))],
        'first_mass_ug': str(mass[0]), 'last_mass_ug': str(mass[-1]),
        'reported_sample_weight_mg': value('B6'), 'sample_name': value('B5'),
        'source_gas_statement': value('B16'),
        'program_start_c': value('C10'), 'program_end_c': value('D10'),
        'program_ramp_c_min': value('E10'), 'program_hold_min': value('F10'),
        'mass_increase_steps_preserved': sum(b > a for a, b in zip(mass, mass[1:])),
        'temperature_decrease_steps_preserved': sum(b < a for a, b in zip(temperature, temperature[1:])),
        'unit_conversions': {'time_s': 'A*60', 'temperature_k': 'B+273.15', 'mass_kg': 'D*1e-9'},
        'dta_is_heat_flow': False, 'kinetic_parameters_fitted': False,
        'independent_holdout_available_in_this_workbook': False,
        'source_formulas_outside_A_E_used': False,
        'qualification': 'single_instrument_run_not_cross_rate_validation_or_material_parameter_pack',
        'csv_sha256': hashlib.sha256((BASE/'tga-observations.csv').read_bytes()).hexdigest(),
        'extractor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (BASE/'tga-extraction-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    extract()
