"""Heat-driven decomposition and recarbonation in the specified equilibrium limit."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF
from scipy.optimize import brentq

from calcite_affinity_setup import build
from sludge_sandbox.equilibrium_calcite_calorimeter import EquilibriumCalciteCalorimeter


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;config=json.loads(args.parameters.read_text())
    affinity=json.loads((root/config['affinity_parameters']).read_text());reaction,source,facts=build(root,affinity)
    model=EquilibriumCalciteCalorimeter(reaction,config,affinity['root']);policy=config['numerics']
    factor=1. if args.tolerance=='base' else policy['refinement_factor']
    initial=model.amount*model.reactant.standard(config['initial_temperature_k'])['enthalpy_j_mol']
    y=np.array([initial,0.,0.,0.,0.,0.,0.]);steps=0;started=time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def state_record(kind,at_time,values):
            return {'kind':kind,'time_s':float(at_time),'values':values.tolist(),'state':model.state(float(values[0]))}
        emit({'kind':'input','parameters':config,'affinity_parameters':affinity,'source':source,'reference_facts':facts,
            'tolerance':args.tolerance,'equilibrium_temperature_k':model.equilibrium_temperature,
            'jacobian_method':'analytic single feedback H column; exact zero ledger columns; branchwise derivative',
            'enthalpy_phase_boundaries_j':model.limits,'state_order':['solid_H','CO2_out','Q_in','CO2_H_out','wall_S_loss','CO2_S_out','heat_production_S'],
            'material_qualified':False,'training_eligible':False})
        emit(state_record('initial',config['wall_program'][0]['start_s'],y))
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
                if solver.status=='failed':
                    raise RuntimeError('calorimeter BDF failed: '+str(message))
                steps+=1;dense=solver.dense_output()
                record=state_record('accepted',solver.t,solver.y)
                record.update(wall_temperature_k=wall,dense_output={'start_time_s':previous,'end_time_s':solver.t,
                    'shifts_s':dense.t_shift.tolist(),'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()})
                emit(record)
                for boundary in model.limits:
                    if (previous_h>boundary)!=(solver.y[0]>boundary):
                        event=brentq(lambda t:float(dense(t)[0])-boundary,previous,solver.t,
                            xtol=policy['event_absolute_time_s'],rtol=policy['event_relative_tolerance'],maxiter=policy['event_iterations'])
                        record=state_record('phase_event',event,dense(event));record.update(boundary_enthalpy_j=boundary,
                            direction='heating' if solver.y[0]>previous_h else 'cooling')
                        emit(record)
                while index<len(samples) and samples[index]<=solver.t:
                    t=float(samples[index]);emit(state_record('sample',t,dense(t)));index+=1
                if steps%policy['progress_every_steps']==0:
                    print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
            y=solver.y.copy()
        emit({'kind':'summary','status':'completed','final':model.state(float(y[0])),'values':y.tolist(),
            'accepted_steps':steps,'elapsed_s':time.monotonic()-started})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':
    main()
