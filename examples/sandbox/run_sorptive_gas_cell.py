"""Offline common-gas drying of the explicitly selected sorptive cell.

Evolve O2/N2/total-water/U with equal and opposite external integrals. The
reported moisture crossing is operational, not a zero-water phase transition.
"""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import BDF
from scipy.optimize import brentq

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sorptive_gas_cell_setup import build_sorptive_cell
from run_open_gas_boundary import json_value
from sludge_sandbox.boundary_program import BoundaryProgram, ProgramIdentity
from sludge_sandbox.gas_transport import ideal_gas_reservoir
from sludge_sandbox.open_gas_boundary import GasBoundaryTransfer, open_gas_boundary_rate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--tolerance', required=True, choices=('base','refined'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    config = json.loads(args.parameters.read_text())
    cell = build_sorptive_cell(root,config)
    policy = config['numerics']['implicit']
    factor = 1. if args.tolerance == 'base' else policy['refinement_tolerance_factor']
    program = BoundaryProgram(identity=ProgramIdentity(**config['boundary_program']['identity']),
                              **config['boundary_program']['values'])
    transfer = GasBoundaryTransfer(**config['transfer'])
    species = config['boundary_program']['values']['species_order']
    width = len(species)+1
    initial = config['initial']
    inventory = cell.inventories_at_tp_moisture(initial['temperature_k'],initial['total_pressure_pa'],
        initial['moisture_kg_kg_dry'],initial['carrier_mole_fractions'])
    _, point = cell.at_temperature(inventory,initial['temperature_k'])
    point.update(internal_energy_j=point['constitutive_internal_energy_j'],energy_inverse_residual_j=0.)
    y = np.array([inventory[k] for k in species]+[point['internal_energy_j']]+[0.]*width)
    temperature_seed = [initial['temperature_k']]

    @lru_cache(maxsize=policy['equilibrium_cache_entries'])
    def cached_decode(values):
        return cell.decode(dict(zip(species,values[:-1],strict=True)),values[-1],temperature_seed[0])

    def decode(vector):
        gas, state = cached_decode(tuple(map(float,vector[:width])))
        temperature_seed[0] = state['temperature_k']
        return gas, state

    def rate(vector,at_time):
        gas, state = decode(vector)
        boundary = program.at(float(at_time))
        reservoir = ideal_gas_reservoir(temperature_k=boundary.gas_temperature_k,
            pressure_pa=boundary.total_pressure_pa,mole_fractions=boundary.mole_fractions,
            molar_masses_kg_mol=config['molar_masses_kg_mol'],
            gas_constant_j_mol_k=cell.fluid.thermochemistry.gas_constant_j_mol_k)
        face = open_gas_boundary_rate(gas,reservoir,transfer,cell.fluid.gas_enthalpy_j_mol)
        return face, state, boundary

    def rhs(at_time,vector):
        face,_,_ = rate(vector,at_time)
        outward = np.array([face.exchange.net_mol_s[k] for k in species]+[face.energy_out_w])
        return np.concatenate((-outward,outward))

    atol = np.tile([policy['inventory_absolute_tolerance_mol']]*len(species)+[policy['energy_absolute_tolerance_j']],2)*factor
    knots = config['boundary_program']['values']['knot_times_s']
    step = policy['observation_interval_s']
    target = config['observation']['moisture_target_kg_kg']
    started = time.monotonic()
    accepted = 0
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(row,default=json_value,allow_nan=False)+'\n');stream.flush()
        emit({'kind':'input','parameters':config,'tolerance':args.tolerance,
            'water_source':cell.fluid.water.source_record,'sorption_source':cell.excess.record,
            'thermochemistry':json.loads((root/config['thermochemistry_file']).read_text()),
            'source_policy':'Complete numeric/source JSON snapshots; no code or environment snapshot implied.',
            'material_qualified':False,'training_eligible':False})
        emit({'kind':'initial','time_s':knots[0],'state':point,'conserved_state':y.tolist()})
        for left,right in zip(knots[:-1],knots[1:],strict=True):
            solver=BDF(rhs,left,y,right,rtol=policy['relative_tolerance']*factor,atol=atol,
                max_step=policy['maximum_step_s'],first_step=policy['initial_step_s'])
            sample_times=np.arange(left+step,right+step,step)
            sample_times=sample_times[sample_times<=right]
            sample_index=0
            previous_score=decode(y)[1]['moisture_kg_kg_dry']-target
            while solver.status == 'running':
                previous_time=solver.t
                message=solver.step()
                if solver.status == 'failed':
                    raise RuntimeError('sorptive BDF failed: '+str(message))
                accepted+=1
                dense=solver.dense_output()
                face,state,boundary=rate(solver.y,solver.t)
                emit({'kind':'accepted','time_s':solver.t,'state':state,'conserved_state':solver.y.tolist(),
                    'face':face,'boundary':boundary,'dense_output':{'start_time_s':previous_time,'end_time_s':solver.t,
                    'shifts_s':dense.t_shift.tolist(),'denominators_s':dense.denom.tolist(),'differences':dense.D.tolist()}})
                score=state['moisture_kg_kg_dry']-target
                if (score>0)!=(previous_score>0):
                    event_time=brentq(lambda t:decode(dense(t))[1]['moisture_kg_kg_dry']-target,previous_time,solver.t,
                        xtol=config['observation']['moisture_event_absolute_time_tolerance_s'],
                        rtol=config['observation']['moisture_event_relative_tolerance'],
                        maxiter=config['observation']['moisture_event_maximum_iterations'])
                    event_y=dense(event_time)
                    emit({'kind':'moisture_event','time_s':event_time,'moisture_target_kg_kg':target,
                        'transition':'below_target' if score<=0 else 'above_target',
                        'state':decode(event_y)[1],'conserved_state':event_y.tolist(),
                        'accepted_bracket_s':[previous_time,solver.t]})
                previous_score=score
                while sample_index<len(sample_times) and sample_times[sample_index]<=solver.t:
                    t=float(sample_times[sample_index]);sample_y=dense(t)
                    emit({'kind':'sample','time_s':t,'state':decode(sample_y)[1],'conserved_state':sample_y.tolist()})
                    sample_index+=1
                if accepted%policy['progress_every_accepted_steps']==0:
                    print(json.dumps({'time_s':solver.t,'accepted_steps':accepted,'elapsed_s':time.monotonic()-started}),flush=True)
            y=solver.y.copy()
        emit({'kind':'summary','status':'completed','final':decode(y)[1],
              'accepted_steps':accepted,'elapsed_s':time.monotonic()-started,'time_s':knots[-1]})
    print(json.dumps({'status':'completed','elapsed_s':time.monotonic()-started,'accepted_steps':accepted}))


if __name__ == '__main__':
    main()
