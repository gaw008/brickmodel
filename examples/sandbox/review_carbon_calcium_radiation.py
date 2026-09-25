"""Independent SI radiation, source state and energy/entropy rate review."""
import argparse
import json
from pathlib import Path

import mpmath as mp
import numpy as np

from carbon_calcium_inventory_setup import build
from carbon_calcium_radiation_reference import RadiationSource
from carbon_calcium_source_audit import SourceState, independent_exchange
from review_carbon_calcium_open_cell import source_bath
from sludge_sandbox.carbon_calcium_caloric_inventory import caloric_inventory_tangent
from sludge_sandbox.carbon_calcium_radiative_cell import CarbonCalciumRadiativeCell, black_enclosure_exchange


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    face = json.loads((root / p['exchange_parameters']).read_text())
    rigid = json.loads((root / face['rigid_parameters']).read_text())
    pressure = json.loads((root / rigid['pressure_parameters']).read_text())
    model, sources, _ = build(root, pressure)
    cell = CarbonCalciumRadiativeCell(model, p, face, rigid['numerics'])
    source, policy = SourceState(sources), p['radiation_review']
    radiation_rows, state_rows = [], []
    for reservoir in policy['reservoir_temperatures_k']:
        radiation = dict(p['radiation'], reservoir_temperature_k=reservoir)
        reference = RadiationSource(radiation)
        for temperature in policy['temperatures_k']:
            actual = black_enclosure_exchange(temperature, radiation)
            with mp.workdps(policy['decimal_precision']):
                expected = reference.decimal_flux(temperature, policy['decimal_precision'])
                errors = {k: float(abs(mp.mpf(actual[k]) - v)) for k, v in expected.items()}
                sigma_error = float(abs(mp.mpf(radiation['stefan_boltzmann_w_m2_k4']) - mp.mpf(reference.sigma_decimal)))
            flags = {'source_sigma': sigma_error <= policy['sigma_absolute_budget_w_m2_k4'],
                'heat': errors['energy_in_w'] <= policy['energy_budget_w'],
                'derivative': errors['temperature_derivative_w_k'] <= policy['temperature_derivative_budget_w_k'],
                'entropy': max(errors[k] for k in errors if 'entropy' in k) <= policy['entropy_budget_w_k'],
                'nonnegative_production': actual['entropy_production_w_k'] >= 0.,
                'entropy_identity': abs(actual['body_entropy_rate_w_k'] + actual['reservoir_entropy_rate_w_k']
                    - actual['entropy_production_w_k']) <= policy['entropy_budget_w_k']}
            radiation_rows.append({'temperature_k': temperature, 'reservoir_temperature_k': reservoir,
                'radiation': actual, 'source_decimal': {k: str(v) for k, v in expected.items()},
                'errors': errors, 'sigma_error_w_m2_k4': sigma_error, 'within_budgets': flags})
    radiation = RadiationSource(p['radiation'])
    bath = p['reservoir']
    gas = source_bath(source, bath['temperature_k'], bath['pressure_pa'], bath['mole_fractions'])
    for temperature in policy['temperatures_k']:
        y = cell.initial.copy()
        y[3] = temperature
        state = cell.state(y)
        ref = source.reconstruct(state, p['volume_m3'], [cell.calcium, *y[:3]])
        flux = independent_exchange(gas, ref, face)
        rad = radiation.flux(temperature)
        tangent = caloric_inventory_tangent(model, state, p['volume_m3'], cell.calcium, float(y[0]), float(y[1]))
        rates = cell.rates(0., y)
        coordinate_rates = np.array([rates[3], *rates[:3]])
        energy_rate = float(np.array(tangent['internal_energy_derivatives']) @ coordinate_rates)
        entropy_rate = float(np.array(tangent['entropy_derivatives']) @ coordinate_rates)
        energy_error = max(abs(energy_rate - flux['energy'] - rad['energy_in_w']),
            abs(rates[4] - energy_rate), abs(rates[7] - rad['energy_in_w']))
        entropy_error = max(abs(entropy_rate - flux['entropy'][1] - rad['body_entropy_rate_w_k']),
            abs(entropy_rate + rates[5] + rates[8] - rates[6]),
            abs(rates[5] - flux['entropy'][0]), abs(rates[8] - rad['reservoir_entropy_rate_w_k']))
        flags = {k: v <= p['verification'][k] for k, v in ref['errors'].items()}
        flags.update(constitutive_energy=energy_error <= policy['constitutive_energy_rate_budget_w'],
            constitutive_entropy=entropy_error <= policy['constitutive_entropy_rate_budget_w_k'],
            positive_cv=state['equilibrium_cv_j_k'] > 0., nonnegative_total_production=bool(rates[6] >= 0.))
        flags = {k: bool(v) for k, v in flags.items()}
        state_rows.append({'state': state, 'rates': rates.tolist(), 'source_errors': ref['errors'],
            'energy_rate_error_w': energy_error, 'entropy_rate_error_w_k': entropy_error, 'within_budgets': flags})
    result = {'settings': p, 'source_records': sources, 'radiation_states': radiation_rows,
        'cell_states': state_rows, 'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in radiation_rows + state_rows),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'radiation_states': len(radiation_rows), 'cell_states': len(state_rows),
        'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met']}))


if __name__ == '__main__':
    main()
