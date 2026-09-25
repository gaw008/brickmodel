"""Local ideal-gas Maxwell-Stefan fluxes at uniform temperature and pressure.

Positive mole fractions, symmetric positive binary diffusivities and a
zero-sum composition gradient are explicit mathematical preconditions.
No Darcy, Knudsen, Soret, reaction or finite-face approximation is included.
"""
import numpy as np


def local_fluxes(mole_fractions, gradient_per_m, binary_diffusivities_m2_s,
                 concentration_mol_m3, molar_masses_kg_mol, gas_constant_j_mol_k):
    x = np.asarray(mole_fractions, dtype=float)
    gradient = np.asarray(gradient_per_m, dtype=float)
    diffusivity = np.asarray(binary_diffusivities_m2_s, dtype=float)
    masses = np.asarray(molar_masses_kg_mol, dtype=float)
    count = len(x)
    friction = np.zeros((count, count))
    for i in range(count):
        for j in range(i+1, count):
            coefficient = x[i]*x[j]/diffusivity[i, j]
            friction[i, i] += coefficient
            friction[j, j] += coefficient
            friction[i, j] -= coefficient
            friction[j, i] -= coefficient
    system = np.zeros((count+1, count+1))
    system[:count, :count] = friction
    system[:count, count] = x
    system[count, :count] = x
    solution = np.linalg.solve(system, np.concatenate((-gradient, [0.0])))
    velocities = solution[:count]
    molar_fluxes = concentration_mol_m3*x*velocities
    mass_mean_velocity = np.dot(masses, molar_fluxes)/(concentration_mol_m3*np.dot(masses, x))
    mass_frame_molar_fluxes = molar_fluxes-concentration_mol_m3*x*mass_mean_velocity
    entropy_from_force = -gas_constant_j_mol_k*np.dot(molar_fluxes, gradient/x)
    entropy_from_friction = concentration_mol_m3*gas_constant_j_mol_k*sum(
        x[i]*x[j]/diffusivity[i, j]*(velocities[i]-velocities[j])**2
        for i in range(count) for j in range(i+1, count))
    return {
        'molar_frame_fluxes_mol_m2_s': molar_fluxes,
        'molar_frame_velocities_m_s': velocities,
        'mass_frame_molar_fluxes_mol_m2_s': mass_frame_molar_fluxes,
        'mass_mean_velocity_relative_to_molar_m_s': float(mass_mean_velocity),
        'entropy_force_w_m3_k': float(entropy_from_force),
        'entropy_friction_w_m3_k': float(entropy_from_friction),
        'friction_matrix_s_m2': friction,
        'constraint_multiplier_per_m': float(solution[count]),
    }
