"""Zero-storage ideal gas surface with four species and one energy balance."""
import math

from scipy.optimize import brentq

from .carbon_calcium_radiative_cell import black_enclosure_exchange
from .carbon_calcium_rigid_exchange import exchange


def surface_exchange(model, bulk, reservoir, interior, exterior, radiation, settings):
    names = exterior['gas_order']
    tb, tc = reservoir['temperature_k'], bulk['temperature_k']
    hb = {k: model.phases[k].standard(tb)['enthalpy_j_mol'] for k in names}
    hc = {k: model.phases[k].standard(tc)['enthalpy_j_mol'] for k in names}
    lo, li = exterior['gas_mobilities_mol2_k_j_s'], interior['gas_mobilities_mol2_k_j_s']

    def at_temperature(temperature):
        thermal = {k: model.phases[k].standard(temperature) for k in names}
        potentials, flows = {}, {}
        for name in names:
            hs = thermal[name]['enthalpy_j_mol']
            a = reservoir['chemical_potentials_j_mol'][name] / tb + (hb[name] + hs) / 2 * (1/temperature - 1/tb)
            b = bulk['chemical_potentials_j_mol'][name] / tc - (hc[name] + hs) / 2 * (1/tc - 1/temperature)
            potentials[name] = (lo[name] * a + li[name] * b) / (lo[name] + li[name])
            flows[name] = lo[name] * li[name] / (lo[name] + li[name]) * (a - b)
        rad = black_enclosure_exchange(temperature, radiation)
        residual = math.fsum([exterior['heat_conductance_w_k'] * (tb - temperature),
            -interior['heat_conductance_w_k'] * (temperature - tc), rad['energy_in_w']]
            + [(hb[k] - hc[k]) / 2 * flows[k] for k in names])
        return residual, potentials, thermal, rad

    policy = settings['numerics']
    temperature = brentq(lambda t: at_temperature(t)[0], *settings['surface_temperature_domain_k'],
        xtol=policy['temperature_absolute_tolerance_k'], rtol=policy['temperature_relative_tolerance'],
        maxiter=policy['maximum_root_iterations'])
    residual, potentials, thermal, rad = at_temperature(temperature)
    partial = {k: model.p0 * math.exp((potentials[k] - thermal[k]['gibbs_j_mol'] / temperature) / model.r) for k in names}
    pressure = math.fsum(partial.values())
    surface = {'temperature_k': temperature, 'pressure_pa': pressure,
        'partial_pressures_pa': partial, 'mole_fractions': {k: v / pressure for k, v in partial.items()},
        'chemical_potentials_j_mol': {k: temperature * v for k, v in potentials.items()}}
    outer = exchange(model, reservoir, surface, exterior)
    inner = exchange(model, surface, bulk, interior)
    species_residuals = {k: outer['gas_flows_mol_s'][k] - inner['gas_flows_mol_s'][k] for k in names}
    energy_residual = outer['energy_flow_w'] + rad['energy_in_w'] - inner['energy_flow_w']
    entropy_residual = math.fsum([outer['right_entropy_rate_w_k'], inner['left_entropy_rate_w_k'],
                                  rad['body_entropy_rate_w_k']])
    production = math.fsum([outer['entropy_production_w_k'], inner['entropy_production_w_k'],
                            rad['entropy_production_w_k']])
    return {'surface': surface, 'outer': outer, 'inner': inner, 'radiation': rad,
        'species_balance_residuals_mol_s': species_residuals, 'energy_balance_residual_w': energy_residual,
        'eliminated_energy_balance_residual_w': residual, 'surface_entropy_balance_w_k': entropy_residual,
        'combined_entropy_production_w_k': production,
        'body_plus_reservoir_entropy_rate_w_k': math.fsum([inner['right_entropy_rate_w_k'],
            outer['left_entropy_rate_w_k'], rad['reservoir_entropy_rate_w_k']])}
