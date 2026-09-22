"""Read saved trajectories and report physical balances without running a host.

Fraction arithmetic separates floating-point projection from conservation.
Saved liquid properties are reused: this does not independently evaluate the
liquid EOS, certify the entire domain, or supply experimental accuracy.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path


def exact(value):
    if isinstance(value, dict):
        return Fraction(value['numerator'], value['denominator'])
    return Fraction(value)


def summarize(path):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    metadata = records[0]
    config = metadata['parameters']
    thermo = metadata['thermochemistry']
    r = thermo['gas_constant']['value_j_mol_k']
    initial = records[1]['state']
    previous = initial
    steps = [item for item in records if item['kind'] == 'step']
    maxima = {key: 0. for key in ('corrected_inventory_mol', 'corrected_energy_j',
        'unadjusted_inventory_mol', 'unadjusted_energy_j', 'phase_water_sum_mol',
        'energy_constitutive_j', 'volume_closure_m3', 'mechanical_closure_pa',
        'wet_chemical_gap_j_mol')}
    phase_values = {'liquid_mol': [], 'gas_water_mol': [], 'vapor_chemical_gap_j_mol': [],
                    'dry_chemical_gap_j_mol': [], 'internal_evaporation_mol': []}
    dry_times = []
    wet_times = []

    def keep(key, value):
        maxima[key] = max(maxima[key], abs(float(value)))

    for item in steps:
        state, update = item['state'], item['update']
        for species, amount in state['inventories_mol'].items():
            residual = exact(amount)-exact(previous['inventories_mol'][species])+exact(
                update['outward_amounts_mol'][species])
            keep('unadjusted_inventory_mol', residual)
            keep('corrected_inventory_mol', residual-exact(update['amount_projection_mol'][species]))
        energy = exact(state['internal_energy_j'])-exact(previous['internal_energy_j'])+exact(
            update['outward_energy_j'])
        keep('unadjusted_energy_j', energy)
        keep('corrected_energy_j', energy-exact(update['energy_projection_j']))
        phase_values['internal_evaporation_mol'].append(item['internal_evaporation_mol'])
        for point in (item['midpoint'], state):
            liquid = exact(point['liquid_water_mol'])
            gas_water = exact(point['amounts_mol']['H2O'])
            keep('phase_water_sum_mol', liquid+gas_water-exact(point['inventories_mol']['H2O']))
            u = liquid*exact(point['liquid_molar_u_j_mol'])+sum(
                exact(n)*exact(point['gas_molar_u_j_mol'][k]) for k, n in point['amounts_mol'].items())
            keep('energy_constitutive_j', u-exact(point['internal_energy_j']))
            keep('volume_closure_m3', exact(point['liquid_volume_m3'])+exact(
                point['gas_volume_m3'])-exact(config['storage']['available_fluid_volume_m3']))
            pressure = sum(exact(n) for n in point['amounts_mol'].values())*exact(r)*exact(
                point['temperature_k'])/exact(point['gas_volume_m3'])
            keep('mechanical_closure_pa', pressure-exact(point['liquid_pressure_pa']))
            # Recompute chemical potentials from saved h/u/s, not saved mu.
            t = point['temperature_k']
            mu_liquid = point['liquid_molar_h_j_mol']-t*point['liquid_molar_s_j_mol_k']
            p_water = float(gas_water)*r*t/point['gas_volume_m3']
            mu_vapor = point['gas_molar_u_j_mol']['H2O']+r*t-t*(
                point['vapor_standard_s_j_mol_k']-r*math.log(
                    p_water/config['storage']['reference_pressure_pa']))
            gap = mu_vapor-mu_liquid
            phase_values['liquid_mol'].append(float(liquid))
            phase_values['gas_water_mol'].append(float(gas_water))
            phase_values['vapor_chemical_gap_j_mol'].append(gap)
            if point['phase'] == 'liquid_vapor':
                keep('wet_chemical_gap_j_mol', gap)
            else:
                phase_values['dry_chemical_gap_j_mol'].append(gap)
        time = float(exact(item['time_s']))
        (wet_times if state['phase'] == 'liquid_vapor' else dry_times).append(time)
        previous = state

    return {'file': path.name, 'case': metadata['case'],
            'completion_record': records[-1]['kind'], 'steps': len(steps),
            'corrected_balance_count': len(steps)*(len(initial['inventories_mol'])+1),
            'initial': initial, 'final': previous, 'max_absolute_residuals': maxima,
            'ranges': {k: {'min': min(v), 'max': max(v)} if v else None for k, v in phase_values.items()},
            'liquid_depletion_sample_bracket_s': (
                [max(t for t in [0., *wet_times] if t < dry_times[0]), dry_times[0]]
                if dry_times and initial['liquid_water_mol'] > 0 else None)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    results = [summarize(p) for p in sorted(args.directory.glob('*.jsonl'))
               if p.name != 'calorimetry.jsonl']
    refinement = {}
    for case in ('evaporation', 'liquid_depletion'):
        rows = sorted((row for row in results if row['case'] == case), key=lambda row: row['steps'])
        if len(rows) >= 3:
            selected = rows[-3:]
            refinement[case] = {'steps': [row['steps'] for row in selected], 'fields': {}}
            for field in ('temperature_k', 'pressure_pa', 'liquid_water_mol'):
                values = [row['final'][field] for row in selected]
                differences = [abs(values[i]-values[i+1]) for i in range(2)]
                refinement[case]['fields'][field] = {
                    'final_values': values, 'absolute_differences': differences,
                    'difference_ratio': differences[0]/differences[1] if differences[1] else None}
    document = {'scope': 'saved-record arithmetic, not independent EOS or real-material validation',
                'runs': results, 'time_refinement': refinement,
                'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'runs': len(results), 'steps': sum(row['steps'] for row in results),
                      'corrected_balances': sum(row['corrected_balance_count'] for row in results)}))


if __name__ == '__main__':
    main()
