"""Zero-storage sorptive surface joining interior water paths to a gas film.

Surface coordinates are material trace values, with no assigned inventory.
Both connections use full enthalpy, so no separate latent source is added.
"""
from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import root

from .gas_transport import ideal_gas_reservoir
from .open_gas_boundary import GasBoundaryTransfer, open_gas_boundary_rate
from .recorded_condensed_transport import combine_faces, condensed_exchange


def surface_state(host, temperature_k, pressure_pa, moisture_kg_kg, carrier_fractions):
    liquid, _, mu, _, pure_pressure = host.pure_liquid(temperature_k, pressure_pa)
    excess = host.excess.evaluate(temperature_k, moisture_kg_kg)
    xv = pure_pressure*excess['activity']/pressure_pa
    fractions = {**{k:(1-xv)*v for k,v in carrier_fractions.items()}, 'H2O':xv}
    gas = ideal_gas_reservoir(temperature_k=temperature_k, pressure_pa=pressure_pa,
        mole_fractions=fractions, molar_masses_kg_mol=host.fluid.molar_masses_kg_mol,
        gas_constant_j_mol_k=host.fluid.thermochemistry.gas_constant_j_mol_k)
    return gas, {'temperature_k':temperature_k, 'pressure_pa':pressure_pa,
        'moisture_kg_kg_dry':moisture_kg_kg, 'gas_mole_fractions':dict(gas.mole_fractions),
        'water_activity':excess['activity'],
        'condensed_chemical_potential_j_mol':mu+excess['mu_j_mol'],
        'condensed_partial_enthalpy_j_mol':liquid.enthalpy_j_mol+excess['partial_h_j_mol']}


@dataclass(frozen=True)
class EvaporatingSurfaceRate:
    exchange: object
    energy_out_w: float
    interior_face: object
    exterior_face: object
    surface: dict
    inventory_rate_residuals_mol_s: dict
    energy_rate_residual_w: float
    root_evaluations: int


class SorptiveEvaporatingSurface:
    def __init__(self, host, config, cell_count):
        self.host=host;self.config=config;self.policy=config['surface_equilibrium']
        self.species=config['boundary_program']['values']['species_order']
        area=config['geometry']['face_area_m2']
        self.inside_distance=config['geometry']['length_m']/cell_count/2
        film=config['transfer']['reservoir_distance_m']
        inside_k=config['transfer']['cell_conductivity_w_m_k']
        outside_k=config['transfer']['reservoir_conductivity_w_m_k']
        self.inside=GasBoundaryTransfer(**{**config['transfer'], 'area_m2':area,
            'cell_distance_m':self.inside_distance/2, 'reservoir_distance_m':self.inside_distance/2,
            'cell_conductivity_w_m_k':inside_k, 'reservoir_conductivity_w_m_k':inside_k})
        self.outside=GasBoundaryTransfer(**{**config['transfer'], 'area_m2':area,
            'cell_distance_m':film/2, 'reservoir_distance_m':film/2,
            'cell_conductivity_w_m_k':outside_k, 'reservoir_conductivity_w_m_k':outside_k})
        self.references=np.array([host.fluid.gas_enthalpy_j_mol(k,self.policy['residual_reference_temperature_k']) for k in self.species])
        self.scales=np.array([self.policy['inventory_residual_scale_mol_s']]*len(self.species)+[self.policy['energy_residual_scale_w']])

    def rate(self, gas, point, reservoir):
        policy=self.policy;host=self.host
        carrier=gas.mole_fractions['O2']/(gas.mole_fractions['O2']+gas.mole_fractions['N2'])
        x0=np.array([point['temperature_k']/policy['temperature_coordinate_scale_k'],
            point['pressure_pa']/policy['pressure_coordinate_scale_pa'],
            math.log(point['moisture_kg_kg_dry']),math.log(carrier/(1-carrier))])

        def evaluate(coordinates):
            t=float(coordinates[0])*policy['temperature_coordinate_scale_k']
            p=float(coordinates[1])*policy['pressure_coordinate_scale_pa']
            w=math.exp(float(coordinates[2]));fraction=1/(1+math.exp(-float(coordinates[3])))
            surface_gas,surface=surface_state(host,t,p,w,{'O2':fraction,'N2':1-fraction})
            inside_gas=open_gas_boundary_rate(gas,surface_gas,self.inside,host.fluid.gas_enthalpy_j_mol)
            condensed=condensed_exchange(point,surface,area_m2=self.inside.area_m2,
                distance_m=self.inside_distance,
                mobility_density_mol2_k_j_s_m=self.config['condensed_transfer']['mobility_density_mol2_k_j_s_m'])
            inside=combine_faces(inside_gas,condensed)
            outside=open_gas_boundary_rate(surface_gas,reservoir,self.outside,host.fluid.gas_enthalpy_j_mol)
            differences=np.array([inside.exchange.net_mol_s[k]-outside.exchange.net_mol_s[k] for k in self.species]+
                [inside.energy_out_w-outside.energy_out_w])
            return inside,outside,surface,differences

        def residual(coordinates):
            differences=evaluate(coordinates)[-1].copy()
            differences[-1]-=differences[:-1]@self.references
            return differences/self.scales

        solution=root(residual,x0,method=policy['method'],
            options={'xtol':policy['coordinate_tolerance'],'maxfev':policy['maximum_function_evaluations']})
        if not solution.success:
            raise RuntimeError('surface equilibrium did not converge: '+solution.message)
        inside,outside,surface,differences=evaluate(solution.x)
        return EvaporatingSurfaceRate(inside.exchange,inside.energy_out_w,inside,outside,surface,
            dict(zip(self.species,map(float,differences[:-1]),strict=True)),float(differences[-1]),int(solution.nfev))
