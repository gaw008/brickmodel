"""Restricted crystalline-product affinity roots, distinct from kinetic onset."""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp
from scipy.optimize import brentq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase
from sludge_sandbox.recorded_gas_reactions import standard_reaction
from review_hydrogen_steam_thermochemistry import thermal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    thermo = json.loads((root / p['thermochemistry_parameters']).read_text())
    source = json.loads((root / thermo['source_file']).read_text())
    steam = json.loads((root / thermo['steam_source_file']).read_text())
    data = {**source['phases'], 'H2O': steam['phases']['H2O']}
    mp.mp.dps = p['decimal_digits']
    t0 = mp.mpf(source['reference_temperature_k'])
    r = mp.mpf(source['gas_constant_j_mol_k'])
    p0 = mp.mpf(source['reference_pressure_pa'])
    phases = {name: RecordedThermalPhase(tuple(map(float, item['cp_coefficient_strings'])), float(t0),
        float(item['reference_enthalpy_j_mol']), float(item['reference_entropy_j_mol_k']),
        tuple(thermo['selected_temperature_domain_k'])) for name, item in data.items()}
    rows = []
    for name, nu in thermo['reactions'].items():
        for pressure in p['steam_partial_pressures_pa']:
            log_p = math.log(pressure / float(p0))
            def nominal(t):
                return standard_reaction(phases, nu, t, float(r))['gibbs_j_mol'] + nu['H2O'] * float(r) * t * log_p
            def independent(t):
                return mp.fsum(coefficient * thermal(data[phase], t, t0)['gibbs_j_mol']
                    for phase, coefficient in nu.items()) + nu['H2O'] * r * t * mp.log(mp.mpf(pressure) / p0)
            numerical = p['root_parameters']
            temperature = brentq(nominal, *p['temperature_bracket_k'], xtol=numerical['absolute_tolerance_k'],
                rtol=numerical['relative_tolerance'], maxiter=numerical['maximum_iterations'])
            reference = mp.findroot(independent, tuple(map(mp.mpf, p['temperature_bracket_k'])), solver='anderson')
            difference = float(abs(mp.mpf(temperature) - reference))
            rows.append({'reaction': name, 'steam_partial_pressure_pa': pressure,
                'affinity_zero_temperature_k': temperature, 'independent_temperature_k': str(reference),
                'independent_temperature_difference_k': difference,
                'reaction_gibbs_residual_j_mol_extent': nominal(temperature),
                'within_numerical_budget': difference <= p['independent_temperature_difference_budget_k']})
    result = {'settings': p, 'boundaries': rows,
        'all_numerical_budgets_met': all(row['within_numerical_budget'] for row in rows),
        'experimental_dehydroxylation_onsets': False, 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
