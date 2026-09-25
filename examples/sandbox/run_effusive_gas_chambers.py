"""Record two finite source-thermochemistry gas chambers joined by effusion."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import scipy
from scipy.integrate import BDF

from calcite_closed_setup import build_closed
from sludge_sandbox.effusive_gas_face import effusive_gas_face
from sludge_sandbox.recorded_ideal_gas_cell import RecordedIdealGasCell


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args();root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text());policy = settings['numerics']
    config = json.loads((root/settings['thermochemistry_parameters']).read_text())
    reaction,nitrogen,affinity,source,facts,nsource = build_closed(root,config)
    phases = {'co2':reaction.phases[reaction.gas_phase],'nitrogen':nitrogen}
    r,p0 = reaction.gas_constant_j_mol_k,reaction.standard_pressure_pa
    face_settings = json.loads((root/settings['face_parameters']).read_text())
    aperture = dict(face_settings['aperture'],area_m2=settings['aperture_area_m2'])
    cells = [RecordedIdealGasCell(phases,r,p0,p['volume_m3'],policy) for p in settings['cells']]
    initial = []
    for cell,condition in zip(cells,settings['cells'],strict=True):
        total = condition['pressure_pa']*cell.volume/(r*condition['temperature_k'])
        carbon = total*condition['co2_fraction'];carrier = total-carbon
        state = cell.at_temperature(carbon,carrier,condition['temperature_k'])
        initial.extend([carbon,carrier,state['internal_energy_j']])
    initial = np.array(initial+[0.]*4)
    def observe(y):
        states = [cell.inventory_state(*y[3*i:3*i+3]) for i,cell in enumerate(cells)]
        return states,effusive_gas_face(*states,aperture,r)
    def rates(t,y):
        _,face = observe(y)
        flux = np.array([face['carbon_flow_mol_s'],face['nitrogen_flow_mol_s'],face['energy_flow_w']])
        return np.concatenate((-flux,flux,flux,[face['entropy_production_w_k']]))
    factor = 1. if args.tolerance=='base' else policy['refinement_factor']
    begin,end = settings['time_interval_s'];started = time.monotonic();steps = index = 0
    times = np.arange(begin+policy['observation_interval_s'],end+policy['observation_interval_s'],policy['observation_interval_s'])
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()
        def record(kind,t,y):
            states,face = observe(y)
            return {'kind':kind,'time_s':float(t),'values':y.tolist(),'states':states,'face':face}
        emit({'kind':'input','settings':settings,'aperture':aperture,'face_settings':face_settings,
            'affinity_parameters':affinity,'source':source,'reference_facts':facts,'nitrogen_source':nsource,
            'tolerance':args.tolerance,'scipy_version':scipy.__version__,'material_qualified':False,'training_eligible':False})
        emit(record('initial',begin,initial))
        solver = BDF(rates,begin,initial,end,rtol=policy['relative_tolerance']*factor,
            atol=np.array(policy['absolute_tolerances'])*factor,first_step=policy['initial_step_s'],max_step=policy['maximum_step_s'])
        while solver.status=='running':
            previous = solver.t;message = solver.step()
            if solver.status=='failed':
                emit({'kind':'integration_failure','time_s':solver.t,'reason':str(message)})
                raise RuntimeError(str(message))
            steps += 1;dense = solver.dense_output();row = record('accepted',solver.t,solver.y)
            row['dense_output'] = {'start_time_s':previous,'end_time_s':solver.t,'shifts_s':dense.t_shift.tolist(),
                'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()};emit(row)
            while index<len(times) and times[index]<=solver.t:
                at = float(times[index]);emit(record('sample',at,dense(at)));index += 1
            if steps%policy['progress_every_steps']==0:
                print(json.dumps({'time_s':solver.t,'accepted_steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
        emit({'kind':'summary','status':'completed','time_s':solver.t,'accepted_steps':steps,
            'elapsed_s':time.monotonic()-started,'final':record('final',solver.t,solver.y)})
    print(json.dumps({'status':'completed','accepted_steps':steps,'elapsed_s':time.monotonic()-started}))


if __name__=='__main__':
    main()
