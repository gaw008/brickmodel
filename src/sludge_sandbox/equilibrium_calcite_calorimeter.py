"""Isobaric pure-solid equilibrium calorimeter coupled to a CO2 reservoir."""
import math

from scipy.optimize import brentq

from .exchanges import boundary_heat


class EquilibriumCalciteCalorimeter:
    def __init__(self, reaction, config, equilibrium_root_policy):
        self.reaction=reaction;self.config=config;self.amount=config['initial_calcite_mol']
        self.reactant=reaction.phases[config['reactant_phase']]
        self.product=reaction.phases[config['product_phase']]
        self.pressure=config['co2_partial_pressure_pa'];p=equilibrium_root_policy
        self.equilibrium_temperature=brentq(lambda t:reaction.affinity(t,self.pressure)['affinity_j_mol_extent'],
            *p['bracket_k'],xtol=p['absolute_tolerance_k'],rtol=p['relative_tolerance'],maxiter=p['maximum_iterations'])
        a=self.reactant.standard(self.equilibrium_temperature);b=self.product.standard(self.equilibrium_temperature)
        self.limits=(self.amount*a['enthalpy_j_mol'],self.amount*b['enthalpy_j_mol'])
        self.solid_reaction_enthalpy=b['enthalpy_j_mol']-a['enthalpy_j_mol']

    def state(self, enthalpy_j):
        if self.limits[0]<=enthalpy_j<=self.limits[1]:
            t=self.equilibrium_temperature
            extent=(enthalpy_j-self.limits[0])/self.solid_reaction_enthalpy
            slope=1/self.solid_reaction_enthalpy;phase='coexistence'
        else:
            phase='calcite' if enthalpy_j<self.limits[0] else 'lime'
            selected=self.reactant if phase=='calcite' else self.product
            extent=0. if phase=='calcite' else self.amount;slope=0.
            p=self.config['numerics']
            t=brentq(lambda t:self.amount*selected.standard(t)['enthalpy_j_mol']-enthalpy_j,
                *selected.temperature_domain_k,xtol=p['temperature_inverse_absolute_k'],
                rtol=p['temperature_inverse_relative'],maxiter=p['temperature_inverse_iterations'])
        a=self.reactant.standard(t);b=self.product.standard(t);gas=self.reaction.phases[self.reaction.gas_phase].standard(t)
        gas_entropy=gas['entropy_j_mol_k']-self.reaction.gas_constant_j_mol_k*math.log(self.pressure/self.reaction.standard_pressure_pa)
        return {'enthalpy_j':enthalpy_j,'temperature_k':t,'extent_mol':extent,'phase':phase,
            'calcite_mol':self.amount-extent,'lime_mol':extent,'extent_derivative_mol_j':slope,
            'entropy_j_k':(self.amount-extent)*a['entropy_j_mol_k']+extent*b['entropy_j_mol_k'],
            'co2_enthalpy_j_mol':gas['enthalpy_j_mol'],'co2_entropy_j_mol_k':gas_entropy,
            'constitutive_enthalpy_j':(self.amount-extent)*a['enthalpy_j_mol']+extent*b['enthalpy_j_mol']}

    def rates(self, enthalpy_j, wall_temperature_k):
        state=self.state(enthalpy_j);t=state['temperature_k']
        q=self.heat_rate(t,wall_temperature_k)
        hdot=q/(1+state['co2_enthalpy_j_mol']*state['extent_derivative_mol_j'])
        extent_rate=state['extent_derivative_mol_j']*hdot
        return [hdot,extent_rate,q,state['co2_enthalpy_j_mol']*extent_rate,
            q/wall_temperature_k,state['co2_entropy_j_mol_k']*extent_rate,q*(1/t-1/wall_temperature_k)]

    def heat_rate(self, temperature_k, wall_temperature_k):
        if 'radiation' in self.config:
            p=self.config['radiation']
            return boundary_heat(surface_temperature_k=temperature_k,gas_temperature_k=wall_temperature_k,
                radiation_temperature_k=wall_temperature_k,area_m2=p['area_m2'],
                convection_w_m2_k=self.config['heat_conductance_w_k']/p['area_m2'],
                emissivity=p['emissivity'],stefan_boltzmann_w_m2_k4=p['stefan_boltzmann_w_m2_k4']).total_in_w
        return self.config['heat_conductance_w_k']*(wall_temperature_k-temperature_k)

    def heat_temperature_derivative(self, temperature_k):
        derivative=-self.config['heat_conductance_w_k']
        if 'radiation' in self.config:
            p=self.config['radiation']
            derivative-=4*p['area_m2']*p['emissivity']*p['stefan_boltzmann_w_m2_k4']*temperature_k**3
        return derivative

    def enthalpy_rate_derivative(self, enthalpy_j, wall_temperature_k):
        state=self.state(enthalpy_j)
        if state['phase']=='coexistence':
            return [0.]*7
        t=state['temperature_k'];phase=self.reactant if state['phase']=='calcite' else self.product
        temperature_derivative=1/(self.amount*phase.standard(t)['cp_j_mol_k'])
        q=self.heat_rate(t,wall_temperature_k);slope=self.heat_temperature_derivative(t)
        heat_derivative=slope*temperature_derivative
        production_derivative=(slope*(1/t-1/wall_temperature_k)-q/t**2)*temperature_derivative
        return [heat_derivative,0.,heat_derivative,0.,heat_derivative/wall_temperature_k,0.,production_derivative]
