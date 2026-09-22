"""BDF evolution of a one-dimensional source-sorptive common-gas column.

Cell inventories and U evolve through shared internal faces. Exterior fluxes
are integrated alongside them; no post-step balance correction is applied.
"""
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import signal
import sys
from tempfile import TemporaryDirectory
import time

import numpy as np
import scipy
from scipy.integrate import BDF
from scipy.optimize import brentq
from scipy.sparse import lil_matrix

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_open_gas_boundary import json_value
from sorptive_column_setup import build_column,cell_parameters,restore_column
from sorptive_column_checkpoint import read_checkpoint
from sorptive_energy_coordinates import GasReferenceEnergy
from sorptive_physical_jacobian import PhysicalColumnJacobian


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    inputs=parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--parameters',type=Path)
    inputs.add_argument('--resume-from',type=Path)
    parser.add_argument('--mesh')
    parser.add_argument('--tolerance',choices=('base','refined'))
    parser.add_argument('--execution-parameters',type=Path)
    parser.add_argument('--energy-coordinates',type=Path,
                        help='Explicit root policy for a linear solver-coordinate study; otherwise retain physical U coordinates')
    parser.add_argument('--jacobian-parameters',type=Path,
                        help='Explicit policy for feedback-state differentiation and exact exterior ledger blocks')
    parser.add_argument('--stop-at')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.parameters and (args.mesh is None or args.tolerance is None):
        parser.error('new runs require --mesh and --tolerance')
    if args.resume_from and (args.mesh is not None or args.tolerance is not None):
        parser.error('resumed runs use the recorded mesh and tolerance')
    if args.stop_at and args.execution_parameters is None:
        parser.error('--stop-at requires --execution-parameters')
    with TemporaryDirectory(prefix='sorptive-column-sources-') as directory:
        run(args,Path(directory))


