"""Independent rate integration and time refinement of the equilibrium cycle."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from numpy.polynomial.legendre import leggauss

from calcite_affinity_setup import from_records
from sludge_sandbox.equilibrium_calcite_calorimeter import EquilibriumCalciteCalorimeter
from audit_sorptive_gas_cell import polynomial


def audit(rows):
    header=rows[0];config=header['parameters'];budget=config['verification']
    reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    model=EquilibriumCalciteCalorimeter(reaction,config,header['affinity_parameters']['root'])
    initial=rows[1];initial_h=initial['values'][0];initial_s=initial['state']['entropy_j_k']
    observed=[p for p in rows if p['kind'] in ('initial','accepted','sample','phase_event')]
    maximum={'energy_j':0.,'co2_mol':0.,'entropy_j_k':0.}
    for row in observed:
        h,n,q,hgas,swall,sgas,production=row['values'];state=row['state']
        maximum['energy_j']=max(maximum['energy_j'],abs(h-initial_h+hgas-q))
        maximum['co2_mol']=max(maximum['co2_mol'],abs(n-state['extent_mol']))
        maximum['entropy_j_k']=max(maximum['entropy_j_k'],abs(state['entropy_j_k']-initial_s+sgas-swall-production))
    events=[p['time_s'] for p in rows if p['kind']=='phase_event'];integrals=[]
    def heat_rate(t,wall):
        q=config['heat_conductance_w_k']*(wall-t)
        if 'radiation' in config:
            p=config['radiation'];q+=p['area_m2']*p['emissivity']*p['stefan_boltzmann_w_m2_k4']*(wall**4-t**4)
        return q
    def rates(h,wall):
        state=model.state(float(h));t=state['temperature_k'];q=heat_rate(t,wall)
        flow=(q/reaction.standard(t)['reaction']['enthalpy_j_mol']) if state['phase']=='coexistence' else 0.
        hgas=state['co2_enthalpy_j_mol']*flow;sgas=state['co2_entropy_j_mol_k']*flow
        return np.array([q-hgas,flow,q,hgas,q/wall,sgas,q*(1/t-1/wall)])
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(7);previous=initial
        local_h=local_n=entropy=0.;minimum_step=math.inf;worst_step=None
        for row in rows:
            if row['kind']!='accepted':continue
            left=row['dense_output']['start_time_s'];right=row['time_s'];wall=row['wall_temperature_k']
            splits=[left]+[t for t in events if left<t<right]+[right]
            integral=np.zeros(7)
            for a,b in zip(splits[:-1],splits[1:],strict=True):
                for node,weight in zip(nodes,weights,strict=True):
                    t=(a+b)/2+(b-a)*node/2
                    integral+=rates(polynomial(row['dense_output'],t)[0],wall)*weight*(b-a)/2
            total+=integral
            local_h=max(local_h,abs(row['values'][0]-previous['values'][0]-integral[0]))
            local_n=max(local_n,abs(row['state']['extent_mol']-previous['state']['extent_mol']-integral[1]))
            entropy=max(entropy,abs(row['state']['entropy_j_k']-initial_s+total[5]-total[4]-total[6]))
            step_entropy=row['state']['entropy_j_k']-previous['state']['entropy_j_k']+integral[5]-integral[4]
            if step_entropy<minimum_step:
                minimum_step=step_entropy
                worst_step={'start_time_s':left,'end_time_s':right,'start_state':previous['state'],'end_state':row['state'],
                    'integral':integral.tolist()}
            previous=row
        integrals.append({'quadrature_order':order,'integrals':total.tolist(),'maximum_local_enthalpy_residual_j':local_h,
            'maximum_local_extent_residual_mol':local_n,'maximum_entropy_balance_residual_j_k':entropy,
            'minimum_step_combined_entropy_j_k':minimum_step,
            'minimum_step_details':worst_step,
            'within_budgets':bool(local_h<=budget['balance_energy_j'] and local_n<=budget['balance_co2_mol'] and
                entropy<=budget['balance_entropy_j_k'] and minimum_step>=-budget['negative_entropy_allowance_j_k'])})
    difference=np.abs(np.array(integrals[-1]['integrals'])-np.array(integrals[0]['integrals']))
    # Separate nominal caloric integration predicts the first heating events.
    wall=config['wall_program'][0]['temperature_k'];teq=model.equilibrium_temperature
    source_review=header['affinity_parameters']['verification']
    options={'epsabs':source_review['quadrature_absolute_tolerance'],'epsrel':source_review['quadrature_relative_tolerance'],
             'limit':source_review['quadrature_maximum_subintervals']}
    sensible_time=quad(lambda t:model.amount*model.reactant.standard(t)['cp_j_mol_k']/heat_rate(t,wall),
        config['initial_temperature_k'],teq,**options)[0]
    plateau_time=(model.amount*reaction.standard(teq)['reaction']['enthalpy_j_mol']/
        heat_rate(teq,wall))
    reference_events=[config['wall_program'][0]['start_s']+sensible_time,config['wall_program'][0]['start_s']+sensible_time+plateau_time]
    actual=[p['time_s'] for p in rows if p['kind']=='phase_event' and p['direction']=='heating']
    event_difference=max(abs(x-y) for x,y in zip(reference_events,actual,strict=True))
    flags={'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'energy_ledger':maximum['energy_j']<=budget['balance_energy_j'],'co2_ledger':maximum['co2_mol']<=budget['balance_co2_mol'],
        'entropy_ledger':maximum['entropy_j_k']<=budget['balance_entropy_j_k'],
        'local_integrals':all(r['within_budgets'] for r in integrals),
        'quadrature_energy':float(np.max(difference[[0,2,3]]))<=budget['quadrature_energy_j'],
        'quadrature_entropy':float(np.max(difference[4:]))<=budget['quadrature_entropy_j_k'],
        'independent_heating_event':event_difference<=budget['event_difference_s']}
    return {'tolerance':header['tolerance'],'observed_states':len(observed),'maximum_ledgers':maximum,
        'integral_reviews':integrals,'integral_quadrature_differences':difference.tolist(),
        'independent_heating_events_s':reference_events,'heating_event_difference_s':event_difference,
        'within_budgets':flags,'all_requested_numerical_budgets_met':all(flags.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    records={name:[json.loads(line) for line in (root/name).read_text().splitlines()] for name in settings['trajectories']}
    reports=[{'trajectory':name,**audit(rows)} for name,rows in records.items()];comparisons=[]
    for case in settings['comparisons']:
        left,right=[records[case[k]] for k in ('left','right')];budget=left[0]['parameters']['verification']
        a,b=[[r for r in rows if r['kind'] in ('initial','sample')] for rows in (left,right)]
        if [r['time_s'] for r in a]!=[r['time_s'] for r in b]:raise ValueError('observation times differ')
        differences={k:max(abs(x['state'][k]-y['state'][k]) for x,y in zip(a,b,strict=True)) for k in ('temperature_k','extent_mol')}
        ea,eb=[[r for r in rows if r['kind']=='phase_event'] for rows in (left,right)]
        if [(r['direction'],r['boundary_enthalpy_j']) for r in ea]!=[(r['direction'],r['boundary_enthalpy_j']) for r in eb]:
            raise ValueError('phase event identities differ')
        event=max(abs(x['time_s']-y['time_s']) for x,y in zip(ea,eb,strict=True))
        comparisons.append({**case,'observations':len(a),'max_differences':differences,'maximum_event_difference_s':event,
            'within_budgets':differences['temperature_k']<=budget['time_temperature_k'] and differences['extent_mol']<=budget['time_extent_mol'] and event<=budget['event_difference_s']})
    result={'settings':settings,'reports':reports,'comparisons':comparisons,'material_qualified':False,'training_eligible':False,
        'scope':'Independent flux integration and caloric time integral; shared equilibrium flash and source polynomials. No actual reaction-rate validation.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
