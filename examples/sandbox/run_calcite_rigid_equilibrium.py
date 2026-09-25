"""Record a heat-driven closed rigid reactive capsule and its phase crossings."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF
from scipy.optimize import brentq

from calcite_rigid_setup import build_rigid
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture


def phase_boundaries(model,carbon,policy):
    records=[];tlo,thi=model.domain
    amounts=[('lime',carbon)]
    if carbon>model.calcium:amounts.insert(0,('calcite',carbon-model.calcium))
    for name,g in amounts:
        ends=[model.reaction_potential(t,carbon,g) for t in (tlo,thi)]
        row={'pure_phase':name,'co2_mol':g,'temperature_bracket_k':[tlo,thi],'reaction_gibbs_at_bracket_j_mol':ends,
            'boundary_in_selected_temperature_domain':ends[0]*ends[1]<=0}
        if row['boundary_in_selected_temperature_domain']:
            t=brentq(lambda t:model.reaction_potential(t,carbon,g),tlo,thi,xtol=policy['absolute_tolerance_k'],
                rtol=policy['relative_tolerance'],maxiter=policy['maximum_iterations'])
            row.update(temperature_k=t,internal_energy_j=model.at_temperature(t,carbon)['internal_energy_j'])
        records.append(row)
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;config=json.loads(args.parameters.read_text())
    reaction,nitrogen,affinity,source,facts,nsource,volume=build_rigid(root,config)
    model=RigidCalciteMixture(reaction,nitrogen,volume,config,config['cell']);c=config['initial_carbon_mol'];policy=config['numerics']
    boundaries=phase_boundaries(model,c,affinity['root']);factor=1. if args.tolerance=='base' else policy['refinement_factor']
    y=np.array([model.at_temperature(config['initial_temperature_k'],c)['internal_energy_j'],0.,0.,0.]);steps=0;started=time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,values):return {'kind':kind,'time_s':float(t),'values':values.tolist(),'state':model.state(c,float(values[0]))}
        emit({'kind':'input','parameters':config,'affinity_parameters':affinity,'source':source,'reference_facts':facts,
            'nitrogen_source':nsource,'volume_source':volume,'tolerance':args.tolerance,'phase_boundaries':boundaries,
            'state_order':['total_U','Q_in','wall_S_loss','heat_production_S'],'jacobian_method':'analytic thermal feedback using equilibrium Cv',
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',config['wall_program'][0]['start_s'],y))
        for segment in config['wall_program']:
            wall=segment['temperature_k'];left=segment['start_s'];right=segment['end_s']
            def jacobian(t,v):
                out=np.zeros((len(v),len(v)));out[:,0]=model.energy_rate_derivative(c,float(v[0]),wall)
                return out
            solver=BDF(lambda t,v:np.array(model.rates(c,float(v[0]),wall)),left,y,right,
                rtol=policy['relative_tolerance']*factor,atol=np.array(policy['absolute_tolerances'])*factor,
                first_step=policy['initial_step_s'],max_step=policy['maximum_step_s'],jac=jacobian)
            samples=np.arange(left+policy['observation_interval_s'],right+policy['observation_interval_s'],policy['observation_interval_s']);index=0
            while solver.status=='running':
                previous=solver.t;previous_u=solver.y[0];message=solver.step()
                if solver.status=='failed':raise RuntimeError('rigid equilibrium BDF failed: '+str(message))
                steps+=1;dense=solver.dense_output();row=record('accepted',solver.t,solver.y)
                row.update(wall_temperature_k=wall,dense_output={'start_time_s':previous,'end_time_s':solver.t,
                    'shifts_s':dense.t_shift.tolist(),'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()});emit(row)
                for boundary in boundaries:
                    if not boundary['boundary_in_selected_temperature_domain']:continue
                    u=boundary['internal_energy_j']
                    if (previous_u>u)!=(solver.y[0]>u):
                        at=brentq(lambda t:float(dense(t)[0])-u,previous,solver.t,xtol=policy['event_absolute_time_s'],
                            rtol=policy['event_relative_tolerance'],maxiter=policy['event_iterations'])
                        row=record('phase_event',at,dense(at));row.update(boundary=boundary,direction='heating' if solver.y[0]>previous_u else 'cooling');emit(row)
                while index<len(samples) and samples[index]<=solver.t:
                    at=float(samples[index]);emit(record('sample',at,dense(at)));index+=1
                if steps%policy['progress_every_steps']==0:
                    print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
            y=solver.y.copy()
        emit({'kind':'summary','status':'completed','final':model.state(c,float(y[0])),'values':y.tolist(),
            'accepted_steps':steps,'elapsed_s':time.monotonic()-started})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
