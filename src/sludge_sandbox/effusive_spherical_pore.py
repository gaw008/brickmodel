"""Energy-consistent gas exchange for a deforming pore and finite gas chamber.

The negligible-area ideal port is a lumped approximation. Its transport area
does not remove surface energy or traction from the leading-order sphere.
"""
import math

from .molecular_effusion import effusive_exchange


class EffusiveSphericalPore:
    def __init__(self, closed_pore, reservoir, connection, molecular_source):
        self.closed = closed_pore
        self.p = closed_pore.p
        self.r = closed_pore.r
        self.reservoir = reservoir
        self.connection = connection
        self.area = math.pi*connection['aperture_radius_m']**2
        row = molecular_source['species'][connection['molar_mass_species']]
        constants = molecular_source['constants']
        self.molar_mass = float(row['molar_mass_g_mol'])*float(constants['gram_kg'])
        self.diameter = float(row['diameter_angstrom'])*float(constants['angstrom_m'])
        self.avogadro = float(constants['avogadro_mol_inverse'])

    def gas(self, temperature, amount, volume):
        source = self.closed.phase.standard(temperature)
        pressure = amount*self.r*temperature/volume
        h = source['enthalpy_j_mol']
        s = source['entropy_j_mol_k']-self.r*math.log(pressure/self.p['standard_pressure_pa'])
        return {'temperature_k':temperature,'pressure_pa':pressure,
                'partial_pressures_pa':[pressure], 'enthalpies_j_mol':[h],
                'chemical_potentials_j_mol':[h-temperature*s],
                'molar_internal_energy_j_mol':h-self.r*temperature,
                'molar_entropy_j_mol_k':s,'cv_j_k':amount*(source['cp_j_mol_k']-self.r),
                'amount_mol':amount,'volume_m3':volume}

    def at_state(self, radius, pore_temperature, reservoir_temperature, pore_amount,
                 reservoir_amount, boundary):
        pore = self.closed.at_state(radius,pore_temperature,pore_amount,
            boundary['pore_bath_temperature_k'],boundary['pore_heat_conductance_w_k'])
        gases = [self.gas(pore_temperature,pore_amount,pore['pore_volume_m3']),
                 self.gas(reservoir_temperature,reservoir_amount,self.reservoir['volume_m3'])]
        exchange = effusive_exchange(*gases,[self.molar_mass],self.r,self.area)
        flow = float(exchange['species_mol_s'][0]); energy = exchange['energy_w']
        body_cv = self.reservoir['body_heat_capacity_j_k']
        reservoir_cv = gases[1]['cv_j_k']+body_cv
        q = boundary['reservoir_heat_conductance_w_k']*(boundary['reservoir_bath_temperature_k']-reservoir_temperature)
        pore_rate = pore['temperature_rate_k_s']+(-energy+gases[0]['molar_internal_energy_j_mol']*flow)/pore['cv_j_k']
        reservoir_rate = (q+energy-gases[1]['molar_internal_energy_j_mol']*flow)/reservoir_cv
        reservoir_energy = reservoir_amount*gases[1]['molar_internal_energy_j_mol']+body_cv*(reservoir_temperature-self.p['reference_temperature_k'])
        reservoir_entropy = reservoir_amount*gases[1]['molar_entropy_j_mol_k']+body_cv*math.log(reservoir_temperature/self.p['reference_temperature_k'])
        reservoir_heat_production = q*(1/reservoir_temperature-1/boundary['reservoir_bath_temperature_k'])
        bath_entropy = pore['bath_entropy_rate_w_k']-q/boundary['reservoir_bath_temperature_k']
        effusion_production = float(exchange['entropy_production_w_k'])
        pore['temperature_rate_k_s'] = pore_rate
        pore['entropy_rate_w_k'] += (-energy+gases[0]['chemical_potentials_j_mol'][0]*flow)/pore_temperature
        # Molecular size and mean-free-path figures are regime diagnostics,
        # based on the selected LJ diameter treated as a nominal hard sphere.
        paths = [self.r/self.avogadro*g['temperature_k']/(math.sqrt(2)*math.pi*self.diameter**2*g['pressure_pa']) for g in gases]
        return {'pore':pore,'gases':gases,'radius_m':radius,
                'pore_temperature_k':pore_temperature,'reservoir_temperature_k':reservoir_temperature,
                'pore_amount_mol':pore_amount,'reservoir_amount_mol':reservoir_amount,
                'radius_rate_m_s':pore['radius_rate_m_s'],
                'pore_temperature_rate_k_s':pore_rate,'reservoir_temperature_rate_k_s':reservoir_rate,
                'gas_transfer_mol_s':flow,'effusive_energy_w':energy,
                'one_way_species_mol_s':exchange['one_way_species_mol_s'][:,0].tolist(),
                'pore_heat_in_w':pore['heat_in_w'],'reservoir_heat_in_w':q,
                'external_work_in_w':pore['external_work_in_w'],
                'viscous_dissipation_w':pore['viscous_dissipation_w'],
                'internal_energy_j':pore['internal_energy_j']+reservoir_energy,
                'entropy_j_k':pore['entropy_j_k']+reservoir_entropy,
                'bath_entropy_rate_w_k':bath_entropy,
                'effusion_entropy_production_w_k':effusion_production,
                'heat_entropy_production_w_k':pore['heat_entropy_production_w_k']+reservoir_heat_production,
                'entropy_production_w_k':pore['entropy_production_w_k']+reservoir_heat_production+effusion_production,
                'port_area_over_pore_area':self.area/(4*math.pi*radius**2),
                'nominal_mean_free_paths_m':paths,
                'nominal_mean_free_path_over_port_radius':[x/self.connection['aperture_radius_m'] for x in paths]}
