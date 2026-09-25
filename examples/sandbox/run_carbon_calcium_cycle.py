"""Record coupled calcite/carbon finite-inventory equilibrium calorimetry."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF
from scipy.optimize import brentq

from carbon_calcium_setup import build


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text())
    equilibrium=json.loads((root/p['equilibrium_parameters']).read_text());model,sources=build(root,equilibrium)
    inventory=next(i for i in equilibrium['inventories'] if i['name']==p['inventory_name'])
    inputs=[inventory[k] for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
    capsule=p['virtual_calorimeter'];g=capsule['heat_conductance_w_k'];program=capsule['program'];policy=p['numerics'];inverse=p['enthalpy_inverse']
    initial=model.at_temperature(capsule['initial_temperature_k'],*inputs);h0=initial['enthalpy_j'];s0=initial['entropy_j_k']
    def decode(y):return model.from_enthalpy(h0+float(y[0]),*inputs,inverse)
    reference=json.loads((root/p['phase_boundary_reference']).read_text())
    boundaries=[row for row in reference['records'] if row['case']['inventory_name']==p['inventory_name']]
    thresholds=[(row['case']['name'],model.at_temperature(float(row['reference_temperature_k']),*inputs)['enthalpy_j']-h0) for row in boundaries]
    factor=1. if args.tolerance=='base' else policy['refinement_factor'];values=np.zeros(4)
    times=np.arange(program[0]['start_s']+policy['observation_interval_s'],program[-1]['end_s']+policy['observation_interval_s'],policy['observation_interval_s'])
    sample=steps=0;started=time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,y,segment):
            state=decode(y);wall=program[segment]['reservoir_temperature_k'];q=g*(wall-state['temperature_k'])
            return {'kind':kind,'time_s':float(t),'segment_index':segment,'values':y.tolist(),'state':state,
                'total_enthalpy_j':h0+float(y[0]),'reservoir_temperature_k':wall,'heat_in_w':q,
                'total_entropy_change_j_k':state['entropy_j_k']-s0+float(y[2]),
                'instantaneous_entropy_production_w_k':q*(1/state['temperature_k']-1/wall)}
        emit({'kind':'input','settings':p,'equilibrium_parameters':equilibrium,'sources':sources,'inventory':inventory,
            'tolerance':args.tolerance,'initial_total_enthalpy_j':h0,'phase_boundary_references':boundaries,
            'phase_event_enthalpy_changes_j':dict(thresholds),'coordinate_definition':['enthalpy_change_from_initial_j','integrated_heat_in_j','reservoir_entropy_change_j_k','integrated_entropy_production_j_k'],
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',program[0]['start_s'],values,0))
        for segment,boundary in enumerate(program):
            wall=boundary['reservoir_temperature_k']
            if segment:emit(record('boundary_transition',boundary['start_s'],values,segment))
            def rates(t,y):
                state=decode(y);temp=state['temperature_k'];q=g*(wall-temp)
                return np.array([q,q,-q/wall,q*(1/temp-1/wall)])
            def jacobian(t,y):
                state=decode(y);temp=state['temperature_k'];slope=g/state['equilibrium_cp_j_k'];matrix=np.zeros((4,4))
                matrix[:,0]=[-slope,-slope,slope/wall,slope*(-wall/temp**2+1/wall)]
                return matrix
            solver=BDF(rates,boundary['start_s'],values,boundary['end_s'],jac=jacobian,
                rtol=policy['relative_tolerance']*factor,atol=np.array(policy['absolute_tolerances_enthalpy_heat_entropy_production'])*factor,
                max_step=policy['maximum_step_s'],first_step=policy['first_step_s'])
            while solver.status=='running':
                before_t,before_y=solver.t,solver.y.copy();message=solver.step()
                if solver.status=='failed':raise RuntimeError(message)
                dense=solver.dense_output();steps+=1;row=record('accepted',solver.t,solver.y,segment)
                row['dense_output']={'start_time_s':before_t,'end_time_s':solver.t,'shifts_s':dense.t_shift.tolist(),
                    'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()};emit(row)
                for name,target in thresholds:
                    if before_y[0]<target<=solver.y[0] or solver.y[0]<=target<before_y[0]:
                        at=brentq(lambda t:dense(t)[0]-target,before_t,solver.t,
                            xtol=policy['event_absolute_time_s'],rtol=policy['event_relative_tolerance'],maxiter=policy['root_maximum_iterations'])
                        event=record('phase_event',at,dense(at),segment)
                        event.update(name=name,direction='heating' if solver.y[0]>before_y[0] else 'cooling',enthalpy_change_target_j=target);emit(event)
                while sample<len(times) and times[sample]<=solver.t:
                    at=float(times[sample]);emit(record('sample',at,dense(at),segment));sample+=1
                if steps%policy['progress_every_steps']==0:print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
            values=solver.y
        emit({'kind':'summary','status':'completed','steps':steps,'elapsed_s':time.monotonic()-started,'final':record('final',program[-1]['end_s'],values,len(program)-1)})
    print(json.dumps({'status':'completed','steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
