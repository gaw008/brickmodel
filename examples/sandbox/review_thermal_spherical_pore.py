"""Independent nonisothermal pore energy, entropy and radial-work identities."""
import argparse
import itertools
import json
import math
from pathlib import Path

import mpmath as mp

from thermal_pore_setup import build
from thermal_pore_reference import ThermalPoreReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text()); policy = p['static_review']
    mp.mp.dps = policy['decimal_digits']; model, sources = build(root, p)
    a0 = p['model']['reference_radius_m']; v0 = 4*math.pi*a0**3/3
    records = []
    for pressure0, radius, temperature, bath in itertools.product(policy['initial_pressures_pa'],
            policy['radii_m'], policy['temperatures_k'], policy['bath_temperatures_k']):
        amount = pressure0*v0/(model.r*policy['initial_temperature_k'])
        ref = ThermalPoreReference(p, sources, amount)
        a, t, tb, g = map(mp.mpf, [radius, temperature, bath, policy['conductance_w_k']])
        actual = model.at_state(radius, temperature, amount, bath, policy['conductance_w_k'])
        independent = ref.at_state(a, t, tb, g)
        fields = {'radius_rate_m_s':'radius_rate_m_s', 'temperature_rate_k_s':'temperature_rate_k_s',
                  'source_energy_j':'internal_energy_j', 'source_entropy_j_k':'entropy_j_k',
                  'source_cv_j_k':'cv_j_k', 'source_pressure_pa':'gas_pressure_pa',
                  'dissipation_w':'viscous_dissipation_w'}
        errors = {key: abs(mp.mpf(actual[field])-independent[field]) for key, field in fields.items()}
        du_da = mp.diff(lambda x: ref.energy_entropy(x, t)[0], a)
        du_dt = mp.diff(lambda x: ref.energy_entropy(a, x)[0], t)
        ds_da = mp.diff(lambda x: ref.energy_entropy(x, t)[1], a)
        ds_dt = mp.diff(lambda x: ref.energy_entropy(a, x)[1], t)
        adot, tdot = mp.mpf(actual['radius_rate_m_s']), mp.mpf(actual['temperature_rate_k_s'])
        errors['energy_rate_w'] = abs(du_da*adot+du_dt*tdot-actual['heat_in_w']-actual['external_work_in_w'])
        errors['entropy_rate_w_k'] = abs(ds_da*adot+ds_dt*tdot+actual['bath_entropy_rate_w_k']-actual['entropy_production_w_k'])
        # Direct source Cp and Cp/T quadrature verifies the independent primitives.
        h, s = ref.standard(t)
        source_h = ref.h0+mp.quad(ref.cp, [ref.t0, t])
        source_s = ref.s0+mp.quad(lambda x: ref.cp(x)/x, [ref.t0, t])
        errors['source_energy_j'] = max(errors['source_energy_j'], abs(h-source_h)*ref.n)
        errors['source_entropy_j_k'] = max(errors['source_entropy_j_k'], abs(s-source_s)*ref.n)
        radial_dissipation = mp.quad(lambda x: 48*mp.pi*ref.p['viscosity_pa_s']*independent['radial_velocity_constant_m3_s']**2/x**4, [a, independent['outer_radius_m']])
        errors['dissipation_w'] = max(errors['dissipation_w'], abs(radial_dissipation-mp.mpf(actual['viscous_dissipation_w'])))
        flags = {key: bool(error <= policy['budgets'][key]) for key, error in errors.items()}
        flags.update(positive_cv=actual['cv_j_k'] > 0,
                     nonnegative_viscous_entropy=actual['viscous_entropy_production_w_k'] >= 0,
                     nonnegative_heat_entropy=actual['heat_entropy_production_w_k'] >= 0)
        records.append({'initial_pressure_pa': pressure0, 'state': actual,
                        'errors': {key: float(value) for key, value in errors.items()},
                        'within_budgets': flags, 'all_requested_budgets_met': all(flags.values())})
    result = {'settings': p, 'sources': sources, 'records': records,
              'maxima': {key: max(row['errors'][key] for row in records) for key in policy['budgets']},
              'all_requested_budgets_met': all(row['all_requested_budgets_met'] for row in records),
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'states':len(records), 'all_requested_budgets_met':result['all_requested_budgets_met'], 'maxima':result['maxima']}), flush=True)


if __name__ == '__main__':
    main()
