"""Fixed published-parameter comparison, with independent numerical review.

Physical endpoint records remain unsupported; there is no clipping or
fitting to observed porosity. Printed observation errors are diagnostic,
not a statistical confidence band or a material acceptance budget.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.vented_spherical_pore import VentedPoreClock, capillary_clock, vft_viscosity
from sludge_sandbox.viscous_spherical_pore import spherical_pore_mechanics


def independent_clock(records, coefficients, radius, tension):
    """50-digit analytical primitive of inverse VFT; no Gauss rule."""
    a,b,c = [mp.mpf(str(coefficients[key])) for key in ['A','B_k','C_k']]
    beta = mp.log(10)*b

    def primitive(t):
        u = t-c
        return mp.power(10,-a)*(u*mp.exp(-beta/u)+beta*mp.ei(-beta/u))

    clock = mp.mpf(0); values = [clock]
    factor = mp.mpf(str(tension))/mp.mpf(str(radius))
    for left,right in zip(records,records[1:]):
        t1,t2 = [mp.mpf(str(row['temperature_k'])) for row in (left,right)]
        dt = mp.mpf(str(right['time_s']))-mp.mpf(str(left['time_s']))
        integral = (dt*mp.power(10,-a-b/(t1-c)) if t1==t2
                    else dt*(primitive(t2)-primitive(t1))/(t2-t1))
        clock += factor*integral; values.append(clock)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text()); review = p['independent_review']
    data = json.loads((root/p['observations']).read_text())
    mp.mp.dps = review['decimal_digits']
    models = {phi:{'base':VentedPoreClock(phi,p['numerics'],1.0,1.0),
                   'refined':VentedPoreClock(phi,p['numerics'],p['numerics']['refinement_factor'],p['numerics']['refined_maximum_step_factor'])}
              for phi in review['porosities']}
    maxima = {'time_normalized_porosity':0.0,'quadrature_clock':0.0,
              'source_clock':0.0,'closure_clock':0.0,'radius_implicit_clock':0.0,
              'mechanical_rate_m_s':0.0,'vft_relative':0.0}
    static = []
    for phi,pair in models.items():
        k = mp.mpf(str(phi))/(1-mp.mpf(str(phi)))
        closed = 2*mp.quad(lambda x:1/(1+k*x**3),[0,1])
        for tolerance,model in pair.items():
            error = float(abs(closed-model.closure_clock))
            maxima['closure_clock'] = max(maxima['closure_clock'],error)
            static.append({'porosity':phi,'tolerance':tolerance,'closure_clock':model.closure_clock,
                           'source_closure_clock':float(closed),'error':error,
                           'accepted_clock_steps':len(model.solution.t)-1,
                           'solver_status':model.solution.status,'solver_message':model.solution.message})
        for x0 in review['radius_fractions']:
            tau = 2*mp.quad(lambda x:1/(1+k*x**3),[mp.mpf(str(x0)),1])
            x = pair['refined'].at_clock(float(tau))['radius_fraction']
            error = float(abs(2*mp.quad(lambda z:1/(1+k*z**3),[mp.mpf(x),1])-tau))
            maxima['radius_implicit_clock'] = max(maxima['radius_implicit_clock'],error)
            radius = p['model']['initial_pore_radius_m']*x0
            volume = 4*math.pi*p['model']['initial_pore_radius_m']**3/3*(1-phi)/phi
            for temperature in review['temperatures_k']:
                eta = float(vft_viscosity(temperature,p['model']['vft']))
                state = spherical_pore_mechanics(radius,review['outside_pressure_pa'],matrix_volume=volume,
                    viscosity=eta,surface_tension=p['model']['surface_tension_n_m'],outside_pressure=review['outside_pressure_pa'])
                expected = -p['model']['surface_tension_n_m']/(2*eta)*(1+float(k)*x0**3)
                maxima['mechanical_rate_m_s'] = max(maxima['mechanical_rate_m_s'],abs(state['radius_rate_m_s']-expected))
                v = p['model']['vft']; independent = mp.power(10,mp.mpf(str(v['A']))+mp.mpf(str(v['B_k']))/(mp.mpf(str(temperature))-mp.mpf(str(v['C_k']))))
                maxima['vft_relative'] = max(maxima['vft_relative'],float(abs(eta-independent)/independent))
    results = []
    for run in data['runs']:
        records = run['records']; times = [r['time_s'] for r in records]; temperatures = [r['temperature_k'] for r in records]
        variants = []
        for variant in p['sensitivity_variants']:
            radius = variant['initial_pore_radius_m']; phi = variant['initial_porosity']; tension = p['model']['surface_tension_n_m']
            pair = models[phi]
            clocks = [capillary_clock(times,temperatures,radius,tension,variant['vft'],order) for order in p['numerics']['clock_gauss_orders']]
            source = independent_clock(records,variant['vft'],radius,tension)
            maxima['quadrature_clock'] = max(maxima['quadrature_clock'],float(np.max(np.abs(clocks[0]-clocks[1]))))
            maxima['source_clock'] = max(maxima['source_clock'],max(float(abs(x-y)) for x,y in zip(source,clocks[-1])))
            points = []
            for i,(row,tau) in enumerate(zip(records,clocks[-1])):
                supported = tau < min(pair['base'].closure_clock,pair['refined'].closure_clock)
                item = {**row,'capillary_clock':float(tau),'inside_positive_radius_domain':bool(supported)}
                if supported:
                    base = pair['base'].at_clock(tau); state = pair['refined'].at_clock(tau)
                    maxima['time_normalized_porosity'] = max(maxima['time_normalized_porosity'],abs(base['normalized_porosity']-state['normalized_porosity']))
                    if i % review['reference_sample_stride']==0 or i==len(records)-1:
                        k = mp.mpf(str(phi))/(1-mp.mpf(str(phi)))
                        back = 2*mp.quad(lambda x:1/(1+k*x**3),[mp.mpf(state['radius_fraction']),1])
                        maxima['radius_implicit_clock'] = max(maxima['radius_implicit_clock'],float(abs(back-source[i])))
                    residual = state['normalized_porosity']-row['normalized_porosity']
                    item.update(radius_fraction=state['radius_fraction'],
                        normalized_porosity_prediction=state['normalized_porosity'],porosity_residual=residual,
                        within_printed_error=bool(abs(residual)<=row['porosity_error_printed']))
                else:
                    item.update(radius_fraction=None,normalized_porosity_prediction=None,porosity_residual=None,
                                within_printed_error=None,reason='Vented positive-radius solution has reached its finite closure endpoint; no tail model.')
                points.append(item)
            supported = [r for r in points if r['inside_positive_radius_domain']]
            early = [r for r in supported if r['capillary_clock']<=p['comparison']['early_capillary_clock_max']]
            metrics = {}
            for name,group in [('supported',supported),('early',early)]:
                metrics[name] = {'count':len(group),'mae':float(np.mean([abs(r['porosity_residual']) for r in group])),
                                 'maximum_absolute_residual':max(abs(r['porosity_residual']) for r in group),
                                 'inside_printed_error_count':sum(r['within_printed_error'] for r in group)}
            variants.append({'settings':variant,'closure_clock':pair['refined'].closure_clock,
                             'metrics':metrics,'unsupported_after_closure_count':len(points)-len(supported),'points':points})
        results.append({key:value for key,value in run.items() if key!='records'}|{'variants':variants})
        print(json.dumps({'run':run['run_id'],'central':variants[0]['metrics'],
                          'after_closure':variants[0]['unsupported_after_closure_count']}),flush=True)
    budgets = {'time_normalized_porosity':review['time_budget_normalized_porosity'],
               'quadrature_clock':review['clock_budget'],'source_clock':review['clock_budget'],
               'closure_clock':review['closure_clock_budget'],'radius_implicit_clock':review['radius_implicit_clock_budget'],
               'mechanical_rate_m_s':review['mechanical_rate_budget_m_s'],'vft_relative':review['vft_relative_budget']}
    flags = {key:value<=budgets[key] for key,value in maxima.items()}
    result = {'settings':p,'source':json.loads((root/p['source']).read_text()),'numerical_review':{
        'static':static,'maxima':maxima,'budgets':budgets,'within_budgets':flags,
        'all_requested_numerical_budgets_met':all(flags.values())},'runs':results,
        'material_qualified':False,'training_eligible':False,
        'interpretation':'Numerical qualification and observed-curve discrepancies are separate. No fit, no complete material error budget, no extrapolation past positive-radius closure.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
    print(json.dumps(result['numerical_review']),flush=True)


if __name__=='__main__':
    main()
