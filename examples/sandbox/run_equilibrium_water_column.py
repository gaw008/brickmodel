"""Offline shared-face channel, solid heat storage, and programmed boundary."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--mesh', required=True)
    parser.add_argument('--resolution', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    config = json.loads(args.parameters.read_text())
    sys.path.insert(0, str(root/'src'))
    sys.path.insert(0, str(root/'examples'/'sandbox'))
    from run_open_gas_boundary import json_value
    from equilibrium_water_column_setup import build_column
    from sludge_sandbox.equilibrium_water_column import apply_column_rates

    start = time.monotonic()
    count = config['numerics']['meshes'][args.mesh]
    model = build_column(root, config, count)
    rates = model.rates
    water, solid = model.water, model.solid
    steps_each_segment = config['numerics']['steps_per_segment'][args.resolution]

    def decode(updates, previous):
        values = [model.host_for_cell(i).decode(item['inventories_mol'], item['internal_energy_j'], point['temperature_k'])
                  for i, (item, point) in enumerate(zip(updates, previous, strict=True))]
        return [item[0] for item in values], [item[1] for item in values]

    with args.output.open('x') as stream:
        def emit(record):
            stream.write(json.dumps(record, default=json_value, allow_nan=False)+'\n')
            stream.flush()

        emit({'kind': 'input', 'parameters': config, 'mesh': args.mesh, 'resolution': args.resolution,
              'cell_count': count,
              **({'cell_fluid_volume_m3': model.volumes[0]} if config['schema'] == 'equilibrium_water_column_v1' else {}),
              'spatial_geometry': model.record_geometry(), 'water_source': water.source_record,
              'solid_source_facts': solid, 'thermochemistry': json.loads((root/config['thermochemistry_file']).read_text()),
              'method': 'shared-face explicit midpoint, knot-aligned steps, warm secant equilibrium decode',
              'material_qualified': False, 'training_eligible': False})
        initial = config['initial']
        gases, points = [], []
        for i in range(count):
            inventories = {k: value*model.volumes[i] for k, value in initial['total_concentrations_mol_m3'].items()}
            gas, point = model.host_for_cell(i).at_temperature(inventories, initial['temperature_k'])
            point.update(internal_energy_j=point['constitutive_internal_energy_j'], energy_inverse_residual_j=0.)
            gases.append(gas)
            points.append(point)
        emit({'kind': 'initial', 'time_s': 0, 'states': points})
        index = 0
        times = [Fraction(t) for t in config['boundary_program']['values']['knot_times_s']]
        for segment, (left, right) in enumerate(zip(times[:-1], times[1:], strict=True)):
            step = (right-left)/steps_each_segment[segment]
            for number in range(steps_each_segment[segment]):
                time_s = left+number*step
                face0, rad0, _, _ = rates(gases, time_s)
                predictor, _ = apply_column_rates(points, face0, step/2, rad0)
                middle_gases, middle_points = decode(predictor, points)
                faces, rad, boundary, surface_point = rates(middle_gases, time_s+step/2)
                updates, ledger = apply_column_rates(points, faces, step, rad)
                gases, points = decode(updates, middle_points)
                index += 1
                emit({'kind': 'step', 'index': index, 'segment': segment, 'time_s': time_s+step,
                      'states': points, 'midpoint_states': middle_points,
                      'updates': updates, 'ledger': ledger, 'rates': faces,
                      'surface_radiation_out_w': rad, 'boundary_midpoint': boundary,
                      'surface_midpoint': surface_point})
        emit({'kind': 'summary', 'status': 'completed', 'steps': index, 'final': points,
              'elapsed_s': time.monotonic()-start,
              'material_qualified': False, 'training_eligible': False})
    print(json.dumps({'status': 'completed', 'cells': count, 'steps': index,
                      'elapsed_s': time.monotonic()-start,
                      'temperatures_k': [p['temperature_k'] for p in points],
                      'liquid_mol': [p['liquid_water_mol'] for p in points]}))


if __name__ == '__main__':
    main()
