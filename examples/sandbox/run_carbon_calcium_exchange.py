"""Closed two-cell heat, elemental gas exchange and reactive equilibration."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from carbon_calcium_pressure_setup import build
from sludge_sandbox.carbon_calcium_rigid_exchange import exchange


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;settings=json.loads(args.parameters.read_text())
    face_parameters=json.loads((root/settings['exchange_parameters']).read_text())
    rigid=json.loads((root/face_parameters['rigid_parameters']).read_text())
    pressure=json.loads((root/rigid['pressure_parameters']).read_text());model,sources,_=build(root,pressure)
    cells=settings['cells'];keys=face_parameters['transferred_inventory_order'];initial_states=[];inventories=[]
    for cell in cells:
        inventory=next(i for i in pressure['inventories'] if i['name']==cell['inventory_name']);inventories.append(inventory)
        initial_states.append(model.at_temperature_volume(cell['initial_temperature_k'],cell['volume_m3'],
            inventory['calcium_atoms_mol'],*[inventory[k] for k in keys],rigid['numerics']))
    energies=[s['internal_energy_j'] for s in initial_states]
    initial=np.array([x for inv in inventories for x in [*[inv[k] for k in keys],0.]]+[0.])
    def decode(values):
        return [model.from_internal_energy(energies[i]+float(values[4*i+3]),cell['volume_m3'],
            inventories[i]['calcium_atoms_mol'],*map(float,values[4*i:4*i+3]),rigid['numerics']) for i,cell in enumerate(cells)]
    policy=settings['numerics'];factor=1. if args.tolerance=='base' else policy['refinement_factor']
    atol=np.array(policy['cell_absolute_tolerances_carbon_oxygen_nitrogen_energy']*len(cells)
                  +[policy['production_absolute_tolerance_j_k']])*factor
    times=np.arange(policy['observation_interval_s'],settings['duration_s']+policy['observation_interval_s'],policy['observation_interval_s'])
    sample=steps=0;started=time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def observe(values):
            states=decode(values)
            return states,exchange(model,states[0],states[1],face_parameters)
        def record(kind,at,values):
            states,face=observe(values)
            return {'kind':kind,'time_s':float(at),'values':values.tolist(),'states':states,'face':face}
        emit({'kind':'input','settings':settings,'face_parameters':face_parameters,'rigid_parameters':rigid,
            'pressure_parameters':pressure,'sources':sources,'inventories':inventories,'initial_internal_energies_j':energies,
            'tolerance':args.tolerance,'relative_tolerance':policy['relative_tolerance']*factor,'absolute_tolerances':atol.tolist(),
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',0.,initial))
        def rates(at,values):
            try:
                _,face=observe(values)
            except Exception as error:
                emit({'kind':'evaluation_failure','time_s':float(at),'values':values.tolist(),
                      'error_type':type(error).__name__,'error':str(error)})
                raise
            flow=np.array([*[face['inventory_flows_mol_s'][k] for k in keys],face['energy_flow_w']])
            return np.concatenate((-flow,flow,[face['entropy_production_w_k']]))
        solver=BDF(rates,0.,initial,settings['duration_s'],rtol=policy['relative_tolerance']*factor,atol=atol,
                   max_step=policy['maximum_step_s'],first_step=policy['first_step_s'])
        while solver.status=='running':
            before=solver.t;message=solver.step()
            if solver.status=='failed':raise RuntimeError(message)
            dense=solver.dense_output();steps+=1;row=record('accepted',solver.t,solver.y)
            row['dense_output']={'start_time_s':before,'end_time_s':solver.t,'shifts_s':dense.t_shift.tolist(),
                'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()};emit(row)
            while sample<len(times) and times[sample]<=solver.t:
                at=float(times[sample]);emit(record('sample',at,dense(at)));sample+=1
            if steps%policy['progress_every_steps']==0:
                print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
        emit({'kind':'summary','status':'completed','steps':steps,'elapsed_s':time.monotonic()-started,
              'final':record('final',solver.t,solver.y)})
    print(json.dumps({'status':'completed','steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
