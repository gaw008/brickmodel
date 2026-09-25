"""Primary-source binary viscosity replay and mixture-observation comparison."""
import argparse
import json
from pathlib import Path

import mpmath as mp

from run_co2_n2_reference_dusty_gas import reference_properties
from sludge_sandbox.chapman_enskog_binary_viscosity import (
    binary_viscosity_pa_s, interaction_viscosity_from_molar_diffusion,
)
from sludge_sandbox.co2_n2_diffusion import CarbonDioxideNitrogenDiffusion


def source_matrix_viscosity(x, eta, masses, interaction, a_star):
    """Unreduced source H matrix, independently solved at80-digit precision."""
    fractions = [mp.mpf(x), 1-mp.mpf(x)]
    h = mp.matrix(2)
    for i, j in [(0, 1), (1, 0)]:
        coefficient = (2*fractions[i]*fractions[j]*masses[i]*masses[j]
                       / (interaction*(masses[i]+masses[j])**2))
        h[i, i] = fractions[i]**2/eta[i] + coefficient*(5/(3*a_star)+masses[j]/masses[i])
        h[i, j] = -coefficient*(5/(3*a_star)-1)
    velocity = mp.lu_solve(h, mp.matrix(fractions))
    return mp.fsum(fractions[i]*velocity[i] for i in range(2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    observations = json.loads((root/p['measurement_parameters']).read_text())
    column = json.loads((root/observations['property_parameters']).read_text())
    diffusion_settings = json.loads((root/column['property_sources']['CO2_N2_diffusion']).read_text())
    diffusion = CarbonDioxideNitrogenDiffusion(diffusion_settings)
    q = p['review']
    mp.mp.dps = q['decimal_precision']
    rows, arithmetic, limits = [], [], []
    unit = mp.mpf(observations['micro_pa_s_to_pa_s'])
    cross_sections = {r['temperature_k']: r for r in p['cross_section_rows']}
    for observation in observations['rows']:
        temperature = observation['temperature_k']
        source = cross_sections[temperature]
        properties = reference_properties(dict(column, temperature_k=float(temperature)), root)
        masses = list(map(mp.mpf, properties['molar_masses_kg_mol']))
        a_star = mp.mpf(source['A_star'])
        pure_table = [mp.mpf(observation[k])*unit for k in ['pure_CO2_micro_pa_s', 'pure_N2_micro_pa_s']]
        rho_d = diffusion.molar_density_diffusivity(float(temperature))
        inferred = interaction_viscosity_from_molar_diffusion(rho_d, list(map(float, masses)), float(a_star))
        independent_interaction = mp.mpf(rho_d)/(mp.mpf(3)/5*(1/masses[0]+1/masses[1])*a_star)
        arithmetic.append({'temperature_k': temperature, 'kind': 'molar_form_of_Eq31',
                           'relative_error': float(abs(mp.mpf(inferred)/independent_interaction-1))})
        for index, nitrogen in enumerate(observations['nitrogen_mole_fractions']):
            x = 1-mp.mpf(nitrogen)
            target = mp.mpf(observation['mixture_micro_pa_s'][index])*unit
            configurations = {
                'source_replay_not_validation': (pure_table, mp.mpf(source['source_inferred_interaction_viscosities_micro_pa_s'][index])*unit),
                'ab_initio_diffusion_with_table_pure': (pure_table, mp.mpf(inferred)),
                'ab_initio_diffusion_with_reference_pure': (list(map(mp.mpf, properties['pure_viscosities_pa_s'])), mp.mpf(inferred)),
            }
            for name, (pure, interaction) in configurations.items():
                expected = source_matrix_viscosity(x, pure, masses, interaction, a_star)
                actual = binary_viscosity_pa_s(float(x), list(map(float, pure)), list(map(float, masses)),
                                               float(interaction), float(a_star))
                arithmetic.append({'temperature_k': temperature, 'kind': name, 'nitrogen_mole_fraction': nitrogen,
                                   'relative_error': float(abs(mp.mpf(actual)/expected-1))})
                budget = q['source_replay_relative_budget'] if name == 'source_replay_not_validation' else q['prediction_relative_screen']
                difference = float(expected/target-1)
                rows.append({'temperature_k': temperature, 'nitrogen_mole_fraction': nitrogen, 'path': name,
                             'source_target_pa_s': float(target), 'mixture_pa_s': actual,
                             'independent_matrix_pa_s_decimal': str(expected), 'interaction_viscosity_pa_s': float(interaction),
                             'signed_relative_difference': difference, 'comparison_budget': budget,
                             'within_budget': abs(difference) <= budget})
        pure = properties['pure_viscosities_pa_s']
        for x in q['endpoint_mole_fractions'] + q['interior_mole_fractions']:
            x = float(x)
            actual = binary_viscosity_pa_s(x, pure, list(map(float, masses)), inferred, float(a_star))
            swapped = binary_viscosity_pa_s(1-x, pure[::-1], list(map(float, masses[::-1])), inferred, float(a_star))
            expected = (mp.mpf(pure[0 if x == 1 else 1]) if x in (0, 1) else
                        source_matrix_viscosity(mp.mpf(x), list(map(mp.mpf, pure)), masses, mp.mpf(inferred), a_star))
            limits.append({'temperature_k': temperature, 'CO2_mole_fraction': x,
                           'source_relative_difference': float(abs(mp.mpf(actual)/expected-1)),
                           'species_swap_relative_difference': abs(actual/swapped-1), 'viscosity_pa_s': actual})
    paths = sorted({row['path'] for row in rows})
    result = {'settings': p, 'measurement_settings': observations, 'diffusion_settings': diffusion_settings,
              'records': rows, 'source_arithmetic': arithmetic, 'composition_limits': limits,
              'all_arithmetic_budgets_met': all(r['relative_error'] <= q['arithmetic_relative_budget'] for r in arithmetic),
              'all_composition_limit_budgets_met': all(max(r['source_relative_difference'], r['species_swap_relative_difference'])
                  <= q['arithmetic_relative_budget'] for r in limits),
              'comparison_summary': {path: {'rows': len(group), 'passing': sum(r['within_budget'] for r in group),
                  'maximum_absolute_relative_difference': max(abs(r['signed_relative_difference']) for r in group)}
                  for path in paths for group in [[r for r in rows if r['path'] == path]]},
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ['all_arithmetic_budgets_met', 'all_composition_limit_budgets_met', 'comparison_summary']}))


if __name__ == '__main__':
    main()
