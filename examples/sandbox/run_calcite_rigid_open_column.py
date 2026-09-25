"""Record a conservative reacting column with one massless open surface."""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
import scipy
from scipy.integrate import BDF

from calcite_rigid_setup import build_rigid
from sludge_sandbox.rigid_reactive_open_column import OpenRigidReactiveColumn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--mesh',required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    parser.add_argument('--jacobian',choices=['analytic','numerical'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text())
    config = json.loads((root/settings['model_parameters']).read_text())
    surface = json.loads((root/settings['surface_parameters']).read_text())['surface']
    reaction,nitrogen,affinity,source,facts,nsource,volume = build_rigid(root,config)
    n = settings['meshes'][args.mesh]
    model = OpenRigidReactiveColumn(reaction,nitrogen,volume,config,settings,surface,n)
    values = model.initial;policy = settings['numerics'];factor = 1. if args.tolerance=='base' else policy['refinement_factor']
    absolute = np.array(policy['physical_coordinate_absolute_tolerances']*n+policy['ledger_absolute_tolerances'])*factor
    begin,end = settings['boundary_program'][0]['start_s'],settings['boundary_program'][-1]['end_s']
    times = np.arange(begin+policy['observation_interval_s'],end+policy['observation_interval_s'],policy['observation_interval_s'])
    index = steps = 0;started = time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,y,segment):
            physical,states,faces,reservoir,contact = model.observe(y,segment)
            return {'kind':kind,'time_s':float(t),'segment_index':segment,'integration_values':y.tolist(),'values':physical.tolist(),
                'states':states,'faces':faces,'reservoir':reservoir,'contact':contact}
        emit({'kind':'input','settings':settings,'model_parameters':config,'surface_parameters':model.surface_parameters,
            'affinity_parameters':affinity,'source':source,'reference_facts':facts,'nitrogen_source':nsource,'volume_source':volume,
            'cell_count':n,'cell_volume_m3':model.volume,'cell_width_m':model.width,'internal_face_parameters':model.face_parameters,
            'tolerance':args.tolerance,'jacobian_method':args.jacobian,'scipy_version':scipy.__version__,
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',begin,values,0))
        for segment,program in enumerate(settings['boundary_program']):
            widths = []
            if segment:emit(record('boundary_transition',program['start_s'],values,segment))
            def rates(t,y):
                try:
                    return model.rates(t,y,segment)
                except (ValueError,RuntimeError) as error:
                    emit({'kind':'evaluation_failure','time_s':math.fsum([program['start_s'],*widths,t]),
                        'solver_time_s':t,'segment_index':segment,'integration_values':y.tolist(),'error':str(error)})
                    raise
            jacobian = (lambda t,y:model.jacobian(t,y,segment)) if args.jacobian=='analytic' else None
            solver = BDF(rates,0.,values,program['end_s']-program['start_s'],
                rtol=policy['relative_tolerance']*factor,atol=absolute,jac=jacobian,
                first_step=policy['initial_step_s'],max_step=policy['maximum_step_s'])
            while solver.status=='running':
                previous = solver.t;message = solver.step()
                if solver.status=='failed':
                    emit({'kind':'integration_failure','segment_index':segment,'reason':str(message),
                        'solver_time_s':solver.t,'proposed_step_s':solver.h_abs,'completed_local_widths':len(widths)})
                    raise RuntimeError('Open reactive column integration failed: '+str(message))
                steps += 1;dense = solver.dense_output()
                absolute_time = math.fsum([program['start_s'],*widths,solver.t])
                row = record('accepted',absolute_time,solver.y,segment)
                row['dense_output'] = {'start_time_s':previous,'end_time_s':solver.t,'shifts_s':dense.t_shift.tolist(),
                    'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()};emit(row)
                while index<len(times) and times[index]<=absolute_time:
                    at = float(times[index]);solver_at = math.fsum([at,-program['start_s'],*(-h for h in widths)])
                    emit(record('sample',at,dense(solver_at),segment));index += 1
                if steps%policy['progress_every_steps']==0:
                    print(json.dumps({'time_s':absolute_time,'accepted_steps':steps,'segment':segment,'elapsed_s':time.monotonic()-started,
                        'segment_function_evaluations':solver.nfev,'segment_jacobian_evaluations':solver.njev}),flush=True)
                widths.append(solver.t)
                if solver.status=='running':
                    solver.t_old -= solver.t;solver.t = 0.
                    solver.t_bound = math.fsum([program['end_s']-program['start_s'],*(-h for h in widths)])
            values = solver.y
        emit({'kind':'summary','status':'completed','time_s':end,'accepted_steps':steps,'elapsed_s':time.monotonic()-started,
            'values':model.physical_values(values).tolist(),'integration_values':values.tolist(),
            'final':record('final',end,values,len(settings['boundary_program'])-1)})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':
    main()
