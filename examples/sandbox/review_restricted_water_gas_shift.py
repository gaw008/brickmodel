"""Source-based constrained chemical equilibrium and rigid energy review."""
import argparse
import json
import math
from pathlib import Path
import sys

import mpmath as mp

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from sludge_sandbox.recorded_reaction_affinity import RecordedThermalPhase
from sludge_sandbox.restricted_water_gas_shift import RestrictedWaterGasShift


class Reference:
    def __init__(self, parameters, source):
        self.p, self.source = parameters, source
        self.r = mp.mpf(str(parameters['gas_constant_j_mol_k']))
        self.p0 = mp.mpf(str(parameters['standard_pressure_pa']))
        self.t0 = mp.mpf(str(parameters['reference_temperature_k']))
        self.tolerance = mp.mpf(parameters['independent_reference']['root_tolerance'])

    def thermal(self, name, t):
        data = self.source[name]
        a, b, c, d, e = map(mp.mpf, data['cp_coefficient_strings'])
        t0 = self.t0
        h = mp.mpf(data['reference_enthalpy_j_mol']) + a*(t-t0) + b*(t*t-t0*t0)/2 + c*(1/t0-1/t) + 2*d*(mp.sqrt(t)-mp.sqrt(t0)) + e*(t**3-t0**3)/3
        s = mp.mpf(data['reference_entropy_j_mol_k']) + a*mp.log(t/t0) + b*(t-t0) + c*(1/t0**2-1/t**2)/2 + 2*d*(1/mp.sqrt(t0)-1/mp.sqrt(t)) + e*(t*t-t0*t0)/2
        return h, s

    def root(self, function, left, right):
        for _ in range(self.p['independent_reference']['root_maximum_iterations']):
            middle = (left + right)/2
            value = function(middle)
            if value > 0:
                right = middle
            else:
                left = middle
            if right-left <= self.tolerance:
                return (left+right)/2
        raise ArithmeticError('independent source bisection did not reach its declared precision')

    def state(self, t, volume, initial, extent):
        amounts = {name: value + self.p['stoichiometry'][name]*extent for name, value in initial.items()}
        thermal = {name: self.thermal(name, t) for name in amounts}
        pressure = {name: value*self.r*t/volume for name, value in amounts.items()}
        entropy = mp.fsum(value*(thermal[name][1]-self.r*mp.log(pressure[name]/self.p0)) for name, value in amounts.items())
        energy = mp.fsum(value*(thermal[name][0]-self.r*t) for name, value in amounts.items())
        chemical = {name: thermal[name][0]-t*thermal[name][1]+self.r*t*mp.log(pressure[name]/self.p0) for name in amounts}
        return {'temperature_k': t, 'extent_mol': extent, 'amounts_mol': amounts,
                'pressure_pa': mp.fsum(pressure.values()), 'internal_energy_j': energy,
                'entropy_j_k': entropy, 'helmholtz_j': energy-t*entropy,
                'reaction_gibbs_j_mol': mp.fsum(self.p['stoichiometry'][name]*value for name, value in chemical.items())}

    def equilibrium(self, t, volume, initial):
        thermal = {name: self.thermal(name, t) for name in initial}
        dg = mp.fsum(self.p['stoichiometry'][name]*(values[0]-t*values[1]) for name, values in thermal.items())
        k = mp.exp(-dg/(self.r*t))
        a, b, c, d = [initial[name] for name in ['CO', 'H2O', 'CO2', 'H2']]
        extent = self.root(lambda x: (c+x)*(d+x)-k*(a-x)*(b-x), -min(c, d), min(a, b))
        return self.state(t, volume, initial, extent)

    def adiabatic(self, initial_t, volume, initial):
        energy = self.state(initial_t, volume, initial, mp.mpf(0))['internal_energy_j']
        bracket = list(map(lambda v: mp.mpf(str(v)), self.p['numerics']['temperature_bracket_k']))
        t = self.root(lambda t: self.equilibrium(t, volume, initial)['internal_energy_j']-energy, *bracket)
        return self.equilibrium(t, volume, initial)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text()); root = args.parameters.resolve().parent
    sources = [json.loads((root / path).read_text()) for path in p['sources']]
    source = {name: values for item in sources for name, values in item['phases'].items() if name in p['species']}
    mp.mp.dps = p['independent_reference']['decimal_digits']
    phases = {name: RecordedThermalPhase(tuple(map(float, data['cp_coefficient_strings'])), p['reference_temperature_k'], float(data['reference_enthalpy_j_mol']), float(data['reference_entropy_j_mol_k']), tuple(p['temperature_domain_k'])) for name, data in source.items()}
    model = RestrictedWaterGasShift(phases, p['stoichiometry'], p['gas_constant_j_mol_k'], p['standard_pressure_pa'])
    reference = Reference(p, source)
    records = []
    for case in p['cases']:
        t, volume, initial = case['initial_temperature_k'], case['volume_m3'], case['initial_amounts_mol']
        mt, mv = mp.mpf(str(t)), mp.mpf(str(volume))
        mn = {name: mp.mpf(str(value)) for name, value in initial.items()}
        initial_state = model.at_extent(t, volume, initial, 0.)
        states = {'isothermal': model.at_temperature(t, volume, initial),
                  'adiabatic_rigid': model.at_energy(initial_state['internal_energy_j'], volume, initial, p['numerics'])}
        references = {'isothermal': reference.equilibrium(mt, mv, mn),
                      'adiabatic_rigid': reference.adiabatic(mt, mv, mn)}
        reviews = {}
        for mode, state in states.items():
            expected = references[mode]
            errors = {'amount_mol': max(float(abs(mp.mpf(state['amounts_mol'][name])-value)) for name, value in expected['amounts_mol'].items()),
                      'temperature_k': float(abs(mp.mpf(state['temperature_k'])-expected['temperature_k'])),
                      'energy_j': float(abs(mp.mpf(state['internal_energy_j'])-expected['internal_energy_j'])),
                      'entropy_j_k': float(abs(mp.mpf(state['entropy_j_k'])-expected['entropy_j_k'])),
                      'pressure_pa': float(abs(mp.mpf(state['pressure_pa'])-expected['pressure_pa'])),
                      'helmholtz_j': float(abs(mp.mpf(state['helmholtz_j'])-expected['helmholtz_j'])),
                      'reaction_gibbs_j_mol': abs(state['reaction_gibbs_j_mol'])}
            step = mp.mpf(p['independent_reference']['temperature_difference_k'])
            samples = {i: reference.equilibrium(expected['temperature_k']+i*step, mv, mn) for i in [-2, -1, 1, 2]}
            derivative = lambda key: (samples[-2][key]-8*samples[-1][key]+8*samples[1][key]-samples[2][key])/(12*step)
            errors['cv_j_k'] = float(abs(mp.mpf(state['equilibrium_cv_j_k'])-derivative('internal_energy_j')))
            errors['extent_temperature_derivative_mol_k'] = float(abs(mp.mpf(state['extent_temperature_derivative_mol_k'])-derivative('extent_mol')))
            elements = {element: math.fsum(p['atoms'][name].get(element, 0)*(state['amounts_mol'][name]-initial[name]) for name in initial) for element in ['C', 'H', 'O', 'N']}
            errors['element_mol'] = max(map(abs, elements.values()))
            volume_state = model.at_temperature(state['temperature_k'], volume*p['volume_multiplier'], initial)
            volume_effect = max(abs(value-volume_state['amounts_mol'][name]) for name, value in state['amounts_mol'].items())
            low, high = -min(initial['CO2'], initial['H2']), min(initial['CO'], initial['H2O'])
            samples_a = [model.at_extent(state['temperature_k'], volume, initial, low+(high-low)*f) for f in p['helmholtz_extent_fractions']]
            minimum_helmholtz_difference = min(s['helmholtz_j']-state['helmholtz_j'] for s in samples_a)
            scaled = []
            for factor in p['inventory_scale_factors']:
                amounts = {name: value*factor for name, value in initial.items()}
                result = model.at_temperature(state['temperature_k'], volume*factor, amounts)
                scaled.append({'factor': factor, 'maximum_normalized_amount_error_mol': max(abs(result['amounts_mol'][name]/factor-value) for name, value in state['amounts_mol'].items()), 'pressure_difference_pa': abs(result['pressure_pa']-state['pressure_pa'])})
            flags = {name: error <= p['budgets'][name] for name, error in errors.items()}
            flags.update(positive_amounts=min(state['amounts_mol'].values()) > 0,
                         positive_equilibrium_cv=state['equilibrium_cv_j_k'] > state['frozen_cv_j_k'] > 0,
                         positive_helmholtz_curvature=state['helmholtz_extent_curvature_j_mol2'] > 0,
                         volume_invariant_composition=volume_effect <= p['budgets']['amount_mol'],
                         sampled_helmholtz_minimum=minimum_helmholtz_difference >= -p['budgets']['helmholtz_j'],
                         extensive_scaling=all(s['maximum_normalized_amount_error_mol'] <= p['budgets']['amount_mol'] and s['pressure_difference_pa'] <= p['budgets']['pressure_pa'] for s in scaled))
            if mode == 'adiabatic_rigid':
                flags['constant_internal_energy'] = abs(state['energy_inverse_residual_j']) <= p['budgets']['energy_j']
                flags['nonnegative_adiabatic_entropy'] = state['entropy_j_k']-initial_state['entropy_j_k'] >= -p['budgets']['nonnegative_entropy_j_k']
            else:
                flags['initial_to_equilibrium_helmholtz_decrease'] = state['helmholtz_j']-initial_state['helmholtz_j'] <= p['budgets']['helmholtz_j']
            reviews[mode] = {'state': state, 'independent_errors': errors, 'element_residuals_mol': elements,
                             'minimum_sampled_helmholtz_difference_j': minimum_helmholtz_difference,
                             'extensive_scaling': scaled, 'entropy_change_j_k': state['entropy_j_k']-initial_state['entropy_j_k'],
                             'within_budgets': flags, 'all_requested_budgets_met': all(flags.values())}
        records.append({'case': case, 'initial_state': initial_state, 'reviews': reviews})
        print(json.dumps({'case': case['id'], 'isothermal': reviews['isothermal']['all_requested_budgets_met'], 'adiabatic_rigid': reviews['adiabatic_rigid']['all_requested_budgets_met']}), flush=True)
    result = {'settings': p, 'source_ids': [item['source_id'] for item in sources], 'records': records,
              'all_requested_budgets_met': all(review['all_requested_budgets_met'] for item in records for review in item['reviews'].values()),
              'scope': p['scope'], 'material_qualified': False, 'training_eligible': False}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')


if __name__ == '__main__':
    main()
