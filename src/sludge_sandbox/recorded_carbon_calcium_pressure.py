"""Restricted Ca/C/O equilibrium with ideal gas and incompressible pure solids.

This explicitly extends source reference volumes as constants in temperature
and pressure. It does not supply measured high-temperature equations of state.
The elemental domain remains Ctotal > Catotal, Ototal > 3 Catotal, N2 > 0.
"""
import math

import numpy as np
from scipy.optimize import brentq


class RecordedCarbonCalciumPressure:
    def __init__(self, phases, gas_constant_j_mol_k, standard_pressure_pa,
                 solid_volumes_m3_mol, parameters):
        self.phases = phases
        self.r = gas_constant_j_mol_k
        self.p0 = standard_pressure_pa
        self.volumes = solid_volumes_m3_mol
        self.parameters = parameters

    def at_temperature_volume(self, temperature_k, total_volume_m3,
                              calcium_atoms_mol, carbon_atoms_mol,
                              oxygen_atoms_mol, nitrogen_molecules_mol, numerics):
        """Flash a rigid capsule whose volume exceeds the solid upper bound.

        The elemental gas and solid upper bounds give the pressure bracket;
        no guessed pressure floor, composition clipping or fallback is used.
        """
        inputs = (calcium_atoms_mol, carbon_atoms_mol,
                  oxygen_atoms_mol, nitrogen_molecules_mol)
        maximum_solid_volume = calcium_atoms_mol * max(self.volumes['calcite'], self.volumes['lime'])
        maximum_solid_volume += carbon_atoms_mol * self.volumes['C']
        maximum_gas_moles = nitrogen_molecules_mol + carbon_atoms_mol + oxygen_atoms_mol / 2
        rt = self.r * temperature_k
        lower = nitrogen_molecules_mol * rt / total_volume_m3
        upper = maximum_gas_moles * rt / (total_volume_m3 - maximum_solid_volume)
        log_pressure = brentq(lambda value: self.at_temperature_pressure(
            temperature_k, math.exp(value), *inputs)['total_volume_m3'] / total_volume_m3 - 1,
            math.log(lower), math.log(upper),
            xtol=numerics['log_pressure_absolute_tolerance'],
            rtol=numerics['log_pressure_relative_tolerance'],
            maxiter=numerics['maximum_root_iterations'])
        return self.at_temperature_pressure(temperature_k, math.exp(log_pressure), *inputs)

    def from_internal_energy(self, internal_energy_j, total_volume_m3,
                             calcium_atoms_mol, carbon_atoms_mol,
                             oxygen_atoms_mol, nitrogen_molecules_mol, numerics):
        inputs = (total_volume_m3, calcium_atoms_mol, carbon_atoms_mol,
                  oxygen_atoms_mol, nitrogen_molecules_mol, numerics)
        temperature = brentq(lambda value: self.at_temperature_volume(
            value, *inputs)['internal_energy_j'] - internal_energy_j,
            *self.phases['calcite'].temperature_domain_k,
            xtol=numerics['temperature_absolute_tolerance_k'],
            rtol=numerics['temperature_relative_tolerance'],
            maxiter=numerics['maximum_root_iterations'])
        return self.at_temperature_volume(temperature, *inputs)

    def at_temperature_pressure(self, temperature_k, pressure_pa,
                                calcium_atoms_mol, carbon_atoms_mol,
                                oxygen_atoms_mol, nitrogen_molecules_mol):
        t, p = temperature_k, pressure_pa
        rt, pi = self.r * t, p / self.p0
        ca, ct, ot, nn = (calcium_atoms_mol, carbon_atoms_mol,
                          oxygen_atoms_mol, nitrogen_molecules_mol)
        thermal = {name: phase.standard(t) for name, phase in self.phases.items()}
        h = {name: state['enthalpy_j_mol'] for name, state in thermal.items()}
        g = {name: state['gibbs_j_mol'] for name, state in thermal.items()}
        for name, volume in self.volumes.items():
            h[name] += (p - self.p0) * volume
            g[name] += (p - self.p0) * volume
        ln_k1 = -(g['CO'] - g['C'] - g['O2'] / 2) / rt
        ln_k2 = -(g['CO2'] - g['C'] - g['O2']) / rt
        k1, k2 = math.exp(ln_k1), math.exp(ln_k2)
        policy = self.parameters['equilibrium_numerics']

        def partition(fraction):
            calcite = ca * fraction
            carbon, oxygen = ct - calcite, ot - ca - 2 * calcite
            c, o = carbon / nn, oxygen / nn
            a, b = (o + 2) * (k2 + 1), (o + 1) * k1
            q = 2 * o * pi / (b + math.sqrt(b * b + 4 * a * o * pi))
            partial = {'CO': k1 * q, 'CO2': k2 * q * q, 'O2': q * q}
            partial['N2'] = (partial['CO'] + 2 * partial['CO2'] + 2 * partial['O2']) / o
            gas = {name: nn * value / partial['N2'] for name, value in partial.items()}
            gas['N2'] = nn
            required = math.fsum((gas['CO'], gas['CO2']))
            if carbon >= required:
                solid_carbon = carbon - required
                carbon_phase = 'graphite_present'
            else:
                solid_carbon = 0.
                carbon_phase = 'graphite_exhausted'
                delta, ln_k3 = o - c, ln_k2 - ln_k1
                # The positive oxygen surplus brackets the gas-only root.
                lower = min(math.log(delta / 8), 2 * math.log(delta)
                            + math.log1p(c) - math.log(16) - 2 * math.log(c)
                            - 2 * ln_k3 - math.log(pi))
                upper = math.log(delta / 2)

                def residual(log_z):
                    z = math.exp(log_z)
                    w = math.exp(ln_k3) * math.sqrt(pi * z / (1 + c + z))
                    return c * (1 + w / (1 + w)) + 2 * z - o

                z = math.exp(brentq(residual, lower, upper,
                    xtol=policy['log_oxygen_absolute_tolerance'],
                    rtol=policy['log_oxygen_relative_tolerance'],
                    maxiter=policy['maximum_root_iterations']))
                w = math.exp(ln_k3) * math.sqrt(pi * z / (1 + c + z))
                gas = {'CO': carbon / (1 + w), 'CO2': carbon * w / (1 + w),
                       'O2': nn * z, 'N2': nn}
                ng = math.fsum(gas.values())
                partial = {name: pi * value / ng for name, value in gas.items()}
            amounts = {'calcite': calcite, 'lime': ca - calcite, 'C': solid_carbon, **gas}
            mu = {name: g[name] + rt * math.log(value) for name, value in partial.items()}
            mu.update({name: g[name] for name in self.volumes})
            affinity = mu['lime'] + mu['CO2'] - mu['calcite']
            return amounts, partial, mu, carbon_phase, affinity

        state = partition(1.)
        if state[-1] >= 0:
            fraction, calcium_phase = 1., 'calcite'
        else:
            state = partition(0.)
            if state[-1] <= 0:
                fraction, calcium_phase = 0., 'lime'
            else:
                calcium_phase = 'coexistence'
                fraction = brentq(lambda value: partition(value)[-1], 0., 1.,
                    xtol=policy['calcite_fraction_absolute_tolerance'],
                    rtol=policy['calcite_fraction_relative_tolerance'],
                    maxiter=policy['maximum_root_iterations'])
                state = partition(fraction)
        n, partial, mu, carbon_phase, affinity = state
        gas_names = ['CO', 'CO2', 'O2', 'N2']
        ng = math.fsum(n[name] for name in gas_names)
        solid_volume = math.fsum(n[name] * volume for name, volume in self.volumes.items())
        gas_volume = ng * rt / p
        total_volume = solid_volume + gas_volume
        enthalpy = math.fsum(n[name] * h[name] for name in n)
        entropy = math.fsum(n[name] * thermal[name]['entropy_j_mol_k'] for name in n)
        entropy -= self.r * math.fsum(n[name] * math.log(partial[name]) for name in gas_names)
        response = self.caloric_response(t, p, n, calcium_phase, carbon_phase, thermal, h)
        return {'temperature_k': t, 'pressure_pa': p, 'calcium_phase': calcium_phase,
            'carbon_phase': carbon_phase, 'calcite_fraction': fraction, 'amounts_mol': n,
            'partial_pressures_pa': {name: self.p0 * value for name, value in partial.items()},
            'chemical_potentials_j_mol': mu, 'calcination_gibbs_j_mol': affinity,
            'enthalpy_j': enthalpy, 'entropy_j_k': entropy, 'gibbs_j': enthalpy - t * entropy,
            'internal_energy_j': enthalpy - p * total_volume,
            'helmholtz_j': enthalpy - p * total_volume - t * entropy,
            'gas_volume_m3': gas_volume, 'solid_volume_m3': solid_volume,
            'total_volume_m3': total_volume, **response}


    def caloric_response(self, t, p, n, calcium_phase, carbon_phase, thermal, h):
        """Same-phase reaction-Hessian response shared by both static domains."""
        rt = self.r*t
        gas_names = ['CO', 'CO2', 'O2', 'N2']
        ng = math.fsum(n[name] for name in gas_names)
        names = self.parameters['phase_order']
        basis = self.parameters['coexistence_basis' if calcium_phase == 'coexistence'
                                else 'fixed_calcium_basis'][carbon_phase]
        stoichiometry = np.array([[self.parameters['reaction_stoichiometry'][reaction][name]
                                  for reaction in basis] for name in names])
        gas_stoichiometry = np.array([stoichiometry[names.index(name)] for name in gas_names])
        gas_amounts = np.array([n[name] for name in gas_names])
        gas_change = np.sum(gas_stoichiometry, axis=0)
        matrix = rt * (gas_stoichiometry.T @ np.diag(1 / gas_amounts) @ gas_stoichiometry
                       - np.outer(gas_change, gas_change) / ng)
        partial_volumes = {**self.volumes, **{name: rt / p for name in gas_names}}
        reaction_h = stoichiometry.T @ np.array([h[name] for name in names])
        reaction_v = stoichiometry.T @ np.array([partial_volumes[name] for name in names])
        extent_t = np.linalg.solve(matrix, reaction_h / t)
        extent_p = np.linalg.solve(matrix, -reaction_v)
        dn_t = stoichiometry @ extent_t
        dn_p = stoichiometry @ extent_p
        frozen_cp = math.fsum(n[name] * thermal[name]['cp_j_mol_k'] for name in names)
        cp = frozen_cp + float(reaction_h @ extent_t)
        volume_t = ng * self.r / p + float(reaction_v @ extent_t)
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
