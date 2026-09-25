"""Record conservative carbon, nitrogen and internal energy exchange between reactive cells."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from calcite_rigid_setup import build_rigid
from sludge_sandbox.rigid_reactive_column import RigidReactiveColumn
from sludge_sandbox.rigid_reactive_tangent import column_jacobian


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    parser.add_argument('--mesh',required=True)
    parser.add_argument('--analytic-jacobian-parameters',type=Path)
    args=parser.parse_args();root=args.parameters.resolve().parent;config=json.loads(args.parameters.read_text())
    reaction,nitrogen,affinity,source,facts,nsource,volume=build_rigid(root,config)
    column=RigidReactiveColumn(reaction,nitrogen,volume,config,config['meshes'][args.mesh]);y=column.initial
    policy=config['numerics'];factor=1. if args.tolerance=='base' else policy['refinement_factor'];left,right=config['time_interval_s']
    states=column.states;rates=column.rates
    jacobian_settings=json.loads(args.analytic_jacobian_parameters.read_text()) if args.analytic_jacobian_parameters else None
    jacobian=({'phase_local_analytic_csc':lambda t,y:column_jacobian(column,t,y)}[jacobian_settings['method']]
              if jacobian_settings else None)
    atols=policy['inventory_absolute_tolerances']*(2*column.count-1)+[policy['entropy_absolute_tolerance_j_k']]
    started=time.monotonic();steps=0
    with args.output.open('x') as stream:
        def emit(row):stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,values):
            pair=states(values)
            return {'kind':kind,'time_s':float(t),'values':values.tolist(),'states':pair,'faces':column.faces(pair)}
        emit({'kind':'input','parameters':config,'affinity_parameters':affinity,'source':source,'reference_facts':facts,
            'nitrogen_source':nsource,'volume_source':volume,'tolerance':args.tolerance,'mesh':args.mesh,'cell_count':column.count,'face_parameters':column.face_parameters,
            'state_order':'cell-major C/N2/U; face-major integrated C/N2/E left to right; total entropy production',
            'jacobian_method':jacobian_settings['method'] if jacobian_settings else 'SciPy BDF finite difference in full physical inventories; no matrix feedback approximation',
            'jacobian_parameters':jacobian_settings,
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',left,y))
        solver=BDF(rates,left,y,right,rtol=policy['relative_tolerance']*factor,
            atol=np.array(atols)*factor,max_step=policy['maximum_step_s'],first_step=policy['initial_step_s'],jac=jacobian)
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
                print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started,
                    'function_evaluations':solver.nfev,'jacobian_evaluations':solver.njev,'lu_decompositions':solver.nlu}),flush=True)
        emit({'kind':'summary','status':'completed','final_states':states(solver.y),'values':solver.y.tolist(),
            'accepted_steps':steps,'elapsed_s':time.monotonic()-started,
            'function_evaluations':solver.nfev,'jacobian_evaluations':solver.njev,'lu_decompositions':solver.nlu})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
