"""Read-only DTU material-direction study. Standard library, no solver imports.

The OOXML reader reads values and shared-formula provenance, never evaluates
arbitrary Excel expressions, external links, macros, or network references.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from zipfile import ZipFile
import xml.etree.ElementTree as ET

DEFAULT_INPUT = Path('/home/ubuntu/.hermes/reports/sludge-material-design-v2')
HERE = Path(__file__).resolve().parent
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def col_number(text):
    result = 0
    for letter in text:
        result = 26 * result + ord(letter) - 64
    return result


def col_name(number):
    result = ''
    while number:
        number, digit = divmod(number - 1, 26)
        result = chr(65 + digit) + result
    return result


def coordinate(addr):
    match = re.fullmatch(r'([A-Z]+)(\d+)', addr)
    if not match:
        raise ValueError('invalid cell coordinate')
    return col_number(match[1]), int(match[2])


def translate_formula(text, source, target):
    """Translate shared A1 references, preserving absolute refs and quoted text.

    Not an Excel engine: formula strings are provenance only. No expression is
    executed. Structured table references are retained as provenance, not
    resolved or evaluated by this translator.
    """
    sc, sr = coordinate(source)
    tc, tr = coordinate(target)
    def move(match):
        ac, c, ar, r = match.groups()
        nc = col_number(c) + (0 if ac else tc - sc)
        nr = int(r) + (0 if ar else tr - sr)
        if nc < 1 or nr < 1:
            raise ValueError('invalid translated formula reference')
        return ac + col_name(nc) + ar + str(nr)
    chunks = re.split(r'("(?:[^"]|"")*"|\'(?:[^\']|\'\')*\')', text)
    for i in range(0, len(chunks), 2):
        chunks[i] = re.sub(r'(?<![A-Za-z0-9_])(\$?)([A-Z]{1,3})(\$?)(\d+)(?![A-Za-z0-9_])', move, chunks[i])
    return ''.join(chunks)


@dataclass(frozen=True)
class Cell:
    value: object = None
    formula: str | None = None
    kind: str = 'n'
    shared_anchor: str | None = None


@dataclass
class Sheet:
    name: str
    cells: dict[str, Cell]
    state: str
    dimension: str
    merged_ranges: list[str]
    def __getitem__(self, addr):
        return self.cells.get(addr, Cell())
    def value(self, addr):
        return self[addr].value
    @property
    def row_numbers(self):
        return sorted({coordinate(a)[1] for a, c in self.cells.items() if c.value is not None or c.formula is not None})


def read_workbook(path):
    result = {}
    with ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(t.text or '' for t in si.findall('.//m:t', NS))
                      for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {r.attrib['Id']: r.attrib['Target']
                for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
                if r.attrib.get('TargetMode') != 'External'}
        nodes = ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS)
        if nodes is None:
            raise ValueError('workbook has no sheets')
        for node in nodes:
            target = rels[node.attrib['{' + REL + '}id']]
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            if '..' in target.split('/'):
                raise ValueError('unsupported workbook path')
            root = ET.fromstring(z.read(target))
            cells, anchors, pending = {}, {}, []
            for c in root.findall('.//m:sheetData/m:row/m:c', NS):
                addr, kind = c.attrib['r'], c.attrib.get('t', 'n')
                value_node, formula_node = c.find('m:v', NS), c.find('m:f', NS)
                value = value_node.text if value_node is not None else None
                if kind == 's' and value is not None:
                    value = shared[int(value)]
                elif kind == 'inlineStr':
                    value = ''.join(t.text or '' for t in c.findall('.//m:t', NS))
                elif kind == 'n' and value is not None:
                    value = float(value)
                    if not math.isfinite(value):
                        raise ValueError('nonfinite input')
                formula, anchor = None, None
                if formula_node is not None:
                    formula = formula_node.text or ''
                    if formula_node.attrib.get('t') == 'shared':
                        idx = formula_node.attrib['si']
                        if formula:
                            anchors[idx] = (addr, formula)
                            anchor = addr
                        else:
                            pending.append((addr, idx))
                cells[addr] = Cell(value, formula, kind, anchor)
            for addr, idx in pending:
                anchor, text = anchors[idx]
                cells[addr] = Cell(cells[addr].value, translate_formula(text, anchor, addr), cells[addr].kind, anchor)
            dim = root.find('m:dimension', NS)
            result[node.attrib['name']] = Sheet(node.attrib['name'], cells,
                node.attrib.get('state', 'visible'), dim.attrib['ref'] if dim is not None else '',
                [m.attrib['ref'] for m in root.findall('m:mergeCells/m:mergeCell', NS)])
    return result


MATERIAL_FIELDS = 'source_id material_id material_class original_label property value unit basis file sheet cell identity_status'.split()
OBSERVATION_FIELDS = 'source_id specimen_id matrix_id additive_id additive_fraction_dry firing_temperature_C property value unit replicate_id file sheet cell evidence_status'.split()
ALIASES = {
    '#0250': ('Y', 'clay'), '#0252': ('R', 'clay'),
    '#0262': ('SSA-P1-Raw', 'sewage_sludge_ash'),
    'Pilot-8': ('SSA-P1-ED', 'sewage_sludge_ash'),
    '#0263': ('SSA-P2-Raw', 'sewage_sludge_ash'),
    'Pilot-10': ('SSA-P2-ED', 'sewage_sludge_ash'),
    'SSA-Av-Raw': ('SSA-P1-Raw', 'sewage_sludge_ash'),
    'SSA-Av-ED': ('SSA-P1-ED', 'sewage_sludge_ash'),
    'SSA-Ly-Raw': ('SSA-P2-Raw', 'sewage_sludge_ash'),
    'SSA-Ly-ED': ('SSA-P2-ED', 'sewage_sludge_ash'),
}
ALIASES.update({v[0]: v for v in list(ALIASES.values())})


def resolve_identity(label):
    if label in ALIASES:
        material, kind = ALIASES[label]
        return material, kind, 'resolved'
    return 'unresolved:' + str(label), 'unknown', 'identity_ambiguous'


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def dry_fraction(clay, ash, *, basis, unit):
    if basis != 'dry' or unit not in ('g', 'kg') or not all(number(x) and x >= 0 for x in (clay, ash)):
        return None
    return ash / (clay + ash) if clay + ash > 0 else None


class Study:
    def __init__(self, input_dir):
        self.input_dir = Path(input_dir)
        self.manifest = json.loads((self.input_dir / 'download-manifest.json').read_text())
        self.books, self.files, self.input_hashes = {}, {}, []
        for item in self.manifest:
            path = self.input_dir / 'public-data' / str(item['dataset_id']) / item['name']
            data = path.read_bytes()
            sha, md5 = hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()
            if sha != item['sha256'] or md5 != item['md5'] or len(data) != item['bytes']:
                raise ValueError('source checksum/size mismatch: ' + item['name'])
            self.input_hashes.append({'file': str(path.relative_to(self.input_dir)), 'sha256': sha, 'md5': md5, 'bytes': len(data)})
            if item['name'].endswith('.xlsx'):
                sid = str(item['dataset_id'])
                self.books[sid] = read_workbook(path)
                self.files[sid] = str(path.relative_to(self.input_dir))
        self.materials, self.observations, self.derivations = [], [], []
        self.used = set()
        self.material_evidence, self.conditions = [], []
        self.imputations = []
        self.summary_exclusions = set()

    def use(self, sid, sheet, cells):
        for cell in cells:
            self.used.add((sid, sheet, cell))

    def material(self, sid, sheet, cell, label, prop, unit, basis, *, derived=False):
        identity, kind, status = resolve_identity(label)
        source = self.books[sid][sheet][cell]
        value = source.value if number(source.value) else None
        self.materials.append(dict(zip(MATERIAL_FIELDS, [sid, identity, kind, label, prop, value, unit, basis, self.files[sid], sheet, cell, status])))
        self.material_evidence.append({'source_id': sid, 'sheet': sheet, 'cell': cell,
            'evidence_status': 'missing' if value is None else 'source_derived' if derived or source.formula is not None else 'measured',
            'formula': source.formula})
        self.use(sid, sheet, [cell])

    def observation(self, sid, sheet, cell, specimen, matrix, additive, fraction, temp, prop, unit, replicate='', derived=False, ambiguous=False):
        source = self.books[sid][sheet][cell]
        value = source.value if number(source.value) else None
        status = 'identity_ambiguous' if ambiguous else 'missing' if value is None else 'source_derived' if derived or source.formula is not None else 'measured'
        row = dict(zip(OBSERVATION_FIELDS, [sid, specimen, matrix, additive, fraction, temp, prop, value, unit, replicate, self.files[sid], sheet, cell, status]))
        self.observations.append(row)
        self.use(sid, sheet, [cell])
        return row

    def derived(self, sid, sheet, cell, inputs, expression, recomputed, *, scale=1):
        """Compare independent Python arithmetic to ORIGINAL workbook caches."""
        source = self.books[sid][sheet][cell]
        cached = source.value
        difference = recomputed - cached * scale if number(cached) and number(recomputed) else None
        record = {'source_id': sid, 'file': self.files[sid], 'sheet': sheet, 'cell': cell,
            'source_formula': source.formula, 'shared_anchor': source.shared_anchor,
            'inputs': inputs, 'expression': expression, 'cached_value': cached, 'cached_scale': scale,
            'recomputed_value': recomputed, 'difference': difference,
            'absolute_tolerance': 1e-8, 'verified': difference is not None and abs(difference) <= 1e-8}
        self.derivations.append(record)
        return record

    def import_xrf(self):
        sid, sheet = '30156127', 'Sheet1'
        ws = self.books[sid][sheet]
        for col in 'BCDEFGH':
            for row in list(range(2, 17)) + [18, 20]:
                self.material(sid, sheet, f'{col}{row}', ws.value(col+'1'), 'xrf_'+ws.value(f'A{row}'), 'wt%', 'source_oxide_plus_LOI1050_total_pct', derived=row==20)
            inputs = [f'{col}{r}' for r in list(range(2,17))+[18] if number(ws.value(f'{col}{r}'))]
            self.derived(sid, sheet, col+'20', [{'sheet':sheet,'cell':a} for a in inputs],
                'sum(reported numeric oxide contents and reported LOI); omitted components not assigned physical zero',
                sum(ws.value(a) for a in inputs))
        # Source calculated mixtures, not independent specimens or new XRF tests.
        for c in range(2, 14):
            col = col_name(c)
            label = ws.value(col+'28')
            matrix = 'Y' if c < 8 else 'R'
            raw_add = ws.value(col+'27')
            additive, _, identity = resolve_identity(raw_add) if raw_add is not None else ('', '', 'resolved')
            fraction = 0.3 if raw_add is not None else 0.0
            for row in range(29, 40):
                prop = ws.value(f'A{row}')
                self.observation(sid, sheet, f'{col}{row}', 'mix:'+label, matrix, additive, fraction, None,
                    'mixture_xrf_'+prop, 'wt%', derived=True, ambiguous=identity != 'resolved')
                raw_row = next(r for r in list(range(2, 17)) + [20] if ws.value(f'A{r}') == prop)
                matrix_col = 'B' if matrix == 'Y' else 'C'
                matrix_cell = f'{matrix_col}{raw_row}'
                inputs = [matrix_cell]
                recomputed = ws.value(matrix_cell)
                if raw_add is not None:
                    add_col = next(k for k in 'DEFGH' if ws.value(k+'1') == raw_add)
                    inputs.append(f'{add_col}{raw_row}')
                    recomputed = (1-fraction)*recomputed + fraction*ws.value(inputs[-1])
                self.derived(sid, sheet, f'{col}{row}', [{'sheet': sheet, 'cell': a} for a in inputs],
                    '0.7*matrix + 0.3*ash' if fraction else 'matrix (reference)', recomputed)

    def import_tga(self):
        sid = '30157066'
        for sheet, ws in self.books[sid].items():
            identity, kind, status = resolve_identity(sheet)
            condition = {'source_id': sid, 'curve_id': 'tga:'+sheet, 'original_label': ws.value('B16'),
                'material_id': identity, 'material_class': kind, 'identity_status': status,
                'atmosphere': 'N2', 'atmosphere_source': '30157066-metadata.json description',
                'heating_rate_K_min': 10, 'range_source': sheet+'!B28', 'range_original': ws.value('B28'),
                'sample_mass_mg': ws.value('B17'), 'geometry': ws.value('B21'),
                'kinetic_identifiability': 'unknown_single_heating_rate',
                'drying': 'clay 7 d 50 C; SSA 24 h 105 C (metadata)',
                'transfer_exclusion': 'not air oxidation; not raw sewage sludge; not full brick'}
            self.conditions.append(condition)
            self.material(sid, sheet, 'B17', sheet, 'tga_sample_mass', 'mg', 'instrument_initial_sample_mass')
            self.use(sid, sheet, ['B16', 'B21', 'B28'])
            dtg_col = next(coordinate(a)[0] for a, c in ws.cells.items() if coordinate(a)[1] == 32 and isinstance(c.value, str) and c.value.startswith('DTG/'))
            for row in ws.row_numbers:
                if row < 33 or not number(ws.value(f'A{row}')):
                    continue
                for col, prop, unit in [('A', 'tga_temperature', 'degC'), ('B', 'tga_time', 'min'),
                        ('C', 'tga_mass_change', 'mg'), (col_name(dtg_col), 'tga_dtg', 'mg/min')]:
                    self.material(sid, sheet, f'{col}{row}', sheet, prop, unit, 'N2_instrument_signed_signal_not_air_oxidation', derived=prop=='tga_dtg')
                    if prop=='tga_dtg':
                        self.material_evidence[-1].update(method_status='unknown_instrument_algorithm',
                            method='instrument-reported derivative; raw time/mass channels retained; smoothing/window unknown',
                            input_channels=['A:temperature','B:time','C:mass_change'], independently_recomputed=False)
                if ws.value('D32') == 'Mass loss %':
                    # Diagnostic of local-column interpretation only. Structured
                    # Table refs are preserved, never silently evaluated as C(row).
                    check = self.derived(sid, sheet, f'D{row}', [{'sheet': sheet, 'cell': f'C{row}'}, {'sheet': sheet, 'cell': 'B17'}],
                        'diagnostic local_C / initial_mass * 100; NOT evaluation of structured Table reference',
                        ws.value(f'C{row}') / ws.value('B17') * 100)
                    check['role'] = 'excluded_source_percent_diagnostic'

    def import_psd(self):
        sid, sheet = '30156970', 'Sheet2'
        ws = self.books[sid][sheet]
        for col, cumulative in [('F', 'G'), ('H', 'I'), ('J', 'K'), ('L', 'M'), ('O', 'P'), ('Q', 'R')]:
            raw = ws.value(col+'4')
            label = raw if col not in ('O', 'Q') else raw+' | '+ws.value(col+'5')
            total = 0.0
            inputs = []
            for row in ws.row_numbers:
                if row < 7 or not number(ws.value(f'{col}{row}')) or not number(ws.value(f'E{row}')):
                    continue
                basis = 'volume_distribution_ethanol_dried_milled_as_labeled'
                self.material(sid, sheet, f'E{row}', label, 'psd_size_coordinate', 'um', basis)
                self.material(sid, sheet, f'{col}{row}', label, 'psd_bin_volume', '%', basis)
                self.material(sid, sheet, f'{cumulative}{row}', label, 'psd_cumulative_volume', '%', basis)
                total += ws.value(f'{col}{row}')
                inputs.append({'sheet': sheet, 'cell': f'{col}{row}'})
                self.derived(sid, sheet, f'{cumulative}{row}', list(inputs), 'sum(bin_volume from row 7 through current row)', total)

    def import_pellets(self):
        """Explicit, inspected block map; headers and source-mass joins gate it.

        These are within-study labels, not proof of laboratory chain-of-custody.
        A2P records never pass the identity gate, even if numerical joins match.
        """
        sid = '30157108'
        mixing = self.books[sid]['Mixing']
        wb = self.books[sid]['Water and Burning']
        hd = self.books[sid]['High and Diameter']
        pd = self.books[sid]['Porosity and Density']
        # short label, mixing row, HD first row/column offset, WB first row/offset, PD first row
        blocks = [('Ref', 43, 9, 0, 9, 0, 14),
                  ('P1-Raw', 44, 60, 0, 59, 0, 36),
                  ('P1-ED', 45, 60, 26, 59, 5, 56),
                  ('P2-Raw', 46, 110, 0, 110, 0, 78),
                  ('P2-ED', 47, 110, 26, 110, 5, 98),
                  ('A2P-unresolved', 48, 160, 0, 9, 5, 120)]
        for label, mix_start, hd_start, hd_off, wb_start, wb_off, pd_start in blocks:
            for matrix, raw_matrix, mr, dr, pr in [('Y', '#0250', 0, 0, 0), ('R', '#0252', 10, 7, 3)]:
                for ti, temp in enumerate((1020, 1030, 1050)):
                    ambiguous = label == 'A2P-unresolved'
                    additive = '' if label == 'Ref' else 'unresolved:A2P' if ambiguous else 'SSA-'+label
                    group = f'{matrix}|{label}|{temp}'
                    mixrow, mixcol = mix_start + mr, 9 * ti
                    m_clay, m_ash = f'{col_name(4+mixcol)}{mixrow}', f'{col_name(5+mixcol)}{mixrow}'
                    fraction = dry_fraction(mixing.value(m_clay), mixing.value(m_ash), basis='dry', unit='g')
                    if fraction != (0.0 if label == 'Ref' else 0.3):
                        raise ValueError('unknown dry-basis mixing fraction')
                    hstart = hd_start + 16*ti + dr
                    wstart = wb_start + 16*ti + dr
                    pstart = pd_start + 6*ti + pr
                    hc = lambda n, row: f'{col_name(n+hd_off)}{row}'
                    wc = lambda n, row: f'{col_name(n+wb_off)}{row}'
                    if raw_matrix not in str(hd.value(hc(1, hstart))) or wb.value('A'+str(wstart)) != raw_matrix or pd.value('B'+str(pstart)) != raw_matrix:
                        raise ValueError('sample matrix header mismatch')
                    if not ambiguous:
                        raw_add = {'Ref': '', 'P1-Raw': '#0262', 'P1-ED': 'Pilot-8', 'P2-Raw': '#0263', 'P2-ED': 'Pilot-10'}[label]
                        expected = raw_matrix + ('-'+raw_add if raw_add else '')
                        pd_label = pd.value('C'+str(pd_start))
                        pd_identity = '' if pd_label == 'Ref' else resolve_identity(pd_label)[0]
                        if hd.value(hc(1,hstart)) != expected or pd_identity != additive:
                            raise ValueError('sample additive identity mismatch')
                    if str(temp) not in str(hd.value(hc(13, hd_start+16*ti-2))) or str(temp) not in str(wb.value('A'+str(wb_start+16*ti-2))) or str(temp) not in str(pd.value('A'+str(pd_start+6*ti))):
                        raise ValueError('firing temperature header mismatch')
                    self.conditions.append({'source_id': sid, 'group_id': group, 'matrix_id': matrix,
                        'additive_id': additive, 'additive_fraction_dry': fraction, 'firing_temperature_C': temp,
                        'identity_status': 'identity_ambiguous' if ambiguous else 'resolved',
                        'original_hd_label': hd.value(hc(1, hd_start+16*ti-2)),
                        'original_hd_material': hd.value(hc(1, hstart)),
                        'original_pd_label': pd.value('C'+str(pd_start)),
                        'dry_fraction_sources': ['Mixing!'+m_clay, 'Mixing!'+m_ash, 'Mixing!D15:E17'],
                        'hd_range': f'{hc(1,hstart)}:{hc(25,hstart+6)}',
                        'wb_range': f'{wc(3,wstart)}:{wc(7,wstart+6)}', 'pd_range': f'E{pstart}:R{pstart+2}',
                        'geometry': 'small discs; nominal 4 g green; dimensions measured in mm',
                        'replicates_produced': 7, 'replicates_water_tested': 3,
                        'atmosphere': 'unknown', 'heating_rate_K_min': None, 'hold_time_min': None,
                        'drying': 'brick discs 105 C 24 h (Mixing!B32)',
                        'batch_independence': 'one recorded mix per series; no independent batch validation'})
                    self.use(sid, 'Mixing', [m_clay, m_ash])
                    for ri, rep in enumerate('ABCDEFG'):
                        specimen = group+'|'+rep
                        hr, wr = hstart+ri, wstart+ri
                        if str(hd.value(hc(2, hr))).strip().split()[-1] != rep or wb.value('B'+str(wr)) != rep:
                            raise ValueError('replicate header mismatch')
                        common = (specimen, matrix, additive, fraction, temp)
                        # Raw diameter/height triplicates are readings of ONE disc.
                        for prefix, first in [('dry_diameter',3), ('dry_height',7), ('fired_diameter',14), ('fired_height',18)]:
                            for reading in range(3):
                                self.observation(sid, hd.name, hc(first+reading,hr), *common, f'{prefix}_reading_{reading+1}', 'mm', rep, ambiguous=ambiguous)
                                addr = hc(first+reading,hr)
                                formula = hd[addr].formula
                                if formula is not None:
                                    match = re.fullmatch(r'AVERAGE\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)',formula)
                                    if not match or match[1]!=match[3] or int(match[4])>=hr:
                                        raise ValueError('unknown derived reading; manual audit required')
                                    inputs=[f'{match[1]}{r}' for r in range(int(match[2]),int(match[4])+1)]
                                    self.derived(sid,hd.name,addr,[{'sheet':hd.name,'cell':a} for a in inputs],
                                        'source-imputed reading = mean(other discs); NOT an independent measurement',statistics.mean(hd.value(a) for a in inputs))
                                    self.imputations.append({'source_id':sid,'sheet':hd.name,'cell':addr,'specimen_id':specimen,
                                        'property':f'{prefix}_reading_{reading+1}','formula':formula,'input_cells':inputs,
                                        'reason':'source mean of other specimens; preserve source value but exclude dependent statistics'})
                                    dimension='diameter' if 'diameter' in prefix else 'height'
                                    for prop in (prefix+'_mean',dimension+'_shrinkage','volume_shrinkage',prefix.split('_')[0]+'_geometric_volume'):
                                        self.summary_exclusions.add((specimen,prop))
                        for n, prop, unit in [(6,'dry_diameter_mean','mm'), (10,'dry_height_mean','mm'),
                                (17,'fired_diameter_mean','mm'), (21,'fired_height_mean','mm'),
                                (11,'dry_geometric_volume','mm3'), (22,'fired_geometric_volume','mm3'),
                                (23,'diameter_shrinkage','%'), (24,'height_shrinkage','%'), (25,'volume_shrinkage','%')]:
                            self.observation(sid, hd.name, hc(n,hr), *common, prop, unit, rep, derived=True, ambiguous=ambiguous)
                        means = {}
                        for first, dest in [(3,6),(7,10),(14,17),(18,21)]:
                            inputs = [hc(first+k,hr) for k in range(3)]
                            mean = statistics.mean(hd.value(a) for a in inputs)
                            means[dest] = mean
                            self.derived(sid, hd.name, hc(dest,hr), [{'sheet':hd.name,'cell':a} for a in inputs], 'mean(3 readings of same disc)', mean)
                        volumes = {11: math.pi*(means[6]/2)**2*means[10], 22: math.pi*(means[17]/2)**2*means[21]}
                        for dest, inputs in [(11,[3,4,5,7,8,9]),(22,[14,15,16,18,19,20])]:
                            self.derived(sid, hd.name, hc(dest,hr), [{'sheet':hd.name,'cell':hc(a,hr)} for a in inputs], 'pi*(mean(diameter)/2)^2*mean(height)', volumes[dest])
                        for dest, before, after, inputs in [(23,means[6],means[17],[3,4,5,14,15,16]),
                                (24,means[10],means[21],[7,8,9,18,19,20]), (25,volumes[11],volumes[22],[3,4,5,7,8,9,14,15,16,18,19,20])]:
                            self.derived(sid, hd.name, hc(dest,hr), [{'sheet':hd.name,'cell':hc(a,hr)} for a in inputs], '100*(dry-fired)/dry (from raw readings)', 100*(before-after)/before)
                        for n, prop, unit in [(3,'green_mass','g'),(4,'dried_mass_105C','g'),(6,'fired_mass','g'),
                                (5,'forming_water_content','%'),(7,'firing_mass_loss','%')]:
                            self.observation(sid, wb.name, wc(n,wr), *common, prop, unit, rep, derived=n in (5,7), ambiguous=ambiguous)
                        for dest, before, after in [(5,3,4),(7,4,6)]:
                            cells = [wc(before,wr), wc(after,wr)]
                            a, b = [wb.value(c) for c in cells]
                            self.derived(sid, wb.name, wc(dest,wr), [{'sheet':wb.name,'cell':c} for c in cells], '100*(mass_before-mass_after)/mass_before', 100*(a-b)/a)
                        if ri >= 3:
                            continue
                        row = pstart+ri
                        if pd.value('D'+str(row)) != rep:
                            raise ValueError('water test replicate mismatch')
                        mass_ref = pd['E'+str(row)].formula
                        if mass_ref != "'Water and Burning'!"+wc(6,wr) or not math.isclose(pd.value('E'+str(row)), wb.value(wc(6,wr)), abs_tol=1e-12):
                            raise ValueError('cross-sheet specimen mass join mismatch')
                        for col, prop, unit in [('F','saturated_mass','g'),('G','submerged_mass','g'),
                                ('K','water_displacement_volume','m3'),('L','open_pore_volume','m3'),
                                ('M','open_porosity','m3/m3'),('N','dry_density','kg/m3'),
                                ('O','apparent_solid_density','kg/m3'),('P','saturated_density','kg/m3'),('Q','water_absorption','kg/kg')]:
                            self.observation(sid, pd.name, f'{col}{row}', *common, prop, unit, rep, derived=col not in 'FG', ambiguous=ambiguous)
                        dry, sat, sub = [pd.value(f'{c}{row}') for c in 'EFG']
                        rho = pd.value('L10')
                        vol, pores = (sat-sub)*1e-3/rho, (sat-dry)*1e-3/rho
                        derived = {'K':vol,'L':pores,'M':(sat-dry)/(sat-sub),'N':dry*1e-3/vol,
                            'O':dry*1e-3/(vol-pores),'P':sat*1e-3/vol,'Q':(sat-dry)/dry}
                        expressions = {'K':'(sat_g-sub_g)*1e-3/rho_water','L':'(sat_g-dry_g)*1e-3/rho_water',
                            'M':'(sat_g-dry_g)/(sat_g-sub_g)','N':'dry_g*rho_water/(sat_g-sub_g)',
                            'O':'dry_g*rho_water/(dry_g-sub_g)','P':'sat_g*rho_water/(sat_g-sub_g)',
                            'Q':'(sat_g-dry_g)/dry_g'}
                        for dest, computed in derived.items():
                            self.derived(sid, pd.name, f'{dest}{row}', [{'sheet':wb.name,'cell':wc(6,wr)},
                                {'sheet':pd.name,'cell':f'F{row}'},{'sheet':pd.name,'cell':f'G{row}'},
                                {'sheet':pd.name,'cell':'L10'}], expressions[dest], computed)

    def summarize(self):
        """No calibration, fit, hypothesis test, train/test split or interpolation."""
        records = {}
        for row in self.observations:
            if row['source_id'] != '30157108' or row['evidence_status'] in ('identity_ambiguous','missing'):
                continue
            if (row['specimen_id'],row['property']) in self.summary_exclusions:
                continue
            group = row['specimen_id'].rsplit('|',1)[0]
            records.setdefault(group, {}).setdefault(row['property'], []).append(row)
        result = []
        for group, props in sorted(records.items()):
            rows = props['diameter_shrinkage']
            first = rows[0]
            summary = {k:first[k] for k in ['matrix_id','additive_id','additive_fraction_dry','firing_temperature_C']}
            summary.update(group_id=group, evidence_status='model_derived', n_shrinkage=len(rows),
                n_water=len(props['water_absorption']), n_volume=len(props['volume_shrinkage']), n_independent_batches=None)
            for prop in ['diameter_shrinkage','volume_shrinkage','water_absorption','open_porosity','dry_density']:
                samples = props[prop]
                if len({r['specimen_id'] for r in samples}) != len(samples):
                    raise ValueError('duplicate specimens in group')
                values = [r['value'] for r in samples]
                summary[prop+'_mean'] = statistics.mean(values)
                summary[prop+'_sd'] = statistics.stdev(values) if len(values)>1 else None
            summary['shrinkage_specimens'] = [r['specimen_id'] for r in rows]
            summary['water_specimens'] = [r['specimen_id'] for r in props['water_absorption']]
            summary['volume_specimens'] = [r['specimen_id'] for r in props['volume_shrinkage']]
            if not set(summary['water_specimens']) <= set(summary['shrinkage_specimens']):
                raise ValueError('unmatched water specimens')
            result.append(summary)
        return result


def input_snapshot(input_dir):
    input_dir = Path(input_dir)
    manifest = json.loads((input_dir/'download-manifest.json').read_text())
    paths = [input_dir / name for name in ['DIRECTION_BRIEF.md','download-manifest.json','selected-datasets.json',
        'workbook-inventory.json','dtu-collection.json','dtu-items.json']]
    paths += [input_dir/(sid+'-metadata.json') for sid in ['30156127','30157066','30157108','30156970']]
    for item in manifest:
        if str(item['dataset_id']) not in ('30156127','30157066','30157108','30156970') or Path(item['name']).name != item['name']:
            raise ValueError('unsupported input manifest entry')
        paths.append(input_dir/'public-data'/str(item['dataset_id'])/item['name'])
    return {str(p.relative_to(input_dir)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def run(input_dir=DEFAULT_INPUT, output_dir=HERE/'artifacts'):
    from reporting import export, dump_json
    import time
    import resource
    start = time.perf_counter()
    output = Path(output_dir).resolve()
    if not output.is_relative_to(HERE) or output == HERE:
        raise ValueError('output must be a subdirectory of experiments/material_design_v2')
    before = input_snapshot(input_dir)
    study = Study(input_dir)
    study.import_xrf()
    study.import_tga()
    study.import_psd()
    study.import_pellets()
    failed = [d for d in study.derivations if not d.get('role') and not d['verified']]
    if failed:
        raise ValueError('source recomputation mismatch in selected data')
    counts = export(study, output)
    after = input_snapshot(input_dir)
    if before != after:
        raise ValueError('inputs changed during run')
    result = {'status':'ok_research_only_pending_review','counts':counts,'input_sha256_before':before,
        'input_sha256_after':after,'input_hashes_unchanged':before==after,
        'raw_file_checks':study.input_hashes,'elapsed_seconds':time.perf_counter()-start,
        'peak_rss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'runtime':'Python standard library; serial; no core solver imports; no network calls',
        'tests':'not run by pipeline; see verification.json from verify.py'}
    dump_json(output/'pipeline_run.json',result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=DEFAULT_INPUT)
    parser.add_argument('--output-dir',type=Path,default=HERE/'artifacts')
    args = parser.parse_args()
    result = run(args.input_dir,args.output_dir)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))
