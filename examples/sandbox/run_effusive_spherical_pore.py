"""Record finite gas transfer, pore motion, two temperatures and shared ledgers."""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.integrate import BDF

from effusive_pore_setup import build


def decode(model,p,case,values,segment):
    a0 = p['model']['reference_radius_m']
    ts,ns = (p['normalization'][k] for k in ['temperature_k','amount_mol'])
    return model.at_state(a0*float(values[0]),ts*float(values[1]),ts*float(values[2]),
                          ns*float(values[3]),ns*float(values[4]),case['segments'][segment])


def physical_rates(state):
    flow = state['gas_transfer_mol_s']
    return np.array([state['radius_rate_m_s'],state['pore_temperature_rate_k_s'],
        state['reservoir_temperature_rate_k_s'],-flow,flow,state['external_work_in_w'],
        state['pore_heat_in_w'],state['reservoir_heat_in_w'],state['effusive_energy_w'],
        state['viscous_dissipation_w'],state['bath_entropy_rate_w_k'],state['entropy_production_w_k']])


def scales(p):
    n = p['normalization']; return np.array([p['model']['reference_radius_m'],
        n['temperature_k'],n['temperature_k'],n['amount_mol'],n['amount_mol'],
        *[n['energy_j']]*5,*[n['entropy_j_k']]*2])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--case',required=True)
    parser.add_argument('--tolerance',choices=['base','refined'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(); p = json.loads(args.parameters.read_text())
    model,sources = build(args.parameters.resolve().parent,p); case = p['cases'][args.case]
    policy = p['numerics']; scale = scales(p)
    factor = 1. if args.tolerance=='base' else policy['refinement_factor']
    a0 = p['model']['reference_radius_m']
    volumes = [4*math.pi*a0**3/3,p['reservoir']['volume_m3']]
    amounts = [pressure*volume/(model.r*temperature) for pressure,volume,temperature in
               zip(case['initial_pressures_pa'],volumes,case['initial_temperatures_k'],strict=True)]
    values = np.array([a0,*case['initial_temperatures_k'],*amounts,*[0.]*7])/scale
    initial = decode(model,p,case,values,0)
    duration = case['segments'][-1]['end_time_s']
    times = np.arange(1,round(duration/policy['observation_interval_s'])+1)*policy['observation_interval_s']
    started,steps,index,start = time.monotonic(),0,0,0.
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush()

        def record(kind,at,y,segment):
            state = decode(model,p,case,y,segment); physical = y*scale
            return {'kind':kind,'time_s':float(at),'segment_index':segment,'values':y.tolist(),'state':state,
                'amount_balance_mol':float(physical[3]+physical[4]-sum(amounts)),
                'energy_balance_j':float(state['internal_energy_j']-initial['internal_energy_j']-sum(physical[5:8])),
                'entropy_balance_j_k':float(state['entropy_j_k']-initial['entropy_j_k']+physical[10]-physical[11])}

        emit({'kind':'input','settings':p,'sources':sources,'case_name':args.case,'case':case,
            'tolerance':args.tolerance,'coordinate_order':['radius_ratio','pore_temperature','reservoir_temperature',
                'pore_amount','reservoir_amount','external_work','pore_heat','reservoir_heat','effusive_energy',
                'viscous_dissipation','bath_entropy','entropy_production'],'coordinate_scales':scale.tolist(),
            'material_qualified':False,'training_eligible':False})
        emit(record('initial',0.,values,0))
        for segment,boundary in enumerate(case['segments']):
            if segment:emit(record('boundary_transition',start,values,segment))
            def rates(at,y):
                return physical_rates(decode(model,p,case,y,segment))/scale
            solver = BDF(rates,start,values,boundary['end_time_s'],
                rtol=policy['relative_tolerance']*factor,
                atol=np.array(policy['absolute_tolerances_normalized'])*factor,
                first_step=policy['first_step_s'],max_step=policy['maximum_step_s'])
            while solver.status=='running':
                before = solver.t; message = solver.step()
                if solver.status=='failed':raise RuntimeError(message)
                dense = solver.dense_output();steps+=1
                row = record('accepted',solver.t,solver.y,segment)
                row['dense_output'] = {'start_time_s':before,'end_time_s':solver.t,
                    'shifts_s':dense.t_shift.tolist(),'denominators_s':dense.denom.tolist(),
                    'differences':dense.D.tolist()}
                emit(row)
                while index<len(times) and times[index]<=solver.t:
                    at = float(times[index]);emit(record('sample',at,dense(at),segment));index+=1
                if steps%policy['progress_every_steps']==0:
                    print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
            values,start = solver.y,boundary['end_time_s']
        emit({'kind':'summary','status':'completed','steps':steps,'elapsed_s':time.monotonic()-started,
              'final':record('final',duration,values,len(case['segments'])-1)})
    print(json.dumps({'status':'completed','steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)


if __name__ == '__main__':
    main()
