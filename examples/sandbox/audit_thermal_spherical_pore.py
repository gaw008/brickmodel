"""Independent thermal-pore source, trajectory and entropy accounting."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path
import time

import mpmath as mp
import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_water_gas_shift_cycle import polynomial
from thermal_pore_reference import ThermalPoreReference


def source_differences(actual, computed, reference, policy):
    return {key:float(abs(mp.mpf(actual[key])-computed[key])) for key in policy['source_budgets']}


def reference_factory(header):
    return ThermalPoreReference(header['settings'], header['sources'], header['gas_amount_mol'])


def audit(path, policy, make_reference, compare_source):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream]
    header = rows[0]; p = header['settings']; case = header['case']
    ref = make_reference(header)
    a0 = ref.p['reference_radius_m']; ts, es, ss = [mp.mpf(str(p['normalization'][k])) for k in ['temperature_k','energy_j','entropy_j_k']]
    scales = np.array(list(map(float, [a0, ts, es, es, es, ss, ss])))
    accepted = [row for row in rows if row['kind'] == 'accepted']; ends = [row['time_s'] for row in accepted]
    times = {row['time_s'] for row in rows if 'state' in row}
    source_errors = {key:0. for key in policy['source_budgets']}
    maxima = {key:0. for key in ['energy_j','entropy_j_k','external_work_j','matrix_volume_m3','normal_traction_pa']}
    minima = {'entropy_rate_w_k':float('inf'),'viscous_dissipation_w':float('inf'),'cv_j_k':float('inf')}
    counts = {'recorded':0,'dense':0}

    def state(values, segment):
        boundary = case['segments'][segment]
        return ref.at_state(mp.mpf(float(values[0]))*a0, mp.mpf(float(values[1]))*ts,
                            mp.mpf(str(boundary['bath_temperature_k'])), mp.mpf(str(boundary['conductance_w_k'])))

    initial = state(rows[1]['values'], 0); origin = np.array(rows[1]['values'])*scales

    def at_time(at):
        if at == 0:
            values, segment = np.asarray(rows[1]['values']), 0
        else:
            row = accepted[bisect_left(ends, at)]
            values, segment = polynomial(row, at), row['segment_index']
        return state(values, segment), values

    def inspect(values, computed, category):
        counts[category] += 1
        physical = np.asarray(values)*scales
        work, heat = mp.mpf(float(values[2]))*es, mp.mpf(float(values[3]))*es
        bath_s, production = mp.mpf(float(values[5]))*ss, mp.mpf(float(values[6]))*ss
        maxima['energy_j'] = max(maxima['energy_j'], float(abs(computed['internal_energy_j']-initial['internal_energy_j']-work-heat)))
        maxima['entropy_j_k'] = max(maxima['entropy_j_k'], float(abs(computed['entropy_j_k']-initial['entropy_j_k']+bath_s-production)))
        maxima['external_work_j'] = max(maxima['external_work_j'], float(abs(work+ref.p['outside_pressure_pa']*(computed['pore_volume_m3']-initial['pore_volume_m3']))))
        for key, field in [('entropy_rate_w_k','entropy_production_w_k'),('viscous_dissipation_w','viscous_dissipation_w'),('cv_j_k','cv_j_k')]:
            minima[key] = min(minima[key], float(computed[field]))
        fields = ['radius_rate_m_s','temperature_rate_k_s','external_work_in_w','heat_in_w',
                  'viscous_dissipation_w','bath_entropy_rate_w_k','entropy_production_w_k']
        return physical, np.array([float(computed[key]) for key in fields])

    for row in rows:
        if 'state' not in row:
            continue
        computed = state(row['values'], row['segment_index']); actual = row['state']
        for key, error in compare_source(actual, computed, ref, policy).items():
            source_errors[key] = max(source_errors[key], error)
        a, outer = mp.mpf(actual['radius_m']), mp.mpf(actual['outer_radius_m'])
        c, pressure = mp.mpf(actual['radial_velocity_constant_m3_s']), mp.mpf(actual['matrix_pressure_pa'])
        inner = -pressure-4*ref.p['viscosity_pa_s']*c/a**3
        exterior = -pressure-4*ref.p['viscosity_pa_s']*c/outer**3
        maxima['normal_traction_pa'] = max(maxima['normal_traction_pa'], float(abs(inner+computed['gas_pressure_pa']-2*ref.p['surface_tension_n_m']/a)), float(abs(exterior+ref.p['outside_pressure_pa'])))
        maxima['matrix_volume_m3'] = max(maxima['matrix_volume_m3'], float(abs(4*mp.pi*(outer**3-a**3)/3-ref.p['matrix_volume_m3'])))
        inspect(row['values'], computed, 'recorded')
    reviews, integrals = [], []
    budgets = np.array(policy['integral_budgets'])
    for order in policy['quadrature_orders']:
        nodes, weights = leggauss(order); total = np.zeros(7); previous = origin.copy()
        max_local = np.zeros(7); max_cumulative = np.zeros(7); increments = []
        previous_entropy, previous_bath = initial['entropy_j_k'], mp.mpf(0)
        minimum_step = float('inf')
        for row in accepted:
            left, right = [row['dense_output'][key] for key in ['start_time_s','end_time_s']]
            increment = np.zeros(7)
            for node, weight in zip(nodes, weights, strict=True):
                at = float((left+right)/2+(right-left)*node/2); times.add(at)
                values = polynomial(row, at); computed = state(values, row['segment_index'])
                _, rates = inspect(values, computed, 'dense'); increment += rates*weight*(right-left)/2
            computed = state(row['values'], row['segment_index'])
            current, _ = inspect(row['values'], computed, 'recorded')
            total += increment; increments.append(increment)
            max_local = np.maximum(max_local, np.abs(current-previous-increment))
            max_cumulative = np.maximum(max_cumulative, np.abs(current-origin-total))
            bath = mp.mpf(row['values'][5])*ss
            increment_entropy = computed['entropy_j_k']-previous_entropy+bath-previous_bath
            minimum_step = min(minimum_step, float(increment_entropy))
            previous, previous_entropy, previous_bath = current, computed['entropy_j_k'], bath
        flags = {'local_integrals':bool(np.all(max_local <= budgets)),
                 'cumulative_integrals':bool(np.all(max_cumulative <= budgets)),
                 'nonnegative_step_entropy':minimum_step >= -policy['global_budgets']['negative_step_entropy_j_k']}
        reviews.append({'order':order, 'maximum_local_residuals':max_local.tolist(),
                        'maximum_cumulative_residuals':max_cumulative.tolist(),
                        'minimum_step_entropy_j_k':minimum_step, 'within_budgets':flags})
        integrals.append(np.array(increments))
    difference = integrals[1]-integrals[0]
    quadrature = np.maximum(np.max(np.abs(difference),axis=0), np.max(np.abs(np.cumsum(difference,axis=0)),axis=0))
    flags = {key:value <= policy['global_budgets'][key] for key,value in maxima.items()}
    flags.update(source=all(value <= policy['source_budgets'][key] for key,value in source_errors.items()),
        completed=rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        local_integrals=all(all(row['within_budgets'].values()) for row in reviews),
        quadrature=bool(np.all(quadrature <= budgets)), positive_cv=minima['cv_j_k']>0,
        nonnegative_dissipation=minima['viscous_dissipation_w']>=0,
        nonnegative_entropy_rate=minima['entropy_rate_w_k']>=-policy['global_budgets']['negative_entropy_rate_w_k'])
    endpoint = None
    if all(boundary['conductance_w_k'] == 0 for boundary in case['segments']):
        q = policy['adiabatic_equilibrium']; po = ref.p['outside_pressure_pa']; gamma = ref.p['surface_tension_n_m']
        enthalpy0 = initial['internal_energy_j']+po*initial['pore_volume_m3']
        def residual(ratio, t):
            a = a0*ratio; v = 4*mp.pi*a**3/3
            return (ref.n*ref.r*t/v-po-2*gamma/a)/po, (ref.energy_entropy(a,t)[0]+po*v-enthalpy0)/es
        ratio, temperature = mp.findroot(residual, (q['radius_ratio_start'], q['temperature_start_k']), tol=mp.mpf(q['root_tolerance']), maxsteps=q['root_maximum_steps'])
        radius = a0*ratio; computed, _ = at_time(ends[-1])
        errors = {'radius_m':float(abs(computed['radius_m']-radius)),
                  'temperature_k':float(abs(computed['temperature_k']-temperature)),
                  'equilibrium_force_pa':float(abs(residual(ratio,temperature)[0]*po)),
                  'energy_j':float(abs(residual(ratio,temperature)[1]*es))}
        endpoint = {'radius_m':float(radius), 'temperature_k':float(temperature), 'errors':errors,
                    'within_budgets':{key:value <= q[key] for key,value in errors.items()},
                    'method':'Independent simultaneous constant U+pV and mechanical equilibrium, not a second time integrator.'}
        flags['adiabatic_equilibrium'] = all(endpoint['within_budgets'].values())
    result = {'trajectory':str(path), 'counts':counts, 'source_maxima':source_errors, 'global_maxima':maxima,
              'minima':minima, 'integral_reviews':reviews, 'quadrature_differences':quadrature.tolist(),
              'adiabatic_equilibrium':endpoint, 'final':rows[-1]['final'], 'within_budgets':flags,
              'all_requested_budgets_met':all(flags.values())}
    print(json.dumps({'trajectory':str(path),'all_requested_budgets_met':result['all_requested_budgets_met']}),flush=True)
    return result, times, at_time


def main(make_reference, compare_source):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text()); mp.mp.dps = p['decimal_digits']
    started = time.monotonic(); results = {}
    for case, paths in p['trajectories'].items():
        reviews, functions, nodes = {}, {}, set()
        for name, path in paths.items():
            reviews[name], times, functions[name] = audit(root/path,p,make_reference,compare_source); nodes.update(times)
        maxima = {key:0. for key in p['time_budgets']}
        with (root/paths['base']).open() as stream:
            header = json.loads(next(stream))
        energy_scale = header['settings']['normalization']['energy_j']; entropy_scale = header['settings']['normalization']['entropy_j_k']
        for at in sorted(nodes):
            left, x = functions['base'](at); right, y = functions['refined'](at)
            for key in ['radius_m','temperature_k','gas_pressure_pa','porosity']:
                maxima[key] = max(maxima[key],float(abs(left[key]-right[key])))
            maxima['energy_j'] = max(maxima['energy_j'],float(np.max(np.abs(x[2:5]-y[2:5])))*energy_scale, float(abs(left['internal_energy_j']-right['internal_energy_j'])))
            maxima['entropy_j_k'] = max(maxima['entropy_j_k'],float(np.max(np.abs(x[5:]-y[5:])))*entropy_scale, float(abs(left['entropy_j_k']-right['entropy_j_k'])))
        flags = {key:value <= p['time_budgets'][key] for key,value in maxima.items()}
        results[case] = {'trajectory_reviews':reviews,'time_comparison':{'union_nodes':len(nodes),'maxima':maxima,'within_budgets':flags},
                         'all_requested_budgets_met':all(flags.values()) and all(row['all_requested_budgets_met'] for row in reviews.values())}
    result = {'settings':p,'cases':results,'all_requested_budgets_met':all(row['all_requested_budgets_met'] for row in results.values()),
              'elapsed_s':time.monotonic()-started,'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_budgets_met':result['all_requested_budgets_met'],'elapsed_s':result['elapsed_s']}),flush=True)


if __name__ == '__main__':
    main(reference_factory, source_differences)
