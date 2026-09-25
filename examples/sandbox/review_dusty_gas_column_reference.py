"""Compare independent vectorized original DGM equations with saved MP integrals."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from dusty_gas_column_reference import ColumnReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    anchors = json.loads((root/p['reference_anchors']).read_text())
    settings = deepcopy(p)
    settings['geometry']['length_m'] = 2*anchors['settings']['distance_m']
    header = {key: anchors[key] for key in ['gas_constant_j_mol_k', 'molar_masses_kg_mol',
        'pure_viscosities_pa_s', 'diffusivity_pressure_products_pa_m2_s']}
    header.update(settings=settings, cell_count=2)
    reference = ColumnReference(header)
    budget = p['verification']
    records = []
    for row in anchors['face_reviews']:
        if row['quadrature_order'] != anchors['settings']['quadrature_orders'][-1]:
            continue
        concentrations = np.asarray([row['left_partial_concentrations_mol_m3'], row['right_partial_concentrations_mol_m3']])
        actual = reference.evaluate(concentrations.ravel())
        mp_flux = np.asarray(row['reference_fluxes_decimal'], dtype=float)
        mp_entropy = float(row['reference_entropy_decimal'])*settings['geometry']['area_m2']
        errors = {'flux_mol_m2_s': float(np.max(np.abs(actual['flux'][0]-mp_flux))),
            'entropy_rate_w_k': abs(float(actual['production'][0])-mp_entropy),
            'path_entropy_rate_w_k': abs(float(actual['path_production'][0])-mp_entropy),
            'original_equation_mol_m4': actual['original_equation_residual_mol_m4']}
        limits = {'flux_mol_m2_s': budget['source_flux_absolute_budget_mol_m2_s'],
            'entropy_rate_w_k': budget['source_entropy_rate_budget_w_k'],
            'path_entropy_rate_w_k': budget['source_entropy_rate_budget_w_k'],
            'original_equation_mol_m4': budget['reference_equation_residual_budget_mol_m4']}
        records.append({'case': row['case'], 'errors': errors,
            'within_budgets': {key: error <= limits[key] for key, error in errors.items()}})
    result = {'settings': p, 'records': records,
        'all_requested_budgets_met': all(all(row['within_budgets'].values()) for row in records),
        'reference_scope': 'Saved 60-digit original-equation face integrals, rounded once for this binary64 comparison. Independent full Wilke coefficient matrix and direct nonsymmetric total-flux solve.',
        'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'all_requested_budgets_met': result['all_requested_budgets_met']}), flush=True)


if __name__ == '__main__':
    main()
