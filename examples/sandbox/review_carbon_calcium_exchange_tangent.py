"""Independent source finite differences for two-endpoint exchange derivatives."""
import argparse
import json
from pathlib import Path

from mpmath import mp
import numpy as np

from carbon_calcium_pressure_setup import build
from carbon_calcium_rigid_decimal_reference import reconstruct
from review_carbon_calcium_exchange import source_face
from sludge_sandbox.carbon_calcium_rigid_exchange import exchange_jacobian
from sludge_sandbox.carbon_calcium_rigid_tangent import rigid_tangent


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    parameters=json.loads((root/settings['exchange_parameters']).read_text());rigid=json.loads((root/parameters['rigid_parameters']).read_text())
    pressure=json.loads((root/rigid['pressure_parameters']).read_text());model,sources,_=build(root,pressure)
    volume=rigid['virtual_volume_m3'];mp.dps=settings['decimal_digits'];keys=['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol'];records=[]
    for inventory in pressure['inventories']:
        inputs=[inventory[k] for k in keys];states=[];refs=[];tangents=[]
        for t in settings['temperature_points_k']:
            state=model.at_temperature_volume(t,volume,*inputs,rigid['numerics']);states.append(state)
            refs.append(reconstruct(model,t,volume,inventory,state,settings));tangents.append(rigid_tangent(model,state,volume,*inputs[:3]))
        for a,b in settings['pairings']:
            candidates=[states[a],states[b]];references=[refs[a],refs[b]];derivatives=[tangents[a],tangents[b]]
            jac=exchange_jacobian(model,*candidates,*derivatives,parameters);forward=np.zeros((8,8))
            for side,tangent in enumerate(derivatives):
                block=np.zeros((4,4));block[:3,1:]=np.eye(3);block[3]=tangent['internal_energy_derivatives']
                forward[4*side:4*side+4,4*side:4*side+4]=block
            physical={key:{k:np.array(v)@forward for k,v in jac[key].items()} for key in ['gas','inventory']}
            physical.update({key:np.array(jac[key])@forward for key in ['energy','entropy_left','entropy_right','production']})
            reviews=[]
            for side in [0,1]:
                for index,coordinate in enumerate(derivatives[side]['coordinate_order']):
                    thermal=index==0;column=4*side+index
                    steps=settings['temperature_difference_steps_k'] if thermal else settings['inventory_relative_difference_steps']
                    budget=settings['temperature_derivative_budgets'] if thermal else settings['inventory_derivative_budgets']
                    for raw_step in steps:
                        step=mp.mpf(raw_step)*(1 if thermal else mp.mpf(inventory[coordinate]));pair=[];phases=[]
                        for sign in [-1,1]:
                            temperatures=[mp.mpf(s['temperature_k']) for s in candidates]
                            if thermal:temperatures[side]+=sign*step
                            inv=inventory if thermal else {**inventory,coordinate:mp.mpf(inventory[coordinate])+sign*step}
                            state=model.at_temperature_volume(float(temperatures[side]),volume,*[float(inv[k]) for k in keys],rigid['numerics'])
                            phases.append((state['calcium_phase'],state['carbon_phase']))
                            source_pair=references.copy();source_pair[side]=reconstruct(model,temperatures[side],volume,inv,state,settings)
                            pair.append(source_face(*source_pair,*temperatures,parameters))
                        low,high=pair
                        errors={key:max(float(abs(mp.mpf(physical[key][k][column])-(high[key][k]-low[key][k])/(2*step))) for k in high[key]) for key in ['gas','inventory']}
                        errors['energy']=float(abs(mp.mpf(physical['energy'][column])-(high['energy']-low['energy'])/(2*step)))
                        errors['entropy']=max(float(abs(mp.mpf(physical[k][column])-(high[v]-low[v])/(2*step))) for k,v in
                            [('entropy_left','left_entropy'),('entropy_right','right_entropy'),('production','production')])
                        flags={k:v<=budget[k] for k,v in errors.items()};flags['same_phase']=all(v==(candidates[side]['calcium_phase'],candidates[side]['carbon_phase']) for v in phases)
                        reviews.append({'side':side,'coordinate':coordinate,'difference_step':str(step),'errors':errors,'within_budgets':flags})
            identity=float(np.max(np.abs(np.array(jac['entropy_left'])+np.array(jac['entropy_right'])-np.array(jac['production']))))
            flags={'source_derivatives':all(all(v['within_budgets'].values()) for v in reviews),
                   'entropy_identity':identity<=settings['entropy_identity_derivative_absolute_budget']}
            records.append({'inventory':inventory,'temperatures_k':[s['temperature_k'] for s in candidates],'jacobian':jac,
                'difference_reviews':reviews,'entropy_identity_derivative_error':identity,'within_budgets':flags})
            print(json.dumps({'inventory':inventory['name'],'temperatures_k':records[-1]['temperatures_k'],'flags':flags}),flush=True)
    result={'settings':settings,'exchange_parameters':parameters,'rigid_parameters':rigid,'sources':sources,'records':records,
        'all_requested_budgets_met':all(all(r['within_budgets'].values()) for r in records),'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':main()
