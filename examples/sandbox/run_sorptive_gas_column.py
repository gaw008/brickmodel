"""BDF evolution of a one-dimensional source-sorptive common-gas column.

Cell inventories and U evolve through shared internal faces. Exterior fluxes
are integrated alongside them; no post-step balance correction is applied.
"""
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import scipy
from scipy.integrate import BDF
from scipy.optimize import brentq
from scipy.sparse import lil_matrix

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_open_gas_boundary import json_value
from sorptive_column_setup import build_column,cell_parameters


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--mesh',required=True)
    parser.add_argument('--tolerance',choices=('base','refined'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    config=json.loads(args.parameters.read_text());n=config['numerics']['meshes'][args.mesh]
    model=build_column(root,config,n);host=model.host
    policy=config['numerics']['implicit'];factor=1. if args.tolerance=='base' else policy['refinement_tolerance_factor']
    species=config['boundary_program']['values']['species_order'];width=len(species)+1
    initial=config['initial'];seed=[initial['temperature_k']]*n;inverse_seed=[seed[0]]
    inventory=host.inventories_at_tp_moisture(initial['temperature_k'],initial['total_pressure_pa'],
        initial['moisture_kg_kg_dry'],initial['carrier_mole_fractions'])
    _,point=host.at_temperature(inventory,seed[0])
    point.update(internal_energy_j=point['constitutive_internal_energy_j'],energy_inverse_residual_j=0.)
    y=np.array([[inventory[k] for k in species]+[point['internal_energy_j']]]*n+[[0.]*width]).ravel()
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
        for i,values in enumerate(vector[:n*width].reshape(n,width)):
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
        return np.concatenate((derivative.ravel(),flux[-1]))

    def mean_moisture(states):
        return math.fsum(p['moisture_kg_kg_dry'] for p in states)/n

    knots=config['boundary_program']['values']['knot_times_s']
    obs=config['observation'];target=obs['moisture_target_kg_kg']
    started=time.monotonic();accepted=0
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,default=json_value,allow_nan=False)+'\n');stream.flush()
        emit({'kind':'input','parameters':config,'cell_parameters':cell_parameters(config,n),
            'geometry':model.geometry(),'cell_count':n,'mesh':args.mesh,'tolerance':args.tolerance,
            'absolute_tolerances':atol.tolist(),'relative_tolerance':policy['relative_tolerance']*factor,
            'scipy_version':scipy.__version__,'water_source':host.fluid.water.source_record,
            'sorption_source':host.excess.record,'thermochemistry':json.loads((root/config['thermochemistry_file']).read_text()),
            'source_policy':'Frozen numeric/source JSON; no code/environment identity claim.',
            'material_qualified':False,'training_eligible':False})
        emit({'kind':'initial','time_s':knots[0],'states':[point]*n,'conserved_state':y.tolist(),
              'mean_moisture_kg_kg':mean_moisture([point]*n)})
        for left,right in zip(knots[:-1],knots[1:],strict=True):
            solver=BDF(rhs,left,y,right,rtol=policy['relative_tolerance']*factor,atol=atol,
                max_step=policy['maximum_step_s'],first_step=policy['initial_step_s'],jac_sparsity=sparsity.tocsr())
            samples=np.arange(left+policy['observation_interval_s'],right+policy['observation_interval_s'],policy['observation_interval_s'])
            samples=samples[samples<=right];sample_index=0
            previous_score=mean_moisture(decode(y)[1])-target
            while solver.status=='running':
                previous_time=solver.t;message=solver.step()
                if solver.status=='failed':
                    raise RuntimeError('sorptive column BDF failed: '+str(message))
                accepted+=1;dense=solver.dense_output()
                faces,states,boundary=rates(solver.t,solver.y)
                mean=mean_moisture(states);score=mean-target
                emit({'kind':'accepted','time_s':solver.t,'states':states,'conserved_state':solver.y.tolist(),
                    'mean_moisture_kg_kg':mean,'faces':faces,'boundary':boundary,
                    'dense_output':{'start_time_s':previous_time,'end_time_s':solver.t,
                        'shifts_s':dense.t_shift.tolist(),'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()}})
                if (score>0)!=(previous_score>0):
                    event=brentq(lambda t:mean_moisture(decode(dense(t))[1])-target,previous_time,solver.t,
                        xtol=obs['moisture_event_absolute_time_tolerance_s'],rtol=obs['moisture_event_relative_tolerance'],
                        maxiter=obs['moisture_event_maximum_iterations'])
                    vector=dense(event);event_states=decode(vector)[1]
                    emit({'kind':'moisture_event','time_s':event,'moisture_target_kg_kg':target,
                        'transition':'below_target' if score<=0 else 'above_target','states':event_states,
                        'mean_moisture_kg_kg':mean_moisture(event_states),'conserved_state':vector.tolist(),
                        'accepted_bracket_s':[previous_time,solver.t]})
                previous_score=score
                while sample_index<len(samples) and samples[sample_index]<=solver.t:
                    t=float(samples[sample_index]);vector=dense(t);sample_states=decode(vector)[1]
                    emit({'kind':'sample','time_s':t,'states':sample_states,'conserved_state':vector.tolist(),
                          'mean_moisture_kg_kg':mean_moisture(sample_states)})
                    sample_index+=1
                if accepted%policy['progress_every_accepted_steps']==0:
                    print(json.dumps({'time_s':solver.t,'accepted_steps':accepted,'elapsed_s':time.monotonic()-started}),flush=True)
            y=solver.y.copy()
        final=decode(y)[1]
        emit({'kind':'summary','status':'completed','time_s':knots[-1],'final':final,
            'final_mean_moisture_kg_kg':mean_moisture(final),'accepted_steps':accepted,'elapsed_s':time.monotonic()-started})
    print(json.dumps({'status':'completed','accepted_steps':accepted,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':
    main()
