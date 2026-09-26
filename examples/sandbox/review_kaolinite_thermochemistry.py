"""Reconstruct selected USGS clay/crystalline-product thermochemistry.

This is a source and thermodynamic calculation, not a heating simulation or
experimental validation. Crystalline-product affinities do not describe the
metastable metakaolin pathway or its kinetics.
"""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase
from sludge_sandbox.recorded_gas_reactions import standard_reaction
from review_carbon_gas_thermochemistry import cp_certificate
from review_hydrogen_steam_thermochemistry import thermal, rounding, half_printed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    source = json.loads((root / p['source_file']).read_text())
    steam = json.loads((root / p['steam_source_file']).read_text())
    mp.mp.dps = p['decimal_digits']
    t0 = mp.mpf(source['reference_temperature_k'])
    r = mp.mpf(source['gas_constant_j_mol_k'])
    data = {**source['phases'], 'H2O': steam['phases']['H2O']}
    phases = {name: RecordedThermalPhase(
        tuple(map(float, item['cp_coefficient_strings'])), float(t0),
        float(item['reference_enthalpy_j_mol']),
        float(item['reference_entropy_j_mol_k']),
        tuple(p['selected_temperature_domain_k'])) for name, item in data.items()}
    phase_reviews = {}
    for name, item in source['phases'].items():
        maximum = {key: 0. for key in p['numerical_budgets']}
        points = []
        for temperature in p['review_temperatures_k']:
            state = phases[name].standard(temperature)
            ref = thermal(item, mp.mpf(str(temperature)), t0)
            errors = {key: float(abs(mp.mpf(state[key]) - ref[key])) for key in maximum}
            maximum = {key: max(value, errors[key]) for key, value in maximum.items()}
            points.append({'temperature_k': temperature, 'state': state,
                           'independent_integral_errors': errors})
        tables = []
        for row in item['source_table']:
            t = mp.mpf(row['temperature_k'])
            ref = thermal(item, t, t0)
            values = {key: ref[key] for key in ['cp_j_mol_k', 'entropy_j_mol_k']}
            values['sensible_enthalpy_over_t_j_mol_k'] = (
                ref['enthalpy_j_mol'] - mp.mpf(item['reference_enthalpy_j_mol'])) / t
            enclosure = rounding(item, t, t0)
            enclosure['sensible_enthalpy_over_t_j_mol_k'] = enclosure['sensible_enthalpy_j_mol'] / t
            delta = {key: value - mp.mpf(row[key]) for key, value in values.items()}
            bounds = {key: enclosure[key] + half_printed(row[key]) for key in values}
            tables.append({'printed': row,
                'nominal_minus_printed': {key: float(value) for key, value in delta.items()},
                'printing_enclosure': {key: float(value) for key, value in bounds.items()},
                'within_table_half_unit': {key: bool(abs(value) <= half_printed(row[key]))
                                           for key, value in delta.items()},
                'within_complete_arithmetic_enclosure': {
                    key: bool(abs(value) <= bounds[key] + p['source_arithmetic_enclosure_allowance'])
                    for key, value in delta.items()}})
        certificate = cp_certificate([Fraction(float(value)) for value in item['cp_coefficient_strings']],
                                     p['cp_certificate'])
        flags = {key: value <= p['numerical_budgets'][key] for key, value in maximum.items()}
        flags['whole_domain_positive_cp'] = certificate['whole_cover_positive']
        phase_reviews[name] = {'points': points, 'maximum_errors': maximum,
            'within_numerical_budgets': flags, 'cp_certificate': certificate, 'table_comparisons': tables,
            'all_table_half_units_met': all(all(row['within_table_half_unit'].values()) for row in tables),
            'all_arithmetic_enclosures_met': all(all(row['within_complete_arithmetic_enclosure'].values())
                                                for row in tables)}

    reactions = {}
    for name, nu in p['reactions'].items():
        maximum = {key: 0. for key in p['reaction_budgets']}
        atoms = sorted({atom for phase in nu for atom in p['atoms'][phase]})
        balance = {atom: sum(Fraction(coefficient) * p['atoms'][phase].get(atom, 0)
                            for phase, coefficient in nu.items()) for atom in atoms}
        points = []
        for temperature in p['review_temperatures_k']:
            t = mp.mpf(str(temperature))
            state = standard_reaction(phases, nu, temperature, float(r))
            refstates = {phase: thermal(data[phase], t, t0) for phase in nu}
            ref = {key: mp.fsum(coefficient * refstates[phase][key] for phase, coefficient in nu.items())
                   for key in ['enthalpy_j_mol', 'entropy_j_mol_k', 'gibbs_j_mol']}
            ref['log_equilibrium'] = -ref['gibbs_j_mol'] / (r * t)
            def gibbs(v):
                return mp.fsum(coefficient * thermal(data[phase], v, t0)['gibbs_j_mol']
                               for phase, coefficient in nu.items())
            ref['gibbs_temperature_derivative_j_mol_k'] = mp.diff(gibbs, t)
            ref['vant_hoff_derivative_per_k'] = mp.diff(lambda v: -gibbs(v) / (r * v), t)
            errors = {key: float(abs(mp.mpf(state[key]) - ref[key])) for key in maximum}
            maximum = {key: max(value, errors[key]) for key, value in maximum.items()}
            water_nu = nu['H2O']
            equilibrium = float(source['reference_pressure_pa']) * math.exp(state['log_equilibrium'] / water_nu)
            basis = p['reaction_extent_basis_kaolinite_mol'][name]
            pressure_states = []
            for pressure in p['steam_partial_pressures_pa']:
                delta_g = state['gibbs_j_mol'] + water_nu * float(r) * temperature * math.log(
                    pressure / float(source['reference_pressure_pa']))
                pressure_states.append({'steam_partial_pressure_pa': pressure,
                    'reaction_gibbs_j_per_mol_kaolinite': delta_g / basis,
                    'forward_affinity_j_per_mol_kaolinite': -delta_g / basis})
            points.append({'temperature_k': temperature, 'state': state,
                'independent_errors': errors, 'equilibrium_steam_pressure_pa': equilibrium,
                'equilibrium_pressure_within_declared_total_pressure': equilibrium <= p['total_pressure_pa'],
                'pressure_states': pressure_states})
        flags = {key: value <= p['reaction_budgets'][key] for key, value in maximum.items()}
        flags['exact_element_balance'] = all(value == 0 for value in balance.values())
        reactions[name] = {'stoichiometry': nu, 'atom_balance': {key: str(value) for key, value in balance.items()},
            'points': points, 'maximum_errors': maximum, 'within_budgets': flags}
    result = {'settings': p, 'source': source, 'steam_source': p['steam_source_file'],
        'phase_reviews': phase_reviews, 'reactions': reactions,
        'all_numerical_relations_met': all(all(row['within_numerical_budgets'].values())
            for row in phase_reviews.values()) and all(all(row['within_budgets'].values()) for row in reactions.values()),
        'all_table_half_units_met': all(row['all_table_half_units_met'] for row in phase_reviews.values()),
        'all_arithmetic_enclosures_met': all(row['all_arithmetic_enclosures_met'] for row in phase_reviews.values()),
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ['all_numerical_relations_met',
        'all_table_half_units_met', 'all_arithmetic_enclosures_met']}))


if __name__ == '__main__':
    main()
