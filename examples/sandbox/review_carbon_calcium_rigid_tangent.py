"""Source-derived high-precision qualification of rigid inventory tangents."""
import argparse
import json
from pathlib import Path

from mpmath import mp
import numpy as np

from carbon_calcium_pressure_setup import build
from carbon_calcium_rigid_decimal_reference import reconstruct
from sludge_sandbox.carbon_calcium_rigid_tangent import rigid_tangent


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    rigid=json.loads((root/settings['rigid_parameters']).read_text());pressure=json.loads((root/rigid['pressure_parameters']).read_text())
    model,sources,_=build(root,pressure);volume=rigid['virtual_volume_m3'];mp.dps=settings['decimal_digits']
    keys=['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol'];records=[]
    for inventory in pressure['inventories']:
        for temperature in settings['temperature_points_k']:
            inputs=[inventory[k] for k in keys];state=model.at_temperature_volume(temperature,volume,*inputs,rigid['numerics'])
            tangent=rigid_tangent(model,state,volume,*inputs[:3]);ref=reconstruct(model,temperature,volume,inventory,state,settings)
            reviews=[]
            for index,coordinate in enumerate(tangent['coordinate_order']):
                thermal=index==0;steps=settings['temperature_difference_steps_k'] if thermal else settings['inventory_relative_difference_steps']
                budget=settings['temperature_derivative_budgets'] if thermal else settings['inventory_derivative_budgets']
                for raw_step in steps:
                    step=mp.mpf(raw_step)*(1 if thermal else mp.mpf(inventory[coordinate]));pair=[];phases=[]
                    for sign in [-1,1]:
                        temp=mp.mpf(temperature)+sign*step if thermal else mp.mpf(temperature)
                        inv=inventory if thermal else {**inventory,coordinate:mp.mpf(inventory[coordinate])+sign*step}
                        candidate=model.at_temperature_volume(float(temp),volume,*[float(inv[k]) for k in keys],rigid['numerics'])
                        phases.append((candidate['calcium_phase'],candidate['carbon_phase']))
                        pair.append(reconstruct(model,temp,volume,inv,candidate,settings))
                    lower,upper=pair
                    finite={key:(upper[key]-lower[key])/(2*step) for key in ['pressure','internal_energy','entropy']}
                    amounts={k:(upper['amounts'][k]-lower['amounts'][k])/(2*step) for k in state['amounts_mol']}
                    mu={k:(upper['mu'][k]-lower['mu'][k])/(2*step) for k in ['CO','CO2','O2','N2']}
                    errors={key:float(abs(mp.mpf(tangent[key+'_derivatives'][index])-value)) for key,value in finite.items()}
                    errors['amount']=max(float(abs(mp.mpf(tangent['amount_derivatives'][k][index])-v)) for k,v in amounts.items())
                    errors['gas_chemical_potential']=max(float(abs(mp.mpf(tangent['gas_chemical_potential_derivatives'][k][index])-v)) for k,v in mu.items())
                    flags={k:v<=budget[k] for k,v in errors.items()};flags['same_phase']=all(pair==(state['calcium_phase'],state['carbon_phase']) for pair in phases)
                    reviews.append({'coordinate':coordinate,'difference_step':str(step),'source_derivatives':{k:str(v) for k,v in finite.items()},
                        'errors':errors,'within_budgets':flags})
            u=np.array(tangent['internal_energy_derivatives']);s=np.array(tangent['entropy_derivatives']);mu=ref['mu']
            potential=np.array([float(mu['CO']-mu['O2']/2),float(mu['O2']/2),float(mu['N2'])])
            forward=np.zeros((4,4));forward[:3,1:]=np.eye(3);forward[3]=u
            identities={'thermal_gibbs_j_k':abs(u[0]-temperature*s[0]),
                'elemental_gibbs_j_mol':float(np.max(np.abs(u[1:]-temperature*s[1:]-potential))),
                'existing_cv_j_k':abs(u[0]-state['equilibrium_cv_j_k']),
                'inverse_chain_absolute':float(np.max(np.abs(forward@np.array(tangent['physical_from_conserved_derivative'])-np.eye(4))))}
            flags={k:float(v)<=settings['identity_budgets'][k] for k,v in identities.items()}
            flags['source_derivatives']=all(all(r['within_budgets'].values()) for r in reviews)
            records.append({'inventory':inventory,'state':state,'tangent':tangent,'difference_reviews':reviews,
                'identity_errors':{k:float(v) for k,v in identities.items()},'within_budgets':{k:bool(v) for k,v in flags.items()}})
            print(json.dumps({'inventory':inventory['name'],'temperature_k':temperature,'flags':{k:bool(v) for k,v in flags.items()}}),flush=True)
    result={'settings':settings,'rigid_parameters':rigid,'pressure_parameters':pressure,'sources':sources,'records':records,
        'all_requested_budgets_met':all(all(r['within_budgets'].values()) for r in records),'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
