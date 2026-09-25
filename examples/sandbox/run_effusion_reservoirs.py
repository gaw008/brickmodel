"""Record finite nonisothermal effusion, including both thermostat heat ledgers."""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import BDF

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from sludge_sandbox.molecular_effusion import EffusionGasState, FixedTemperatureEffusionReservoirs
from sludge_sandbox.thermochemistry import load_thermochemistry


def plain(value):
    if isinstance(value, dict):
        return {k:plain(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--tolerance', choices=['base','refined'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    source = json.loads((root/p['source_review_parameters']).read_text())
    pack = json.loads((root/source['thermochemistry_file']).read_text())
    molecular = json.loads((root/source['molecular_constants_file']).read_text())
    masses = [float(molecular['species'][name]['molar_mass_g_mol'])*float(molecular['constants']['gram_kg'])
              for name in source['species_order']]
    gas = EffusionGasState(load_thermochemistry(root/source['thermochemistry_file']),
                          source['species_order'], source['reference_pressure_pa'])
    model = FixedTemperatureEffusionReservoirs(p, gas, masses)
    policy = p['numerics']
    factor = {'base':1.0,'refined':policy['refinement_factor']}[args.tolerance]
    atol = np.array([policy['inventory_absolute_mol']]*2*model.species_count
                    + [policy['heat_absolute_j']]*2 + [policy['entropy_absolute_j_k']])*factor
    times = np.arange(1, round(p['duration_s']/policy['observation_interval_s'])+1)*policy['observation_interval_s']
    started, steps, index = time.monotonic(), 0, 0
    with args.output.open('x') as stream:
        def emit(row):
            stream.write(json.dumps(plain(row),allow_nan=False)+'\n')
            stream.flush()

        def record(kind, at, values):
            states, exchange, heat = model.observe(values)
            return {'kind':kind,'time_s':float(at),'values':values,'states':states,
                    'exchange':exchange,'heat_inputs_w':heat,
                    'thermostat_entropy_j_k':float(-np.dot(values[-3:-1],1/model.temperatures))}

        emit({'kind':'input','settings':p,'source_settings':source,'thermochemistry':pack,
              'molecular_settings':molecular,'molar_masses_kg_mol':masses,
              'relative_tolerance':policy['relative_tolerance']*factor,'absolute_tolerances':atol,
              'material_qualified':False,'training_eligible':False})
        emit(record('initial',0.,model.initial))
        solver = BDF(model.rates,0.,model.initial,p['duration_s'],rtol=policy['relative_tolerance']*factor,
                     atol=atol,first_step=policy['first_step_s'],max_step=policy['maximum_step_s'])
        while solver.status == 'running':
            before = solver.t
            message = solver.step()
            if solver.status == 'failed':
                raise RuntimeError(message)
            dense = solver.dense_output()
            steps += 1
            row = record('accepted',solver.t,solver.y)
            row['dense_output'] = {'start_time_s':before,'end_time_s':solver.t,
                'shifts_s':dense.t_shift,'denominators_s':dense.denom,'differences':dense.D}
            emit(row)
            while index < len(times) and times[index] <= solver.t:
                at = float(times[index]);emit(record('sample',at,dense(at)));index += 1
            if steps % policy['progress_every_steps'] == 0:
                print(json.dumps({'time_s':solver.t,'steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)
        emit({'kind':'summary','status':'completed','steps':steps,'elapsed_s':time.monotonic()-started,
              'final':record('final',solver.t,solver.y)})
    print(json.dumps({'status':'completed','steps':steps,'elapsed_s':time.monotonic()-started}),flush=True)


if __name__ == '__main__':
    main()
