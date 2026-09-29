"""Frozen local diagnostics of the assumed full-cycle constitutive laws."""
from math import expm1, log

from scipy.optimize import brentq


def frozen_water_equilibrium(config, *, water_moles, sites_mol, temperature_k,
                             phase_affinity_j_mol) -> dict:
    """Classify local water phase equilibrium with all other quantities frozen.

    Inputs are scalar: n0>0, N>=0 and T>0, with the existing nonnegative
    binding energy and heat-capacity parameters. The supplied affinity is
    mu_vapor-mu_water at n0. Temperature, site inventory, vapor chemical
    potential and all non-retention contributions remain fixed as n varies.
    This conditional root is not a coupled steady state or a conserved-mass
    trajectory; bulk/pore geometry feasibility is not checked.
    """
    parameters = config['parameters']
    gas_constant = parameters['reference.R']['value']
    reference_temperature = parameters['reference.temperature']['value']
    binding_energy = parameters['water.binding_energy']['value']
    binding_capacity = parameters['water.binding_heat_capacity']['value']
    rtol = parameters['numerics.rtol']['value']
    atol = parameters['numerics.atol']['value']
    n0, sites, temperature = water_moles, sites_mol, temperature_k
    rt = gas_constant*temperature
    binding = -binding_energy+binding_capacity*(
        (temperature-reference_temperature)-temperature*log(temperature/reference_temperature))
    log_activity = log(n0/(n0+sites))
    binding_partial = binding*(sites/(n0+sites))**2
    constant = phase_affinity_j_mol+rt*log_activity+binding_partial
    result = {
        'status': None,
        'n_eq_mol': None,
        'A_j_mol': constant,
        'B_j_mol': binding,
        'reconstructed_initial_affinity_j_mol': constant-rt*log_activity-binding_partial,
        'root_residual_j_mol': None,
        'n_eq_over_n0': None,
        'identity': 'simulation',
        'constitutive_identity': 'assumed',
        'frozen_conditions': 'Temperature, site inventory, vapor chemical potential and all non-retention affinity terms are fixed; only the local liquid-water amount varies.',
        'interpretation': 'Conditional local phase-exchange equilibrium only; not a fully coupled steady state, conserved-mass path, material qualification or process qualification.',
        'global_geometry_feasibility': 'not_checked',
        'root_coordinate': 'y=-ln(n/(n+N)); dimensionless',
        'tolerance_policy': 'Root-coordinate xtol and rtol reuse root numerics.atol and numerics.rtol directly.',
        'root_coordinate_atol': atol,
        'root_coordinate_rtol': rtol,
    }
    if sites == 0:
        result['status'] = ('any_positive_water_amount_equilibrium' if phase_affinity_j_mol == 0
                            else 'no_equilibrium_zero_sites')
        return result
    if constant >= 0:
        result['status'] = ('equilibrium_only_at_infinite_water_limit' if constant == 0
                            else 'no_finite_positive_equilibrium')
        return result

    upper = -constant/rt

    def transformed_affinity(y):
        # A+RT*y written about the upper endpoint preserves its exact zero.
        return rt*(y-upper)-binding*(-expm1(-y))**2

    coordinate = brentq(transformed_affinity, 0, upper, xtol=atol, rtol=rtol)
    equilibrium = sites/expm1(coordinate)
    result.update({
        'status': 'unique_finite_positive_equilibrium',
        'n_eq_mol': equilibrium,
        'root_residual_j_mol': constant+rt*coordinate-binding*(-expm1(-coordinate))**2,
        'n_eq_over_n0': equilibrium/n0,
    })
    return result
