"""Source EOS, closed-capsule U/S ledgers and independent heat integrals."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import quad

from calcite_affinity_setup import from_records
from calcite_closed_setup import nitrogen_from_record
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from audit_sorptive_gas_cell import polynomial


def audit(rows,settings):
    header=rows[0];config=header['parameters'];budget=config['verification'];initial=rows[1]
    reaction=from_records(header['affinity_parameters'],header['source'],header['reference_facts'])
    nitrogen=nitrogen_from_record(header['nitrogen_source']);model=RigidCalciteMixture(reaction,nitrogen,header['volume_source'],config,config['cell'])
    c=config['initial_carbon_mol'];u0=initial['values'][0];s0=initial['state']['entropy_j_k'];r=reaction.gas_constant_j_mol_k
    maxima={key:0. for key in ('energy_ledger_j','entropy_ledger_j_k','element_residual_mol','source_internal_energy_j',
        'source_entropy_j_k','source_pressure_pa','source_gas_volume_m3','source_enthalpy_identity_j','chemical_stability_j_mol')}
    observed=[row for row in rows if row['kind'] in ('initial','accepted','sample','phase_event')];phases={}
    for row in observed:
        state=row['state'];t=state['temperature_k'];nc=state['calcite_mol'];nl=state['lime_mol'];ng=state['co2_mol'];nn=state['nitrogen_mol']
        a,b,g,n=[phase.standard(t) for phase in (model.reactant,model.product,model.gas,nitrogen)]
        vg=model.volume-nc*model.vc-nl*model.vl;pc=ng*r*t/vg;pn=nn*r*t/vg;p=pc+pn
        uref=math.fsum((nc*(a['enthalpy_j_mol']-model.p0*model.vc),nl*(b['enthalpy_j_mol']-model.p0*model.vl),ng*(g['enthalpy_j_mol']-r*t),nn*(n['enthalpy_j_mol']-r*t)))
        sref=math.fsum((nc*a['entropy_j_mol_k'],nl*b['entropy_j_mol_k'],ng*(g['entropy_j_mol_k']-r*math.log(pc/model.p0)),nn*(n['entropy_j_mol_k']-r*math.log(pn/model.p0))))
        href=math.fsum((nc*(a['enthalpy_j_mol']+(p-model.p0)*model.vc),nl*(b['enthalpy_j_mol']+(p-model.p0)*model.vl),ng*g['enthalpy_j_mol'],nn*n['enthalpy_j_mol']))
        delta_g=b['gibbs_j_mol']+(p-model.p0)*model.vl+g['gibbs_j_mol']+r*t*math.log(pc/model.p0)-a['gibbs_j_mol']-(p-model.p0)*model.vc
        phase=state['phase'];phases[phase]=phases.get(phase,0)+1
        violation=abs(delta_g) if phase=='coexistence' else (max(0.,-delta_g) if phase=='calcite' else max(0.,delta_g))
        u,q,sw,sp=row['values']
        errors={'energy_ledger_j':abs(u-u0-q),'entropy_ledger_j_k':abs(state['entropy_j_k']-s0-sw-sp),
            'element_residual_mol':max(abs(nc+nl-model.calcium),abs(nc+ng-c),abs(3*nc+nl+2*ng-model.calcium-2*c),abs(nn-model.carrier)),
            'source_internal_energy_j':abs(u-uref),'source_entropy_j_k':abs(state['entropy_j_k']-sref),
            'source_pressure_pa':abs(state['pressure_pa']-p),'source_gas_volume_m3':abs(state['gas_volume_m3']-vg),
            'source_enthalpy_identity_j':abs(href-u-p*model.volume),'chemical_stability_j_mol':violation}
        for key,value in errors.items():maxima[key]=max(maxima[key],value)
    def heat_rate(t,wall):
        p=config['radiation']
        return config['heat_conductance_w_k']*(wall-t)+p['area_m2']*p['emissivity']*p['stefan_boltzmann_w_m2_k4']*(wall**4-t**4)
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
                    at=(a+b)/2+(b-a)*node/2
                    t=model.state(c,float(polynomial(row['dense_output'],at)[0]))['temperature_k'];q=heat_rate(t,wall)
                    integral+=np.array([q,q/wall,q*(1/t-1/wall)])*weight*(b-a)/2
            total+=integral;local=max(local,abs(row['values'][0]-previous['values'][0]-integral[0]))
            entropy=max(entropy,abs(row['state']['entropy_j_k']-s0-total[1]-total[2]))
            step=row['state']['entropy_j_k']-previous['state']['entropy_j_k']-integral[1]
            if step<minimum:minimum=step;worst={'start_time_s':left,'end_time_s':right,'temperature_k':row['state']['temperature_k'],'integral':integral.tolist()}
            previous=row
        integrals.append({'quadrature_order':order,'integrals':total.tolist(),'maximum_local_energy_residual_j':local,
            'maximum_entropy_integral_residual_j_k':entropy,'minimum_step_combined_entropy_j_k':minimum,'minimum_step_details':worst,
            'within_budgets':bool(local<=budget['balance_energy_j'] and entropy<=budget['balance_entropy_j_k'] and minimum>=-budget['negative_entropy_allowance_j_k'])})
    difference=np.abs(np.array(integrals[-1]['integrals'])-np.array(integrals[0]['integrals']))
    observations={row['time_s']:row for row in rows if row['kind'] in ('initial','sample')};reference_events=[];stage_reports=[]
    source_policy=header['affinity_parameters']['verification'];options={'epsabs':source_policy['quadrature_absolute_tolerance'],
        'epsrel':source_policy['quadrature_relative_tolerance'],'limit':source_policy['quadrature_maximum_subintervals']}
    for segment in config['wall_program']:
        start=observations[segment['start_s']];end=observations[segment['end_s']];t=start['state']['temperature_k'];at=segment['start_s'];wall=segment['temperature_k']
        for event in [event for event in events if segment['start_s']<event['time_s']<=segment['end_s']]:
            target=event['boundary']['temperature_k']
            at+=quad(lambda temperature:model.at_temperature(temperature,c)['equilibrium_cv_j_k']/heat_rate(temperature,wall),t,target,**options)[0]
            reference_events.append({'direction':event['direction'],'pure_phase':event['boundary']['pure_phase'],
                'predicted_time_s':at,'recorded_time_s':event['time_s'],'difference_s':abs(at-event['time_s'])});t=target
        stage_reports.append({**segment,'heat_in_j':end['values'][1]-start['values'][1],
            'internal_energy_change_j':end['values'][0]-start['values'][0],
            'combined_entropy_change_j_k':end['state']['entropy_j_k']-start['state']['entropy_j_k']-(end['values'][2]-start['values'][2]),'final_state':end['state']})
    flags={'completed':rows[-1]['kind']=='summary' and rows[-1]['status']=='completed',
        'energy_ledger':maxima['energy_ledger_j']<=budget['balance_energy_j'],
        'entropy_ledger':maxima['entropy_ledger_j_k']<=budget['balance_entropy_j_k'],
        'elements':maxima['element_residual_mol']<=budget['balance_co2_mol'],
        'source_energy':maxima['source_internal_energy_j']<=budget['balance_energy_j'],
        'source_entropy':maxima['source_entropy_j_k']<=budget['balance_entropy_j_k'],
        'source_pressure':maxima['source_pressure_pa']<=settings['source_pressure_absolute_pa'],
        'source_volume':maxima['source_gas_volume_m3']<=settings['source_volume_absolute_m3'],
        'source_enthalpy_identity':maxima['source_enthalpy_identity_j']<=budget['balance_energy_j'],
        'chemical_stability':maxima['chemical_stability_j_mol']<=settings['source_reaction_affinity_absolute_j_mol'],
        'local_integrals':all(row['within_budgets'] for row in integrals),
        'quadrature_energy':bool(difference[0]<=budget['quadrature_energy_j']),
        'quadrature_entropy':bool(max(difference[1:])<=budget['quadrature_entropy_j_k']),
        'caloric_event_time':max(event['difference_s'] for event in reference_events)<=budget['event_difference_s']}
    return {'tolerance':header['tolerance'],'observed_states':len(observed),'phase_counts':phases,'maximum_residuals':maxima,
        'pressure_range_pa':[min(row['state']['pressure_pa'] for row in observed),max(row['state']['pressure_pa'] for row in observed)],
        'integral_reviews':integrals,'quadrature_differences':difference.tolist(),'caloric_event_comparison':reference_events,'wall_stages':stage_reports,
        'within_budgets':flags,'all_requested_numerical_budgets_met':all(flags.values())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    records={name:[json.loads(line) for line in (root/name).read_text().splitlines()] for name in settings['trajectories']}
    reports=[{'trajectory':name,**audit(rows,settings)} for name,rows in records.items()];comparisons=[]
    for case in settings['comparisons']:
        left,right=[records[case[k]] for k in ('left','right')];budget=left[0]['parameters']['verification']
        a,b=[[row for row in rows if row['kind'] in ('initial','sample')] for rows in (left,right)]
        if [row['time_s'] for row in a]!=[row['time_s'] for row in b]:raise ValueError('observation times differ')
        differences={key:max(abs(x['state'][key]-y['state'][key]) for x,y in zip(a,b,strict=True)) for key in ('temperature_k','pressure_pa','co2_mol','calcite_mol')}
        ea,eb=[[row for row in rows if row['kind']=='phase_event'] for rows in (left,right)]
        if [(row['direction'],row['boundary']['pure_phase']) for row in ea]!=[(row['direction'],row['boundary']['pure_phase']) for row in eb]:raise ValueError('phase event identities differ')
        event=max(abs(x['time_s']-y['time_s']) for x,y in zip(ea,eb,strict=True))
        comparisons.append({**case,'observations':len(a),'maximum_differences':differences,'maximum_event_difference_s':event,
            'within_budgets':differences['temperature_k']<=budget['time_temperature_k'] and differences['co2_mol']<=budget['time_extent_mol']
                and differences['pressure_pa']<=settings['time_pressure_absolute_pa'] and event<=budget['event_difference_s']})
    result={'settings':settings,'reports':reports,'comparisons':comparisons,'all_requested_numerical_budgets_met':all(row['all_requested_numerical_budgets_met'] for row in reports) and all(row['within_budgets'] for row in comparisons),
        'material_qualified':False,'training_eligible':False,'scope':'Explicit incompressible solids and ideal gas; independent source recomposition and expanded heat integrals, shared equilibrium flash for dense quadrature and shared analytic Cv for separate caloric time quadrature.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
