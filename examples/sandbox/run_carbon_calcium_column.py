"""Closed spatial Ca/C/O reactive transport with an analytic local Jacobian."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from carbon_calcium_pressure_setup import build
from sludge_sandbox.carbon_calcium_rigid_column import CarbonCalciumRigidColumn


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--mesh',required=True);parser.add_argument('--tolerance',choices=['base','refined'],required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text())
    face=json.loads((root/p['exchange_parameters']).read_text());rigid=json.loads((root/face['rigid_parameters']).read_text());pressure=json.loads((root/rigid['pressure_parameters']).read_text())
    model,sources,_=build(root,pressure);n=p['meshes'][args.mesh];column=CarbonCalciumRigidColumn(model,p,face,rigid['numerics'],n)
    policy=p['numerics'];factor=1. if args.tolerance=='base' else policy['refinement_factor']
    cell_atol=[v*column.volume for v in policy['cell_density_absolute_tolerances_C_O_N_U']]
    atol=np.array(cell_atol*n+[policy['production_absolute_tolerance_j_k']])*factor
    times=np.arange(policy['observation_interval_s'],p['duration_s']+policy['observation_interval_s'],policy['observation_interval_s'])
    sample=steps=0;started=time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,at,values):
            states,faces=column.observe(values)
            return {'kind':kind,'time_s':float(at),'values':values.tolist(),'states':states,'faces':faces}
        emit({'kind':'input','settings':p,'face_parameters':column.face_parameters,'rigid_parameters':rigid,'pressure_parameters':pressure,
            'sources':sources,'cell_count':n,'cell_volume_m3':column.volume,'cell_width_m':column.width,'cell_centers_m':column.centers,
            'inventories':column.inventories,'initial_internal_energies_j':column.initial_energies,
            'tolerance':args.tolerance,'relative_tolerance':policy['relative_tolerance']*factor,'absolute_tolerances':atol.tolist(),
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',0.,column.initial))
        def rates(at,values):
            try:return column.rates(at,values)
            except Exception as error:
                emit({'kind':'evaluation_failure','time_s':float(at),'values':values.tolist(),'error_type':type(error).__name__,'error':str(error)})
                raise
        jacobian={'analytic':column.jacobian,'numerical':None}[policy['jacobian_method']]
        solver=BDF(rates,0.,column.initial,p['duration_s'],jac=jacobian,rtol=policy['relative_tolerance']*factor,atol=atol,
                   max_step=policy['maximum_step_s'],first_step=policy['first_step_s'])
        while solver.status=='running':
            before=solver.t;message=solver.step()
            if solver.status=='failed':raise RuntimeError(message)
            dense=solver.dense_output();steps+=1;row=record('accepted',solver.t,solver.y)
            row['dense_output']={'start_time_s':before,'end_time_s':solver.t,'shifts_s':dense.t_shift.tolist(),
                'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()};emit(row)
            while sample<len(times) and times[sample]<=solver.t:
                at=float(times[sample]);emit(record('sample',at,dense(at)));sample+=1
            if steps%policy['progress_every_steps']==0:print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
        emit({'kind':'summary','status':'completed','steps':steps,'elapsed_s':time.monotonic()-started,'final':record('final',solver.t,solver.y)})
    print(json.dumps({'status':'completed','steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
