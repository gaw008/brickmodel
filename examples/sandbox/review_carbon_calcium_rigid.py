"""Independent source and constant-volume caloric review of a rigid mixture."""
import argparse
import json
import math
from pathlib import Path

from mpmath import mp

from carbon_calcium_pressure_setup import build
from carbon_calcium_rigid_decimal_reference import reconstruct


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text())
    rigid=json.loads((root/settings['model_parameters']).read_text())
    policy=json.loads((root/rigid['pressure_parameters']).read_text())
    model,sources,_=build(root,policy)
    mp.dps=settings['decimal_digits']
    volume=rigid['virtual_volume_m3']
    numerics,budget=rigid['numerics'],settings['budgets']
    records=[]
    for inventory in policy['inventories']:
        inputs=[inventory[k] for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
        for temperature in settings['temperature_points_k']:
            candidate=model.at_temperature_volume(temperature,volume,*inputs,numerics)
            reference=reconstruct(model,temperature,volume,inventory,candidate,settings)
            n,mu=candidate['amounts_mol'],candidate['chemical_potentials_j_mol']
            elements=[n['calcite']+n['lime'],math.fsum(n[k] for k in ['calcite','C','CO','CO2']),
                math.fsum((3*n['calcite'],n['lime'],n['CO'],2*n['CO2'],2*n['O2'])),n['N2']]
            errors={'element_mol':max(abs(a-b) for a,b in zip(elements,inputs,strict=True)),
                'pressure_pa':float(abs(mp.mpf(candidate['pressure_pa'])-reference['pressure'])),
                'volume_m3':max(abs(candidate['total_volume_m3']-volume),float(abs(reference['volume']-mp.mpf(volume)))),
                'energy_j':max(float(abs(mp.mpf(candidate[field])-reference[key])) for key,field in
                    [('enthalpy','enthalpy_j'),('internal_energy','internal_energy_j'),('helmholtz','helmholtz_j')]),
                'entropy_j_k':float(abs(mp.mpf(candidate['entropy_j_k'])-reference['entropy'])),
                'amount_mol':max(float(abs(mp.mpf(n[k])-v)) for k,v in reference['amounts'].items()),
                'positive_gas_relative':max(float(abs(mp.mpf(n[k])/reference['amounts'][k]-1)) for k in ['CO','CO2','O2','N2'])}
            ac=mu['lime']+mu['CO2']-mu['calcite']
            a1=mu['CO']-mu['C']-mu['O2']/2
            a2=mu['CO2']-mu['C']-mu['O2']
            ag=mu['CO2']-mu['CO']-mu['O2']/2
            calcium_error={'calcite':max(0.,-ac),'lime':max(0.,ac),'coexistence':abs(ac)}[candidate['calcium_phase']]
            carbon_error=max(abs(a1),abs(a2)) if candidate['carbon_phase']=='graphite_present' else max(0.,a1,a2)
            errors['chemical_potential_j_mol']=max(calcium_error,carbon_error,abs(ag))
            inverse=model.from_internal_energy(candidate['internal_energy_j'],volume,*inputs,numerics)
            errors['inverse_temperature_k']=abs(inverse['temperature_k']-temperature)
            rm=reference['mu'];rac=rm['lime']+rm['CO2']-rm['calcite']
            constraints=all(v>=0 for v in reference['amounts'].values())
            if candidate['calcium_phase']=='calcite':constraints=constraints and rac>=0
            if candidate['calcium_phase']=='lime':constraints=constraints and rac<=0
            if candidate['carbon_phase']=='graphite_exhausted':
                constraints=constraints and rm['CO']-rm['C']-rm['O2']/2<=0 and rm['CO2']-rm['C']-rm['O2']<=0
            flags={key:value<=budget[key] for key,value in errors.items()}
            flags['reference_phase_constraints']=bool(constraints)
            flags['positive_capacity']=candidate['equilibrium_cv_j_k']>0
            derivative_reviews=[]
            phases=(candidate['calcium_phase'],candidate['carbon_phase'])
            for step in settings['temperature_difference_steps_k']:
                dt=mp.mpf(step);neighbors=[];states=[]
                for t in (mp.mpf(temperature)-dt,mp.mpf(temperature)+dt):
                    runtime=model.at_temperature_volume(float(t),volume,*inputs,numerics)
                    neighbors.append((runtime['calcium_phase'],runtime['carbon_phase']))
                    states.append(reconstruct(model,t,volume,inventory,runtime,settings))
                lower,upper=states
                du=(upper['internal_energy']-lower['internal_energy'])/(2*dt)
                ds=(upper['entropy']-lower['entropy'])/(2*dt)
                dp=(upper['pressure']-lower['pressure'])/(2*dt)
                derivative_errors={
                    'cv_j_k':float(abs(mp.mpf(candidate['equilibrium_cv_j_k'])-du)),
                    'entropy_derivative_j_k':float(abs(mp.mpf(candidate['equilibrium_cv_j_k'])-mp.mpf(temperature)*ds)),
                    'pressure_derivative_pa_k':float(abs(mp.mpf(candidate['pressure_temperature_derivative_at_volume_pa_k'])-dp)),
                    'amount_derivative_mol_k':max(float(abs(mp.mpf(candidate['amount_temperature_derivatives_at_volume_mol_k'][k])
                        -(upper['amounts'][k]-lower['amounts'][k])/(2*dt))) for k in n)}
                derivative_flags={key:value<=budget[key] for key,value in derivative_errors.items()}
                derivative_flags['same_phase']=all(pair==phases for pair in neighbors)
                derivative_reviews.append({'temperature_difference_k':step,'errors':derivative_errors,
                                           'within_budgets':derivative_flags})
            flags['derivatives']=all(all(v['within_budgets'].values()) for v in derivative_reviews)
            records.append({'inventory':inventory,'candidate':candidate,'errors':errors,
                'reference_pressure_pa':str(reference['pressure']),
                'reference_amounts_mol':{k:str(v) for k,v in reference['amounts'].items()},
                'derivative_reviews':derivative_reviews,'within_budgets':flags})
            print(json.dumps({'inventory':inventory['name'],'temperature_k':temperature,'pressure_pa':candidate['pressure_pa'],
                'phases':phases,'within_budgets':all(flags.values())}),flush=True)
    result={'settings':settings,'rigid_parameters':rigid,'pressure_parameters':policy,'sources':sources,'records':records,
        'all_requested_rigid_budgets_met':all(all(v['within_budgets'].values()) for v in records),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')


if __name__=='__main__':main()
