"""Profile conserved/temperature state maps and qualify their physical rates."""
import argparse
import cProfile
import json
from pathlib import Path
import pstats
import time

import numpy as np

from carbon_calcium_pressure_setup import build
from sludge_sandbox.carbon_calcium_rigid_column import CarbonCalciumRigidColumn
from sludge_sandbox.carbon_calcium_rigid_exchange import exchange
from sludge_sandbox.carbon_calcium_rigid_tangent import rigid_tangent


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text());selected=[]
    with (root/settings['trajectory']).open() as stream:
        header=json.loads(next(stream))
        for line in stream:
            row=json.loads(line)
            if row['kind'] in ('initial','sample') and row['time_s'] in settings['times_s']:selected.append(row)
    model,sources,_=build(root,header['pressure_parameters']);p=header['settings'];rigid=header['rigid_parameters'];n=header['cell_count']
    column=CarbonCalciumRigidColumn(model,p,header['face_parameters'],rigid['numerics'],n);keys=column.face_parameters['transferred_inventory_order']
    def evaluate(row,route):
        y=np.array(row['values'])
        if route=='conserved':
            states=column.states(y);rates=column.rates(row['time_s'],y)
        else:
            states=[model.at_temperature_volume(recorded['temperature_k'],column.volume,column.inventories[i]['calcium_atoms_mol'],
                *map(float,y[4*i:4*i+3]),rigid['numerics']) for i,recorded in enumerate(row['states'])]
            faces=[exchange(model,a,b,column.face_parameters) for a,b in zip(states[:-1],states[1:],strict=True)]
            body=np.zeros((n,4))
            for i,face in enumerate(faces):
                flow=np.array([*[face['inventory_flows_mol_s'][k] for k in keys],face['energy_flow_w']]);body[i]-=flow;body[i+1]+=flow
            rates=np.concatenate((body.ravel(),[sum(f['entropy_production_w_k'] for f in faces)]))
        tangents=[rigid_tangent(model,state,column.volume,column.inventories[i]['calcium_atoms_mol'],y[4*i],y[4*i+1]) for i,state in enumerate(states)]
        primitive=rates.copy();reconstructed=rates.copy()
        for i,tangent in enumerate(tangents):
            du=np.array(tangent['internal_energy_derivatives']);start=4*i
            primitive[start+3]=(rates[start+3]-du[1:]@rates[start:start+3])/du[0]
            reconstructed[start+3]=du[0]*primitive[start+3]+du[1:]@primitive[start:start+3]
        return {'time_s':row['time_s'],'states':states,'conserved_rates':rates.tolist(),
                'primitive_rates':primitive.tolist(),'reconstructed_conserved_rates':reconstructed.tolist()}
    routes=[]
    for route in ['conserved','temperature']:
        profile=cProfile.Profile();started=time.monotonic();profile.enable();values=[evaluate(row,route) for row in selected];profile.disable()
        elapsed=time.monotonic()-started;stats=pstats.Stats(profile).stats
        functions=[{'module':Path(k[0]).name,'function':k[2],'calls':v[1],'self_s':v[2],'cumulative_s':v[3]} for k,v in stats.items()]
        functions.sort(key=lambda r:r['cumulative_s'],reverse=True)
        routes.append({'route':route,'elapsed_profiled_s':elapsed,'values':values,'top_functions':functions[:settings['profile_top_functions']],
            'flash_calls':[r for r in functions if r['function'] in ['from_internal_energy','at_temperature_volume','at_temperature_pressure']]})
    errors={k:0. for k in settings['budgets']}
    for a,b in zip(routes[0]['values'],routes[1]['values'],strict=True):
        for left,right in zip(a['states'],b['states'],strict=True):
            for k in ['temperature_k','pressure_pa']:errors[k]=max(errors[k],abs(left[k]-right[k]))
            errors['species_mol']=max(errors['species_mol'],*(abs(left['amounts_mol'][k]-right['amounts_mol'][k]) for k in left['amounts_mol']))
        delta=(np.array(a['conserved_rates'])-np.array(b['reconstructed_conserved_rates']))[:-1].reshape(n,4)
        errors['conserved_inventory_rate_mol_s']=max(errors['conserved_inventory_rate_mol_s'],float(np.max(np.abs(delta[:,:3]))))
        errors['conserved_energy_rate_w']=max(errors['conserved_energy_rate_w'],float(np.max(np.abs(delta[:,3]))))
        errors['entropy_rate_w_k']=max(errors['entropy_rate_w_k'],abs(a['conserved_rates'][-1]-b['conserved_rates'][-1]))
    flags={k:v<=settings['budgets'][k] for k,v in errors.items()};flags['all_requested_times_present']=[r['time_s'] for r in selected]==settings['times_s']
    result={'settings':settings,'routes':routes,'maximum_differences':errors,'within_budgets':flags,'all_requested_budgets_met':all(flags.values()),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'flags':flags,'routes':[{k:r[k] for k in ['route','elapsed_profiled_s','flash_calls']} for r in routes]}))


if __name__=='__main__':main()
