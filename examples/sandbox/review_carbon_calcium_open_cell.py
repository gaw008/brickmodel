"""Source-defined gas bath, elemental exchange and entropy arithmetic review."""
import argparse
import json
import math
from pathlib import Path

from carbon_calcium_pressure_setup import build as build_restricted
from carbon_calcium_inventory_setup import build as build_inventory
from carbon_calcium_source_audit import SourceState, independent_exchange
from sludge_sandbox.carbon_calcium_open_cell import ideal_gas_reservoir
from sludge_sandbox.carbon_calcium_rigid_exchange import exchange


def source_bath(source, temperature, pressure, fractions):
    h, mu = {}, {}
    for name, fraction in fractions.items():
        coefficients, _, h0, s0 = source.thermal[name]
        hp, sp = source.primitive(coefficients, temperature)
        hp0, sp0 = source.reference[name]
        h[name] = h0 + hp - hp0
        entropy = s0 + sp - sp0 - source.r * math.log(pressure / source.p0 * fraction)
        mu[name] = h[name] - temperature * entropy
    return {'temperature_k': temperature, 'h': h, 'mu': mu}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.parameters.resolve().parent
    p = json.loads(args.parameters.read_text())
    face = json.loads((root / p['exchange_parameters']).read_text())
    rigid = json.loads((root / face['rigid_parameters']).read_text())
    pressure = json.loads((root / rigid['pressure_parameters']).read_text())
    build = {'restricted': build_restricted, 'positive_inventory': build_inventory}[p['equilibrium_formulation']]
    model, sources, _ = build(root, pressure)
    source = SourceState(sources)
    initial, policy = p['initial'], p['static_review']
    inventory = [initial[k] for k in ('calcium_atoms_mol', 'carbon_atoms_mol',
                                      'oxygen_atoms_mol', 'nitrogen_molecules_mol')]
    results, matched = [], []
    for temperature in policy['temperatures_k']:
        state = model.at_temperature_volume(temperature, p['volume_m3'], *inventory, rigid['numerics'])
        independent = source.reconstruct(state, p['volume_m3'], inventory)
        for bath_t in policy['bath_temperatures_k']:
            for bath_p in policy['bath_pressures_pa']:
                fractions = p['reservoir']['mole_fractions']
                bath = ideal_gas_reservoir(model, bath_t, bath_p, fractions)
                gas = source_bath(source, bath_t, bath_p, fractions)
                actual = exchange(model, bath, state, face)
                reference = independent_exchange(gas, independent, face)
                errors = {
                    'chemical_potential_j_mol': max(abs(bath['chemical_potentials_j_mol'][k] - gas['mu'][k]) for k in fractions),
                    'gas_flow_mol_s': max(abs(actual['gas_flows_mol_s'][k] - reference['gas'][k]) for k in fractions),
                    'inventory_flow_mol_s': max(abs(actual['inventory_flows_mol_s'][k] - value)
                                              for k, value in zip(face['transferred_inventory_order'], reference['inventory'], strict=True)),
                    'energy_w': abs(actual['energy_flow_w'] - reference['energy']),
                    'entropy_w_k': max(abs(actual['left_entropy_rate_w_k'] - reference['entropy'][0]),
                                      abs(actual['right_entropy_rate_w_k'] - reference['entropy'][1]),
                                      abs(actual['entropy_production_w_k'] - reference['production'])),
                }
                flags = {k: v <= p['verification'][k] for k, v in independent['errors'].items()}
                flags.update(
                    bath_mole_fractions=sum(fractions.values()) == 1. and min(fractions.values()) > 0.,
                    gas_source=errors['chemical_potential_j_mol'] <= policy['chemical_potential_budget_j_mol'],
                    gas_flow=errors['gas_flow_mol_s'] <= policy['face_inventory_budget_mol_s'],
                    elemental_flow=errors['inventory_flow_mol_s'] <= policy['face_inventory_budget_mol_s'],
                    energy_flow=errors['energy_w'] <= policy['face_energy_budget_w'],
                    entropy_flow=errors['entropy_w_k'] <= policy['face_entropy_budget_w_k'],
                    nonnegative_production=reference['production'] >= 0.,
                    positive_cv=state['equilibrium_cv_j_k'] > 0.)
                results.append({'cell_temperature_k': temperature, 'bath_temperature_k': bath_t,
                    'bath_pressure_pa': bath_p, 'state': state, 'source_errors': independent['errors'],
                    'face': actual, 'independent': reference, 'errors': errors, 'within_budgets': flags})
        partial = state['partial_pressures_pa']
        bath = ideal_gas_reservoir(model, temperature, state['pressure_pa'],
                                   {k: partial[k] / state['pressure_pa'] for k in face['gas_order']})
        result = exchange(model, bath, state, face)
        matched.append({'temperature_k': temperature, 'face': result, 'within_budgets': {
            'zero_gas_flow': max(abs(v) for v in result['gas_flows_mol_s'].values()) <= policy['identical_bath_flow_budget_mol_s'],
            'zero_energy_flow': abs(result['energy_flow_w']) <= policy['identical_bath_energy_budget_w']}})
    result = {'settings': p, 'source_records': sources, 'states': results, 'matched_baths': matched,
        'all_requested_numerical_budgets_met': all(all(r['within_budgets'].values()) for r in results + matched),
        'material_qualified': False, 'training_eligible': False,
        'scope': 'Instantaneous static source and exchange qualification only; no trajectory or real gas-bath transport validation.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'states': len(results), 'matched_baths': len(matched),
                      'all_requested_numerical_budgets_met': result['all_requested_numerical_budgets_met']}))


if __name__ == '__main__':
    main()
