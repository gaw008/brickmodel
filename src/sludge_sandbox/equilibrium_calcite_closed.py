"""Closed, constant-pressure calcite / lime / CO2 / N2 equilibrium calorimeter.

Total enthalpy includes every retained phase. Gas partial pressure follows
the finite mole inventory. A frictionless pressure reservoir supplies only
pV work; no prescribed CO2 reservoir or reaction-rate constant is used.
"""
import math

from scipy.optimize import brentq

from .exchanges import boundary_heat


class ClosedCalciteMixture:
    def __init__(self,reaction,nitrogen,config,root_policy):
        self.reaction=reaction;self.nitrogen=nitrogen;self.config=config
        self.amount=config['initial_calcite_mol'];self.carrier=config['nitrogen_mol']
        self.initial_co2=config['initial_co2_mol'];self.pressure=config['total_pressure_pa']
        self.reactant=reaction.phases[config['reactant_phase']]
        self.product=reaction.phases[config['product_phase']]
        self.gas=reaction.phases[reaction.gas_phase]
        self.domain=tuple(config['temperature_domain_k'])
        self.phase_temperatures=tuple(brentq(
            lambda t:reaction.affinity(t,self.partial_pressure(extent))['affinity_j_mol_extent'],
            *root_policy['bracket_k'],xtol=root_policy['absolute_tolerance_k'],
            rtol=root_policy['relative_tolerance'],maxiter=root_policy['maximum_iterations']) for extent in (0.,self.amount))
        self.limits=tuple(self.at_temperature(t)['enthalpy_j'] for t in self.phase_temperatures)

    def partial_pressure(self,extent_mol):
        co2=self.initial_co2+extent_mol
        return self.pressure*co2/(co2+self.carrier)

    def at_temperature(self,temperature_k):
        t=temperature_k;r=self.reaction.gas_constant_j_mol_k
        standard=self.reaction.standard(t)
        if t<=self.phase_temperatures[0]:
            extent=0.;slope=0.;phase='calcite'
        elif t>=self.phase_temperatures[1]:
            extent=self.amount;slope=0.;phase='lime'
        else:
            peq=self.reaction.standard_pressure_pa*math.exp(-standard['reaction']['gibbs_j_mol']/(r*t))
            extent=self.carrier*peq/(self.pressure-peq)-self.initial_co2
            slope=self.carrier*self.pressure*peq/(self.pressure-peq)**2*standard['reaction']['enthalpy_j_mol']/(r*t*t)
            phase='coexistence'
        a=standard['phases'][self.config['reactant_phase']];b=standard['phases'][self.config['product_phase']]
        c=standard['phases'][self.reaction.gas_phase];n=self.nitrogen.standard(t)
        nc=self.initial_co2+extent;nt=nc+self.carrier
        pc=self.pressure*nc/nt;pn=self.pressure*self.carrier/nt
        amounts=(self.amount-extent,extent,nc,self.carrier);states=(a,b,c,n)
        h=math.fsum(q*s['enthalpy_j_mol'] for q,s in zip(amounts,states,strict=True))
        cp=math.fsum(q*s['cp_j_mol_k'] for q,s in zip(amounts,states,strict=True))
        entropy=math.fsum(q*s['entropy_j_mol_k'] for q,s in zip(amounts,states,strict=True))
        entropy-=r*(nc*math.log(pc/self.reaction.standard_pressure_pa)+self.carrier*math.log(pn/self.reaction.standard_pressure_pa))
        return {'temperature_k':t,'enthalpy_j':h,'extent_mol':extent,'phase':phase,
            'calcite_mol':self.amount-extent,'lime_mol':extent,'co2_mol':nc,'nitrogen_mol':self.carrier,
            'co2_partial_pressure_pa':pc,'nitrogen_partial_pressure_pa':pn,'entropy_j_k':entropy,
            'frozen_cp_j_k':cp,'equilibrium_cp_j_k':cp+standard['reaction']['enthalpy_j_mol']*slope,
            'extent_temperature_derivative_mol_k':slope,'gas_occupied_volume_m3':nt*r*t/self.pressure}

    def state(self,enthalpy_j):
        p=self.config['numerics']
        t=brentq(lambda t:self.at_temperature(t)['enthalpy_j']-enthalpy_j,*self.domain,
            xtol=p['temperature_inverse_absolute_k'],rtol=p['temperature_inverse_relative'],
            maxiter=p['temperature_inverse_iterations'])
        state=self.at_temperature(t);state['constitutive_enthalpy_j']=state['enthalpy_j'];state['enthalpy_j']=enthalpy_j
        return state

    def heat_rate(self,temperature_k,wall_temperature_k):
        p=self.config['radiation']
        return boundary_heat(surface_temperature_k=temperature_k,gas_temperature_k=wall_temperature_k,
            radiation_temperature_k=wall_temperature_k,area_m2=p['area_m2'],
            convection_w_m2_k=self.config['heat_conductance_w_k']/p['area_m2'],
            emissivity=p['emissivity'],stefan_boltzmann_w_m2_k4=p['stefan_boltzmann_w_m2_k4']).total_in_w

    def rates(self,enthalpy_j,wall_temperature_k):
        t=self.state(enthalpy_j)['temperature_k'];q=self.heat_rate(t,wall_temperature_k)
        return [q,q,q/wall_temperature_k,q*(1/t-1/wall_temperature_k)]

    def enthalpy_rate_derivative(self,enthalpy_j,wall_temperature_k):
        state=self.state(enthalpy_j);t=state['temperature_k'];dtdh=1/state['equilibrium_cp_j_k']
        p=self.config['radiation'];slope=-self.config['heat_conductance_w_k']-4*p['area_m2']*p['emissivity']*p['stefan_boltzmann_w_m2_k4']*t**3
        q=self.heat_rate(t,wall_temperature_k);derivative=slope*dtdh
        return [derivative,derivative,derivative/wall_temperature_k,
            (slope*(1/t-1/wall_temperature_k)-q/t**2)*dtdh]
