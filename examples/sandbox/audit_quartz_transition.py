"""Full recorded source, heat, entropy and phase-event review for pure quartz."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.recorded_quartz_transition import RecordedQuartzTransition


def polynomial(record,t):
    dense=record['dense_output'];values=np.array(dense['differences']);result=values[0].copy();product=1.
    for i,(shift,denominator) in enumerate(zip(dense['shifts_s'],dense['denominators_s'],strict=True)):
        product*= (t-shift)/denominator;result+=product*values[i+1]
    return result


def audit(path,settings):
    with path.open() as stream:rows=[json.loads(line) for line in stream]
    header,initial=rows[:2];p=header['settings'];source=header['source_facts'];budget=p['verification']
    model=RecordedQuartzTransition(source,p);capsule=p['virtual_calorimeter'];n=capsule['amount_mol'];g=capsule['heat_conductance_w_k']
    h0=header['initial_total_enthalpy_j'];s0=n*initial['state']['entropy_j_mol_k'];tt=p['phase_transition']['temperature_k']
    def primitive(phase,t):
        a,b,c,d,e,*_=map(float,source['segments'][phase]['coefficients']);scale=p['caloric_representation']['temperature_scale_k'];x=t/scale
        return scale*(a*x+b*x*x/2+c*x**3/3+d*x**4/4-e/x),a*np.log(x)+b*x+c*x*x/2+d*x**3/3-e/(2*x*x)
    low0=primitive(0,p['reference']['temperature_k']);lowt=primitive(0,tt);hight=primitive(1,tt)
    ha=p['reference']['enthalpy_j_mol']+lowt[0]-low0[0];sa=p['reference']['entropy_j_mol_k']+lowt[1]-low0[1]
    latent=p['phase_transition']['latent_enthalpy_j_mol']
    def independent_standard(state):
        t=state['temperature_k'];f=state['beta_fraction']
        if state['phase']=='coexistence':return ha+f*latent,sa+f*latent/tt
        if state['phase']=='alpha':
            h,s=primitive(0,t);return p['reference']['enthalpy_j_mol']+h-low0[0],p['reference']['entropy_j_mol_k']+s-low0[1]
        h,s=primitive(1,t);return ha+latent+h-hight[0],sa+latent/tt+s-hight[1]
    maxima={'source_enthalpy_j_mol':0.,'source_entropy_j_mol_k':0.,'heat_ledger_j':0.}
    observed=0;minimum_production=float('inf');events=[];transitions={}
    for row in rows:
        if 'state' not in row:continue
        observed+=1;state=row['state'];h,s=independent_standard(state)
        maxima['source_enthalpy_j_mol']=max(maxima['source_enthalpy_j_mol'],abs(h-state['enthalpy_j_mol']))
        maxima['source_entropy_j_mol_k']=max(maxima['source_entropy_j_mol_k'],abs(s-state['entropy_j_mol_k']))
        maxima['heat_ledger_j']=max(maxima['heat_ledger_j'],abs(row['values'][0]-row['values'][1]))
        minimum_production=min(minimum_production,row['instantaneous_entropy_production_w_k'])
        if row['kind']=='phase_event':events.append(row)
        if row['kind'] in ('initial','boundary_transition'):transitions[row['segment_index']]=row
    integrals=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(3);max_local=max_global=max_entropy=0.;previous=initial;minimum_step=float('inf')
        for row in rows:
            if row['kind']!='accepted':continue
            dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s'];wall=row['reservoir_temperature_k'];integral=np.zeros(3)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2;state=model.from_enthalpy((h0+polynomial(row,at)[0])/n)
                t=state['temperature_k'];heat=g*(wall-t)
                integral+=weight*(right-left)/2*np.array([heat,-heat/wall,heat*(1/t-1/wall)])
            total+=integral;state=row['state'];entropy=n*state['entropy_j_mol_k']-s0+total[1]
            max_local=max(max_local,abs(row['values'][0]-previous['values'][0]-integral[0]))
            max_global=max(max_global,abs(row['values'][0]-total[0]));max_entropy=max(max_entropy,abs(entropy-total[2]))
            step_entropy=n*(state['entropy_j_mol_k']-previous['state']['entropy_j_mol_k'])+integral[1]
            minimum_step=min(minimum_step,step_entropy);previous=row
        integrals.append({'order':order,'final_integrals_heat_reservoir_entropy_production':total.tolist(),
            'maximum_local_heat_residual_j':max_local,'maximum_cumulative_heat_residual_j':max_global,'maximum_entropy_residual_j_k':max_entropy,
            'minimum_step_total_entropy_change_j_k':minimum_step,'within_budget':bool(max_local<=budget['energy_j'] and max_global<=budget['energy_j'] and max_entropy<=budget['entropy_j_k'] and minimum_step>=-budget['nonnegative_entropy_j_k'])})
    event_reviews=[]
    for segment,start in transitions.items():
        wall=p['virtual_calorimeter']['program'][segment]['reservoir_temperature_k'];temperature=start['state']['temperature_k']
        heating=wall>temperature;phase=0 if heating else 1
        limits=(temperature,tt) if heating else (tt,temperature)
        time_integral,_=quad(lambda t:n/g*model.cp(phase,t)/(wall-t if heating else t-wall),*limits,
            epsabs=settings['analytic_quadrature_absolute_tolerance_s'],epsrel=settings['analytic_quadrature_relative_tolerance'])
        first=start['time_s']+time_integral;second=first+n*latent/(g*abs(wall-tt))
        expected={'alpha_endpoint':first,'beta_endpoint':second} if heating else {'beta_endpoint':first,'alpha_endpoint':second}
        for row in (r for r in events if r['segment_index']==segment):
            difference=row['time_s']-expected[row['endpoint']]
            event_reviews.append({'segment':segment,'endpoint':row['endpoint'],'recorded_time_s':row['time_s'],
                'independent_calorimetric_time_s':expected[row['endpoint']],'difference_s':difference,'within_budget':abs(difference)<=budget['phase_event_time_s']})
    qdiff=np.abs(np.array(integrals[0]['final_integrals_heat_reservoir_entropy_production'])-np.array(integrals[1]['final_integrals_heat_reservoir_entropy_production']))
    flags={'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'source_enthalpy':maxima['source_enthalpy_j_mol']<=budget['source_quadrature_h_j_mol'],
        'source_entropy':maxima['source_entropy_j_mol_k']<=budget['source_quadrature_s_j_mol_k'],
        'heat_ledger':maxima['heat_ledger_j']<=budget['energy_j'],'integrals':all(r['within_budget'] for r in integrals),
        'quadrature':bool(qdiff[0]<=budget['energy_j'] and max(qdiff[1:])<=budget['entropy_j_k']),
        'entropy_sign':minimum_production>=0,'four_expected_events':len(event_reviews)==4,
        'phase_events':all(r['within_budget'] for r in event_reviews)}
    flags={name:bool(value) for name,value in flags.items()}
    return {'trajectory':str(path),'observed_states':observed,'maxima':maxima,'minimum_entropy_production_w_k':minimum_production,
        'integrals':integrals,'quadrature_differences':qdiff.tolist(),'phase_events':event_reviews,'within_budgets':flags,
        'all_requested_numerical_budgets_met':all(flags.values())},rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());reviews={};records={}
    for name,path in settings['trajectories'].items():
        review,rows=audit(root/path,settings);reviews[name]=review;records[name]=rows
        print(json.dumps({'name':name,'within_budgets':review['within_budgets']}),flush=True)
    budget=records['base'][0]['settings']['verification'];left={r['time_s']:r for r in records['base'] if r['kind']=='sample'};right={r['time_s']:r for r in records['refined'] if r['kind']=='sample'}
    temperature=max(abs(left[t]['state']['temperature_k']-right[t]['state']['temperature_k']) for t in left)
    fraction=max(abs(left[t]['state']['beta_fraction']-right[t]['state']['beta_fraction']) for t in left)
    comparison={'sample_count':len(left),'maximum_temperature_difference_k':temperature,'maximum_beta_fraction_difference':fraction,
        'within_budgets':temperature<=budget['time_temperature_k'] and fraction<=budget['time_phase_fraction']}
    result={'settings':settings,'trajectory_reviews':reviews,'time_comparison':comparison,
        'all_requested_numerical_budgets_met':all(r['all_requested_numerical_budgets_met'] for r in reviews.values()) and comparison['within_budgets'],
        'scope':'Full conditional enthalpy and entropy accounting; shared enthalpy decoder in quadrature, independent source primitive evaluation and event-time integrals. No empirical quartz-device or brick validation.',
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'time_comparison':comparison}))


if __name__=='__main__':main()
