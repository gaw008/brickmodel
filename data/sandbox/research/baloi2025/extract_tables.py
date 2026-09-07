"""Reproduce printed tables and explicitly derived room-temperature quantities.

Baloi, Streza and Belean (2025), DOI 10.1371/journal.pone.0328270,
CC BY 4.0. This is evidence extraction, not a qualified brick parameter pack.
"""
from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET


def extract(directory: Path) -> dict:
    source = directory / 'originals/article.xml'
    root = ET.parse(source).getroot()
    tables = {}
    for table in root.findall('.//table-wrap'):
        rows = []
        for row in table.findall('.//tr'):
            cells = [{'text': ' '.join(''.join(cell.itertext()).split()),
                      'attributes': dict(cell.attrib)} for cell in row if cell.tag in ('th', 'td')]
            if cells:
                rows.append(cells)
        tables[table.attrib['id']] = rows
    ids = [f'pone.0328270.t00{i}' for i in (1, 2, 3)]
    if not all(name in tables for name in ids):
        raise ValueError('required_original_tables_missing')
    densities = {row[0]['text']: float(row[2]['text'])*1000
                 for row in tables[ids[1]][1:]}
    derived = []
    for row in tables[ids[2]][1:]:
        name = row[0]['text']
        alpha_scaled, effusivity, reported_k = [float(row[i]['text']) for i in (1, 2, 3)]
        # The printed scaled alpha column is alpha*10^7; recover SI alpha.
        alpha = alpha_scaled*1e-7
        rho = densities[name]
        if not all(math.isfinite(v) and v > 0 for v in (alpha, rho, effusivity, reported_k)):
            raise ValueError('nonpositive_printed_property')
        derived_k = effusivity*math.sqrt(alpha)
        derived.append({
            'sample': name, 'alpha_m2_s': alpha, 'density_kg_m3': rho,
            'effusivity_w_s_half_m2_k': effusivity, 'reported_k_w_m_k': reported_k,
            'recomputed_k_w_m_k': derived_k,
            'k_recomputation_relative_difference': (derived_k-reported_k)/reported_k,
            'derived_effective_cp_j_kg_k': effusivity/(rho*math.sqrt(alpha)),
            'method': 'k=e*sqrt(alpha); apparent_cp=e/(rho*sqrt(alpha))',
            'upstream_locators': [ids[1], ids[2], 'section 2.4'],
            'qualification': 'derived_post_firing_effective_value_not_green_or_high_temperature_cp',
            'uncertainty': 'joint_covariance_and_cp_uncertainty_not_available',
        })
    return {
        'source_id': 'baloi-streza-belean-2025-pone0328270',
        'doi': '10.1371/journal.pone.0328270', 'license': 'CC-BY-4.0',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'extractor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'status': 'candidate_evidence_not_runtime_material_qualified',
        'table_cells_verbatim_whitespace_normalized': tables,
        'derived_rows': derived,
        'basis_notes': [
            'Table1 proportions are volumetric; no dry-mass conversion is made.',
            'Density g/cm3 multiplied by1000; alpha displayed as alpha*10^7.',
            'Cp is newly derived using homogeneous effective heat-diffusion identities, not directly measured.',
            'Printed thermal uncertainty cells retain rowspan; no per-row confidence interval is invented.',
        ],
    }


if __name__ == '__main__':
    folder = Path(__file__).resolve().parent
    result = extract(folder)
    (folder/'tables_and_derivations.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(f"Extracted {len(result['derived_rows'])} paired post-firing rows")
