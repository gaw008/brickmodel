"""Record a closed, isobaric, finite-CO2 equilibrium heating and cooling cycle."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF
from scipy.optimize import brentq

from calcite_closed_setup import build_closed
from sludge_sandbox.equilibrium_calcite_closed import ClosedCalciteMixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;config=json.loads(args.parameters.read_text())
    reaction,nitrogen,affinity,source,facts,nsource=build_closed(root,config)
    model=ClosedCalciteMixture(reaction,nitrogen,config,affinity['root']);policy=config['numerics']
    factor=1. if args.tolerance=='base' else policy['refinement_factor']
    initial=model.at_temperature(config['initial_temperature_k'])['enthalpy_j']
    y=np.array([initial,0.,0.,0.]);steps=0;started=time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,values):
            return {'kind':kind,'time_s':float(t),'values':values.tolist(),'state':model.state(float(values[0]))}
        emit({'kind':'input','parameters':config,'affinity_parameters':affinity,'source':source,'reference_facts':facts,
            'nitrogen_source':nsource,'tolerance':args.tolerance,'phase_temperatures_k':model.phase_temperatures,
            'enthalpy_phase_boundaries_j':model.limits,'state_order':['total_H','Q_in','wall_S_loss','heat_production_S'],
            'jacobian_method':'analytic heat derivative and equilibrium heat capacity; zero ledger columns',
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',config['wall_program'][0]['start_s'],y))
        for segment in config['wall_program']:
            wall=segment['temperature_k'];left=segment['start_s'];right=segment['end_s']
            def jacobian(t,v):
                result=np.zeros((len(v),len(v)));result[:,0]=model.enthalpy_rate_derivative(float(v[0]),wall)
                return result
            solver=BDF(lambda t,v:np.array(model.rates(float(v[0]),wall)),left,y,right,
                rtol=policy['relative_tolerance']*factor,atol=np.array(policy['absolute_tolerances'])*factor,
                max_step=policy['maximum_step_s'],first_step=policy['initial_step_s'],jac=jacobian)
            samples=np.arange(left+policy['observation_interval_s'],right+policy['observation_interval_s'],policy['observation_interval_s']);index=0
            while solver.status=='running':
                previous=solver.t;previous_h=solver.y[0];message=solver.step()
                if solver.status=='failed':raise RuntimeError('closed mixture BDF failed: '+str(message))
                steps+=1;dense=solver.dense_output();row=record('accepted',solver.t,solver.y)
                row.update(wall_temperature_k=wall,dense_output={'start_time_s':previous,'end_time_s':solver.t,
                    'shifts_s':dense.t_shift.tolist(),'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()})
                emit(row)
                for boundary in model.limits:
                    if (previous_h>boundary)!=(solver.y[0]>boundary):
                        event=brentq(lambda t:float(dense(t)[0])-boundary,previous,solver.t,
                            xtol=policy['event_absolute_time_s'],rtol=policy['event_relative_tolerance'],maxiter=policy['event_iterations'])
                        row=record('phase_event',event,dense(event));row.update(boundary_enthalpy_j=boundary,
                            direction='heating' if solver.y[0]>previous_h else 'cooling')
                        emit(row)
                while index<len(samples) and samples[index]<=solver.t:
                    at=float(samples[index]);emit(record('sample',at,dense(at)));index+=1
                if steps%policy['progress_every_steps']==0:
                    print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
            y=solver.y.copy()
        emit({'kind':'summary','status':'completed','final':model.state(float(y[0])),'values':y.tolist(),
            'accepted_steps':steps,'elapsed_s':time.monotonic()-started})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
