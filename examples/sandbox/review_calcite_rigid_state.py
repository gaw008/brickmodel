"""Rigid-mixture first-law derivatives, phase stability and source EOS arithmetic."""
import argparse
import json
import math
from pathlib import Path

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    config=json.loads((root/settings['model_parameters']).read_text());reaction,nitrogen,affinity,source,facts,nsource,volume=build_rigid(root,config)
    model=RigidCalciteMixture(reaction,nitrogen,volume,config,config['cell']);records=[];budget=settings['budgets']
    dt=settings['temperature_step_k'];dc=settings['carbon_step_mol'];dv=model.volume*settings['volume_relative_step']
    volume_models=[RigidCalciteMixture(reaction,nitrogen,volume,config,{**config['cell'],'total_volume_m3':model.volume+sign*dv}) for sign in (-1,1)]
    source_volumes={phase['id']:float(phase['reference_298']['volume_cm3_mol'])*volume['cubic_metres_per_cubic_centimetre']
        for phase in facts['species'] if phase['id'] in (config['reactant_phase'],config['product_phase'])}
    volume_matches={'calcite':model.vc==source_volumes[config['reactant_phase']], 'lime':model.vl==source_volumes[config['product_phase']]}
    for t in settings['temperatures_k']:
        for c in settings['carbon_amounts_mol']:
            state=model.at_temperature(t,c);back=model.state(c,state['internal_energy_j']);g=state['co2_mol']
            ta,tb=[model.at_temperature(u,c) for u in (t-dt,t+dt)];ca,cb=[model.at_temperature(t,u) for u in (c-dc,c+dc)]
            va,vb=[host.at_temperature(t,c) for host in volume_models]
            ut=(tb['internal_energy_j']-ta['internal_energy_j'])/(2*dt);st=(tb['entropy_j_k']-ta['entropy_j_k'])/(2*dt)
            uc=(cb['internal_energy_j']-ca['internal_energy_j'])/(2*dc);sc=(cb['entropy_j_k']-ca['entropy_j_k'])/(2*dc)
            uv=(vb['internal_energy_j']-va['internal_energy_j'])/(2*dv);sv=(vb['entropy_j_k']-va['entropy_j_k'])/(2*dv)
            dlog=settings['log_gas_derivative_step'];dg_dlog=(model.reaction_potential(t,c,g*math.exp(dlog))-model.reaction_potential(t,c,g*math.exp(-dlog)))/(2*dlog)
            phase=state['phase'];f=state['reaction_gibbs_j_mol']
            violation=abs(f) if phase=='coexistence' else (max(0.,-f) if phase=='calcite' else max(0.,f))
            nc=state['calcite_mol'];nl=state['lime_mol'];ni=state['nitrogen_mol'];p=state['pressure_pa']
            href=math.fsum((nc*(model.reactant.standard(t)['enthalpy_j_mol']+(p-model.p0)*model.vc),
                nl*(model.product.standard(t)['enthalpy_j_mol']+(p-model.p0)*model.vl),
                g*model.gas.standard(t)['enthalpy_j_mol'],ni*nitrogen.standard(t)['enthalpy_j_mol']))
            probes=[]
            for probe in [g*math.exp(sign*settings['gibbs_probe_log_step']) for sign in (-1,1)]:
                if max(0.,c-model.calcium)<=probe<=c:
                    other=model.at_partition(t,c,probe,c-probe,(model.calcium-c)+probe,'fixed-composition-probe')
                    probes.append(other['helmholtz_j']-state['helmholtz_j'])
            errors={'inventory_mol':max(abs(nc+nl-model.calcium),abs(nc+g-c),abs(3*nc+nl+2*g-model.calcium-2*c)),
                'inverse_temperature_k':abs(back['temperature_k']-t),'effective_capacity_j_k':abs(ut-state['equilibrium_cv_j_k']),
                'entropy_temperature_identity_j_k':abs(ut-t*st),'carbon_chemical_identity_j_mol':abs(uc-t*sc-state['carbon_chemical_potential_j_mol']),
                'volume_identity_pa':abs(uv-t*sv+p),'reaction_affinity_j_mol':violation,
                'reaction_derivative_relative':abs(dg_dlog/(g*state['reaction_gas_derivative_j_mol2'])-1),
                'reference_enthalpy_identity_j':abs(href-state['internal_energy_j']-p*model.volume)}
            flags={key:value<=budget[key] for key,value in errors.items()}
            flags.update(helmholtz_minimum=min(probes)>=-budget['helmholtz_negative_allowance_j'],positive_capacity=state['equilibrium_cv_j_k']>0,
                positive_gas_volume=state['gas_volume_m3']>0)
            records.append({'state':state,'errors':errors,'helmholtz_probe_increases_j':probes,'within_budgets':flags})
    corners=[]
    for t in settings['equal_inventory_corner_temperatures_k']:
        state=model.at_temperature(t,model.calcium);back=model.state(model.calcium,state['internal_energy_j'])
        corners.append({'state':state,'within_budgets':{'positive_products':state['co2_mol']>0 and state['lime_mol']>0,
            'equal_products':state['co2_mol']==state['lime_mol'],
            'inverse_temperature':abs(back['temperature_k']-t)<=budget['inverse_temperature_k'],
            'chemical_equilibrium':abs(state['reaction_gibbs_j_mol'])<=budget['reaction_affinity_j_mol']}})
    result={'settings':settings,'parameters':config,'volume_source':volume,'source_volume_matches':volume_matches,'records':records,'equal_inventory_corners':corners,
        'all_requested_numerical_budgets_met':all(volume_matches.values()) and all(all(row['within_budgets'].values()) for row in records+corners),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'states':len(records),'corners':len(corners)}))


if __name__=='__main__':main()
