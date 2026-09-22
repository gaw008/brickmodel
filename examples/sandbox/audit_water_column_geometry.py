"""Offline reconstruction of nonuniform geometry and sampled face transport.

This is scientific accounting on saved trajectories. Geometry is independently
derived from the recorded root inputs; source caloric expressions reconstruct
face energy. Runtime and scalar reconstructions share the saved state, source
facts, and declared constitutive assumptions, not experimental observations.
"""
import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from audit_water_column_entropy import SourceEntropy
from column_review_geometry import review_geometry
from equilibrium_water_column_setup import build_column
from review_equilibrium_water_column import reconstruct_face_rates
from sludge_sandbox.gas_transport import ideal_gas_state
from water_column_checkpoint import restore_sources


def audit(path, settings, entropy_settings):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    header = rows[0]
    config = header['parameters']
    expected = review_geometry(config, header['cell_count'])
    recorded = header['spatial_geometry']
    source = SourceEntropy(header, entropy_settings)
    geometry_differences = {
        'volume_m3': max(abs(a-b) for a, b in zip(expected['volumes_m3'], recorded['cell_fluid_volumes_m3'], strict=True)),
        'solid_mol': max(abs(a-b) for a, b in zip(expected['solid_amounts_mol'], recorded['cell_solid_amounts_mol'], strict=True)),
        'distance_m': 0., 'conductivity_w_m_k': 0.}
    for a, b in zip(expected['links'], recorded['face_transfers'], strict=True):
        geometry_differences['distance_m'] = max(geometry_differences['distance_m'],
            abs(a['left_distance_m']-b['cell_distance_m']),
            abs(a['right_distance_m']-b['reservoir_distance_m']))
        geometry_differences['conductivity_w_m_k'] = max(geometry_differences['conductivity_w_m_k'],
            abs(a['left_conductivity_w_m_k']-b['cell_conductivity_w_m_k']),
            abs(a['right_conductivity_w_m_k']-b['reservoir_conductivity_w_m_k']))
    maximum_inventory_rate = maximum_energy_rate = maximum_radiation_rate = 0.
    count = 0
    with TemporaryDirectory(prefix='brick-geometry-sources-') as directory:
        directory = Path(directory)
        model = build_column(directory, restore_sources(header, directory), header['cell_count'])
        for row in rows:
            if row['kind'] != 'sample':
                continue
            gases = [ideal_gas_state(p['amounts_mol'], temperature_k=p['temperature_k'],
                gas_volume_m3=p['gas_volume_m3'], molar_masses_kg_mol=config['molar_masses_kg_mol'],
                gas_constant_j_mol_k=source.r) for p in row['states']]
            runtime, runtime_radiation, _, _ = model.rates(gases, row['time_s'])
            independent, independent_radiation = reconstruct_face_rates(config, row['states'],
                row['boundary'], row['surface'], source.ideal, source.r)
            maximum_radiation_rate = max(maximum_radiation_rate, abs(runtime_radiation-independent_radiation))
            for a, b in zip(runtime, independent, strict=True):
                maximum_energy_rate = max(maximum_energy_rate, abs(a.energy_out_w-b['energy_out_w']))
                maximum_inventory_rate = max(maximum_inventory_rate,
                    *(abs(value-b['exchange']['net_mol_s'][key]) for key, value in a.exchange.net_mol_s.items()))
                count += 1
        contrast = None
        if path.name in settings['host_identity_trajectories']:
            original = rows[1]['states'][-1]
            points = []
            for i, host in enumerate(model.hosts):
                _, point = host.decode(original['inventories_mol'], original['internal_energy_j'], original['temperature_k'])
                points.append({'host_index': i, 'temperature_k': point['temperature_k'],
                    'pressure_pa': point['pressure_pa'], 'liquid_water_mol': point['liquid_water_mol'],
                    'energy_inverse_residual_j': point['energy_inverse_residual_j']})
            contrast = {'identical_inventories_mol': original['inventories_mol'],
                'identical_internal_energy_j': original['internal_energy_j'], 'decoded_hosts': points,
                'interpretation': 'Same N/U but different declared volume and ballast are different states; host identity must remain part of any equilibrium cache key.'}
    budgets = settings['comparison_budgets']
    return {'trajectory': str(path), 'completed': rows[-1]['kind'] == 'summary' and rows[-1]['status'] == 'completed',
        'independent_geometry': expected, 'geometry_max_absolute_differences': geometry_differences,
        'roles_match': expected['roles'] == recorded['cell_roles'], 'sampled_face_count': count,
        'max_inventory_rate_difference_mol_s': maximum_inventory_rate,
        'max_energy_rate_difference_w': maximum_energy_rate,
        'max_radiation_rate_difference_w': maximum_radiation_rate,
        'within_face_reconstruction_budgets': maximum_inventory_rate <= budgets['inventory_rate_mol_s'] and
            max(maximum_energy_rate, maximum_radiation_rate) <= budgets['energy_rate_w'],
        'same_conserved_state_different_hosts': contrast}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    entropy = json.loads((root/settings['entropy_parameters_file']).read_text())
    runs = [audit(root/path, settings, entropy) for path in settings['trajectories']]
    result = {'settings': settings, 'runs': runs, 'material_qualified': False,
        'scope': 'Sampled source-formula and geometry reconstruction; no material validation or universal constitutive proof.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'runs': [{k: v for k, v in run.items() if k != 'independent_geometry'} for run in runs]}, indent=2))


if __name__ == '__main__':
    main()
