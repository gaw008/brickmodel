"""Record a prescribed hot-vent / cool-CO2 cycle with complete exterior ledgers."""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
import scipy
from scipy.integrate import BDF

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from sludge_sandbox.rigid_reactive_open_cell import OpenRigidCalciteCell
from sludge_sandbox.rigid_reactive_offset import OffsetRigidCalciteMixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--coordinate-parameters','--log-nitrogen-parameters',dest='coordinate_parameters',type=Path)
    args = parser.parse_args();root = args.parameters.resolve().parent;settings = json.loads(args.parameters.read_text())
    coordinates = json.loads(args.coordinate_parameters.read_text()) if args.coordinate_parameters else {'method':'physical'}
    config = json.loads((root/settings['model_parameters']).read_text());surface = json.loads((root/settings['surface_parameters']).read_text())['surface']
    reaction,nitrogen,affinity,source,facts,nsource,volume = build_rigid(root,config)
    offset_coordinates = 'carbon_coordinate' in coordinates and coordinates['carbon_coordinate']=='excess_over_calcium'
    local_time = coordinates.get('time_coordinate')=='step_local_autonomous'
    cell_class = OffsetRigidCalciteMixture if offset_coordinates else RigidCalciteMixture
    cell = cell_class(reaction,nitrogen,volume,config,settings['cell'])
    model = OpenRigidCalciteCell(cell,surface,settings['boundary_program'])
    initial = cell.at_temperature(settings['initial']['temperature_k'],settings['initial']['carbon_mol'])
    values = np.array([initial[k] for k in ('carbon_mol','nitrogen_mol','internal_energy_j')]+[0.]*10)
    if offset_coordinates:
        values[0] -= cell.calcium
    if coordinates['method']=='log_nitrogen':
        values[1] = np.log(values[1]/coordinates['reference_nitrogen_mol'])
    def physical(y):
        result = y.copy()
        if offset_coordinates:
            result[0] += cell.calcium
        if coordinates['method']=='log_nitrogen':
            result[1] = coordinates['reference_nitrogen_mol']*np.exp(y[1])
        return result
    policy = settings['numerics'];factor = 1. if args.tolerance=='base' else policy['refinement_factor']
    start = settings['boundary_program'][0]['start_s'];end = settings['boundary_program'][-1]['end_s']
    times = np.arange(start+policy['observation_interval_s'],end+policy['observation_interval_s'],policy['observation_interval_s'])
    index = steps = 0;started = time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,y,segment):
            inventory = physical(y);state,reservoir,contact = model.observe(inventory,segment,y[0] if offset_coordinates else None)
            return {'kind':kind,'time_s':float(t),'segment_index':segment,'values':inventory.tolist(),'integration_values':y.tolist(),'state':state,'reservoir':reservoir,'contact':contact}
        emit({'kind':'input','settings':settings,'model_parameters':config,'surface_parameters':surface,'affinity_parameters':affinity,
            'source':source,'reference_facts':facts,'nitrogen_source':nsource,'volume_source':volume,'tolerance':args.tolerance,
            'integration_coordinates':coordinates,
            'scipy_version':scipy.__version__,
            'state_order':['C','N2','U','C_inner_out','N_inner_out','E_inner_out','C_outer_out','N_outer_out','E_outer_out','Q_radiation_in','S_gas_reservoir','S_radiation_reservoir','S_production'],
            'jacobian_method':'SciPy BDF finite difference in declared integration coordinates and passive ledgers',
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',start,values,0))
        for segment,program in enumerate(settings['boundary_program']):
            widths = []
            if segment:
                emit(record('boundary_transition',program['start_s'],values,segment))
            def rates(t,y):
                inventory = physical(y)
                try:
                    result = model.rates(t,inventory,segment,y[0] if offset_coordinates else None)
                except (ValueError,RuntimeError) as error:
                    emit({'kind':'evaluation_failure','time_s':math.fsum([program['start_s'],*widths,t]) if local_time else float(t),'segment_index':segment,
                        'solver_time_s':float(t),
                        'values':inventory.tolist(),'integration_values':y.tolist(),'error':str(error)})
                    raise
                if coordinates['method']=='log_nitrogen':
                    result[1] /= inventory[1]
                return result
            absolute = np.array(policy['absolute_tolerances'])
            if coordinates['method']=='log_nitrogen':
                absolute[1] = coordinates['log_nitrogen_absolute_tolerance']
            solver = BDF(rates,0. if local_time else program['start_s'],values,
                program['end_s']-program['start_s'] if local_time else program['end_s'],
                rtol=policy['relative_tolerance']*factor,atol=absolute*factor,
                first_step=policy['initial_step_s'],max_step=policy['maximum_step_s'])
            while solver.status=='running':
                previous = solver.t;message = solver.step()
                if solver.status=='failed':
                    emit({'kind':'integration_failure','segment_index':segment,'reason':str(message),
                        'solver_time_s':solver.t,'proposed_step_s':solver.h_abs,'completed_local_widths':len(widths)})
                    raise RuntimeError('Open reactive cell integration failed: '+str(message))
                steps += 1;dense = solver.dense_output()
                absolute_time = math.fsum([program['start_s'],*widths,solver.t]) if local_time else solver.t
                row = record('accepted',absolute_time,solver.y,segment)
                row['dense_output'] = {'start_time_s':previous,'end_time_s':solver.t,'shifts_s':dense.t_shift.tolist(),
                    'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()};emit(row)
                while index<len(times) and times[index]<=absolute_time:
                    at = float(times[index])
                    solver_at = math.fsum([at,-program['start_s'],*(-h for h in widths)]) if local_time else at
                    emit(record('sample',at,dense(solver_at),segment));index += 1
                if steps%policy['progress_every_steps']==0:
                    print(json.dumps({'time_s':absolute_time,'accepted_steps':steps,'segment':segment,'elapsed_s':time.monotonic()-started,
                        'segment_function_evaluations':solver.nfev,'segment_jacobian_evaluations':solver.njev}),flush=True)
                if local_time:
                    widths.append(solver.t)
                    if solver.status=='running':
                        # An autonomous segment permits exact time translation.
                        # Keep BDF differences, order, Jacobian and factorization.
                        solver.t_old -= solver.t
                        solver.t = 0.
                        solver.t_bound = math.fsum([program['end_s']-program['start_s'],*(-h for h in widths)])
            values = solver.y
        emit({'kind':'summary','status':'completed','time_s':end,'values':physical(values).tolist(),'integration_values':values.tolist(),'accepted_steps':steps,
            'elapsed_s':time.monotonic()-started,'final':record('final',end,values,len(settings['boundary_program'])-1)})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':
    main()
