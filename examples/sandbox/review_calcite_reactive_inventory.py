"""Mobile-carbon equilibrium derivatives and reference-invariant exchange study."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

from calcite_closed_setup import build_closed
from sludge_sandbox.equilibrium_calcite_inventory import CalciteInventoryCell,reactive_carbon_face


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    config=json.loads((root/settings['model_parameters']).read_text());reaction,nitrogen,affinity,source,facts,nsource=build_closed(root,config)
    cells=[CalciteInventoryCell(reaction,nitrogen,config,cell) for cell in config['cells']]
    model=cells[0];budget=settings['budgets'];dt=settings['temperature_derivative_step_k'];dc=settings['carbon_derivative_step_mol']
    dh_ref=settings['carbon_reference_shift_j_mol'];ds_ref=settings['carbon_entropy_reference_shift_j_mol_k']
    shifted_phases=dict(reaction.phases)
    for key in (config['reactant_phase'],reaction.gas_phase):
        old=shifted_phases[key];shifted_phases[key]=replace(old,reference_enthalpy_j_mol=old.reference_enthalpy_j_mol+dh_ref,
            reference_entropy_j_mol_k=old.reference_entropy_j_mol_k+ds_ref)
    shifted_reaction=replace(reaction,phases=shifted_phases)
    shifted=[CalciteInventoryCell(shifted_reaction,nitrogen,config,cell) for cell in config['cells']];records=[]
    for t in settings['temperatures_k']:
        for c in settings['carbon_amounts_mol']:
            state=model.at_temperature(t,c);lower,upper=[model.at_temperature(v,c) for v in (t-dt,t+dt)]
            left,right=[model.at_temperature(t,v) for v in (c-dc,c+dc)]
            ht=(upper['enthalpy_j']-lower['enthalpy_j'])/(2*dt);st=(upper['entropy_j_k']-lower['entropy_j_k'])/(2*dt)
            hc=(right['enthalpy_j']-left['enthalpy_j'])/(2*dc);sc=(right['entropy_j_k']-left['entropy_j_k'])/(2*dc)
            back=model.state(c,state['enthalpy_j']);gauge=shifted[0].state(c,state['enthalpy_j']+dh_ref*c)
            af=reaction.affinity(t,state['co2_partial_pressure_pa'])['affinity_j_mol_extent'];phase=state['phase']
            violation=abs(af) if phase=='coexistence' else (max(0.,af) if phase=='calcite' else max(0.,-af))
            # O = Ca + 2 C for the declared CaCO3/CaO/CO2 species inventory.
            elements=[state['calcite_mol']+state['lime_mol']-model.calcium,
                state['calcite_mol']+state['co2_mol']-c,
                3*state['calcite_mol']+state['lime_mol']+2*state['co2_mol']-model.calcium-2*c]
            errors={'inventory_mol':max(abs(v) for v in elements),'inverse_temperature_k':abs(back['temperature_k']-t),
                'heat_capacity_derivative_j_k':abs(ht-state['equilibrium_cp_j_k']),
                'carbon_enthalpy_derivative_j_mol':abs(hc-state['enthalpy_carbon_derivative_j_mol']),
                'entropy_enthalpy_derivative_per_k':abs(st/ht-1/t),
                'chemical_potential_derivative_j_mol':abs(hc-t*sc-state['carbon_chemical_potential_j_mol']),
                'chemical_stability_j_mol':violation,'reference_temperature_k':abs(gauge['temperature_k']-t)}
            flags={key:value<=budget[key] for key,value in errors.items()};flags['positive_capacity']=state['equilibrium_cp_j_k']>0
            records.append({'state':state,'errors':errors,'within_budgets':flags})
    corners=[]
    for t in settings['equal_carbon_calcium_corner_temperatures_k']:
        c=model.calcium;state=model.at_temperature(t,c);back=model.state(c,state['enthalpy_j'])
        af=reaction.affinity(t,state['co2_partial_pressure_pa'])['affinity_j_mol_extent']
        flags={'positive_co2_inventory':state['co2_mol']>0.,'positive_lime_inventory':state['lime_mol']>0.,
            'equal_product_amounts':abs(state['lime_mol']-state['co2_mol'])<=budget['inventory_mol'],
            'inverse_temperature':abs(back['temperature_k']-t)<=budget['inverse_temperature_k'],
            'equilibrium_affinity':abs(af)<=budget['chemical_stability_j_mol']}
        corners.append({'state':state,'affinity_j_mol':af,'within_budgets':flags})
    faces=[]
    for case in settings['face_cases']:
        left,right=[model.at_temperature(*case[key]) for model,key in zip(cells,('left','right'),strict=True)]
        shifted_left,shifted_right=[model.at_temperature(*case[key]) for model,key in zip(shifted,('left','right'),strict=True)]
        face=reactive_carbon_face(left,right,config['face']);gauge=reactive_carbon_face(shifted_left,shifted_right,config['face'])
        tl,tr=left['temperature_k'],right['temperature_k'];h=(left['co2_partial_enthalpy_j_mol']+right['co2_partial_enthalpy_j_mol'])/2
        r=reaction.gas_constant_j_mol_k;p0=reaction.standard_pressure_pa
        sl=model.gas.standard(tl)['entropy_j_mol_k']-r*math.log(left['co2_partial_pressure_pa']/p0)
        sr=model.gas.standard(tr)['entropy_j_mol_k']-r*math.log(right['co2_partial_pressure_pa']/p0)
        force=(left['co2_partial_enthalpy_j_mol']-h)/tl-(right['co2_partial_enthalpy_j_mol']-h)/tr-sl+sr
        reference_flow=config['face']['carbon_mobility_mol2_k_j_s']*force
        direct_entropy=face['enthalpy_flow_w']*(1/tr-1/tl)+face['carbon_flow_mol_s']*(left['carbon_chemical_potential_j_mol']/tl-right['carbon_chemical_potential_j_mol']/tr)
        errors={'reference_carbon_flow_mol_s':max(abs(reference_flow-face['carbon_flow_mol_s']),abs(gauge['carbon_flow_mol_s']-face['carbon_flow_mol_s'])),
            'reference_enthalpy_flow_w':abs(gauge['enthalpy_flow_w']-face['enthalpy_flow_w']-dh_ref*face['carbon_flow_mol_s']),
            'reference_entropy_production_w_k':max(abs(gauge['entropy_production_w_k']-face['entropy_production_w_k']),abs(direct_entropy-face['entropy_production_w_k']))}
        flags={key:value<=budget[key] for key,value in errors.items()};flags['nonnegative_entropy']=face['entropy_production_w_k']>=-budget['nonnegative_entropy_allowance_w_k']
        faces.append({'case':case,'face':face,'errors':errors,'within_budgets':flags})
    result={'settings':settings,'parameters':config,'records':records,'faces':faces,'equal_inventory_corners':corners,
        'all_requested_numerical_budgets_met':all(all(row['within_budgets'].values()) for row in records+faces+corners),
        'material_qualified':False,'training_eligible':False,
        'reference_shift_scope':'The same conserved-carbon H/S zero is added to CaCO3 and CO2; reaction enthalpy/free energy is unchanged. This is a coordinate comparison, not alternative material data.'}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'all_requested_numerical_budgets_met':result['all_requested_numerical_budgets_met'],'states':len(records),'faces':len(faces)}))


if __name__=='__main__':main()
