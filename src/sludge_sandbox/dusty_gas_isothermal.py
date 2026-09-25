"""Isothermal ideal-gas Dusty Gas law in the stationary porous-solid frame.

Cantera 3.2 DustyGasTransport.h/.cpp supply the original concentration-gradient
equations and effective Knudsen coefficients. Here the diffusive part is solved
as a symmetric velocity-friction system; Darcy motion is added explicitly.
All pore and fluid properties are supplied, with no implicit permeability.
Fluxes use bulk cross-sectional area; c is per gas volume. Returned velocities
are superficial flux/c quantities, not the actual mean speed inside a pore.
"""
import numpy as np


def effective_knudsen_diffusivities(temperature_k, gas_constant_j_mol_k,
        molar_masses_kg_mol, pore_radius_m, porosity, tortuosity):
    masses = np.asarray(molar_masses_kg_mol)
    return (2/3*pore_radius_m*porosity/tortuosity
        *np.sqrt(8*gas_constant_j_mol_k*temperature_k/(np.pi*masses)))


def isothermal_dusty_gas_fluxes(mole_fractions, log_partial_concentration_gradient_per_m,
        temperature_k, pressure_pa, gas_constant_j_mol_k, effective_binary_diffusivities_m2_s,
        effective_knudsen_diffusivities_m2_s, viscosity_pa_s, permeability_m2):
    fractions = np.asarray(mole_fractions)
    gradient = np.asarray(log_partial_concentration_gradient_per_m)
    diffusion = np.asarray(effective_binary_diffusivities_m2_s)
    knudsen = np.asarray(effective_knudsen_diffusivities_m2_s)
    concentration = pressure_pa/(gas_constant_j_mol_k*temperature_k)
    count = len(fractions)
    friction = np.diag(fractions/knudsen)
    for i in range(count):
        for j in range(i+1, count):
            coefficient = fractions[i]*fractions[j]/diffusion[i, j]
            friction[i, i] += coefficient
            friction[j, j] += coefficient
            friction[i, j] -= coefficient
            friction[j, i] -= coefficient
    velocities = np.linalg.solve(friction, -fractions*gradient)
    pressure_gradient = pressure_pa*np.dot(fractions, gradient)
    darcy_velocity = -permeability_m2/viscosity_pa_s*pressure_gradient
    diffusive = concentration*fractions*velocities
    viscous = concentration*fractions*darcy_velocity
    total = diffusive+viscous
    molecular_entropy = concentration*gas_constant_j_mol_k*sum(
        fractions[i]*fractions[j]/diffusion[i, j]*(velocities[i]-velocities[j])**2
        for i in range(count) for j in range(i+1, count))
    wall_entropy = concentration*gas_constant_j_mol_k*np.sum(fractions*velocities**2/knudsen)
    darcy_entropy = permeability_m2/(viscosity_pa_s*temperature_k)*pressure_gradient**2
    force_entropy = -gas_constant_j_mol_k*np.dot(total, gradient)
    return {'molar_fluxes_mol_m2_s': total, 'diffusive_fluxes_mol_m2_s': diffusive,
        'darcy_fluxes_mol_m2_s': viscous,
        'diffusive_superficial_velocities_m_s': velocities, 'darcy_superficial_velocity_m_s': float(darcy_velocity),
        'pressure_gradient_pa_m': float(pressure_gradient),
        'entropy_force_w_m3_k': float(force_entropy),
        'entropy_molecular_w_m3_k': float(molecular_entropy),
        'entropy_wall_w_m3_k': float(wall_entropy), 'entropy_darcy_w_m3_k': float(darcy_entropy),
        'entropy_sum_w_m3_k': float(molecular_entropy+wall_entropy+darcy_entropy)}
