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


def free_water_ledger(config, start, end, *, boundary_in_mol,
                      boundary_out_mol) -> dict:
    """Account liquid water plus pore H2O from cumulative endpoint differences.

    No conditional roots are evaluated. Free water excludes hydrogen bound in
    minerals and organics; chemical reaction water sources are explicit.
    Internal redistribution is inferred, not independently integrated.
    """
    import numpy as np

    liquid_start = np.asarray(start['liquid_water_inventory_mol'])
    liquid_end = np.asarray(end['liquid_water_inventory_mol'])
    vapor_start = np.asarray(start['gas_inventory_mol']['H2O'])
    vapor_end = np.asarray(end['gas_inventory_mol']['H2O'])
    liquid_change = liquid_end-liquid_start
    vapor_change = vapor_end-vapor_start
    liquid_reaction = np.zeros_like(liquid_start)
    vapor_reaction = np.zeros_like(vapor_start)
    reaction_water = {}
    for reaction in config['reactions']:
        name = reaction['id']
        extent = (np.asarray(end['reaction_extent_mol'][name])
                  -np.asarray(start['reaction_extent_mol'][name]))
        liquid = extent*reaction['stoichiometry'].get('water', 0)
        vapor = extent*reaction['stoichiometry'].get('H2O', 0)
        liquid_reaction += liquid
        vapor_reaction += vapor
        reaction_water[name] = {
            'signed_extent_mol_by_cell': extent.tolist(),
            'liquid_water_source_mol_by_cell': liquid.tolist(),
            'vapor_water_source_mol_by_cell': vapor.tolist(),
            'total_free_water_source_mol': float(np.sum(liquid+vapor)),
            'role': 'phase_exchange' if name == 'evaporation' else 'chemical_reaction',
        }
    redistribution = liquid_change-liquid_reaction
    net_boundary_out = boundary_out_mol-boundary_in_mol
    chemical_source = sum(item['total_free_water_source_mol'] for item in reaction_water.values()
                          if item['role'] == 'chemical_reaction')
    return {
        'identity': 'simulation', 'constitutive_identity': 'assumed',
        'start_time_s': start['time_s'], 'end_time_s': end['time_s'],
        'inventory_definition': 'Free water is liquid water plus pore-gas H2O; it is not total water-equivalent hydrogen including minerals or organics.',
        'units': 'mol of H2O; signed changes over the reported interval',
        'sign_convention': 'Reaction sources are positive into each inventory. Evaporation extent is positive liquid-to-vapor and negative for condensation. Boundary in/out are separately nonnegative; net outward is out minus in. Cell redistribution is positive for net liquid gain from internal faces; the liquid exterior is closed.',
        'accounting_basis': 'Reaction extent differences and gas boundary in/out differences use existing solver-integrated ledgers. Cell liquid redistribution is inferred as liquid inventory change minus stoichiometric liquid reaction sources; it includes numerical inventory/extent mismatch and is not an independent flux-integral check.',
        'liquid_initial_mol_by_cell': liquid_start.tolist(),
        'liquid_final_mol_by_cell': liquid_end.tolist(),
        'liquid_change_mol_by_cell': liquid_change.tolist(),
        'liquid_reaction_source_mol_by_cell': liquid_reaction.tolist(),
        'internal_liquid_redistribution_inferred_mol_by_cell': redistribution.tolist(),
        'internal_liquid_redistribution_sum_residual_mol': float(redistribution.sum()),
        'pore_vapor_initial_mol_by_cell': vapor_start.tolist(),
        'pore_vapor_final_mol_by_cell': vapor_end.tolist(),
        'pore_vapor_change_mol_by_cell': vapor_change.tolist(),
        'vapor_reaction_source_mol_by_cell': vapor_reaction.tolist(),
        'reaction_water_sources': reaction_water,
        'non_phase_chemical_free_water_source_mol': chemical_source,
        'boundary_vapor_in_mol': float(boundary_in_mol),
        'boundary_vapor_out_mol': float(boundary_out_mol),
        'boundary_vapor_net_out_mol': float(net_boundary_out),
        'pore_vapor_balance_residual_mol': float(vapor_change.sum()-vapor_reaction.sum()+net_boundary_out),
        'total_free_water_change_mol': float(liquid_change.sum()+vapor_change.sum()),
        'total_free_water_balance_residual_mol': float(liquid_change.sum()+vapor_change.sum()-liquid_reaction.sum()-vapor_reaction.sum()+net_boundary_out),
        'reaction_source_note': 'Non-phase reaction water is taken from each existing reaction stoichiometry and signed extent; retention-site loss creates no separate water source. Internal liquid and gas transfers cancel in whole-domain water accounting.',
    }


def drying_water_diagnostics(config, start, end, *, boundary_in_mol,
                             boundary_out_mol) -> dict:
    """Evaluate same-state conditional roots only at the drying endpoint."""
    cells = []
    for i, (water, sites, temperature, affinity) in enumerate(zip(
            end['liquid_water_inventory_mol'], end['water_retention_sites_mol'],
            end['temperature_k'], end['water_phase_affinity_j_mol'])):
        inputs = {'water_moles': float(water), 'sites_mol': float(sites),
                  'temperature_k': float(temperature),
                  'phase_affinity_j_mol': float(affinity)}
        cells.append({'cell_index': i, 'x_m': end['x_m'][i], 'inputs': inputs,
                      'conditional_equilibrium': frozen_water_equilibrium(config, **inputs)})
    return {
        'identity': 'simulation', 'constitutive_identity': 'assumed',
        'stage': 'drying', 'start_time_s': start['time_s'], 'end_time_s': end['time_s'],
        'end_state_cells': cells,
        'global_geometry_feasibility': 'not_checked',
        'interpretation': 'Same-state conditional roots at drying end only; no coupled steady-state, conserved-mass path or material/process qualification is inferred.',
        'free_water_ledger': free_water_ledger(
            config, start, end, boundary_in_mol=boundary_in_mol,
            boundary_out_mol=boundary_out_mol),
    }
