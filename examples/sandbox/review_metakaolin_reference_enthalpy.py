"""Trace reference reaction enthalpy to a published hydration mass/heat basis."""
import argparse
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    source = json.loads((root / p['source_file']).read_text())
    kaol = json.loads((root / p['usgs_kaolinite_file']).read_text())['phases']['kaolinite']
    steam = json.loads((root / p['usgs_steam_file']).read_text())['phases']['H2O']
    cantisani = json.loads((root / p['cantisani_file']).read_text())
    D = Decimal
    with localcontext() as context:
        context.prec = p['decimal_precision']
        h = {k: D(v) for k, v in source['formation_enthalpies_kj_mol'].items()}
        kcal = D(p['joules_per_kilojoule'])
        q = D(source['calorimetry']['heat_released_j_per_g_calcined_clay']) / kcal
        dq = D(source['calorimetry']['reported_margin_j_per_g_calcined_clay']) / kcal
        mass = D(source['mixture']['mass_ratios_CC_CH_gypsum'][2])
        rows = []
        for reported in source['reported_metakaolinite']:
            x, y = D(reported['Ca_Si']), D(reported['water_per_Si'])
            ch, water = 3+2*x, 23+2*y-2*x
            # Cement notation expands to the stated oxide/hydrate amounts.
            reactants = {'Ca': ch+3, 'Al': D(2), 'Si': D(2), 'S': D(3),
                'O': 7+2*ch+18+water, 'H': 2*ch+12+2*water}
            products = {'Ca': 6+2*x, 'Al': D(2), 'Si': D(2), 'S': D(3),
                'O': 50+2*(x+2+y), 'H': 64+4*y}
            residual = {k: products[k]-reactants[k] for k in reactants}
            base = h['ettringite'] + 2*h[reported['CSH_key']] - ch*h['portlandite'] - 3*h['gypsum'] - water*h['liquid_water']
            for basis in p['mass_bases']:
                extent = mass*D(basis['gypsum_fraction']) / D(p['gypsum_molar_mass_g_mol']) / 3
                hr, margin = -q/extent, dq/extent
                hf = base-hr
                independent = math.fsum([float(h['ettringite']), 2*float(h[reported['CSH_key']]),
                    -float(ch)*float(h['portlandite']), -3*float(h['gypsum']),
                    -float(water)*float(h['liquid_water']),
                    float(q)*3*float(p['gypsum_molar_mass_g_mol'])/(float(mass)*float(basis['gypsum_fraction']))])
                error = abs(independent-float(hf))
                rows.append({'Ca_Si': str(x), 'water_per_Si': str(y), 'mass_basis': basis,
                    'stoichiometry_CH_water': [str(ch), str(water)], 'element_residuals': {k: str(v) for k,v in residual.items()},
                    'extent_mol_MK_per_g_CC': str(extent), 'reaction_enthalpy_kj_mol_MK': str(hr),
                    'inferred_formation_enthalpy_kj_mol': str(hf),
                    'heat_measurement_only_propagated_margin_kj_mol': str(margin),
                    'reported_center_difference_kj_mol': str(hf-D(reported['formation_enthalpy_kj_mol'])),
                    'inside_author_reported_margin': abs(hf-D(reported['formation_enthalpy_kj_mol'])) <= D(reported['reported_margin_kj_mol']),
                    'independent_float_absolute_difference_kj_mol': error,
                    'arithmetic_within_budget': error <= p['independent_float_absolute_budget_kj_mol']})
        common_kaol = D(kaol['reference_enthalpy_j_mol']) / kcal
        common_steam = D(steam['reference_enthalpy_j_mol']) / kcal
        candidates = [{'label': 'Muzenda_reported_CaSi_1.67', 'hf': D(source['reported_metakaolinite'][0]['formation_enthalpy_kj_mol'])},
            {'label': 'Cantisani_printed', 'hf': D(str(cantisani['table1']['metakaolin']['formation_enthalpy_j_mol']))/kcal},
            {'label': 'Weise_secondary_quote_only', 'hf': D(source['reported_secondary_comparison']['formation_enthalpy_kj_mol'])}]
        reference = [{'label': c['label'], 'metakaolin_formation_enthalpy_kj_mol': str(c['hf']),
            'USGS_common_parent_steam_dehydroxylation_enthalpy_kj_mol': str(c['hf']+2*common_steam-common_kaol),
            'qualified_reaction_heat': False} for c in candidates]
        result = {'settings': p, 'source': source, 'hydration_reconstructions': rows,
            'common_reference_dehydroxylation_sensitivity': reference,
            'reference_basis': {'temperature_k': p['reference_temperature_k'],
                'USGS_kaolinite_formation_enthalpy_kj_mol': str(common_kaol),
                'USGS_steam_formation_enthalpy_kj_mol': str(common_steam)},
            'all_arithmetic_within_budgets': all(row['arithmetic_within_budget'] for row in rows),
            'scope': 'Reference enthalpy arithmetic and mass-basis sensitivity only. No high-temperature Cp/S closure, finite-rate heat coupling, source error correction or independent material validation.',
            'material_qualified': False, 'training_eligible': False}
    out = root / p['output_directory']
    with (out / 'review.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_arithmetic_within_budgets': result['all_arithmetic_within_budgets'],
        'hydration_reconstructions': rows, 'common_reference_dehydroxylation_sensitivity': reference}))


if __name__ == '__main__':
    main()
