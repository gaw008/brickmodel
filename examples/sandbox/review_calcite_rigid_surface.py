"""Independent source-flux recomposition and implicit-surface differential review."""
import argparse
import json
from pathlib import Path

import numpy as np

from calcite_rigid_setup import build_rigid
from calcite_rigid_source_review import independent_face
from sludge_sandbox.equilibrium_calcite_rigid import RigidCalciteMixture
from sludge_sandbox.rigid_reactive_surface import RigidReactiveSurface, gas_contact_state


def flux(result):
    return np.array([result['interior_face'][k] for k in ('carbon_flow_mol_s', 'nitrogen_flow_mol_s', 'energy_flow_w')])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); root = args.parameters.resolve().parent
    settings = json.loads(args.parameters.read_text()); config = json.loads((root/settings['model_parameters']).read_text())
    reaction, nitrogen, _, _, _, _, volume = build_rigid(root, config)
    cell = RigidCalciteMixture(reaction, nitrogen, volume, config, settings['cell'])
    contact = RigidReactiveSurface(cell, settings['surface']); budget = settings['budgets']; records = []
    for case in settings['cases']:
        bulk = cell.at_inventory(*case['bulk'])
        specification = case['reservoir']
        if specification == 'same_as_bulk':
            specification = [bulk['temperature_k'], bulk['pressure_pa'], bulk['co2_mol']/(bulk['co2_mol']+bulk['nitrogen_mol'])]
        reservoir = gas_contact_state(cell, *specification); wall = case['wall_temperature_k']
        result = contact.solve(bulk, reservoir, wall); surface = result['surface']
        inner = independent_face(bulk, surface, cell, contact.interior)
        outer = independent_face(surface, reservoir, cell, contact.exterior)
        radiation = settings['surface']['area_m2']*settings['surface']['radiation']['emissivity']*settings['surface']['radiation']['stefan_boltzmann_w_m2_k4']*(wall**4-surface['temperature_k']**4)
        balance = inner[:3]-outer[:3]; balance[2] += radiation
        independent_entropy = inner[3]+outer[4]-radiation/wall
        production = result['entropy_production_w_k']
        errors = {'species_balance_mol_s': float(np.max(np.abs(balance[:2]))), 'energy_balance_w': float(abs(balance[2])),
            'independent_species_mol_s': max(abs(vector[i]-result[name][k]) for vector,name in ((inner,'interior_face'),(outer,'exterior_face')) for i,k in enumerate(('carbon_flow_mol_s','nitrogen_flow_mol_s'))),
            'independent_energy_w': max(abs(vector[2]-result[name]['energy_flow_w']) for vector,name in ((inner,'interior_face'),(outer,'exterior_face'))),
            'entropy_identity_w_k': abs(independent_entropy-production)}
        flags = {key: value <= budget[key] for key,value in errors.items()}
        flags['nonnegative_entropy'] = min(production, inner[3]+inner[4], outer[3]+outer[4], result['radiation_entropy_production_w_k']) >= -budget['negative_entropy_allowance_w_k']
        inventory = np.array([bulk[k] for k in ('carbon_mol','nitrogen_mol','internal_energy_j')])
        in_scales = np.array(settings['derivative_inventory_scales']); out_scales = np.array(settings['derivative_flux_scales'])
        difference_scales = np.array(case['difference_inventory_scales'] if 'difference_inventory_scales' in case else settings['derivative_inventory_scales'])
        analytic = np.array(result['interior_flux_inventory_derivative'])*in_scales/out_scales[:,None]
        comparisons = []
        for step in settings['derivative_steps']:
            numerical = np.zeros_like(analytic)
            branches = []
            for j in range(3):
                delta = np.eye(3)[j]*difference_scales[j]*step
                low_values, high_values = inventory-delta, inventory+delta
                low_state, high_state = cell.inventory_state(*low_values), cell.inventory_state(*high_values)
                branches.extend((low_state['phase'], high_state['phase']))
                lo = contact.solve(low_state, reservoir, wall)
                hi = contact.solve(high_state, reservoir, wall)
                numerical[:,j] = (flux(hi)-flux(lo))/(high_values[j]-low_values[j])*in_scales[j]/out_scales
            error = float(np.max(np.abs(numerical-analytic)))
            comparisons.append({'step':step,'difference_inventory_scales':difference_scales.tolist(),
                'maximum_scaled_derivative_error':error,'same_phase_branch':all(p==bulk['phase'] for p in branches),
                'within_budget':error<=budget['scaled_flux_derivative_absolute']})
        flags['implicit_flux_derivative'] = all(c['within_budget'] and c['same_phase_branch'] for c in comparisons)
        if case['name']=='equal':
            flags['zero_species'] = float(np.max(np.abs(flux(result)[:2]))) <= budget['equal_species_mol_s']
            flags['zero_energy'] = abs(float(flux(result)[2])) <= budget['equal_energy_w']
        flags = {key:bool(value) for key,value in flags.items()}
        records.append({'case':case,'bulk':bulk,'reservoir':reservoir,'result':result,'independent_residuals':errors,
            'independent_total_entropy_production_w_k':independent_entropy,'derivative_comparisons':comparisons,'within_budgets':flags})
        print(json.dumps({'case':case['name'],'within_budgets':flags}),flush=True)
    result = {'settings':settings,'records':records,'all_requested_numerical_budgets_met':all(all(r['within_budgets'].values()) for r in records),
        'material_qualified':False,'training_eligible':False,
        'scope':'Independent source face expansion; shared gas potentials and equilibrium flash. Not a global existence/uniqueness theorem.'}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    main()
