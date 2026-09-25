"""Source-formula, pure-limit and species-order review of Wilke viscosity."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport
from sludge_sandbox.wilke_gas_mixture import wilke_viscosity_pa_s


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    pure_p = json.loads((root/p['pure_property_parameters']).read_text())
    provider = NonpolarGasTransport(pure_p)
    names, budget = p['species_order'], p['review']
    mp.mp.dps = budget['decimal_precision']
    masses = np.array([float(pure_p['species'][name]['molar_mass_g_mol'])*float(pure_p['constants']['gram_kg']) for name in names])
    compositions = [('mixture', np.asarray(x, dtype=float)) for x in p['compositions']]
    if budget['include_pure_limits']:
        compositions += [(f'pure_{names[i]}', row) for i, row in enumerate(np.eye(len(names)))]
    if budget['include_equal_binary_compositions']:
        for i, j in combinations(range(len(names)), 2):
            row = np.zeros(len(names)); row[i] = row[j] = 0.5
            compositions.append((f'binary_{names[i]}_{names[j]}', row))
    permutation = budget['species_permutation']
    records = []
    for temperature in p['temperatures_k']:
        viscosities = np.array([provider.viscosity_pa_s(temperature, name) for name in names])
        eta, mass = list(map(mp.mpf, viscosities)), list(map(mp.mpf, masses))
        weights = [[(1+mp.sqrt(eta[i]/eta[j])*(mass[j]/mass[i])**mp.mpf('0.25'))**2
            /mp.sqrt(8*(1+mass[i]/mass[j])) for j in range(len(names))] for i in range(len(names))]
        for label, fractions in compositions:
            x = list(map(mp.mpf, fractions))
            reference = mp.fsum(x[i]*eta[i]/mp.fsum(weights[i][j]*x[j] for j in range(len(names))) for i in range(len(names)))
            actual = wilke_viscosity_pa_s(fractions, viscosities, masses)
            permuted = wilke_viscosity_pa_s(fractions[permutation], viscosities[permutation], masses[permutation])
            error = float(abs(mp.mpf(actual['viscosity_pa_s'])-reference))
            weight_error = max(float(abs(mp.mpf(actual['weighting_factors'][i,j])-weights[i][j])) for i in range(len(names)) for j in range(len(names)))
            permutation_error = abs(actual['viscosity_pa_s']-permuted['viscosity_pa_s'])
            pure_error = abs(actual['viscosity_pa_s']-float(viscosities[np.argmax(fractions)])) if label.startswith('pure_') else None
            allowed = budget['absolute_viscosity_budget_pa_s']+budget['relative_budget']*float(abs(reference))
            flags = {'source_viscosity': error <= allowed,
                'source_weights': weight_error <= budget['absolute_weight_budget'],
                'permutation': permutation_error <= allowed, 'positive_viscosity': actual['viscosity_pa_s'] > 0}
            if pure_error is not None:
                flags['pure_limit'] = pure_error <= allowed
            records.append({'temperature_k': temperature, 'case': label, 'mole_fractions': fractions.tolist(),
                'pure_viscosities_pa_s': viscosities.tolist(), 'actual_viscosity_pa_s': actual['viscosity_pa_s'],
                'reference_viscosity_decimal': str(reference), 'weighting_factors': actual['weighting_factors'].tolist(),
                'errors': {'viscosity_pa_s': error, 'weight': weight_error, 'permutation_pa_s': permutation_error,
                    'pure_limit_pa_s': pure_error}, 'within_budgets': flags})
    output = {'settings': p, 'pure_property_settings': pure_p, 'records': records,
        'all_requested_budgets_met': all(all(row['within_budgets'].values()) for row in records),
        'reference_scope': '80-digit direct all-pairs source formula on actual binary64 pure inputs; production uses triangular reciprocal weights. Pure-property accuracy remains the separate source/experimental review.',
        'mixture_experimentally_validated': False, 'material_qualified': False, 'training_eligible': False}
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'cases': len(records), 'all_requested_budgets_met': output['all_requested_budgets_met']}), flush=True)


if __name__ == '__main__':
    main()
