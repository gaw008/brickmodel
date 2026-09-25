"""Independent source/element/phase review of the general-inventory prototype."""
import argparse
import json
import math
from pathlib import Path

from mpmath import mp

from carbon_calcium_pressure_setup import build
from carbon_calcium_inventory_decimal_reference import reconstruct
from carbon_calcium_inventory_prototype import at_temperature_pressure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    policy = json.loads((root/settings['model_parameters']).read_text())
    model, sources, _ = build(root, policy)
    mp.dps = settings['decimal_digits']
    budget, records = settings['budgets'], []
    for inventory in settings['inventories']:
        inputs = [inventory[name] for name in ['calcium_atoms_mol', 'carbon_atoms_mol',
                                               'oxygen_atoms_mol', 'nitrogen_molecules_mol']]
        for p in settings['pressure_points_pa']:
            for t in settings['temperature_points_k']:
                print(json.dumps({'started_inventory': inventory['name'], 'temperature_k': t,
                                  'pressure_pa': p}), flush=True)
                candidate = at_temperature_pressure(model, t, p, inventory)
                reference = reconstruct(model, t, p, inventory, candidate, settings)
                n, mu = candidate['amounts_mol'], candidate['chemical_potentials_j_mol']
                elements = [n['calcite']+n['lime'], math.fsum(n[k] for k in ['calcite', 'C', 'CO', 'CO2']),
                    math.fsum((3*n['calcite'], n['lime'], n['CO'], 2*n['CO2'], 2*n['O2'])), n['N2']]
                element_error = max(abs(a-b) for a, b in zip(elements, inputs, strict=True))
                gas = ['CO', 'CO2', 'O2', 'N2']
                ng = math.fsum(n[k] for k in gas)
                pressure_error = max(abs(math.fsum(candidate['partial_pressures_pa'].values())-p),
                    *(abs(candidate['partial_pressures_pa'][name]-p*n[name]/ng) for name in gas))
                amount_error = max(float(abs(mp.mpf(n[k])-v)) for k, v in reference['amounts'].items())
                relative_error = max(float(abs(mp.mpf(n[k])/reference['amounts'][k]-1)) for k in gas)
                errors = {key: float(abs(mp.mpf(candidate[field])-reference[key])) for key, field in
                    [('enthalpy', 'enthalpy_j'), ('entropy', 'entropy_j_k'), ('volume', 'total_volume_m3'),
                     ('internal_energy', 'internal_energy_j'), ('gibbs', 'gibbs_j')]}
                ac = mu['lime']+mu['CO2']-mu['calcite']
                a1, a2 = mu['CO']-mu['C']-mu['O2']/2, mu['CO2']-mu['C']-mu['O2']
                ag = mu['CO2']-mu['CO']-mu['O2']/2
                calcium_error = {'calcite': max(0., -ac), 'lime': max(0., ac), 'coexistence': abs(ac)}[candidate['calcium_phase']]
                carbon_error = max(abs(a1), abs(a2)) if candidate['carbon_phase']=='graphite_present' else max(0., a1, a2)
                rm = reference['mu']
                rac = rm['lime']+rm['CO2']-rm['calcite']
                constraints = all(v >= 0 for v in reference['amounts'].values())
                if candidate['calcium_phase']=='calcite': constraints = constraints and rac >= 0
                if candidate['calcium_phase']=='lime': constraints = constraints and rac <= 0
                if candidate['carbon_phase']=='graphite_exhausted':
                    constraints = constraints and rm['CO']-rm['C']-rm['O2']/2 <= 0 and rm['CO2']-rm['C']-rm['O2'] <= 0
                flags = {'elements': element_error <= budget['element_mol'],
                    'pressure': pressure_error <= budget['pressure_pa'],
                    'amounts': amount_error <= budget['amount_mol'],
                    'positive_gas_relative': relative_error <= budget['positive_gas_relative'],
                    'calcium_complementarity': calcium_error <= budget['chemical_potential_j_mol'],
                    'carbon_complementarity': carbon_error <= budget['chemical_potential_j_mol'],
                    'gas_equilibrium': abs(ag) <= budget['chemical_potential_j_mol'],
                    'candidate_phase_constraints': all(v >= 0 for v in n.values()),
                    'reference_phase_constraints': bool(constraints),
                    'source_enthalpy': errors['enthalpy'] <= budget['source_enthalpy_j'],
                    'source_internal_energy': errors['internal_energy'] <= budget['source_enthalpy_j'],
                    'source_gibbs': errors['gibbs'] <= budget['source_enthalpy_j'],
                    'source_entropy': errors['entropy'] <= budget['source_entropy_j_k'],
                    'volume': errors['volume'] <= budget['volume_m3']}
                records.append({'inventory': inventory, 'candidate': candidate,
                    'reference_amounts_mol': {k: str(v) for k, v in reference['amounts'].items()},
                    'reference_equation_residual': str(reference['equation_residual']),
                    'element_error_mol': element_error, 'pressure_error_pa': pressure_error,
                    'amount_error_mol': amount_error, 'positive_gas_relative_error': relative_error,
                    'source_errors': errors, 'calcium_complementarity_error_j_mol': calcium_error,
                    'carbon_complementarity_error_j_mol': carbon_error, 'gas_equilibrium_error_j_mol': abs(ag),
                    'within_budgets': flags})
                print(json.dumps({'completed_inventory': inventory['name'], 'temperature_k': t,
                    'pressure_pa': p, 'within_budgets': flags}), flush=True)
    old_records = []
    baseline = json.loads((root/settings['baseline']).read_text())
    for row in baseline['records']:
        old = row['candidate']
        candidate = at_temperature_pressure(model, old['temperature_k'], old['pressure_pa'], row['inventory'])
        amount_error = max(abs(candidate['amounts_mol'][name]-value) for name, value in old['amounts_mol'].items())
        enthalpy_error = abs(candidate['enthalpy_j']-old['enthalpy_j'])
        flags = {'phase_choice': all(candidate[name]==old[name] for name in ['calcium_phase', 'carbon_phase']),
            'amounts': amount_error <= budget['standard_pressure_amount_mol'],
            'enthalpy': enthalpy_error <= budget['standard_pressure_enthalpy_j']}
        old_records.append({'inventory': row['inventory'], 'candidate': candidate,
            'amount_error_mol': amount_error, 'enthalpy_error_j': enthalpy_error, 'within_budgets': flags})
    result = {'settings': settings, 'model_parameters': policy, 'sources': sources, 'records': records,
        'old_domain_comparisons': old_records,
        'all_requested_static_budgets_met': all(all(row['within_budgets'].values()) for row in records),
        'all_old_domain_comparison_budgets_met': all(all(row['within_budgets'].values()) for row in old_records),
        'derivative_qualified': False, 'dynamic_qualified': False,
        'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
