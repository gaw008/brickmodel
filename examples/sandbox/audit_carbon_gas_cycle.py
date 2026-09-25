"""Full source, heat, entropy and phase-time review of finite-carbon calorimetry."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad

from carbon_gas_setup import build


def polynomial(record,t):
    dense=record['dense_output'];values=np.array(dense['differences']);result=values[0].copy();product=1.
    for i,(shift,denominator) in enumerate(zip(dense['shifts_s'],dense['denominators_s'],strict=True)):
        product*=(t-shift)/denominator;result+=product*values[i+1]
    return result


def audit(path,settings,root):
    with path.open() as stream:rows=[json.loads(line) for line in stream]
    header,initial=rows[:2];p=header['settings'];source=header['source_facts'];budget=p['verification']
    model,_=build(root,header['equilibrium_parameters']);inventory=header['inventory']
    inputs=[inventory[k] for k in ['carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
    h0=header['initial_total_enthalpy_j'];s0=initial['state']['entropy_j_k'];g=p['virtual_calorimeter']['heat_conductance_w_k']
    r=float(source['gas_constant_j_mol_k']);p0=float(source['reference_pressure_pa']);t0=float(source['reference_temperature_k'])
    def primitive(coefficients,t):
        a,b,c,d,e=map(float,coefficients)
        return (a*t+b*t*t/2-c/t+2*d*math.sqrt(t)+e*t**3/3,
            a*math.log(t)+b*t-c/(2*t*t)-2*d/math.sqrt(t)+e*t*t/2)
    reference={name:primitive(phase['cp_coefficient_strings'],t0) for name,phase in source['phases'].items()}
    maxima={name:0. for name in ['element_mol','pressure_pa','reaction_gibbs_j_mol','source_enthalpy_j','source_entropy_j_k','enthalpy_inverse_j','heat_ledger_j','entropy_ledger_j_k']}
    counts={'recorded':0,'dense':0};min_gas=float('inf');min_solid=float('inf');min_production=float('inf');events=[];transitions={}
    def source_review(state,total_h,category):
        nonlocal min_gas,min_solid
        counts[category]+=1;t=state['temperature_k'];amounts=state['amounts_mol'];gas={name:n for name,n in amounts.items() if name!='C'};ng=math.fsum(gas.values())
        min_gas=min(min_gas,*gas.values());min_solid=min(min_solid,amounts['C']);hs={};ss={};mu={}
        for name,phase in source['phases'].items():
            hp,sp=primitive(phase['cp_coefficient_strings'],t);hp0,sp0=reference[name]
            hs[name]=float(phase['reference_enthalpy_j_mol'])+hp-hp0
            ss[name]=float(phase['reference_entropy_j_mol_k'])+sp-sp0
            mu[name]=hs[name]-t*ss[name]
            if name!='C':
                ss[name]-=r*math.log(gas[name]/ng);mu[name]=hs[name]-t*ss[name]
        h=math.fsum(amounts[name]*hs[name] for name in amounts);s=math.fsum(amounts[name]*ss[name] for name in amounts)
        element_error=max(abs(math.fsum((amounts['C'],gas['CO'],gas['CO2']))-inputs[0]),
            abs(math.fsum((gas['CO'],2*gas['CO2'],2*gas['O2']))-inputs[1]),abs(2*gas['N2']-2*inputs[2]))
        pressure_error=max(abs(state['pressure_pa']-p0),abs(math.fsum(state['partial_pressures_pa'].values())-p0),
            *(abs(state['partial_pressures_pa'][name]-p0*n/ng) for name,n in gas.items()))
        a1=mu['CO']-mu['C']-mu['O2']/2;a2=mu['CO2']-mu['C']-mu['O2'];ag=mu['CO2']-mu['CO']-mu['O2']/2
        chemical_error=max(abs(a1),abs(a2),abs(ag)) if state['phase']=='graphite_present' else max(0.,a1,a2,abs(ag))
        for name,value in [('element_mol',element_error),('pressure_pa',pressure_error),('reaction_gibbs_j_mol',chemical_error),
            ('source_enthalpy_j',abs(state['enthalpy_j']-h)),('source_entropy_j_k',abs(state['entropy_j_k']-s)),('enthalpy_inverse_j',abs(total_h-h))]:
            maxima[name]=max(maxima[name],value)
    for row in rows:
        if 'state' not in row:continue
        source_review(row['state'],row['total_enthalpy_j'],'recorded')
        maxima['heat_ledger_j']=max(maxima['heat_ledger_j'],abs(row['values'][0]-row['values'][1]))
        maxima['entropy_ledger_j_k']=max(maxima['entropy_ledger_j_k'],abs(row['state']['entropy_j_k']-s0+row['values'][2]-row['values'][3]))
        min_production=min(min_production,row['instantaneous_entropy_production_w_k'])
        if row['kind']=='phase_event':events.append(row)
        if row['kind'] in ('initial','boundary_transition'):transitions[row['segment_index']]=row
    integral_reviews=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(3);previous=initial;max_local=max_global=max_entropy=0.;minimum_step=float('inf');max_local_entropy=0.;max_ledgers=np.zeros(3)
        for row in rows:
            if row['kind']!='accepted':continue
            dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s'];wall=row['reservoir_temperature_k'];integral=np.zeros(3)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2;values=polynomial(row,at);total_h=h0+float(values[0])
                state=model.from_enthalpy(total_h,*inputs,p['enthalpy_inverse']);source_review(state,total_h,'dense')
                t=state['temperature_k'];heat=g*(wall-t);production=heat*(1/t-1/wall);min_production=min(min_production,production)
                integral+=weight*(right-left)/2*np.array([heat,-heat/wall,production])
            total+=integral;state=row['state'];entropy=state['entropy_j_k']-s0+total[1]
            max_local=max(max_local,abs(row['values'][0]-previous['values'][0]-integral[0]))
            max_global=max(max_global,abs(row['values'][0]-total[0]));max_entropy=max(max_entropy,abs(entropy-total[2]))
            max_ledgers=np.maximum(max_ledgers,np.abs(np.array(row['values'][1:])-total))
            step_entropy=state['entropy_j_k']-previous['state']['entropy_j_k']+integral[1]
            max_local_entropy=max(max_local_entropy,abs(step_entropy-integral[2]));minimum_step=min(minimum_step,step_entropy);previous=row
        flags={'local_energy':max_local<=budget['energy_j'],'cumulative_energy':max_global<=budget['energy_j'],
            'local_entropy':max_local_entropy<=budget['entropy_j_k'],'cumulative_entropy':max_entropy<=budget['entropy_j_k'],
            'heat_integral':max_ledgers[0]<=budget['energy_j'],'entropy_integrals':max(max_ledgers[1:])<=budget['entropy_j_k'],
            'nonnegative_step_entropy':minimum_step>=-budget['nonnegative_entropy_j_k']}
        integral_reviews.append({'order':order,'final_integrals_heat_reservoir_entropy_production':total.tolist(),
            'maximum_local_heat_residual_j':max_local,'maximum_cumulative_heat_residual_j':max_global,
            'maximum_local_entropy_residual_j_k':max_local_entropy,'maximum_cumulative_entropy_residual_j_k':max_entropy,
            'maximum_ledger_integral_residuals':max_ledgers.tolist(),'minimum_step_total_entropy_change_j_k':minimum_step,
            'within_budgets':{key:bool(value) for key,value in flags.items()}})
    boundary=json.loads((root/settings['phase_boundary_reference']).read_text());tt=float(boundary['reference_boundary_temperature_k']);event_reviews=[]
    for event in events:
        start=transitions[event['segment_index']];wall=start['reservoir_temperature_k'];tstart=start['state']['temperature_k']
        dt,error=quad(lambda t:model.at_temperature(t,*inputs)['equilibrium_cp_j_k']/(g*(wall-t)),tstart,tt,
            epsabs=settings['calorimetric_quadrature_absolute_tolerance_s'],epsrel=settings['calorimetric_quadrature_relative_tolerance'])
        target=start['time_s']+dt;difference=event['time_s']-target
        event_reviews.append({'segment':event['segment_index'],'direction':event['direction'],'recorded_time_s':event['time_s'],
            'calorimetric_time_s':target,'quadrature_estimated_error_s':error,'time_difference_s':difference,
            'temperature_difference_k':event['state']['temperature_k']-tt,
            'within_budget':abs(difference)<=budget['phase_event_time_s'] and abs(event['state']['temperature_k']-tt)<=budget['phase_event_temperature_k']})
    qdiff=np.abs(np.array(integral_reviews[0]['final_integrals_heat_reservoir_entropy_production'])-np.array(integral_reviews[1]['final_integrals_heat_reservoir_entropy_production']))
    flags={name:maxima[name]<=budget[name] for name in ['element_mol','pressure_pa','reaction_gibbs_j_mol','source_enthalpy_j','source_entropy_j_k']}
    flags.update({'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed','positive_gas':min_gas>0,'nonnegative_solid':min_solid>=0,
        'enthalpy_inverse':maxima['enthalpy_inverse_j']<=budget['source_enthalpy_j'],'heat_ledger':maxima['heat_ledger_j']<=budget['energy_j'],
        'entropy_ledger':maxima['entropy_ledger_j_k']<=budget['entropy_j_k'],'dense_integrals':all(all(r['within_budgets'].values()) for r in integral_reviews),
        'quadrature':qdiff[0]<=budget['energy_j'] and max(qdiff[1:])<=budget['entropy_j_k'],'entropy_production':min_production>=0,
        'expected_events':len(event_reviews)==budget['expected_phase_events'],'phase_events':all(r['within_budget'] for r in event_reviews)})
    return {'trajectory':str(path),'source_review_counts':counts,'maxima':maxima,'minimum_gas_mol':min_gas,'minimum_solid_mol':min_solid,
        'minimum_entropy_production_w_k':min_production,'integral_reviews':integral_reviews,'quadrature_differences':qdiff.tolist(),
        'phase_event_reviews':event_reviews,'within_budgets':{k:bool(v) for k,v in flags.items()},'all_requested_numerical_budgets_met':bool(all(flags.values()))},rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());reviews={};records={}
    for name,path in settings['trajectories'].items():
        review,rows=audit(root/path,settings,root);reviews[name]=review;records[name]=rows
        print(json.dumps({'name':name,'within_budgets':review['within_budgets']}),flush=True)
    left_name,right_name=settings['time_comparison_pair']
    left={r['time_s']:r for r in records[left_name] if r['kind']=='sample'};right={r['time_s']:r for r in records[right_name] if r['kind']=='sample'}
    budget=records[left_name][0]['settings']['verification'];temperature=max(abs(left[t]['state']['temperature_k']-right[t]['state']['temperature_k']) for t in left)
    species={name:max(abs(left[t]['state']['amounts_mol'][name]-right[t]['state']['amounts_mol'][name]) for t in left) for name in left[next(iter(left))]['state']['amounts_mol']}
    comparison={'samples':len(left),'maximum_temperature_difference_k':temperature,'maximum_species_differences_mol':species,
        'within_budgets':temperature<=budget['time_temperature_k'] and max(species.values())<=budget['time_species_mol']}
    result={'settings':settings,'trajectory_reviews':reviews,'time_comparison':comparison,
        'all_requested_numerical_budgets_met':all(r['all_requested_numerical_budgets_met'] for r in reviews.values()) and comparison['within_budgets'],
        'material_qualified':False,'training_eligible':False,'scope':settings['scope']}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'time_comparison':comparison}))


if __name__=='__main__':main()
