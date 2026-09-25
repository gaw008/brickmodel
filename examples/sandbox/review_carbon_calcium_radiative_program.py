"""Independent programmed gas/radiation sources and coupled thermodynamic rates."""
import argparse
import json
from pathlib import Path

import mpmath as mp
import numpy as np

from carbon_calcium_inventory_setup import build
from carbon_calcium_source_audit import SourceState, independent_exchange
from carbon_calcium_radiation_reference import RadiationSource
from review_carbon_calcium_open_cell import source_bath
from sludge_sandbox.carbon_calcium_caloric_inventory import caloric_inventory_tangent
from sludge_sandbox.carbon_calcium_radiative_program import CarbonCalciumRadiativeProgram


from review_carbon_calcium_program import independent_program, independent_thermal


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
    source = SourceState(sources)
    cell = CarbonCalciumRadiativeProgram(model, p, face, rigid['numerics'])
    policy = p['boundary_source_review']
    mp.mp.dps = policy['decimal_precision']
    rows = []
    radiation_source = RadiationSource(p['radiation'])
    radiation_program = dict(p['boundary_program'], gas_temperature_k=p['boundary_program']['radiation_temperature_k'])
    for at in policy['times_s']:
        actual = cell.reservoir_at(at)
        t, pressure, fractions = independent_program(p['boundary_program'], at)
        reference = independent_thermal(source, t, pressure, fractions)
        errors = {
            'temperature_k': float(abs(mp.mpf(actual['temperature_k']) - t)),
            'pressure_pa': float(abs(mp.mpf(actual['pressure_pa']) - pressure)),
            'mole_fraction': max(float(abs(mp.mpf(actual['mole_fractions'][k]) - v)) for k, v in fractions.items()),
            'enthalpy_j_mol': max(float(abs(mp.mpf(model.phases[k].standard(actual['temperature_k'])['enthalpy_j_mol']) - v['h'])) for k, v in reference.items()),
            'chemical_potential_j_mol': max(float(abs(mp.mpf(actual['chemical_potentials_j_mol'][k]) - v['mu'])) for k, v in reference.items()),
        }
        bounds = {'temperature_k': policy['temperature_budget_k'], 'pressure_pa': policy['pressure_budget_pa'],
            'mole_fraction': policy['mole_fraction_budget'], 'enthalpy_j_mol': policy['enthalpy_budget_j_mol'],
            'chemical_potential_j_mol': policy['chemical_potential_budget_j_mol']}
        rad_t = independent_program(radiation_program, at)[0]
        values = cell.initial.copy()
        values[3] = float(t)
        state = cell.state(values)
        body = source.reconstruct(state, p['volume_m3'], [cell.calcium, *values[:3]])
        flux = independent_exchange(source_bath(source, float(t), float(pressure), {k: float(v) for k, v in fractions.items()}), body, face)
        rad = cell.radiation(at, state)
        rad_ref = radiation_source.decimal_flux(state['temperature_k'], rad_t, p['radiation_review']['decimal_precision'])
        errors['radiation_temperature_k'] = float(abs(mp.mpf(rad['reservoir_temperature_k']) - rad_t))
        errors['radiation_energy_w'] = float(abs(mp.mpf(rad['energy_in_w']) - rad_ref['energy_in_w']))
        errors['radiation_entropy_w_k'] = max(float(abs(mp.mpf(rad[k]) - rad_ref[k])) for k in rad_ref if 'entropy' in k)
        rates = cell.rates(at, values)
        tangent = caloric_inventory_tangent(model, state, p['volume_m3'], cell.calcium, float(values[0]), float(values[1]))
        coordinates = np.array([rates[3], *rates[:3]])
        du = float(np.array(tangent['internal_energy_derivatives']) @ coordinates)
        ds = float(np.array(tangent['entropy_derivatives']) @ coordinates)
        errors['constitutive_energy_w'] = max(abs(du - flux['energy'] - float(rad_ref['energy_in_w'])), abs(du - rates[4]))
        errors['constitutive_entropy_w_k'] = max(abs(ds - flux['entropy'][1] - float(rad_ref['body_entropy_rate_w_k'])), abs(ds + rates[5] + rates[8] - rates[6]))
        rp = p['radiation_review']
        bounds.update(radiation_temperature_k=policy['temperature_budget_k'], radiation_energy_w=rp['energy_budget_w'], radiation_entropy_w_k=rp['entropy_budget_w_k'], constitutive_energy_w=rp['constitutive_energy_rate_budget_w'], constitutive_entropy_w_k=rp['constitutive_entropy_rate_budget_w_k'])
        flags = {k: bool(value <= bounds[k]) for k, value in errors.items()}
        flags.update({k: bool(v <= p['verification'][k]) for k, v in body['errors'].items()})
        flags['nonnegative_production'] = bool(rates[6] >= 0.)
        rows.append({'time_s': at, 'recorded_bath': actual,
            'independent_temperature_k': str(t), 'independent_pressure_pa': str(pressure),
            'independent_mole_fractions': {k: str(v) for k, v in fractions.items()},
            'independent_thermochemistry': {k: {q: str(v) for q, v in values.items()} for k, values in reference.items()},
            'radiation': rad, 'source_radiation': {k: str(v) for k, v in rad_ref.items()}, 'state': state, 'rates': rates.tolist(), 'source_state_errors': body['errors'], 'errors': errors, 'within_budgets': flags})
    result = {'settings': p, 'source_records': sources, 'observations': rows,
        'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in rows),
        'material_qualified': False, 'training_eligible': False,
        'scope': 'Independent affine primitive inputs and source Cp integrals with arbitrary-precision arithmetic; no claim of physical input precision or trajectory qualification.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met'],
                      'maxima': {k: max(r['errors'][k] for r in rows) for k in rows[0]['errors']}}))


if __name__ == '__main__':
    main()
