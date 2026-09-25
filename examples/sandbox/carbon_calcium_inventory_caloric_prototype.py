"""Unmodified reaction-Hessian caloric closure on the new static prototype.

Research only: qualification across trace phases is still pending.
"""
import math
import numpy as np


def caloric_response(model, state):
    t, p, n = state['temperature_k'], state['pressure_pa'], state['amounts_mol']
    rt = model.r*t
    calcium_phase, carbon_phase = state['calcium_phase'], state['carbon_phase']
    gas_names = ['CO', 'CO2', 'O2', 'N2']
    ng = math.fsum(n[name] for name in gas_names)
    thermal = {name: phase.standard(t) for name, phase in model.phases.items()}
    h = {name: value['enthalpy_j_mol'] for name, value in thermal.items()}
    for name, volume in model.volumes.items():
        h[name] += (p-model.p0)*volume
    names = model.parameters['phase_order']
    basis = model.parameters['coexistence_basis' if calcium_phase == 'coexistence'
                            else 'fixed_calcium_basis'][carbon_phase]
    stoichiometry = np.array([[model.parameters['reaction_stoichiometry'][reaction][name]
                              for reaction in basis] for name in names])
    gas_stoichiometry = np.array([stoichiometry[names.index(name)] for name in gas_names])
    gas_amounts = np.array([n[name] for name in gas_names])
    gas_change = np.sum(gas_stoichiometry, axis=0)
    matrix = rt * (gas_stoichiometry.T @ np.diag(1 / gas_amounts) @ gas_stoichiometry
                   - np.outer(gas_change, gas_change) / ng)
    partial_volumes = {**model.volumes, **{name: rt / p for name in gas_names}}
    reaction_h = stoichiometry.T @ np.array([h[name] for name in names])
    reaction_v = stoichiometry.T @ np.array([partial_volumes[name] for name in names])
    extent_t = np.linalg.solve(matrix, reaction_h / t)
    extent_p = np.linalg.solve(matrix, -reaction_v)
    dn_t = stoichiometry @ extent_t
    dn_p = stoichiometry @ extent_p
    frozen_cp = math.fsum(n[name] * thermal[name]['cp_j_mol_k'] for name in names)
    cp = frozen_cp + float(reaction_h @ extent_t)
    volume_t = ng * model.r / p + float(reaction_v @ extent_t)
    volume_p = -ng * rt / (p * p) + float(reaction_v @ extent_p)
    pressure_t_at_v = -volume_t / volume_p
    dn_t_at_v = dn_t + dn_p * pressure_t_at_v
    cv = cp + t * volume_t * volume_t / volume_p

    return {'frozen_cp_j_k': frozen_cp,
        'equilibrium_cp_j_k': cp, 'equilibrium_cv_j_k': cv,
        'volume_temperature_derivative_m3_k': volume_t,
        'volume_pressure_derivative_m3_pa': volume_p,
        'pressure_temperature_derivative_at_volume_pa_k': pressure_t_at_v,
        'amount_temperature_derivatives_mol_k': dict(zip(names, map(float, dn_t), strict=True)),
        'amount_pressure_derivatives_mol_pa': dict(zip(names, map(float, dn_p), strict=True)),
        'amount_temperature_derivatives_at_volume_mol_k': dict(zip(names, map(float, dn_t_at_v), strict=True)),
        'active_reaction_basis': basis}
