"""Record conservative carbon and enthalpy exchange between reactive cells."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from calcite_closed_setup import build_closed
from sludge_sandbox.equilibrium_calcite_inventory import CalciteInventoryCell,reactive_carbon_face


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;config=json.loads(args.parameters.read_text())
    reaction,nitrogen,affinity,source,facts,nsource=build_closed(root,config)
    cells=[CalciteInventoryCell(reaction,nitrogen,config,cell) for cell in config['cells']]
    initial=[model.at_temperature(cell['initial_temperature_k'],cell['initial_carbon_mol']) for model,cell in zip(cells,config['cells'],strict=True)]
    y=np.array([initial[0]['carbon_mol'],initial[0]['enthalpy_j'],initial[1]['carbon_mol'],initial[1]['enthalpy_j'],0.,0.,0.])
    policy=config['numerics'];factor=1. if args.tolerance=='base' else policy['refinement_factor'];left,right=config['time_interval_s']
    def states(values):return [model.state(float(values[2*i]),float(values[2*i+1])) for i,model in enumerate(cells)]
    def rates(t,values):
        a,b=states(values);face=reactive_carbon_face(a,b,config['face']);n=face['carbon_flow_mol_s'];h=face['enthalpy_flow_w']
        return np.array([-n,-h,n,h,n,h,face['entropy_production_w_k']])
    started=time.monotonic();steps=0
    with args.output.open('x') as stream:
        def emit(row):stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,values):
            pair=states(values)
            return {'kind':kind,'time_s':float(t),'values':values.tolist(),'states':pair,'face':reactive_carbon_face(*pair,config['face'])}
        emit({'kind':'input','parameters':config,'affinity_parameters':affinity,'source':source,'reference_facts':facts,
            'nitrogen_source':nsource,'tolerance':args.tolerance,'state_order':['C_left','H_left','C_right','H_right','C_left_to_right','H_left_to_right','entropy_production'],
            'jacobian_method':'SciPy BDF finite difference in full physical inventories; no matrix feedback approximation',
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',left,y))
        solver=BDF(rates,left,y,right,rtol=policy['relative_tolerance']*factor,
            atol=np.array(policy['absolute_tolerances'])*factor,max_step=policy['maximum_step_s'],first_step=policy['initial_step_s'])
        samples=np.arange(left+policy['observation_interval_s'],right+policy['observation_interval_s'],policy['observation_interval_s']);index=0
        while solver.status=='running':
            previous=solver.t;message=solver.step()
            if solver.status=='failed':raise RuntimeError('reactive exchange BDF failed: '+str(message))
            steps+=1;dense=solver.dense_output();row=record('accepted',solver.t,solver.y)
            row['dense_output']={'start_time_s':previous,'end_time_s':solver.t,'shifts_s':dense.t_shift.tolist(),
                'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()};emit(row)
            while index<len(samples) and samples[index]<=solver.t:
                at=float(samples[index]);emit(record('sample',at,dense(at)));index+=1
            if steps%policy['progress_every_steps']==0:
                print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
        emit({'kind':'summary','status':'completed','final_states':states(solver.y),'values':solver.y.tolist(),
            'accepted_steps':steps,'elapsed_s':time.monotonic()-started})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
