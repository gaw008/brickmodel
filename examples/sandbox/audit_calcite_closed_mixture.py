"""Closed-mixture element / total-enthalpy / entropy and independent time integrals."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad
from scipy.optimize import brentq

from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from sludge_sandbox.equilibrium_calcite_closed import ClosedCalciteMixture
from audit_sorptive_gas_cell import polynomial


def audit(rows,settings,static_settings):
    header=rows[0];config=header['parameters'];budget=config['verification'];initial=rows[1]
    reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    nitrogen=nitrogen_from_record(header['nitrogen_source'])
    model=ClosedCalciteMixture(reaction,nitrogen,config,header['affinity_parameters']['root'])
    h0=initial['values'][0];s0=initial['state']['entropy_j_k'];n0=config['initial_calcite_mol'];c0=config['initial_co2_mol'];nn=config['nitrogen_mol']
    p=config['total_pressure_pa'];r=reaction.gas_constant_j_mol_k;p0=reaction.standard_pressure_pa
    maximum={'energy_ledger_j':0.,'entropy_ledger_j_k':0.,'elements_mol':0.,'source_enthalpy_j':0.,'source_entropy_j_k':0.,'chemical_stability_j_mol':0.}
    observed=[row for row in rows if row['kind'] in ('initial','accepted','sample','phase_event')]
    for row in observed:
        state=row['state'];t=state['temperature_k'];h,q,sw,sp=row['values'];nc=state['calcite_mol'];nl=state['lime_mol'];ng=state['co2_mol'];ni=state['nitrogen_mol']
        amounts=(nc,nl,ng,ni);phases=(model.reactant.standard(t),model.product.standard(t),model.gas.standard(t),nitrogen.standard(t))
        href=math.fsum(n*s['enthalpy_j_mol'] for n,s in zip(amounts,phases,strict=True))
        sref=math.fsum(n*s['entropy_j_mol_k'] for n,s in zip(amounts,phases,strict=True))-r*(ng*math.log(p*ng/(ng+ni)/p0)+ni*math.log(p*ni/(ng+ni)/p0))
        a=reaction.affinity(t,p*ng/(ng+ni))['affinity_j_mol_extent']
        violation=abs(a) if state['phase']=='coexistence' else (max(0.,a) if state['phase']=='calcite' else max(0.,-a))
        residuals={'energy_ledger_j':abs(h-h0-q),'entropy_ledger_j_k':abs(state['entropy_j_k']-s0-sw-sp),
            'elements_mol':max(abs(nc+nl-n0),abs(nc+ng-n0-c0),abs(3*nc+nl+2*ng-3*n0-2*c0),abs(2*ni-2*nn)),
            'source_enthalpy_j':abs(h-href),'source_entropy_j_k':abs(state['entropy_j_k']-sref),'chemical_stability_j_mol':violation}
        for key,value in residuals.items():maximum[key]=max(maximum[key],value)
    def heat_rate(t,wall):
        rad=config['radiation']
        return config['heat_conductance_w_k']*(wall-t)+rad['area_m2']*rad['emissivity']*rad['stefan_boltzmann_w_m2_k4']*(wall**4-t**4)
    events=[row for row in rows if row['kind']=='phase_event'];integrals=[]
    for order in budget['quadrature_orders']:
        nodes,weights=leggauss(order);total=np.zeros(3);previous=initial
        local=entropy=0.;minimum=math.inf;worst=None
        for row in rows:
            if row['kind']!='accepted':continue
            left=row['dense_output']['start_time_s'];right=row['time_s'];wall=row['wall_temperature_k']
            splits=[left]+[event['time_s'] for event in events if left<event['time_s']<right]+[right];integral=np.zeros(3)
            for a,b in zip(splits[:-1],splits[1:],strict=True):
                for node,weight in zip(nodes,weights,strict=True):
                    t=(a+b)/2+(b-a)*node/2
                    temperature=model.state(float(polynomial(row['dense_output'],t)[0]))['temperature_k'];q=heat_rate(temperature,wall)
                    integral+=np.array([q,q/wall,q*(1/temperature-1/wall)])*weight*(b-a)/2
            total+=integral;delta_h=row['values'][0]-previous['values'][0]
            local=max(local,abs(delta_h-integral[0]))
            entropy=max(entropy,abs(row['state']['entropy_j_k']-s0-total[1]-total[2]))
            step=row['state']['entropy_j_k']-previous['state']['entropy_j_k']-integral[1]
            if step<minimum:
                minimum=step;worst={'start_time_s':left,'end_time_s':right,'temperature_k':row['state']['temperature_k'],'integral':integral.tolist()}
            previous=row
        integrals.append({'quadrature_order':order,'integrals':total.tolist(),'maximum_local_enthalpy_residual_j':local,
            'maximum_entropy_balance_residual_j_k':entropy,'minimum_step_combined_entropy_j_k':minimum,'minimum_step_details':worst,
            'within_budgets':bool(local<=budget['balance_energy_j'] and entropy<=budget['balance_entropy_j_k'] and minimum>=-budget['negative_entropy_allowance_j_k'])})
    difference=np.abs(np.array(integrals[-1]['integrals'])-np.array(integrals[0]['integrals']))
    # Independent extent root (affinity in extent, not the explicit pressure expression)
    # and implicit derivative of equilibrium chemical potential determine Cp/Q times.
    def capacity(t):
        def affinity(x):return reaction.affinity(t,p*(c0+x)/(c0+x+nn))['affinity_j_mol_extent']
        if affinity(0.)<=0.:x=0.;dxdt=0.
        elif affinity(n0)>=0.:x=n0;dxdt=0.
        else:
            x=brentq(affinity,0.,n0,xtol=static_settings['extent_root_absolute_mol'],
                rtol=static_settings['extent_root_relative_tolerance'],maxiter=static_settings['extent_root_iterations'])
            dxdt=reaction.standard(t)['reaction']['enthalpy_j_mol']*(c0+x)*(c0+x+nn)/(r*t*t*nn)
        frozen=math.fsum(n*phase.standard(t)['cp_j_mol_k'] for n,phase in zip((n0-x,x,c0+x,nn),
            (model.reactant,model.product,model.gas,nitrogen),strict=True))
        return frozen+reaction.standard(t)['reaction']['enthalpy_j_mol']*dxdt
    reference_policy=header['affinity_parameters']['verification']
    options={'epsabs':reference_policy['quadrature_absolute_tolerance'],'epsrel':reference_policy['quadrature_relative_tolerance'],
        'limit':reference_policy['quadrature_maximum_subintervals']}
    observations={row['time_s']:row for row in rows if row['kind'] in ('initial','sample')};reference_events=[];stage_reports=[]
    for segment in config['wall_program']:
        start=observations[segment['start_s']];end=observations[segment['end_s']]
        wall=segment['temperature_k'];t=start['state']['temperature_k'];at=segment['start_s']
        direction='heating' if wall>t else 'cooling'
        selected=[event for event in events if segment['start_s']<event['time_s']<=segment['end_s']]
        for event in selected:
            target=header['phase_temperatures_k'][header['enthalpy_phase_boundaries_j'].index(event['boundary_enthalpy_j'])]
            at+=quad(lambda temperature:capacity(temperature)/heat_rate(temperature,wall),t,target,**options)[0]
            reference_events.append({'direction':direction,'boundary_enthalpy_j':event['boundary_enthalpy_j'],
                'predicted_time_s':at,'recorded_time_s':event['time_s'],'difference_s':abs(at-event['time_s'])});t=target
        stage_reports.append({**segment,'heat_in_j':end['values'][1]-start['values'][1],
            'total_enthalpy_change_j':end['values'][0]-start['values'][0],
            'combined_entropy_change_j_k':end['state']['entropy_j_k']-start['state']['entropy_j_k']-(end['values'][2]-start['values'][2])})
    flags={'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'energy_ledger':maximum['energy_ledger_j']<=budget['balance_energy_j'],
        'entropy_ledger':maximum['entropy_ledger_j_k']<=budget['balance_entropy_j_k'],
        'element_ledgers':maximum['elements_mol']<=budget['balance_co2_mol'],
        'source_enthalpy':maximum['source_enthalpy_j']<=budget['balance_energy_j'],
        'source_entropy':maximum['source_entropy_j_k']<=budget['balance_entropy_j_k'],
        'chemical_stability':maximum['chemical_stability_j_mol']<=settings['source_affinity_budget_j_mol'],
        'local_integrals':all(v['within_budgets'] for v in integrals),
        'quadrature_energy':difference[0]<=budget['quadrature_energy_j'],
        'quadrature_entropy':float(max(difference[1:]))<=budget['quadrature_entropy_j_k'],
        'independent_events':max(e['difference_s'] for e in reference_events)<=budget['event_difference_s']}
    flags={k:bool(v) for k,v in flags.items()}
    return {'tolerance':header['tolerance'],'observed_states':len(observed),'maximum_residuals':maximum,'integral_reviews':integrals,
        'integral_quadrature_differences':difference.tolist(),'independent_phase_events':reference_events,'wall_stages':stage_reports,
        'within_budgets':flags,'all_requested_numerical_budgets_met':all(flags.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    static=json.loads((root/settings['static_study_parameters']).read_text())
    records={name:[json.loads(line) for line in (root/name).read_text().splitlines()] for name in settings['trajectories']}
    reports=[{'trajectory':name,**audit(rows,settings,static)} for name,rows in records.items()];comparisons=[]
    for case in settings['comparisons']:
        left,right=[records[case[k]] for k in ('left','right')];budget=left[0]['parameters']['verification']
        a,b=[[row for row in rows if row['kind'] in ('initial','sample')] for rows in (left,right)]
        if [row['time_s'] for row in a]!=[row['time_s'] for row in b]:raise ValueError('observation times differ')
        differences={key:max(abs(x['state'][key]-y['state'][key]) for x,y in zip(a,b,strict=True))
            for key in ('temperature_k','extent_mol','co2_partial_pressure_pa','gas_occupied_volume_m3')}
        ea,eb=[[row for row in rows if row['kind']=='phase_event'] for rows in (left,right)]
        if [(row['direction'],row['boundary_enthalpy_j']) for row in ea]!=[(row['direction'],row['boundary_enthalpy_j']) for row in eb]:
            raise ValueError('phase event identities differ')
        event=max(abs(x['time_s']-y['time_s']) for x,y in zip(ea,eb,strict=True))
        comparisons.append({**case,'observations':len(a),'maximum_differences':differences,'maximum_event_difference_s':event,
            'within_budgets':differences['temperature_k']<=budget['time_temperature_k'] and differences['extent_mol']<=budget['time_extent_mol'] and event<=budget['event_difference_s']})
    result={'settings':settings,'reports':reports,'comparisons':comparisons,'all_requested_numerical_budgets_met':all(r['all_requested_numerical_budgets_met'] for r in reports) and all(c['within_budgets'] for c in comparisons),
        'material_qualified':False,'training_eligible':False,'scope':'Shared source phase polynomials and H flash; independent heat integration, extent equilibrium root and event-time quadrature; no measured kinetic claim.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
