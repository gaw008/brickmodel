"""Independent radial-stress, viscous-work and gas/heat ledger calculation."""
import argparse
import json
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.viscous_spherical_pore import ViscousSphericalPore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); p = json.loads(args.parameters.read_text())
    source = json.loads((args.parameters.resolve().parent/p['source_file']).read_text())
    mp.mp.dps = p['decimal_digits']; model = ViscousSphericalPore(p['model'])
    values = {name: mp.mpf(str(value)) for name, value in p['model'].items()}
    eta, gamma, t, po, r = [values[key] for key in ['viscosity_pa_s', 'surface_tension_n_m', 'temperature_k', 'outside_pressure_pa', 'gas_constant_j_mol_k']]
    vm, a0 = values['matrix_volume_m3'], values['reference_radius_m']
    volume = lambda a: 4*mp.pi*a**3/3
    area = lambda a: 4*mp.pi*a*a
    phi0 = volume(a0)/(vm+volume(a0))
    records = []

    def review(a, pg, actual, mode, amount):
        outer = ((vm+volume(a))*3/(4*mp.pi))**(mp.mpf(1)/3)
        # Two independent normal-traction boundary equations determine p_l,C.
        matrix = mp.matrix([[1, 4*eta/outer**3], [1, 4*eta/a**3]])
        pressure, constant = mp.lu_solve(matrix, mp.matrix([po, pg-2*gamma/a]))
        rate = constant/a**2
        dissipation = mp.quad(lambda radius: 2*eta*((-2*constant/radius**3)**2+2*(constant/radius**3)**2)*4*mp.pi*radius**2, [a, outer])
        runtime_c = mp.mpf(actual['radial_velocity_constant_m3_s'])
        runtime_p = mp.mpf(actual['matrix_pressure_pa'])
        runtime_outer = mp.mpf(actual['outer_radius_m'])
        inner_stress = -runtime_p-4*eta*runtime_c/a**3
        outer_stress = -runtime_p-4*eta*runtime_c/runtime_outer**3
        errors = {'radius_rate_m_s': abs(mp.mpf(actual['radius_rate_m_s'])-rate),
                  'normal_traction_pa': max(abs(inner_stress-(-pg+2*gamma/a)), abs(outer_stress+po)),
                  'matrix_volume_rate_m3_s': abs(4*mp.pi*runtime_outer**2*mp.mpf(actual['outer_radius_rate_m_s'])-4*mp.pi*a**2*mp.mpf(actual['radius_rate_m_s'])),
                  'dissipation_w': abs(mp.mpf(actual['viscous_dissipation_w'])-dissipation)}
        if mode == 'closed':
            potential = lambda x: gamma*area(x)+po*volume(x)-amount*r*t*mp.log(volume(x)/volume(a0))
            errors['energy_rate_w'] = abs(mp.mpf(actual['surface_energy_rate_w'])-mp.mpf(actual['heat_in_w'])-mp.mpf(actual['external_work_in_w']))
            errors['entropy_rate_w_k'] = abs(mp.mpf(actual['gas_entropy_rate_w_k'])+mp.mpf(actual['bath_entropy_rate_w_k'])-dissipation/t)
        else:
            potential = lambda x: gamma*area(x)+(po-pg)*volume(x)
            errors['entropy_rate_w_k'] = abs(mp.mpf(actual['entropy_production_w_k'])-dissipation/t)
        errors['free_energy_rate_w'] = abs(mp.diff(potential, a)*mp.mpf(actual['radius_rate_m_s'])+dissipation)
        flags = {key: bool(error <= p['budgets'][key]) for key, error in errors.items()}
        flags.update(nonnegative_dissipation=actual['viscous_dissipation_w'] >= 0,
                     matrix_volume_positive=bool(vm > 0), pore_inside_shell=actual['outer_radius_m'] > actual['radius_m'])
        records.append({'mode': mode, 'state': actual, 'independent_radial_integral_dissipation_w': float(dissipation),
                        'independent_errors': {key: float(error) for key, error in errors.items()},
                        'within_budgets': flags, 'all_requested_budgets_met': all(flags.values())})

    vented_source = []
    for radius in p['review_radii_m']:
        a = mp.mpf(str(radius))
        for factor in p['laplace_pressure_multipliers']:
            gas_pressure = float(po+mp.mpf(str(factor))*2*gamma/a)
            actual = model.vented(radius, gas_pressure)
            review(a, mp.mpf(gas_pressure), actual, 'prescribed_pressure', None)
        for initial_pressure in p['trapped_reference_pressures_pa']:
            amount = float(mp.mpf(str(initial_pressure))*volume(a0)/(r*t))
            actual = model.closed(radius, amount)
            review(a, mp.mpf(amount)*r*t/volume(a), actual, 'closed', mp.mpf(amount))
        actual = model.vented(radius, float(po))
        phi = volume(a)/(vm+volume(a))
        source_rate = -3*gamma/(2*eta*a0)*(phi0/(1-phi0))**(mp.mpf(1)/3)*phi**(mp.mpf(2)/3)*(1-phi)**(mp.mpf(1)/3)
        error = abs(mp.mpf(actual['porosity_rate_s'])-source_rate)
        vented_source.append({'radius_m': radius, 'source_porosity_rate_s': float(source_rate),
                              'error_s': float(error), 'within_budget': bool(error <= p['budgets']['porosity_rate_s'])})
    closing_time = 2*eta/gamma*mp.quad(lambda a: vm/(vm+volume(a)), [0, a0])
    result = {'settings': p, 'sources': source, 'records': records, 'vented_source_identity': vented_source,
              'constant_parameter_vented_closure_time_s': float(closing_time),
              'closure_scope': 'Improper-radius endpoint integral of the printed Eq2.12, finite for positive finite eta/gamma; no simulation beyond zero radius or real material closure claim.',
              'all_requested_budgets_met': all(row['all_requested_budgets_met'] for row in records) and all(row['within_budget'] for row in vented_source),
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'all_requested_budgets_met': result['all_requested_budgets_met'], 'states': len(records), 'source_identity_points': len(vented_source), 'vented_closure_time_s': float(closing_time)}), flush=True)


if __name__ == '__main__':
    main()
