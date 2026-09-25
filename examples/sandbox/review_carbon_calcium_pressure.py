"""Source, element and phase review for a finite-pressure Ca/C/O mixture."""
import argparse
import json
import math
from pathlib import Path

from mpmath import mp

from carbon_calcium_pressure_setup import build
from carbon_calcium_pressure_decimal_reference import reconstruct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text())
    policy = json.loads((root / settings['model_parameters']).read_text())
    model, sources, standard = build(root, policy)
    mp.dps = settings['decimal_digits']
    budget, records = settings['budgets'], []
    for inventory in policy['inventories']:
        inputs = [inventory[name] for name in ['calcium_atoms_mol', 'carbon_atoms_mol',
                                               'oxygen_atoms_mol', 'nitrogen_molecules_mol']]
        for p in policy['pressure_points_pa']:
            for t in policy['temperature_points_k']:
                candidate = model.at_temperature_pressure(t, p, *inputs)
                reference = reconstruct(model, t, p, inventory, candidate, settings)
                n, mu = candidate['amounts_mol'], candidate['chemical_potentials_j_mol']
                elements = [n['calcite'] + n['lime'], math.fsum(n[k] for k in ['calcite', 'C', 'CO', 'CO2']),
                    math.fsum((3*n['calcite'], n['lime'], n['CO'], 2*n['CO2'], 2*n['O2'])), n['N2']]
                element_error = max(abs(a-b) for a,b in zip(elements, inputs, strict=True))
                gas = ['CO', 'CO2', 'O2', 'N2']
                ng = math.fsum(n[k] for k in gas)
                pressure_error = max(abs(math.fsum(candidate['partial_pressures_pa'].values()) - p),
                    *(abs(candidate['partial_pressures_pa'][name] - p*n[name]/ng) for name in gas))
                amount_error = max(float(abs(mp.mpf(n[k]) - v)) for k,v in reference['amounts'].items())
                relative_error = max(float(abs(mp.mpf(n[k])/reference['amounts'][k]-1)) for k in gas)
                errors = {key: float(abs(mp.mpf(candidate[field]) - reference[key])) for key,field in
                    [('enthalpy','enthalpy_j'), ('entropy','entropy_j_k'), ('volume','total_volume_m3'),
                     ('internal_energy','internal_energy_j'), ('gibbs','gibbs_j')]}
                ac = mu['lime'] + mu['CO2'] - mu['calcite']
                a1 = mu['CO'] - mu['C'] - mu['O2']/2
                a2 = mu['CO2'] - mu['C'] - mu['O2']
                ag = mu['CO2'] - mu['CO'] - mu['O2']/2
                calcium_error = {'calcite': max(0.,-ac), 'lime': max(0.,ac), 'coexistence': abs(ac)}[candidate['calcium_phase']]
                carbon_error = max(abs(a1),abs(a2)) if candidate['carbon_phase']=='graphite_present' else max(0.,a1,a2)
                rm = reference['mu']
                rac = rm['lime'] + rm['CO2'] - rm['calcite']
                constraints = all(v >= 0 for v in reference['amounts'].values())
                if candidate['calcium_phase']=='calcite': constraints = constraints and rac >= 0
                if candidate['calcium_phase']=='lime': constraints = constraints and rac <= 0
                if candidate['carbon_phase']=='graphite_exhausted':
                    constraints = constraints and rm['CO']-rm['C']-rm['O2']/2 <= 0 and rm['CO2']-rm['C']-rm['O2'] <= 0
                flags = {'elements':element_error <= budget['element_mol'], 'pressure':pressure_error <= budget['pressure_pa'],
                    'amounts':amount_error <= budget['amount_mol'], 'positive_gas_relative':relative_error <= budget['positive_gas_relative'],
                    'calcium_complementarity':calcium_error <= budget['chemical_potential_j_mol'],
                    'carbon_complementarity':carbon_error <= budget['chemical_potential_j_mol'],
                    'gas_equilibrium':abs(ag) <= budget['chemical_potential_j_mol'], 'reference_phase_constraints':bool(constraints),
                    'source_enthalpy':errors['enthalpy'] <= budget['source_enthalpy_j'],
                    'source_internal_energy':errors['internal_energy'] <= budget['source_enthalpy_j'],
                    'source_gibbs':errors['gibbs'] <= budget['source_enthalpy_j'],
                    'source_entropy':errors['entropy'] <= budget['source_entropy_j_k'], 'volume':errors['volume'] <= budget['volume_m3'],
                    'positive_capacities':candidate['equilibrium_cp_j_k'] >= candidate['equilibrium_cv_j_k'] > 0,
                    'negative_volume_pressure_slope':candidate['volume_pressure_derivative_m3_pa'] < 0}
                baseline = None
                if p == standard.p0:
                    old = standard.at_temperature(t,*inputs)
                    baseline = {'enthalpy_j':abs(old['enthalpy_j']-candidate['enthalpy_j']),
                        'amount_mol':max(abs(old['amounts_mol'][k]-n[k]) for k in n)}
                    flags['standard_pressure_enthalpy'] = baseline['enthalpy_j'] <= budget['standard_pressure_enthalpy_j']
                    flags['standard_pressure_amount'] = baseline['amount_mol'] <= budget['standard_pressure_amount_mol']
                record = {'inventory':inventory, 'candidate':candidate,
                    'reference_amounts_mol':{k:str(v) for k,v in reference['amounts'].items()},
                    'element_error_mol':element_error, 'pressure_error_pa':pressure_error,
                    'amount_error_mol':amount_error, 'positive_gas_relative_error':relative_error,
                    'source_errors':errors, 'calcium_complementarity_error_j_mol':calcium_error,
                    'carbon_complementarity_error_j_mol':carbon_error, 'gas_equilibrium_error_j_mol':abs(ag),
                    'standard_pressure_comparison':baseline, 'within_budgets':flags}
                records.append(record)
                print(json.dumps({'inventory':inventory['name'],'temperature_k':t,'pressure_pa':p,
                                  'within_budgets':all(flags.values())}),flush=True)
    result = {'settings':settings,'model_parameters':policy,'sources':sources,'records':records,
        'all_requested_static_budgets_met':all(all(v['within_budgets'].values()) for v in records),
        'material_qualified':False,'training_eligible':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')


if __name__=='__main__': main()
