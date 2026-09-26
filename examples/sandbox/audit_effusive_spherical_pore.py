"""Full independent source, inventory, energy and entropy trajectory review."""
import argparse
from bisect import bisect_left
import json
from pathlib import Path
import time

import mpmath as mp
import numpy as np
from numpy.polynomial.legendre import leggauss

from audit_water_gas_shift_cycle import polynomial
from effusive_pore_reference import EffusivePoreReference


def audit(path,policy):
    with path.open() as stream:rows = [json.loads(line) for line in stream]
    header = rows[0];p = header['settings'];budget = p['verification']
    ref = EffusivePoreReference(p,header['sources'])
    scales = np.asarray(header['coordinate_scales']);mpscales = list(map(mp.mpf,scales))
    accepted = [r for r in rows if r['kind']=='accepted'];ends = [r['time_s'] for r in accepted]
    times = {r['time_s'] for r in rows if 'state' in r}
    counts = {'recorded':0,'dense':0}
    source_maxima = {key:0. for key in policy['source_budgets']}
    maxima = {'energy_j':0.,'entropy_j_k':0.,'gas_amount_mol':0.,'external_work_j':0.}
    minima = {'gas_amount_mol':float('inf'),'radius_m':float('inf'),
              'temperature_k':float('inf'),'entropy_production_w_k':float('inf'),
              'effusion_entropy_production_w_k':float('inf')}

    def state(values,segment):
        physical = [mp.mpf(float(v))*s for v,s in zip(values,mpscales,strict=True)]
        return ref.at_state(*physical[:5],header['case']['segments'][segment]),physical

    initial,origin_mp = state(rows[1]['values'],0)
    origin = np.asarray(rows[1]['values'])*scales
    v0 = 4*mp.pi*origin_mp[0]**3/3
    n0 = origin_mp[3]+origin_mp[4]

    def inspect(values,segment,category):
        computed,physical = state(values,segment);counts[category]+=1
        maxima['energy_j'] = max(maxima['energy_j'],float(abs(computed['internal_energy_j']-initial['internal_energy_j']-sum(physical[5:8]))))
        maxima['entropy_j_k'] = max(maxima['entropy_j_k'],float(abs(computed['entropy_j_k']-initial['entropy_j_k']+physical[10]-physical[11])))
        maxima['gas_amount_mol'] = max(maxima['gas_amount_mol'],float(abs(physical[3]+physical[4]-n0)))
        volume = 4*mp.pi*physical[0]**3/3
        maxima['external_work_j'] = max(maxima['external_work_j'],float(abs(physical[5]+ref.p['outside_pressure_pa']*(volume-v0))))
        minima['gas_amount_mol'] = min(minima['gas_amount_mol'],float(min(physical[3:5])))
        minima['radius_m'] = min(minima['radius_m'],float(physical[0]))
        minima['temperature_k'] = min(minima['temperature_k'],float(min(physical[1:3])))
        for field in ['entropy_production_w_k','effusion_entropy_production_w_k']:
            minima[field] = min(minima[field],float(computed[field]))
        flow = computed['gas_transfer_mol_s']
        rates = [computed['radius_rate_m_s'],computed['pore_temperature_rate_k_s'],
            computed['reservoir_temperature_rate_k_s'],-flow,flow,computed['external_work_in_w'],
            computed['pore_heat_in_w'],computed['reservoir_heat_in_w'],computed['effusive_energy_w'],
            computed['viscous_dissipation_w'],computed['bath_entropy_rate_w_k'],computed['entropy_production_w_k']]
        return computed,np.array(list(map(float,physical))),np.array(list(map(float,rates)))

    for row in rows:
        if 'state' not in row:continue
        computed,_,_ = inspect(row['values'],row['segment_index'],'recorded')
        for key in source_maxima:
            source_maxima[key] = max(source_maxima[key],float(abs(mp.mpf(row['state'][key])-computed[key])))
    integrals,reviews = [],[]
    integral_budget = np.asarray(policy['integral_budgets'])
    for order in budget['quadrature_orders']:
        nodes,weights = leggauss(order);total = np.zeros(len(scales));previous = origin
        previous_s,previous_bath = initial['entropy_j_k'],mp.mpf(0)
        maximum_local = np.zeros(len(scales));maximum_cumulative = np.zeros(len(scales))
        increments = [];minimum_step = float('inf')
        for row in accepted:
            dense = row['dense_output'];left,right = dense['start_time_s'],dense['end_time_s']
            increment = np.zeros(len(scales))
            for node,weight in zip(nodes,weights,strict=True):
                at = float((left+right)/2+(right-left)*node/2);times.add(at)
                _,_,rates = inspect(polynomial(row,at),row['segment_index'],'dense')
                increment += rates*weight*(right-left)/2
            computed,current,_ = inspect(row['values'],row['segment_index'],'recorded')
            total += increment;increments.append(increment)
            maximum_local = np.maximum(maximum_local,np.abs(current-previous-increment))
            maximum_cumulative = np.maximum(maximum_cumulative,np.abs(current-origin-total))
            bath = mp.mpf(row['values'][10])*mpscales[10]
            minimum_step = min(minimum_step,float(computed['entropy_j_k']-previous_s+bath-previous_bath))
            previous,previous_s,previous_bath = current,computed['entropy_j_k'],bath
        flags = {'local':bool(np.all(maximum_local<=integral_budget)),
                 'cumulative':bool(np.all(maximum_cumulative<=integral_budget)),
                 'nonnegative_step_entropy':minimum_step>=-budget['negative_step_entropy_j_k']}
        reviews.append({'order':order,'maximum_local_residuals':maximum_local.tolist(),
                        'maximum_cumulative_residuals':maximum_cumulative.tolist(),
                        'minimum_step_entropy_j_k':minimum_step,'within_budgets':flags})
        integrals.append(np.asarray(increments))
    delta = integrals[1]-integrals[0]
    quadrature = np.maximum(np.max(np.abs(delta),axis=0),np.max(np.abs(np.cumsum(delta,axis=0)),axis=0))
    flags = {key:value<=budget[key] for key,value in maxima.items() if key!='external_work_j'}
    flags.update(external_work=maxima['external_work_j']<=budget['energy_j'],
        source=all(source_maxima[k]<=v for k,v in policy['source_budgets'].items()),
        completed=rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        local_integrals=all(all(r['within_budgets'].values()) for r in reviews),
        quadrature=bool(np.all(quadrature<=integral_budget)),
        positive_amounts=minima['gas_amount_mol']>0,positive_radius=minima['radius_m']>0,
        nonnegative_entropy=minima['entropy_production_w_k']>=-budget['negative_entropy_rate_w_k'],
        nonnegative_effusion=minima['effusion_entropy_production_w_k']>=-budget['negative_entropy_rate_w_k'])

    def at_time(at):
        if at==0:values,segment = rows[1]['values'],0
        else:
            row = accepted[bisect_left(ends,at)]
            values,segment = polynomial(row,at),row['segment_index']
        return state(values,segment)

    result = {'trajectory':str(path),'counts':counts,'source_maxima':source_maxima,'global_maxima':maxima,
        'minima':minima,'integral_reviews':reviews,'quadrature_differences':quadrature.tolist(),
        'final':rows[-1]['final'],'within_budgets':flags,'all_requested_budgets_met':all(flags.values())}
    print(json.dumps({'trajectory':str(path),'all_requested_budgets_met':result['all_requested_budgets_met']}),flush=True)
    return result,times,at_time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent
    policy = json.loads(args.parameters.read_text());mp.mp.dps = policy['decimal_digits']
    started = time.monotonic();cases = {}
    for name,paths in policy['trajectories'].items():
        reviews = {k:audit(root/path,policy) for k,path in paths.items()}
        union = sorted(reviews['base'][1]|reviews['refined'][1])
        maxima = {k:0. for k in ['radius_m','temperature_k','amount_mol','pressure_pa']}
        for at in union:
            a,xa = reviews['base'][2](at);b,xb = reviews['refined'][2](at)
            maxima['radius_m'] = max(maxima['radius_m'],float(abs(xa[0]-xb[0])))
            maxima['temperature_k'] = max(maxima['temperature_k'],*(float(abs(xa[i]-xb[i])) for i in [1,2]))
            maxima['amount_mol'] = max(maxima['amount_mol'],*(float(abs(xa[i]-xb[i])) for i in [3,4]))
            maxima['pressure_pa'] = max(maxima['pressure_pa'],*(float(abs(a[k]-b[k])) for k in ['pore_pressure_pa','reservoir_pressure_pa']))
        header = json.loads((root/paths['base']).open().readline())
        budget = header['settings']['verification']
        flags = {k:v<=budget['time_'+k] for k,v in maxima.items()}
        cases[name] = {'trajectories':{k:v[0] for k,v in reviews.items()},
            'time_comparison':{'union_nodes':len(union),'maximum_differences':maxima,'within_budgets':flags},
            'all_requested_budgets_met':all(flags.values()) and all(v[0]['all_requested_budgets_met'] for v in reviews.values())}
        print(json.dumps({'case':name,'all_requested_budgets_met':cases[name]['all_requested_budgets_met'],'time_maxima':maxima}),flush=True)
    result = {'settings':policy,'cases':cases,'elapsed_s':time.monotonic()-started,
        'all_requested_budgets_met':all(c['all_requested_budgets_met'] for c in cases.values()),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__ == '__main__':
    main()
