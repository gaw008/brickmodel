"""Open-inventory thermodynamic identities and two-mode gas-face arithmetic."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from sludge_sandbox.rigid_reactive_exchange import rigid_reactive_face


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    config=json.loads((root/settings['model_parameters']).read_text());reaction,nitrogen,affinity,source,facts,nsource,volume=build_rigid(root,config)
    models=[RigidCalciteMixture(reaction,nitrogen,volume,config,cell) for cell in config['cells']]
    dh=settings['reference_shifts'];phases=dict(reaction.phases)
    for key in (config['reactant_phase'],reaction.gas_phase):
        old=phases[key];phases[key]=replace(old,reference_enthalpy_j_mol=old.reference_enthalpy_j_mol+dh['carbon_enthalpy_j_mol'],
            reference_entropy_j_mol_k=old.reference_entropy_j_mol_k+dh['carbon_entropy_j_mol_k'])
    shifted_reaction=replace(reaction,phases=phases)
    shifted_nitrogen=replace(nitrogen,reference_enthalpy_j_mol=nitrogen.reference_enthalpy_j_mol+dh['nitrogen_enthalpy_j_mol'],
        reference_entropy_j_mol_k=nitrogen.reference_entropy_j_mol_k+dh['nitrogen_entropy_j_mol_k'])
    shifted=[RigidCalciteMixture(shifted_reaction,shifted_nitrogen,volume,config,cell) for cell in config['cells']]
    model=models[0];budget=settings['budgets'];records=[]
    dt,dc,dn=[settings[k] for k in ('temperature_step_k','carbon_step_mol','nitrogen_step_mol')]
    for t in settings['temperatures_k']:
        for c in settings['carbon_amounts_mol']:
            for n in settings['nitrogen_amounts_mol']:
                state=model.at_inventory(t,c,n);back=model.inventory_state(c,n,state['internal_energy_j'])
                derivatives=[]
                for index,step in enumerate((dt,dc,dn)):
                    a,b=[t,c,n],[t,c,n];a[index]-=step;b[index]+=step
                    lo,hi=model.at_inventory(*a),model.at_inventory(*b)
                    derivatives.append(((hi['internal_energy_j']-lo['internal_energy_j'])/(2*step),(hi['entropy_j_k']-lo['entropy_j_k'])/(2*step)))
                (ut,st),(uc,sc),(un,sn)=derivatives
                gauge=shifted[0].inventory_state(c,n,state['internal_energy_j']+dh['carbon_enthalpy_j_mol']*c+dh['nitrogen_enthalpy_j_mol']*n)
                f=state['reaction_gibbs_j_mol'];phase=state['phase'];violation=abs(f) if phase=='coexistence' else (max(0.,-f) if phase=='calcite' else max(0.,f))
                errors={'inventory_mol':max(abs(state['calcite_mol']+state['co2_mol']-c),abs(state['calcite_mol']+state['lime_mol']-model.calcium)),
                    'inverse_temperature_k':abs(back['temperature_k']-t),'effective_capacity_j_k':abs(ut-state['equilibrium_cv_j_k']),
                    'entropy_temperature_identity_j_k':abs(ut-t*st),'carbon_chemical_identity_j_mol':abs(uc-t*sc-state['carbon_chemical_potential_j_mol']),
                    'nitrogen_chemical_identity_j_mol':abs(un-t*sn-state['nitrogen_chemical_potential_j_mol']),
                    'reaction_affinity_j_mol':violation,'reference_temperature_k':abs(gauge['temperature_k']-t),
                    'reference_amount_mol':abs(gauge['co2_mol']-state['co2_mol'])}
                records.append({'state':state,'errors':errors,'within_budgets':{k:v<=budget[k] for k,v in errors.items()}})
    faces=[]
    for case in settings['face_cases']:
        pair=[model.at_inventory(*case[k]) for model,k in zip(models,('left','right'),strict=True)]
        gauges=[model.at_inventory(*case[k]) for model,k in zip(shifted,('left','right'),strict=True)]
        face=rigid_reactive_face(*pair,config['face']);gauge=rigid_reactive_face(*gauges,config['face']);rev=rigid_reactive_face(*reversed(pair),config['face'])
        left,right=pair;tl,tr=left['temperature_k'],right['temperature_k'];r=reaction.gas_constant_j_mol_k;p0=reaction.standard_pressure_pa
        forces=[]
        for key,phase in (('co2',model.gas),('nitrogen',nitrogen)):
            sl=phase.standard(tl);sr=phase.standard(tr);hl,hr=sl['enthalpy_j_mol'],sr['enthalpy_j_mol'];h=(hl+hr)/2
            entropy_l=sl['entropy_j_mol_k']-r*math.log(left[key+'_partial_pressure_pa']/p0)
            entropy_r=sr['entropy_j_mol_k']-r*math.log(right[key+'_partial_pressure_pa']/p0)
            forces.append((hl-h)/tl-(hr-h)/tr-entropy_l+entropy_r)
        x=face['face_mole_fractions'];b=config['face']['bulk_mobility_mol2_k_j_s'];d=config['face']['counter_mobility_mol2_k_j_s']
        matrix=[[b*x[0]**2+d,b*x[0]*x[1]-d],[b*x[0]*x[1]-d,b*x[1]**2+d]]
        direct_flows=[math.fsum(a*y for a,y in zip(row,forces,strict=True)) for row in matrix]
        direct_entropy=face['energy_flow_w']*(1/tr-1/tl)+math.fsum(face[k+'_flow_mol_s']*(left[k+'_chemical_potential_j_mol']/tl-right[k+'_chemical_potential_j_mol']/tr) for k in ('carbon','nitrogen'))
        errors={'reference_flow_mol_s':max(abs(direct_flows[i]-face[k+'_flow_mol_s']) for i,k in enumerate(('carbon','nitrogen'))),
            'reference_energy_flow_w':abs(gauge['energy_flow_w']-face['energy_flow_w']-dh['carbon_enthalpy_j_mol']*face['carbon_flow_mol_s']-dh['nitrogen_enthalpy_j_mol']*face['nitrogen_flow_mol_s']),
            'reference_entropy_production_w_k':max(abs(direct_entropy-face['entropy_production_w_k']),abs(gauge['entropy_production_w_k']-face['entropy_production_w_k'])),
            'flow_reversal_mol_s':max(abs(face[k+'_flow_mol_s']+rev[k+'_flow_mol_s']) for k in ('carbon','nitrogen')),
            'energy_reversal_w':abs(face['energy_flow_w']+rev['energy_flow_w'])}
        errors['reference_flow_mol_s']=max(errors['reference_flow_mol_s'],*(abs(face[k+'_flow_mol_s']-gauge[k+'_flow_mol_s']) for k in ('carbon','nitrogen')))
        flags={k:v<=budget[k] for k,v in errors.items()};flags['nonnegative_entropy']=face['entropy_production_w_k']>=0
        if case['name']=='equal':flags['zero_flow']=max(abs(face[k]) for k in ('carbon_flow_mol_s','nitrogen_flow_mol_s','energy_flow_w'))<=budget['reference_flow_mol_s']
        if case['name']=='isothermal_pressure':
            expected=r*math.log(left['pressure_pa']/right['pressure_pa'])
            flags['pressure_bulk_relation']=abs(face['bulk_flow_mol_s']-b*expected)<=budget['reference_flow_mol_s']
            flags['no_counterflow']=abs(face['counter_flow_mol_s'])<=budget['reference_flow_mol_s']
            flags['pressure_direction']=face['bulk_flow_mol_s']*(left['pressure_pa']-right['pressure_pa'])>0
        faces.append({'case':case,'face':face,'independent_matrix':matrix,'errors':errors,'within_budgets':flags})
    result={'settings':settings,'records':records,'faces':faces,'all_requested_numerical_budgets_met':all(all(row['within_budgets'].values()) for row in records+faces),
        'material_qualified':False,'training_eligible':False,'scope':'Thermodynamic identity and reference-coordinate review; not material transport calibration.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'states':len(records),'faces':len(faces)}))


if __name__=='__main__':main()
