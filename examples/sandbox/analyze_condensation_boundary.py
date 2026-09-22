"""Compare saved condensation profiles at an exact common programme time.

No physical coefficients are inferred. A partial trajectory can supply this
snapshot but cannot qualify the full cycle or its unobserved phase events.
"""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    results = []
    for name, relative in settings['trajectories'].items():
        rows = [json.loads(line) for line in (root/relative).read_text().splitlines()]
        header = rows[0]
        row = next(r for r in rows if r['kind'] == 'sample' and r['time_s'] == settings['time_s'])
        states = row['states']
        count = len(states)
        volume = header['cell_fluid_volume_m3']
        total_liquid = sum(s['liquid_water_mol'] for s in states)
        cells = []
        for i, state in enumerate(states):
            rt = state['pressure_pa']*state['gas_volume_m3']/sum(state['amounts_mol'].values())
            cells.append({'cell': i, 'center_fraction_of_length': (i+.5)/count,
                'temperature_k': state['temperature_k'], 'pressure_pa': state['pressure_pa'],
                'liquid_mol': state['liquid_water_mol'],
                'liquid_concentration_mol_m3': state['liquid_water_mol']/volume,
                'liquid_volume_fraction': state['liquid_volume_m3']/volume,
                'all_vapor_candidate_pressure_pa': sum(state['inventories_mol'].values())*rt/volume})
        boundary_regions = []
        for fraction in settings['boundary_region_fractions']:
            region = cells[count-round(count*fraction):]
            amount = sum(c['liquid_mol'] for c in region)
            boundary_regions.append({'length_fraction': fraction, 'cells': len(region),
                'liquid_mol': amount, 'share_of_total_liquid': amount/total_liquid})
        results.append({'name': name, 'trajectory': relative, 'cell_count': count,
            'snapshot_time_s': row['time_s'],
            'full_trajectory_completed': rows[-1]['kind'] == 'summary' and rows[-1]['status'] == 'completed',
            'surface_temperature_k': row['surface']['temperature_k'],
            'total_liquid_mol': total_liquid,
            'last_cell_share_of_liquid': cells[-1]['liquid_mol']/total_liquid,
            'boundary_regions': boundary_regions, 'cells': cells})
    output = {'settings': settings, 'results': results,
        'qualification': 'Exact saved snapshot comparison; no extrapolation, constitutive inference, continuum-limit proof, or material qualification.'}
    with args.output.open('x') as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps([{k: v for k, v in r.items() if k not in ('cells', 'boundary_regions')}
                      for r in results], indent=2))


if __name__ == '__main__':
    main()
