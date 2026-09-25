"""Ballistic exchange through a thin aperture between ideal-gas reservoirs.

The hole is small compared with the mean free path. Each reservoir has a
Maxwell distribution and equilibrated internal modes. No intermolecular or
wall collisions occur inside the zero-thickness aperture. Positive partial
pressures and source-admitted temperatures are caller inputs.
"""
import math

import numpy as np


def effusive_exchange(left, right, molar_masses, gas_constant, area_m2):
    temperatures = np.array([left['temperature_k'], right['temperature_k']])
    pressures = np.array([left['partial_pressures_pa'], right['partial_pressures_pa']])
    enthalpies = np.array([left['enthalpies_j_mol'], right['enthalpies_j_mol']])
    chemical = np.array([left['chemical_potentials_j_mol'], right['chemical_potentials_j_mol']])
    one_way = area_m2*pressures/np.sqrt(2*np.pi*np.asarray(molar_masses)*gas_constant*temperatures[:, None])
    # Velocity weighting adds RT/2 to the bulk internal energy h-RT.
    crossing_energy = enthalpies-gas_constant*temperatures[:, None]/2
    energy_by_species = one_way[0]*crossing_energy[0]-one_way[1]*crossing_energy[1]
    species = one_way[0]-one_way[1]
    energy = math.fsum(energy_by_species)
    left_entropy = (-energy+float(np.dot(chemical[0], species)))/temperatures[0]
    right_entropy = (energy-float(np.dot(chemical[1], species)))/temperatures[1]
    return {'one_way_species_mol_s': one_way, 'crossing_energies_j_mol': crossing_energy,
            'species_mol_s': species, 'energy_by_species_w': energy_by_species,
            'energy_w': energy, 'left_entropy_w_k': left_entropy,
            'right_entropy_w_k': right_entropy, 'entropy_production_w_k': left_entropy+right_entropy}


class EffusionGasState:
    """Same NIST Shomate enthalpy/Cp and standard entropy on each fit branch."""
    def __init__(self, thermochemistry, species_order, reference_pressure_pa):
        self.thermochemistry = thermochemistry
        self.species = species_order
        self.gases = [thermochemistry.species(name) for name in species_order]
        self.r = thermochemistry.gas_constant_j_mol_k
        self.p0 = reference_pressure_pa

    def at_temperature_pressure(self, temperature, partial_pressures):
        temperature = float(temperature)
        h = np.array([gas.enthalpy_j_mol(temperature) for gas in self.gases])
        cp = np.array([gas.cp_j_mol_k(temperature) for gas in self.gases])
        entropies = []
        t = temperature/1000
        for gas, pressure in zip(self.gases, partial_pressures, strict=True):
            a,b,c,d,e,_,g,_ = gas.segment_for(temperature).coefficients
            standard = a*math.log(t)+b*t+c*t*t/2+d*t**3/3-e/(2*t*t)+g
            entropies.append(standard-self.r*math.log(pressure/self.p0))
        s = np.array(entropies)
        return {'temperature_k': temperature, 'partial_pressures_pa': np.asarray(partial_pressures),
                'pressure_pa': math.fsum(partial_pressures), 'enthalpies_j_mol': h,
                'internal_energies_j_mol': h-self.r*temperature,
                'entropies_j_mol_k': s, 'chemical_potentials_j_mol': h-temperature*s,
                'cp_j_mol_k': cp, 'cv_j_mol_k': cp-self.r}

    def at_temperature_inventory(self, temperature, amounts, volume):
        n = np.asarray(amounts)
        state = self.at_temperature_pressure(temperature, n*self.r*temperature/volume)
        return {**state, 'amounts_mol': n, 'volume_m3': volume,
                'internal_energy_j': float(np.dot(n, state['internal_energies_j_mol'])),
                'entropy_j_k': float(np.dot(n, state['entropies_j_mol_k'])),
                'heat_capacity_cv_j_k': float(np.dot(n, state['cv_j_mol_k']))}


class FixedTemperatureEffusionReservoirs:
    """Finite gas inventories with distinct, externally maintained temperatures."""
    def __init__(self, parameters, thermal_state, molar_masses):
        self.parameters, self.thermal, self.masses = parameters, thermal_state, molar_masses
        self.species_count = len(molar_masses)
        self.temperatures = np.asarray(parameters['temperatures_k'])
        self.volumes = np.asarray(parameters['volumes_m3'])
        self.area = parameters['area_m2']
        pressures = np.asarray(parameters['initial_partial_pressures_pa'])
        amounts = pressures*self.volumes[:, None]/(thermal_state.r*self.temperatures[:, None])
        self.initial = np.concatenate((amounts.ravel(), np.zeros(3)))

    def observe(self, values):
        n = np.asarray(values[:2*self.species_count]).reshape(2, self.species_count)
        states = [self.thermal.at_temperature_inventory(t, row, volume)
                  for t,row,volume in zip(self.temperatures, n, self.volumes, strict=True)]
        exchange = effusive_exchange(*states, self.masses, self.thermal.r, self.area)
        j, energy = exchange['species_mol_s'], exchange['energy_w']
        heat = np.array([energy-float(np.dot(states[0]['internal_energies_j_mol'],j)),
                         float(np.dot(states[1]['internal_energies_j_mol'],j))-energy])
        return states, exchange, heat

    def rates(self, at, values):
        _, exchange, heat = self.observe(values)
        flow = exchange['species_mol_s']
        return np.concatenate((-flow, flow, heat, [exchange['entropy_production_w_k']]))
