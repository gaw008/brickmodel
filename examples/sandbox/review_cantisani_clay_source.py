"""Literal source consistency and a dimensionally normalized F3 material rate."""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_third_order_dehydroxylation import RecordedThirdOrderDehydroxylation


def caloric(coefficients, t, tref):
    a, b, c, d, e, f = coefficients
    cp = a + b*t + c*t*t + d/t + e/t**2 + f/math.sqrt(t)
    dh = a*(t-tref) + b*(t*t-tref*tref)/2 + c*(t**3-tref**3)/3 + d*math.log(t/tref) + e*(1/tref-1/t) + 2*f*(math.sqrt(t)-math.sqrt(tref))
    ds = a*math.log(t/tref) + b*(t-tref) + c*(t*t-tref*tref)/2 + d*(1/tref-1/t) + e*(1/tref**2-1/t**2)/2 + 2*f*(1/math.sqrt(tref)-1/math.sqrt(t))
    return {'cp_j_mol_k': cp, 'sensible_enthalpy_j_mol': dh, 'relative_entropy_j_mol_k': ds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    source = json.loads((root / settings['source_file']).read_text())
    usgs = json.loads((root / settings['usgs_kaolinite_file']).read_text())
    steam = json.loads((root / settings['usgs_steam_file']).read_text())['phases']['H2O']
    mp.mp.dps = settings['numerical_review']['digits']
    M = lambda value: mp.mpf(str(value))
    tref = settings['reference_temperature_k']
    thermal = []
    for name in ['kaolinite', 'metakaolin']:
        record = source['table1'][name]
        ts = list(settings['cp_review_temperatures_k'])
        if name == 'metakaolin':
            ts += settings['metakaolin_additional_temperatures_k']
        c = record['coefficients']
        a,b,d,e,f,g = map(M, c)
        def independent_cp(t):
            return a+b*t+d*t*t+e/t+f/(t*t)+g/mp.sqrt(t)
        for t in ts:
            computed = caloric(c, t, tref)
            independent = {'cp_j_mol_k': float(independent_cp(M(t))),
                'sensible_enthalpy_j_mol': float(mp.quad(independent_cp, [M(tref), M(t)])),
                'relative_entropy_j_mol_k': float(mp.quad(lambda at: independent_cp(at)/at, [M(tref), M(t)]))}
            thermal.append({'phase': name, 'temperature_k': t, 'calculated': computed,
                'independent': independent,
                'within_source_temperature_interval': record['domain_k'][0] <= t <= record['domain_k'][1],
                'absolute_differences': {key: abs(computed[key]-independent[key]) for key in computed}})
    kaol = usgs['phases']['kaolinite']
    a,b,c,d,e = map(float, kaol['cp_coefficient_strings'])
    usgs_comparison = []
    for t in settings['cp_review_temperatures_k']:
        paper_cp = caloric(source['table1']['kaolinite']['coefficients'], t, tref)['cp_j_mol_k']
        usgs_cp = a+b*t+c/t**2+d/math.sqrt(t)+e*t*t
        usgs_comparison.append({'temperature_k': t, 'paper_cp_j_mol_k': paper_cp,
            'usgs_cp_j_mol_k': usgs_cp, 'relative_difference': (paper_cp-usgs_cp)/usgs_cp})
    # Literal SI volume substitution suffices to show the stated initial
    # volume constraint cannot hold, even before adding quartz or gas.
    volumes = []
    for label, state in [('initial', source['source_initial_condition']), ('inlet', source['source_input_condition'])]:
        t = state['temperature_k'] if label == 'initial' else state['solid_temperature_k']
        occupied = 0.
        phase_volumes = {}
        for name in ['kaolinite', 'metakaolin']:
            v = source['table2'][name]['v1'] + source['table2'][name]['v2'] * t
            occupied += state[name+'_concentration_mol_m3'] * v
            phase_volumes[name] = v
        volumes.append({'condition': label, 'temperature_k': t,
            'literal_molar_volumes_m3_mol': phase_volumes,
            'kaolinite_plus_metakaolin_occupied_volume_fraction': occupied,
            'can_add_nonnegative_quartz_and_gas_volume_to_equal_one': occupied <= 1})
    s = settings['f3_diagnostic']
    kinetic = RecordedThirdOrderDehydroxylation(s['frequency_factor_per_s'], s['activation_energy_j_mol'], s['gas_constant_j_mol_k'])
    rate_rows = []
    for t in s['temperatures_k']:
        for pool in s['formula_unit_pools_mol']:
            for fraction in s['unreacted_fractions']:
                nk = pool*fraction
                nm = pool*(1-fraction)
                rate = kinetic.precursor_consumption_mol_s(t, nk, nm)
                kref = M(s['frequency_factor_per_s']) * mp.exp(-M(s['activation_energy_j_mol']) / (M(s['gas_constant_j_mol_k'])*M(t)))
                reference = float(kref * M(nk)**3 / (M(nk)+M(nm))**2)
                scaling = []
                for factor in s['amount_rescaling_factors']:
                    value = kinetic.precursor_consumption_mol_s(t, factor*nk, factor*nm) / factor
                    scaling.append({'factor': factor, 'rate_back_in_original_amount_unit': value,
                        'absolute_difference_mol_s': abs(value-rate)})
                volumes_rows = []
                for volume in s['volume_representation_m3']:
                    ck,cm = nk/volume,nm/volume
                    volumetric = kinetic.rate_constant_per_s(t)*ck*(ck/(ck+cm))**2
                    volumes_rows.append({'volume_m3': volume, 'volumetric_rate_mol_m3_s': volumetric,
                        'amount_rate_mol_s': volumetric*volume, 'absolute_difference_mol_s': abs(volumetric*volume-rate)})
                max_difference = max(abs(rate-reference), *(r['absolute_difference_mol_s'] for r in scaling), *(r['absolute_difference_mol_s'] for r in volumes_rows))
                allowed = settings['numerical_review']['rate_absolute_mol_s'] + settings['numerical_review']['rate_relative']*abs(reference)
                rate_rows.append({'temperature_k': t, 'precursor_mol': nk, 'product_mol': nm,
                    'rate_mol_s': rate, 'independent_rate_mol_s': reference,
                    'amount_rescaling': scaling, 'concentration_representation': volumes_rows,
                    'maximum_absolute_difference_mol_s': max_difference, 'allowed_difference_mol_s': allowed,
                    'within_numeric_budget': max_difference <= allowed})
    atoms = source['standard_formula']
    elemental = {atom: -atoms['kaolinite_atoms'].get(atom,0)+atoms['metakaolin_atoms'].get(atom,0)+2*atoms['water_atoms'].get(atom,0) for atom in ['Al','Si','O','H']}
    common_domain = [max(source['table1'][name]['domain_k'][0] for name in ['kaolinite','metakaolin']),
                     min(source['table1'][name]['domain_k'][1] for name in ['kaolinite','metakaolin'])]
    reaction_domain = [t+settings['kelvin_offset'] for t in source['source_reaction_temperature_c']]
    dhref = source['table1']['metakaolin']['formation_enthalpy_j_mol'] + 2*float(steam['reference_enthalpy_j_mol']) - source['table1']['kaolinite']['formation_enthalpy_j_mol']
    mapping = {'cp_j_mol_k': 'cp_absolute_j_mol_k', 'sensible_enthalpy_j_mol': 'enthalpy_absolute_j_mol', 'relative_entropy_j_mol_k': 'relative_entropy_absolute_j_mol_k'}
    maxima = {key: max(r['absolute_differences'][key] for r in thermal) for key in mapping}
    summary = {'thermal_records': len(thermal), 'thermal_arithmetic_maximum_differences': maxima,
        'thermal_arithmetic_within_budgets': {key: maxima[key] <= settings['numerical_review'][budget] for key,budget in mapping.items()},
        'f3_amount_records': len(rate_rows), 'all_f3_amount_arithmetic_budgets_met': all(r['within_numeric_budget'] for r in rate_rows),
        'standard_formula_reaction_atom_residuals': elemental,
        'literal_volume_constraints': volumes,
        'common_caloric_domain_k': common_domain, 'paper_reaction_temperature_domain_k': reaction_domain,
        'caloric_and_paper_reaction_temperature_domains_overlap': max(common_domain[0],reaction_domain[0]) <= min(common_domain[1],reaction_domain[1]),
        'printed_enthalpies_plus_borrowed_USGS_steam_reaction_heat_at_reference_j_mol': dhref,
        'reaction_heat_is_qualified_measurement': False,
        'absolute_entropy_or_affinity_qualification': False}
    result = {'settings':settings,'source':source,'thermal':thermal,'usgs_kaolinite_comparison':usgs_comparison,
        'f3_amount_diagnostic':rate_rows,'summary':summary,
        'scope':'Literal source audit and algebraic conversion-to-amount coupling only. No repaired source reactor, qualified thermal mechanism, transient specimen prediction or mineral Gibbs function.',
        'material_qualified':False,'training_eligible':False}
    out = root / settings['output_directory']
    out.mkdir(parents=True, exist_ok=True)
    with (out/'review.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