def run(args,source_directory):
    stop_requested=[]
    def request_stop(number,frame):
        stop_requested.append(signal.Signals(number).name)
    signal.signal(signal.SIGINT,request_stop);signal.signal(signal.SIGTERM,request_stop)
    if args.resume_from:
        header,checkpoint,prefix=read_checkpoint(args.resume_from)
        config=header['parameters'];n=header['cell_count']
        args.mesh,args.tolerance=header['mesh'],header['tolerance']
        model=restore_column(header,source_directory)
    else:
        root=args.parameters.resolve().parent
        config=json.loads(args.parameters.read_text());n=config['numerics']['meshes'][args.mesh]
        model=build_column(root,config,n)
    host=model.host
    policy=config['numerics']['implicit'];factor=1. if args.tolerance=='base' else policy['refinement_tolerance_factor']
    species=config['boundary_program']['values']['species_order'];width=len(species)+1
    coordinates=GasReferenceEnergy(host,species,json.loads(args.energy_coordinates.read_text())) if args.energy_coordinates else None
    to_solver=coordinates.to_solver if coordinates else lambda values:values
    to_physical=coordinates.to_physical if coordinates else lambda values:values
    initial=config['initial'];seed=[initial['temperature_k']]*n;inverse_seed=[seed[0]]
    inventory=host.inventories_at_tp_moisture(initial['temperature_k'],initial['total_pressure_pa'],
        initial['moisture_kg_kg_dry'],initial['carrier_mole_fractions'])
    _,point=host.at_temperature(inventory,seed[0])
    point.update(internal_energy_j=point['constitutive_internal_energy_j'],energy_inverse_residual_j=0.)
    y=np.array([[inventory[k] for k in species]+[point['internal_energy_j']]]*n+[[0.]*width]).ravel()
    start_time=config['boundary_program']['values']['knot_times_s'][0]
    if args.resume_from:
        y=np.array(checkpoint['conserved_state']);start_time=checkpoint['time_s']
        seed=checkpoint['temperature_seeds_k'].copy()
    y=to_solver(y)
    base_atol=np.array([policy['inventory_absolute_tolerance_mol']]*len(species)+[policy['energy_absolute_tolerance_j']])
    atol=np.concatenate((np.tile(base_atol/n,n),base_atol))*factor
    sparsity=lil_matrix((len(y),len(y)),dtype=int)
    for i in range(n):
        sparsity[i*width:(i+1)*width,max(0,i-1)*width:min(n,i+2)*width]=1
    sparsity[n*width:,(n-1)*width:n*width]=1

    @lru_cache(maxsize=policy['equilibrium_cache_entries'])
    def cached(values):
        return host.decode(dict(zip(species,values[:-1],strict=True)),values[-1],inverse_seed[0])

    def decode(vector):
        gases=[];states=[]
        for i,values in enumerate(to_physical(vector)[:n*width].reshape(n,width)):
            inverse_seed[0]=seed[i]
            gas,state=cached(tuple(map(float,values)))
            seed[i]=state['temperature_k'];gases.append(gas);states.append(state)
        return gases,states

    def rates(at_time,vector):
        gases,states=decode(vector)
        faces,boundary=model.rates(gases,at_time)
        return faces,states,boundary

    def rhs(at_time,vector):
        faces,_,_=rates(at_time,vector)
        flux=np.array([[p.exchange.net_mol_s[k] for k in species]+[p.energy_out_w] for p in faces])
        derivative=-flux.copy();derivative[1:]+=flux[:-1]
        return to_solver(np.concatenate((derivative.ravel(),flux[-1])))

    def mean_moisture(states):
        return math.fsum(p['moisture_kg_kg_dry'] for p in states)/n

    jacobian=PhysicalColumnJacobian(rhs,n,width,sparsity,atol,json.loads(args.jacobian_parameters.read_text())) if args.jacobian_parameters else None

    knots=config['boundary_program']['values']['knot_times_s']
    obs=config['observation'];target=obs['moisture_target_kg_kg']
    execution=json.loads(args.execution_parameters.read_text()) if args.execution_parameters else None
    stop_time=execution['stop_points_s'][args.stop_at] if args.stop_at else None
    if stop_time is not None and not start_time<stop_time<=knots[-1]:
        raise ValueError('selected stop point must follow restart and lie within the boundary program')
    started=time.monotonic();accepted=checkpoint['accepted_steps'] if args.resume_from else 0
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,default=json_value,allow_nan=False)+'\n');stream.flush()
        input_record={'kind':'input','parameters':config,'cell_parameters':cell_parameters(config,n),
            'geometry':model.geometry(),'cell_count':n,'mesh':args.mesh,'tolerance':args.tolerance,
            'absolute_tolerances':atol.tolist(),'relative_tolerance':policy['relative_tolerance']*factor,
            'scipy_version':scipy.__version__,'water_source':host.fluid.water.source_record,
            'sorption_source':host.excess.record,'thermochemistry':header['thermochemistry'] if args.resume_from else json.loads((root/config['thermochemistry_file']).read_text()),
            'source_policy':'Frozen numeric/source JSON; no code/environment identity claim.',
            'material_qualified':False,'training_eligible':False}
        if args.resume_from:
            stream.writelines(prefix);stream.flush()
            emit({'kind':'resume','time_s':start_time,'parent_trajectory':str(args.resume_from),
                'source_policy':'Original source/parameter JSON restored; original files not reread.',
                'integrator_history':'New BDF history from retained conserved state; not a code/environment snapshot.'})
        else:
            emit(input_record)
            emit({'kind':'initial','time_s':knots[0],'states':[point]*n,'conserved_state':to_physical(y).tolist(),
                  'mean_moisture_kg_kg':mean_moisture([point]*n)})
        if execution is not None:
            emit({'kind':'execution_policy','time_s':start_time,'settings':execution,'selected_stop_point':args.stop_at})
        if coordinates is not None:
            emit({'kind':'solver_coordinate_policy','time_s':start_time,'record':coordinates.record})
        if jacobian is not None:
            emit({'kind':'solver_jacobian_policy','time_s':start_time,'record':jacobian.record})
        for left,right in zip(knots[:-1],knots[1:],strict=True):
            if right<=start_time:
                continue
            segment_start=max(left,start_time)
            segment_end=min(right,stop_time) if stop_time is not None else right
            solver=BDF(rhs,segment_start,y,segment_end,rtol=policy['relative_tolerance']*factor,atol=atol,
                max_step=policy['maximum_step_s'],first_step=policy['initial_step_s'],jac=jacobian,jac_sparsity=sparsity.tocsr())
            samples=np.arange(left+policy['observation_interval_s'],right+policy['observation_interval_s'],policy['observation_interval_s'])
            samples=samples[(samples>segment_start)&(samples<=segment_end)];sample_index=0
            previous_score=mean_moisture(decode(y)[1])-target
            while solver.status=='running':
                previous_time=solver.t;message=solver.step()
                if solver.status=='failed':
                    raise RuntimeError('sorptive column BDF failed: '+str(message))
                accepted+=1;dense=solver.dense_output()
                faces,states,boundary=rates(solver.t,solver.y)
                mean=mean_moisture(states);score=mean-target
                emit({'kind':'accepted','time_s':solver.t,'states':states,'conserved_state':to_physical(solver.y).tolist(),
                    'mean_moisture_kg_kg':mean,'faces':faces,'boundary':boundary,
                    'dense_output':{'start_time_s':previous_time,'end_time_s':solver.t,
                        'shifts_s':dense.t_shift.tolist(),'denominators_s':dense.denom.tolist(),'differences':to_physical(dense.D).tolist()}})
                if (score>0)!=(previous_score>0):
                    event=brentq(lambda t:mean_moisture(decode(dense(t))[1])-target,previous_time,solver.t,
                        xtol=obs['moisture_event_absolute_time_tolerance_s'],rtol=obs['moisture_event_relative_tolerance'],
                        maxiter=obs['moisture_event_maximum_iterations'])
                    vector=dense(event);event_states=decode(vector)[1]
                    emit({'kind':'moisture_event','time_s':event,'moisture_target_kg_kg':target,
                        'transition':'below_target' if score<=0 else 'above_target','states':event_states,
                        'mean_moisture_kg_kg':mean_moisture(event_states),'conserved_state':to_physical(vector).tolist(),
                        'accepted_bracket_s':[previous_time,solver.t]})
                previous_score=score
                while sample_index<len(samples) and samples[sample_index]<=solver.t:
                    t=float(samples[sample_index]);vector=dense(t);sample_states=decode(vector)[1]
                    emit({'kind':'sample','time_s':t,'states':sample_states,'conserved_state':to_physical(vector).tolist(),
                          'mean_moisture_kg_kg':mean_moisture(sample_states)})
                    sample_index+=1
                if accepted%policy['progress_every_accepted_steps']==0:
                    print(json.dumps({'time_s':solver.t,'accepted_steps':accepted,'elapsed_s':time.monotonic()-started,
                        'order':int(solver.order),'segment_function_evaluations':int(solver.nfev),'segment_jacobian_evaluations':int(solver.njev)}),flush=True)
                if stop_requested:
                    break
            y=solver.y.copy()
            if stop_requested or (stop_time is not None and solver.t==stop_time):
                states=decode(y)[1]
                emit({'kind':'checkpoint','time_s':solver.t,'conserved_state':to_physical(y).tolist(),
                    'temperature_seeds_k':[p['temperature_k'] for p in states],'accepted_steps':accepted,
                    'reason':stop_requested if stop_requested else ['selected_stop_point:'+args.stop_at]})
                emit({'kind':'summary','status':'stopped_at_checkpoint','time_s':solver.t,
                    'accepted_steps':accepted,'elapsed_s':time.monotonic()-started})
                print(json.dumps({'status':'stopped_at_checkpoint','time_s':solver.t,'accepted_steps':accepted}),flush=True)
                return
        final=decode(y)[1]
        emit({'kind':'summary','status':'completed','time_s':knots[-1],'final':final,
            'final_mean_moisture_kg_kg':mean_moisture(final),'accepted_steps':accepted,'elapsed_s':time.monotonic()-started})
    print(json.dumps({'status':'completed','accepted_steps':accepted,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':
    main()
