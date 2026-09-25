"""Temperature-coordinate rigid calorimetry with an independent heat ledger."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF
from scipy.optimize import brentq

from carbon_calcium_pressure_setup import build


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent;p=json.loads(args.parameters.read_text())
    rigid=json.loads((root/p['rigid_parameters']).read_text())
    pressure=json.loads((root/rigid['pressure_parameters']).read_text());model,sources,_=build(root,pressure)
    inventory=next(i for i in pressure['inventories'] if i['name']==p['inventory_name'])
    inputs=[inventory[k] for k in ['calcium_atoms_mol','carbon_atoms_mol','oxygen_atoms_mol','nitrogen_molecules_mol']]
    volume=rigid['virtual_volume_m3'];policy=p['numerics'];capsule=p['virtual_calorimeter']
    program=capsule['program'];g=capsule['heat_conductance_w_k']
    def decode(y):return model.at_temperature_volume(float(y[0]),volume,*inputs,rigid['numerics'])
    values=np.array([capsule['initial_temperature_k'],0.,0.,0.]);initial=decode(values)
    u0,s0=initial['internal_energy_j'],initial['entropy_j_k']
    reference=json.loads((root/p['phase_boundary_reference']).read_text())
    boundaries=[r for r in reference['records'] if r['case']['inventory_name']==p['inventory_name']]
    thresholds=[(r['case']['name'],float(r['reference_temperature_k'])) for r in boundaries]
    factor=1. if args.tolerance=='base' else policy['refinement_factor']
    times=np.arange(program[0]['start_s']+policy['observation_interval_s'],program[-1]['end_s']+policy['observation_interval_s'],policy['observation_interval_s'])
    sparsity=np.zeros((4,4));sparsity[:,0]=1
    sample=steps=0;started=time.monotonic()
    with args.output.open('x') as stream:
        def emit(row):stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,y,segment):
            state=decode(y);wall=program[segment]['reservoir_temperature_k'];q=g*(wall-state['temperature_k'])
            return {'kind':kind,'time_s':float(t),'segment_index':segment,'values':y.tolist(),'state':state,
                'internal_energy_change_j':state['internal_energy_j']-u0,'reservoir_temperature_k':wall,'heat_in_w':q,
                'total_entropy_change_j_k':state['entropy_j_k']-s0+float(y[2]),
                'instantaneous_entropy_production_w_k':q*(1/state['temperature_k']-1/wall)}
        emit({'kind':'input','settings':p,'rigid_parameters':rigid,'pressure_parameters':pressure,'sources':sources,
            'inventory':inventory,'tolerance':args.tolerance,'phase_boundary_references':boundaries,
            'initial_internal_energy_j':u0,'coordinate_definition':['temperature_k','integrated_heat_in_j','reservoir_entropy_change_j_k','integrated_entropy_production_j_k'],
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',program[0]['start_s'],values,0))
        for segment,boundary in enumerate(program):
            wall=boundary['reservoir_temperature_k']
            if segment:emit(record('boundary_transition',boundary['start_s'],values,segment))
            def rates(t,y):
                state=decode(y);temp=state['temperature_k'];q=g*(wall-temp)
                return np.array([q/state['equilibrium_cv_j_k'],q,-q/wall,q*(1/temp-1/wall)])
            solver=BDF(rates,boundary['start_s'],values,boundary['end_s'],jac_sparsity=sparsity,
                rtol=policy['relative_tolerance']*factor,atol=np.array(policy['absolute_tolerances_temperature_heat_entropy_production'])*factor,
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
                        event.update(name=name,direction='heating' if solver.y[0]>before_y[0] else 'cooling');emit(event)
                while sample<len(times) and times[sample]<=solver.t:
                    at=float(times[sample]);emit(record('sample',at,dense(at),segment));sample+=1
                if steps%policy['progress_every_steps']==0:print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
            values=solver.y
        emit({'kind':'summary','status':'completed','steps':steps,'elapsed_s':time.monotonic()-started,
            'final':record('final',program[-1]['end_s'],values,len(program)-1)})
    print(json.dumps({'status':'completed','steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':main()
