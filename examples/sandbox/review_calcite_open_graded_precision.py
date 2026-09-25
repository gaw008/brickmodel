"""Independent high-precision central derivatives for small boundary cells."""
import argparse
import json
from pathlib import Path

from mpmath import mp
import numpy as np

from calcite_open_decimal_reference import DecimalOpenColumn
from calcite_rigid_setup import build_rigid
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    review = json.loads((root/settings['static_review_parameters']).read_text())
    policy = json.loads((root/review['column_parameters']).read_text())
    config = json.loads((root/policy['model_parameters']).read_text())
    surface = json.loads((root/policy['surface_parameters']).read_text())['surface']
    reaction, nitrogen, _, _, _, _, volume = build_rigid(root, config)
    mp.dps = settings['decimal_digits']
    records = []
    for case in review['cases']:
        time_s = case['time_s'] if 'continuous_boundary_program' in policy else 0.
        n = len(case['temperatures_k'])
        column = OpenRigidReactiveColumn(reaction, nitrogen, volume, config, policy, surface, n, case['cell_widths_m'])
        z = column.initial.copy()
        for i, cell in enumerate(column.cells):
            dc = case['excess_carbon_densities_mol_m3'][i]*cell.volume
            nn = case['nitrogen_densities_mol_m3'][i]*cell.volume
            state = cell.at_carbon_offset(case['temperatures_k'][i], dc, nn)
            z[3*i:3*i+3] = [column.carbon_coordinate(cell,dc), np.log(nn/column.reference_nitrogen), state['internal_energy_j']]
        if 'integration_values' in case:
            z = np.array(case['integration_values'], dtype=float)
        segment = case['segment_index']
        _, states, _, _, contact = column.observe(z, segment,time_s)
        reference = DecimalOpenColumn(column, states, contact, segment, settings,time_s)
        nominal = [mp.mpf(float(value)) for value in z]
        analytic = column.jacobian(time_s, z, segment).toarray()
        reference_rates, reference_states = reference.rates(nominal)
        physical_rates = column.rates(time_s, z, segment)
        scales = np.array(review['per_cell_rate_scales']*n+review['ledger_rate_scales'])
        if column.log_carbon and review.get('carbon_rate_scale_basis')=='physical_inventory':
            scales[0:3*n:3] /= column.physical_values(z)[0:3*n:3]
        normalization = [entry for cell in column.cells for entry in (
            review['coordinate_normalization']['carbon_density_mol_m3']*cell.volume,
            review['coordinate_normalization']['log_nitrogen'], review['coordinate_normalization']['energy_density_j_m3']*cell.volume)]
        perturbation = [entry for cell in column.cells for entry in (
            case['carbon_difference_density_mol_m3']*cell.volume,
            review['difference_scales']['log_nitrogen'], review['difference_scales']['energy_density_j_m3']*cell.volume)]
        if column.log_carbon:
            physical = column.physical_values(z)
            for i in range(n):
                normalization[3*i] /= physical[3*i]
                perturbation[3*i] /= physical[3*i]
        derivatives = []
        for step in settings['difference_steps']:
            worst = {'scaled_maximum_absolute_difference': 0.}
            phase_ok = True
            for j in range(3*n):
                h = mp.mpf(step)*mp.mpf(perturbation[j])
                left, right = list(nominal), list(nominal)
                left[j] -= h
                right[j] += h
                a, states_a = reference.rates(left)
                b, states_b = reference.rates(right)
                for nominal_state, sa, sb in zip(states, states_a, states_b, strict=True):
                    for state in (sa, sb):
                        phase_ok &= bool(state['nc']>0 and state['nn']>0 and state['calcite']>=0 and state['lime']>=0)
                        if nominal_state['phase']=='calcite': phase_ok &= bool(state['affinity']>=0)
                        if nominal_state['phase']=='lime': phase_ok &= bool(state['affinity']<=0)
                for i, (first, second) in enumerate(zip(a, b, strict=True)):
                    central = (second-first)/(2*h)
                    error = float(abs(mp.mpf(float(analytic[i,j]))-central)*mp.mpf(normalization[j])/mp.mpf(float(scales[i])))
                    if error>worst['scaled_maximum_absolute_difference']:
                        worst = {'scaled_maximum_absolute_difference': error, 'worst_row': i, 'worst_column': j,
                                 'analytic_at_worst': float(analytic[i,j]), 'central_difference_decimal_at_worst': str(central)}
            worst.update(step=step, physical_phase_constraints_met=phase_ok,
                         within_budget=bool(worst['scaled_maximum_absolute_difference']<=review['budgets']['scaled_derivative'] and phase_ok))
            derivatives.append(worst)
            print(json.dumps({'case': case['name'], **worst}), flush=True)
        rate_errors = [float(abs(mp.mpf(float(value))-ref)) for value, ref in zip(physical_rates, reference_rates, strict=True)]
        records.append({'case': case, 'derivatives': derivatives, 'absolute_rate_differences': rate_errors,
                        'reference_temperatures_k': [str(s['t']) for s in reference_states],
                        'all_derivative_budgets_met': all(r['within_budget'] for r in derivatives)})
    result = {'settings': settings, 'static_review_parameters': review, 'records': records,
              'all_derivative_budgets_met': all(r['all_derivative_budgets_met'] for r in records),
              'scope': 'Independent source polynomial, phase-local inventory inverse, surface root and face matrix at higher arithmetic precision. Identical binary-float inputs are promoted; source uncertainty is unchanged. Original double-precision difference failures remain separate.',
              'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
