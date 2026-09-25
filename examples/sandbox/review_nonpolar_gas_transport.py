"""Source arithmetic and reference-table review of dilute-gas transport."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import re
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.nonpolar_gas_transport import NonpolarGasTransport


def source_array(text, name):
    body = re.search(r'double MMCollisionInt::'+name+r'\[[^]]+\]\s*=\s*\{(.*?)\};',
                     text, re.S).group(1)
    return [mp.mpf(v.strip()) for v in body.split(',') if v.strip()]


def lagrange(reduced, temperatures, values):
    # Independent Lagrange form, using the original source decimal strings.
    start = next(i for i, value in enumerate(temperatures) if value > reduced)-1
    nodes = [mp.log(v) for v in temperatures[start:start+3]]
    x = mp.log(reduced)
    return mp.fsum(values[start+i] * mp.fprod(
        (x-nodes[j])/(nodes[i]-nodes[j]) for j in range(3) if j != i)
        for i in range(3))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    mp.mp.dps = p['review']['decimal_precision']
    cpp = (root/p['source_files']['collision_integrals']).read_text()
    gri = (root/p['source_files']['gri30']).read_text()
    nist = json.loads((root/p['source_files']['nist_tables']).read_text())['tables']
    tstar = source_array(cpp, 'tstar22')
    o22 = source_array(cpp, 'omega22_table')[::8]
    astar = source_array(cpp, 'astar_table')[8:-8:8]
    source_flags = {name: [mp.mpf(v) for v in p['collision_tables'][name]] == values
                    for name, values in [('reduced_temperature', tstar),
                                         ('omega22_delta_zero', o22), ('astar_delta_zero', astar)]}
    source_species = {}
    for name, item in p['species'].items():
        block = re.search(r'^- name: '+name+r'\n(.*?)(?=^- name:|\Z)', gri, re.S|re.M).group(1)
        epsilon = mp.mpf(re.search(r'well-depth: (\S+)', block).group(1))
        sigma = mp.mpf(re.search(r'diameter: (\S+)', block).group(1))
        molar_mass = mp.mpf(nist[name]['tables'][0][0][1].split()[-1])
        source_species[name] = (epsilon, sigma*mp.mpf(p['constants']['angstrom_m']),
                               molar_mass*mp.mpf(p['constants']['gram_kg'])
                               / mp.mpf(p['constants']['avogadro_mol_inverse']))
        source_flags[name] = (epsilon == mp.mpf(item['well_depth_over_kb_k'])
                              and sigma == mp.mpf(item['diameter_angstrom'])
                              and molar_mass == mp.mpf(item['molar_mass_g_mol'])
                              and 'dipole:' not in block)
        source_flags[name+'_table_uncertainty'] = (
            mp.mpf(nist[name]['tables'][1][1][-1].rstrip('%'))/100
            == mp.mpf(str(p['review']['nist_uncertainty_fraction'][name])))
    model = NonpolarGasTransport(p)
    kb = mp.mpf(p['constants']['boltzmann_j_k'])
    viscosity_rows, diffusion_rows, table_rows = [], [], []
    for temperature in p['review']['temperatures_k']:
        t = mp.mpf(temperature)
        for name, (epsilon, sigma, mass) in source_species.items():
            omega = lagrange(t/epsilon, tstar, o22)
            reference = 5*mp.sqrt(mp.pi*mass*kb*t)/(16*mp.pi*sigma**2*omega)
            actual = model.viscosity_pa_s(temperature, name)
            error = float(abs(mp.mpf(actual)/reference-1))
            viscosity_rows.append({'species': name, 'temperature_k': temperature,
                'viscosity_pa_s': actual, 'reference_pa_s_decimal': str(reference),
                'relative_arithmetic_error': error,
                'within_arithmetic_budget': error <= p['review']['relative_arithmetic_budget']})
        for left, right in combinations(source_species, 2):
            ea, sa, ma = source_species[left]
            eb, sb, mb = source_species[right]
            reduced = t/mp.sqrt(ea*eb)
            omega11 = lagrange(reduced, tstar, o22)/lagrange(reduced, tstar, astar)
            sigma, mass = (sa+sb)/2, ma*mb/(ma+mb)
            for pressure in p['review']['pressures_pa']:
                reference = 3*kb*t/(16*pressure*sigma**2*omega11)*mp.sqrt(2*kb*t/(mp.pi*mass))
                actual = model.binary_diffusivity_m2_s(temperature, pressure, left, right)
                reverse = model.binary_diffusivity_m2_s(temperature, pressure, right, left)
                first_p = p['review']['pressures_pa'][0]
                first = model.binary_diffusivity_m2_s(temperature, first_p, left, right)
                errors = {'arithmetic': float(abs(mp.mpf(actual)/reference-1)),
                          'symmetry': abs(reverse/actual-1),
                          'pressure_scaling': abs(actual*pressure/(first*first_p)-1)}
                flags = {key: value <= p['review']['relative_'+key+'_budget'] for key, value in errors.items()}
                flags['positive'] = actual > 0
                diffusion_rows.append({'species': [left, right], 'temperature_k': temperature,
                    'pressure_pa': pressure, 'diffusivity_m2_s': actual,
                    'reference_m2_s_decimal': str(reference), 'relative_errors': errors,
                    'within_budgets': flags})
    for name, source in nist.items():
        for row in source['tables'][1][3:]:
            temperature, value = float(row[0]), float(row[-1])
            prediction = model.viscosity_pa_s(temperature, name)/float(p['constants']['micropascal_pa'])
            uncertainty = value*p['review']['nist_uncertainty_fraction'][name]
            rounding = p['review']['nist_rounding_half_unit_micro_pa_s'][name]
            table_rows.append({'species': name, 'temperature_k': temperature,
                'table_micro_pa_s': value, 'model_micro_pa_s': prediction,
                'signed_relative_difference': (prediction-value)/value,
                'table_estimated_uncertainty_micro_pa_s': uncertainty,
                'table_rounding_half_unit_micro_pa_s': rounding,
                'within_table_uncertainty_plus_rounding': abs(prediction-value) <= uncertainty+rounding,
                'source_url': source['url']})
    result = {'settings': p, 'source_inputs_match': source_flags,
        'viscosity': viscosity_rows, 'binary_diffusivity': diffusion_rows,
        'nist_viscosity_comparison': table_rows,
        'all_arithmetic_and_source_budgets_met': all(source_flags.values())
            and all(r['within_arithmetic_budget'] and r['viscosity_pa_s'] > 0 for r in viscosity_rows)
            and all(all(r['within_budgets'].values()) for r in diffusion_rows),
        'all_nist_values_within_reported_uncertainty_plus_rounding':
            all(r['within_table_uncertainty_plus_rounding'] for r in table_rows),
        'pressure_matched_experimental_validation': False,
        'binary_diffusion_experimental_validation': False,
        'material_qualified': False, 'training_eligible': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k.startswith('all_')}), flush=True)


if __name__ == '__main__':
    main()
