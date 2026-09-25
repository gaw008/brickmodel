"""Independent source balances, positive dissipation and separable-time solution."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path
import time

import mpmath as mp
import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_water_gas_shift_cycle import polynomial


class PoreReference:
    def __init__(self, header):
        self.p = header['settings']['review']
        values = {k: mp.mpf(str(v)) for k, v in header['source_parameters']['model'].items()}
        self.a0, self.vm, self.eta, self.gamma, self.t, self.po, self.r = [values[k] for k in
            ['reference_radius_m', 'matrix_volume_m3', 'viscosity_pa_s', 'surface_tension_n_m',
             'temperature_k', 'outside_pressure_pa', 'gas_constant_j_mol_k']]
        self.n = mp.mpf(header['gas_amount_mol']); self.e0 = mp.mpf(header['reference_surface_energy_j'])
        self.v0 = 4*mp.pi*self.a0**3/3
        self.surface0 = 4*mp.pi*self.gamma*self.a0**2

    def at_radius(self, a):
        v = 4*mp.pi*a**3/3; total = v+self.vm
        outer = (3*total/(4*mp.pi))**(mp.mpf(1)/3)
        pg = self.n*self.r*self.t/v
        coefficient = (pg-self.po-2*self.gamma/a)/(4*self.eta*(a**(-3)-outer**(-3)))
        rate = coefficient/a**2; dv = 4*mp.pi*coefficient
        dissipation = 4*mp.pi*a*a*(pg-self.po-2*self.gamma/a)*rate
        surface = 4*mp.pi*self.gamma*a*a
        return {'radius_m': a, 'outer_radius_m': outer, 'pore_volume_m3': v, 'porosity': v/total,
                'gas_pressure_pa': pg, 'radius_rate_m_s': rate, 'surface_energy_j': surface,
                'external_work_in_w': -self.po*dv, 'heat_in_w': pg*dv-dissipation,
                'viscous_dissipation_w': dissipation,
                'free_energy_plus_pressure_work_change_j': surface-self.surface0+self.po*(v-self.v0)-self.n*self.r*self.t*mp.log(v/self.v0),
                'gas_entropy_change_j_k': self.n*self.r*mp.log(v/self.v0)}

    def root(self, function, left, right):
        for _ in range(self.p['root_iterations']):
            middle = (left+right)/2
            if function(middle) > 0:
                right = middle
            else:
                left = middle
            if right-left <= mp.mpf(self.p['root_tolerance']):
                return (left+right)/2
        raise ArithmeticError('independent pore reference did not reach declared root precision')

    def implicit_radius(self, times):
        alpha = self.po*self.a0/(2*self.gamma)
        beta = self.n*self.r*self.t/self.v0*self.a0/(2*self.gamma)
        bracket = list(map(lambda x: mp.mpf(str(x)), self.p['equilibrium_radius_ratio_bracket']))
        z = self.root(lambda q: alpha*q**3+q*q-beta, *bracket)
        b = self.v0/self.vm; c = self.gamma/(2*self.eta*self.a0)
        kappa = lambda q: c*(1+b*q**3)*(alpha*(q*q+q*z+z*z)+q+z)/(q*q)
        low, high = min(z, 1), max(z, 1)
        upper = c*(1+b*high**3)*(3*alpha*high**2+2*high)/(low*low)
        # q=z+(1-z)exp(w) removes the equilibrium pole from the time integral.
        elapsed = lambda w: mp.quad(lambda value: 1/kappa(z+(1-z)*mp.exp(value)), [w, 0])
        results = []
        for at in times:
            t = mp.mpf(str(at))
            w = mp.mpf(0) if t == 0 else self.root(lambda w: t-elapsed(w), -upper*t, mp.mpf(0))
            q = z+(1-z)*mp.exp(w)
            results.append({'time_s': at, 'radius_m': float(self.a0*q),
                            'radius_decimal_m': str(self.a0*q), 'time_integral_residual_s': float(abs(elapsed(w)-t))})
        return {'equilibrium_radius_m': float(self.a0*z), 'points': results,
                'method': 'Independent ideal-gas cubic root and separated time quadrature in log distance from equilibrium; no fitted relaxation times.'}


def audit(path, policy):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream]
    header = rows[0]; ref = PoreReference(header)
    accepted = [row for row in rows if row['kind'] == 'accepted']; ends = [row['time_s'] for row in accepted]
    times = {row['time_s'] for row in rows if 'state' in row}
    maxima = {k: 0. for k in ['source_radius_rate_m_s', 'source_pressure_pa', 'source_dissipation_w',
                              'force_balance_pa', 'matrix_volume_m3', 'surface_energy_j', 'free_energy_j', 'entropy_j_k']}
    counts = {'recorded': 0, 'dense': 0}; minimum_dissipation = float('inf')

    def state(values):
        return ref.at_radius(mp.mpf(float(values[0]))*ref.a0)

    def at_time(at):
        values = np.asarray(rows[1]['values']) if at == 0 else polynomial(accepted[bisect_left(ends, at)], at)
        return state(values), values

    def inspect(values, computed, category):
        nonlocal minimum_dissipation
        counts[category] += 1
        minimum_dissipation = min(minimum_dissipation, float(computed['viscous_dissipation_w']))
        work, heat, dissipation = [mp.mpf(float(v))*ref.e0 for v in values[1:]]
        maxima['surface_energy_j'] = max(maxima['surface_energy_j'], float(abs(computed['surface_energy_j']-ref.surface0-work-heat)))
        maxima['free_energy_j'] = max(maxima['free_energy_j'], float(abs(computed['free_energy_plus_pressure_work_change_j']+dissipation)))
        maxima['entropy_j_k'] = max(maxima['entropy_j_k'], float(abs(computed['gas_entropy_change_j_k']-(heat+dissipation)/ref.t)))
        return np.array([float(computed['radius_m']), float(work), float(heat), float(dissipation)]), np.array([float(computed[k]) for k in ['radius_rate_m_s', 'external_work_in_w', 'heat_in_w', 'viscous_dissipation_w']])

    for row in rows:
        if 'state' not in row:
            continue
        actual = row['state']; computed = state(row['values'])
        for key, field in [('source_radius_rate_m_s', 'radius_rate_m_s'), ('source_pressure_pa', 'gas_pressure_pa'), ('source_dissipation_w', 'viscous_dissipation_w')]:
            maxima[key] = max(maxima[key], float(abs(mp.mpf(actual[field])-computed[field])))
        a, outer = mp.mpf(actual['radius_m']), mp.mpf(actual['outer_radius_m'])
        c, pressure = mp.mpf(actual['radial_velocity_constant_m3_s']), mp.mpf(actual['matrix_pressure_pa'])
        inner = -pressure-4*ref.eta*c/a**3; external = -pressure-4*ref.eta*c/outer**3
        maxima['force_balance_pa'] = max(maxima['force_balance_pa'], float(abs(inner+computed['gas_pressure_pa']-2*ref.gamma/a)), float(abs(external+ref.po)))
        maxima['matrix_volume_m3'] = max(maxima['matrix_volume_m3'], float(abs(4*mp.pi*(outer**3-a**3)/3-ref.vm)))
        inspect(row['values'], computed, 'recorded')
    reviews, integrals = [], []
    origin = np.array([float(ref.a0), 0., 0., 0.])
    for order in policy['quadrature_orders']:
        nodes, weights = leggauss(order); total = np.zeros(4); previous = origin.copy()
        max_local = np.zeros(4); max_cumulative = np.zeros(4); increments = []
        minimum_step = float('inf'); previous_state = state(rows[1]['values'])
        previous_heat = 0.
        for row in accepted:
            dense = row['dense_output']; left, right = dense['start_time_s'], dense['end_time_s']
            increment = np.zeros(4)
            for node, weight in zip(nodes, weights, strict=True):
                at = float((left+right)/2+(right-left)*node/2); times.add(at)
                values = polynomial(row, at); computed = state(values)
                _, rates = inspect(values, computed, 'dense'); increment += rates*weight*(right-left)/2
            computed = state(row['values']); current, _ = inspect(row['values'], computed, 'recorded')
            total += increment; increments.append(increment)
            max_local = np.maximum(max_local, np.abs(current-previous-increment))
            max_cumulative = np.maximum(max_cumulative, np.abs(current-origin-total))
            step_entropy = computed['gas_entropy_change_j_k']-previous_state['gas_entropy_change_j_k']-mp.mpf(current[2]-previous_heat)/ref.t
            minimum_step = min(minimum_step, float(step_entropy)); previous, previous_state, previous_heat = current, computed, current[2]
        flags = {'local_radius': max_local[0] <= policy['radius_reference_m'],
                 'cumulative_radius': max_cumulative[0] <= policy['radius_reference_m'],
                 'local_work_heat_dissipation': max(max_local[1:]) <= policy['local_energy_j'],
                 'cumulative_work_heat_dissipation': max(max_cumulative[1:]) <= policy['cumulative_energy_j'],
                 'nonnegative_step_entropy': minimum_step >= -policy['negative_step_entropy_j_k']}
        reviews.append({'order': order, 'maximum_local_radius_W_Q_D_residuals': max_local.tolist(),
                        'maximum_cumulative_radius_W_Q_D_residuals': max_cumulative.tolist(),
                        'minimum_step_entropy_j_k': minimum_step,
                        'within_budgets': {k: bool(v) for k, v in flags.items()}})
        integrals.append(np.array(increments))
    difference = integrals[1]-integrals[0]
    quadrature = np.maximum(np.max(np.abs(difference), axis=0), np.max(np.abs(np.cumsum(difference, axis=0)), axis=0))
    analytic = ref.implicit_radius(policy['implicit_reference_times_s'])
    for point in analytic['points']:
        computed, _ = at_time(point['time_s'])
        point['numerical_radius_error_m'] = float(abs(computed['radius_m']-mp.mpf(point['radius_decimal_m'])))
    flags = {key: value <= policy[key] for key, value in maxima.items() if key not in ['surface_energy_j', 'free_energy_j']}
    flags.update(completed=rows[-1]['kind'] == 'summary' and rows[-1]['status'] == 'completed',
                 surface_energy=maxima['surface_energy_j'] <= policy['cumulative_energy_j'],
                 free_energy=maxima['free_energy_j'] <= policy['cumulative_energy_j'],
                 nonnegative_dissipation=minimum_dissipation >= 0,
                 local_integrals=all(all(row['within_budgets'].values()) for row in reviews),
                 quadrature_radius=bool(quadrature[0] <= policy['radius_reference_m']),
                 quadrature_energy=bool(max(quadrature[1:]) <= policy['cumulative_energy_j']),
                 implicit_time_reference=max(row['numerical_radius_error_m'] for row in analytic['points']) <= policy['radius_reference_m'])
    result = {'trajectory': str(path), 'counts': counts, 'maxima': maxima,
              'minimum_dissipation_w': minimum_dissipation, 'integral_reviews': reviews,
              'quadrature_radius_W_Q_D_differences': quadrature.tolist(), 'implicit_time_reference': analytic,
              'final': rows[-1]['final'], 'within_budgets': flags, 'all_requested_budgets_met': all(flags.values())}
    print(json.dumps({'trajectory': str(path), 'all_requested_budgets_met': result['all_requested_budgets_met']}), flush=True)
    return result, times, at_time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); p = settings['review']
    mp.mp.dps = p['decimal_digits']; started = time.monotonic(); results = {}
    for case, paths in settings['trajectories'].items():
        reviews, functions, nodes = {}, {}, set()
        for name, path in paths.items():
            reviews[name], times, functions[name] = audit(root/path, p); nodes.update(times)
        initial, _ = functions['base'](0.)
        energy_scale = initial['surface_energy_j']
        maxima = {key: 0. for key in ['time_radius_m', 'time_pressure_pa', 'time_energy_j', 'time_porosity']}
        for at in sorted(nodes):
            left, ly = functions['base'](at); right, ry = functions['refined'](at)
            differences = {'time_radius_m': abs(left['radius_m']-right['radius_m']),
                           'time_pressure_pa': abs(left['gas_pressure_pa']-right['gas_pressure_pa']),
                           'time_energy_j': max(*(abs(left[k]-right[k]) for k in ['surface_energy_j', 'free_energy_plus_pressure_work_change_j']),
                                                *(abs(float(v))*energy_scale for v in ly[1:]-ry[1:])),
                           'time_porosity': abs(left['porosity']-right['porosity'])}
            for key, value in differences.items():
                maxima[key] = max(maxima[key], float(value))
        flags = {key: value <= p[key] for key, value in maxima.items()}
        results[case] = {'trajectory_reviews': reviews, 'time_comparison': {'union_nodes': len(nodes), 'maximum_differences': maxima, 'within_budgets': flags},
                         'all_requested_budgets_met': all(row['all_requested_budgets_met'] for row in reviews.values()) and all(flags.values())}
    result = {'settings': settings, 'cases': results, 'all_requested_budgets_met': all(row['all_requested_budgets_met'] for row in results.values()),
              'elapsed_s': time.monotonic()-started, 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'all_requested_budgets_met': result['all_requested_budgets_met'], 'elapsed_s': result['elapsed_s']}), flush=True)


if __name__ == '__main__':
    main()
