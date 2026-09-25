"""Full coupled Ca/C/O calorimeter source, conservation and phase-time audit."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad

from carbon_calcium_setup import build
from audit_carbon_gas_cycle import polynomial


def audit(path,settings,root):
    with path.open() as stream:rows=[json.loads(line) for line in stream]
    header,initial=rows[:2];p=header['settings'];sources=header['sources'];budget=p['verification']
    model,_=build(root,header['equilibrium_parameters']);inventory=header['inventory']
    inputs=[inventory[k] for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
    h0=header['initial_total_enthalpy_j'];s0=initial['state']['entropy_j_k'];g=p['virtual_calorimeter']['heat_conductance_w_k']
    source=sources['carbon_source'];r=float(source['gas_constant_j_mol_k']);p0=float(source['reference_pressure_pa']);thermal={}
    for name,phase in source['phases'].items():
        thermal[name]=(tuple(map(float,phase['cp_coefficient_strings'])),float(source['reference_temperature_k']),
            float(phase['reference_enthalpy_j_mol']),float(phase['reference_entropy_j_mol_k']))
    for phase in sources['calcite_facts']['species']:
        name=phase['id']
        if name in ['calcite','lime']:
            thermal[name]=(tuple(float(phase['cp']['coefficients_nominal'][key]) for key in ['A1','A2','A3','A4','A5']),
                float(sources['calcite_facts']['reference_state']['temperature_k']),
                float(phase['reference_298']['hf_kj_mol'])*sources['calcite_parameters']['joules_per_kilojoule'],
                float(sources['calcite_source']['phases'][name]['entropy_reference_j_mol_k']))
    def primitive(coefficients,t):
        a,b,c,d,e=coefficients
        return (a*t+b*t*t/2-c/t+2*d*math.sqrt(t)+e*t**3/3,
            a*math.log(t)+b*t-c/(2*t*t)-2*d/math.sqrt(t)+e*t*t/2)
    reference={name:primitive(data[0],data[1]) for name,data in thermal.items()}
    maxima={name:0. for name in ['element_mol','pressure_pa','reaction_gibbs_j_mol','source_enthalpy_j','source_entropy_j_k','enthalpy_inverse_j','heat_ledger_j','entropy_ledger_j_k']}
    counts={'recorded':0,'dense':0};minimum_gas=minimum_solid=minimum_production=float('inf');events=[];transitions={}
    def source_review(state,total_h,category):
        nonlocal minimum_gas,minimum_solid
        counts[category]+=1;t=state['temperature_k'];n=state['amounts_mol'];gas={name:n[name] for name in ['CO','CO2','O2','N2']};ng=math.fsum(gas.values())
        minimum_gas=min(minimum_gas,*gas.values());minimum_solid=min(minimum_solid,*(n[name] for name in ['calcite','lime','C']));hs={};ss={};mu={}
        for name,data in thermal.items():
            hp,sp=primitive(data[0],t);hp0,sp0=reference[name];hs[name]=data[2]+hp-hp0;ss[name]=data[3]+sp-sp0
            if name in gas:ss[name]-=r*math.log(gas[name]/ng)
            mu[name]=hs[name]-t*ss[name]
        h=math.fsum(n[name]*hs[name] for name in n);s=math.fsum(n[name]*ss[name] for name in n)
        element_error=max(abs(n['calcite']+n['lime']-inputs[0]),abs(math.fsum(n[name] for name in ['calcite','C','CO','CO2'])-inputs[1]),
            abs(math.fsum((3*n['calcite'],n['lime'],n['CO'],2*n['CO2'],2*n['O2']))-inputs[2]),abs(2*n['N2']-2*inputs[3]))
        pressure_error=max(abs(state['pressure_pa']-p0),abs(math.fsum(state['partial_pressures_pa'].values())-p0),
            *(abs(state['partial_pressures_pa'][name]-p0*value/ng) for name,value in gas.items()))
        a1=mu['CO']-mu['C']-mu['O2']/2;a2=mu['CO2']-mu['C']-mu['O2'];ag=mu['CO2']-mu['CO']-mu['O2']/2;ac=mu['lime']+mu['CO2']-mu['calcite']
        carbon_error=max(abs(a1),abs(a2),abs(ag)) if state['carbon_phase']=='graphite_present' else max(0.,a1,a2,abs(ag))
        calcium_error={'calcite':max(0.,-ac),'lime':max(0.,ac),'coexistence':abs(ac)}[state['calcium_phase']]
        for name,value in [('element_mol',element_error),('pressure_pa',pressure_error),('reaction_gibbs_j_mol',max(carbon_error,calcium_error)),
            ('source_enthalpy_j',abs(state['enthalpy_j']-h)),('source_entropy_j_k',abs(state['entropy_j_k']-s)),('enthalpy_inverse_j',abs(total_h-h))]:
            maxima[name]=max(maxima[name],value)
    for row in rows:
        if 'state' not in row:continue
        source_review(row['state'],row['total_enthalpy_j'],'recorded')
        maxima['heat_ledger_j']=max(maxima['heat_ledger_j'],abs(row['values'][0]-row['values'][1]))
        maxima['entropy_ledger_j_k']=max(maxima['entropy_ledger_j_k'],abs(row['state']['entropy_j_k']-s0+row['values'][2]-row['values'][3]))
        minimum_production=min(minimum_production,row['instantaneous_entropy_production_w_k'])
        if row['kind']=='phase_event':events.append(row)
        if row['kind'] in ('initial','boundary_transition'):transitions[row['segment_index']]=row
    integral_reviews=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(3);previous=initial;max_local=max_global=max_entropy=max_local_entropy=0.;minimum_step=float('inf');max_ledgers=np.zeros(3)
        for row in rows:
            if row['kind']!='accepted':continue
            dense=row['dense_output'];left,right=dense['start_time_s'],dense['end_time_s'];wall=row['reservoir_temperature_k'];integral=np.zeros(3)
            for node,weight in zip(nodes,weights,strict=True):
                at=(left+right)/2+(right-left)*node/2;values=polynomial(row,at);total_h=h0+float(values[0])
                state=model.from_enthalpy(total_h,*inputs,p['enthalpy_inverse']);source_review(state,total_h,'dense')
                t=state['temperature_k'];heat=g*(wall-t);production=heat*(1/t-1/wall);minimum_production=min(minimum_production,production)
                integral+=weight*(right-left)/2*np.array([heat,-heat/wall,production])
            total+=integral;state=row['state'];entropy=state['entropy_j_k']-s0+total[1]
            max_local=max(max_local,abs(row['values'][0]-previous['values'][0]-integral[0]));max_global=max(max_global,abs(row['values'][0]-total[0]))
            max_entropy=max(max_entropy,abs(entropy-total[2]));max_ledgers=np.maximum(max_ledgers,np.abs(np.array(row['values'][1:])-total))
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
        print(json.dumps({'trajectory':str(path),'quadrature_order':order,'within_budgets':integral_reviews[-1]['within_budgets']}),flush=True)
    boundaries={row['case']['name']:row for row in header['phase_boundary_references']};event_reviews=[]
    for segment,start in transitions.items():
        wall=start['reservoir_temperature_k'];last_temperature=start['state']['temperature_k'];clock=start['time_s'];error_sum=0.
        for event in sorted((row for row in events if row['segment_index']==segment),key=lambda row:row['time_s']):
            boundary=boundaries[event['name']];tt=float(boundary['reference_temperature_k'])
            duration,error=quad(lambda t:model.at_temperature(t,*inputs)['equilibrium_cp_j_k']/(g*(wall-t)),last_temperature,tt,
                epsabs=settings['calorimetric_quadrature_absolute_tolerance_s'],epsrel=settings['calorimetric_quadrature_relative_tolerance'])
            clock+=duration;error_sum+=error;last_temperature=tt
            disappearing={'calcite_onset':'lime','calcite_exhaustion':'calcite','graphite_exhaustion':'C'}[boundary['case']['kind']]
            difference=event['time_s']-clock;temperature_error=event['state']['temperature_k']-tt;endpoint_error=abs(event['state']['amounts_mol'][disappearing])
            event_reviews.append({'segment':segment,'name':event['name'],'direction':event['direction'],'recorded_time_s':event['time_s'],
                'calorimetric_time_s':clock,'quadrature_estimated_error_s':error_sum,'time_difference_s':difference,'temperature_difference_k':temperature_error,
                'phase_endpoint_error_mol':endpoint_error,'within_budget':abs(difference)<=budget['phase_event_time_s'] and abs(temperature_error)<=budget['phase_event_temperature_k'] and endpoint_error<=budget['phase_endpoint_mol']})
    qdiff=np.abs(np.array(integral_reviews[0]['final_integrals_heat_reservoir_entropy_production'])-np.array(integral_reviews[1]['final_integrals_heat_reservoir_entropy_production']))
    flags={name:maxima[name]<=budget[name] for name in ['element_mol','pressure_pa','reaction_gibbs_j_mol','source_enthalpy_j','source_entropy_j_k']}
    flags.update({'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed','positive_gas':minimum_gas>0,'nonnegative_solid':minimum_solid>=0,
        'enthalpy_inverse':maxima['enthalpy_inverse_j']<=budget['source_enthalpy_j'],'heat_ledger':maxima['heat_ledger_j']<=budget['energy_j'],
        'entropy_ledger':maxima['entropy_ledger_j_k']<=budget['entropy_j_k'],'dense_integrals':all(all(v['within_budgets'].values()) for v in integral_reviews),
        'quadrature':qdiff[0]<=budget['energy_j'] and max(qdiff[1:])<=budget['entropy_j_k'],'entropy_production':minimum_production>=0,
        'expected_events':len(event_reviews)==budget['expected_phase_events'] and {(v['segment'],v['name']) for v in event_reviews}=={(segment,name) for segment in transitions for name in boundaries},
        'phase_events':all(v['within_budget'] for v in event_reviews)})
    return {'trajectory':str(path),'source_review_counts':counts,'maxima':maxima,'minimum_gas_mol':minimum_gas,'minimum_solid_mol':minimum_solid,
        'minimum_entropy_production_w_k':minimum_production,'integral_reviews':integral_reviews,'quadrature_differences':qdiff.tolist(),
        'phase_event_reviews':event_reviews,'within_budgets':{k:bool(v) for k,v in flags.items()},'all_requested_numerical_budgets_met':bool(all(flags.values()))},rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());reviews={};records={}
    for name,path in settings['trajectories'].items():
        review,rows=audit(root/path,settings,root);reviews[name]=review;records[name]=rows
        print(json.dumps({'name':name,'within_budgets':review['within_budgets']}),flush=True)
    left_name,right_name=settings['time_comparison_pair'];left={r['time_s']:r for r in records[left_name] if r['kind']=='sample'};right={r['time_s']:r for r in records[right_name] if r['kind']=='sample'}
    budget=records[left_name][0]['settings']['verification'];temperature=max(abs(left[t]['state']['temperature_k']-right[t]['state']['temperature_k']) for t in left)
    species={name:max(abs(left[t]['state']['amounts_mol'][name]-right[t]['state']['amounts_mol'][name]) for t in left) for name in left[next(iter(left))]['state']['amounts_mol']}
    comparison={'samples':len(left),'maximum_temperature_difference_k':temperature,'maximum_species_differences_mol':species,
        'within_budgets':temperature<=budget['time_temperature_k'] and max(species.values())<=budget['time_species_mol']}
    result={'settings':settings,'trajectory_reviews':reviews,'time_comparison':comparison,
        'all_requested_numerical_budgets_met':all(v['all_requested_numerical_budgets_met'] for v in reviews.values()) and comparison['within_budgets'],
        'material_qualified':False,'training_eligible':False,'scope':settings['scope']}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'time_comparison':comparison}))


if __name__=='__main__':main()
