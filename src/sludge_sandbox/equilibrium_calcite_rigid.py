"""Rigid-volume calcite / CaO / CO2 / N2 equilibrium with declared solid EOS."""
import math

from scipy.optimize import brentq

from .exchanges import boundary_heat


class RigidCalciteMixture:
    def __init__(self,reaction,nitrogen,volume_source,config,cell):
        self.reaction=reaction;self.nitrogen=nitrogen;self.config=config
        self.calcium=cell['calcium_mol'];self.carrier=cell['nitrogen_mol'];self.volume=cell['total_volume_m3']
        self.domain=tuple(config['temperature_domain_k']);self.p0=volume_source['reference_pressure_pa']
        factor=volume_source['cubic_metres_per_cubic_centimetre']
        self.vc=float(volume_source['phases'][config['reactant_phase']]['volume_cm3_mol'])*factor
        self.vl=float(volume_source['phases'][config['product_phase']]['volume_cm3_mol'])*factor
        self.dv=self.vc-self.vl;self.reactant=reaction.phases[config['reactant_phase']]
        self.product=reaction.phases[config['product_phase']];self.gas=reaction.phases[reaction.gas_phase]

    def _geometry(self,t,c,g,nitrogen_mol):
        base=self.volume-self.calcium*self.vl-c*self.dv;vg=base+g*self.dv
        rt=self.reaction.gas_constant_j_mol_k*t
        return base,vg,(g+nitrogen_mol)*rt/vg,g*rt/vg,nitrogen_mol*rt/vg

    def reaction_potential(self,t,c,g):
        _,_,p,pc,_=self._geometry(t,c,g,self.carrier)
        return self.reaction.standard(t)['reaction']['gibbs_j_mol']-(p-self.p0)*self.dv+self.reaction.gas_constant_j_mol_k*t*math.log(pc/self.p0)

    def at_temperature(self,t,c):
        return self.at_inventory(t,c,self.carrier)

    def at_inventory(self,t,c,nitrogen_mol):
        standard=self.reaction.standard(t);rt=self.reaction.gas_constant_j_mol_k*t;policy=self.config['numerics']
        dg=standard['reaction']['gibbs_j_mol']
        def score(g):
            _,_,p,pc,_=self._geometry(t,c,g,nitrogen_mol)
            return dg-(p-self.p0)*self.dv+rt*math.log(pc/self.p0)
        if score(c)<=0.:
            g=c;calcite=0.;lime=self.calcium;phase='lime'
        elif c>self.calcium and score(c-self.calcium)>=0.:
            g=c-self.calcium;calcite=self.calcium;lime=0.;phase='calcite'
        else:
            if c>self.calcium:
                log_left=math.log(c-self.calcium)
            else:
                base,_,p_right,_,_=self._geometry(t,c,c,nitrogen_mol);p_left=nitrogen_mol*rt/base
                bound=math.log(self.p0*base/rt)-dg/rt+(min(p_left,p_right)-self.p0)*self.dv/rt
                log_left=bound-policy['log_gas_bracket_padding']
            log_g=brentq(lambda value:score(math.exp(value)),log_left,math.log(c),
                xtol=policy['log_gas_root_absolute_tolerance'],rtol=policy['log_gas_root_relative_tolerance'],
                maxiter=policy['log_gas_root_iterations'])
            g=math.exp(log_g);calcite=c-g;lime=(self.calcium-c)+g;phase='coexistence'
        return self.inventory_partition(t,c,nitrogen_mol,g,calcite,lime,phase)

    def at_partition(self,t,c,g,calcite,lime,phase):
        return self.inventory_partition(t,c,self.carrier,g,calcite,lime,phase)

    def inventory_partition(self,t,c,nitrogen_mol,g,calcite,lime,phase):
        standard=self.reaction.standard(t);r=self.reaction.gas_constant_j_mol_k
        base,vg,p,pc,pn=self._geometry(t,c,g,nitrogen_mol)
        a=standard['phases'][self.config['reactant_phase']];b=standard['phases'][self.config['product_phase']]
        gas=standard['phases'][self.reaction.gas_phase];n=self.nitrogen.standard(t)
        u=math.fsum((calcite*(a['enthalpy_j_mol']-self.p0*self.vc),lime*(b['enthalpy_j_mol']-self.p0*self.vl),
            g*(gas['enthalpy_j_mol']-r*t),nitrogen_mol*(n['enthalpy_j_mol']-r*t)))
        entropy=math.fsum((calcite*a['entropy_j_mol_k'],lime*b['entropy_j_mol_k'],
            g*(gas['entropy_j_mol_k']-r*math.log(pc/self.p0)),nitrogen_mol*(n['entropy_j_mol_k']-r*math.log(pn/self.p0))))
        frozen_cv=math.fsum((calcite*a['cp_j_mol_k'],lime*b['cp_j_mol_k'],
            g*(gas['cp_j_mol_k']-r),nitrogen_mol*(n['cp_j_mol_k']-r)))
        delta_u=standard['reaction']['enthalpy_j_mol']-r*t+self.p0*self.dv
        slope=r*t*(base*base+g*nitrogen_mol*self.dv*self.dv)/(g*vg*vg)
        dg_dt=delta_u/(t*slope) if phase=='coexistence' else 0.
        mu=gas['gibbs_j_mol']+r*t*math.log(pc/self.p0)
        return {'temperature_k':t,'carbon_mol':c,'internal_energy_j':u,'enthalpy_j':u+p*self.volume,
            'entropy_j_k':entropy,'helmholtz_j':u-t*entropy,'phase':phase,'calcite_mol':calcite,'lime_mol':lime,
            'co2_mol':g,'nitrogen_mol':nitrogen_mol,'pressure_pa':p,'co2_partial_pressure_pa':pc,
            'gas_volume_m3':vg,'solid_volume_m3':calcite*self.vc+lime*self.vl,
            'frozen_cv_j_k':frozen_cv,'equilibrium_cv_j_k':frozen_cv+delta_u*dg_dt,
            'co2_temperature_derivative_mol_k':dg_dt,'reaction_internal_energy_j_mol':delta_u,
            'reaction_gas_derivative_j_mol2':slope,'carbon_chemical_potential_j_mol':mu,
            'nitrogen_chemical_potential_j_mol':n['gibbs_j_mol']+r*t*math.log(pn/self.p0),
            'nitrogen_partial_pressure_pa':pn,'co2_partial_enthalpy_j_mol':gas['enthalpy_j_mol'],
            'nitrogen_partial_enthalpy_j_mol':n['enthalpy_j_mol'],
            'reaction_gibbs_j_mol':standard['reaction']['gibbs_j_mol']-(p-self.p0)*self.dv+r*t*math.log(pc/self.p0)}

    def state(self,carbon_mol,internal_energy_j):
        return self.inventory_state(carbon_mol,self.carrier,internal_energy_j)

    def inventory_state(self,carbon_mol,nitrogen_mol,internal_energy_j):
        p=self.config['numerics']
        t=brentq(lambda value:self.at_inventory(value,carbon_mol,nitrogen_mol)['internal_energy_j']-internal_energy_j,*self.domain,
            xtol=p['temperature_inverse_absolute_k'],rtol=p['temperature_inverse_relative'],maxiter=p['temperature_inverse_iterations'])
        state=self.at_inventory(t,carbon_mol,nitrogen_mol);state['constitutive_internal_energy_j']=state['internal_energy_j']
        state['internal_energy_j']=internal_energy_j
        return state

    def heat_rate(self,t,wall):
        p=self.config['radiation']
        return boundary_heat(surface_temperature_k=t,gas_temperature_k=wall,radiation_temperature_k=wall,
            area_m2=p['area_m2'],convection_w_m2_k=self.config['heat_conductance_w_k']/p['area_m2'],
            emissivity=p['emissivity'],stefan_boltzmann_w_m2_k4=p['stefan_boltzmann_w_m2_k4']).total_in_w

    def rates(self,carbon_mol,internal_energy_j,wall):
        t=self.state(carbon_mol,internal_energy_j)['temperature_k'];q=self.heat_rate(t,wall)
        return [q,q,q/wall,q*(1/t-1/wall)]

    def energy_rate_derivative(self,carbon_mol,internal_energy_j,wall):
        state=self.state(carbon_mol,internal_energy_j);t=state['temperature_k'];dtdu=1/state['equilibrium_cv_j_k']
        p=self.config['radiation'];slope=-self.config['heat_conductance_w_k']-4*p['area_m2']*p['emissivity']*p['stefan_boltzmann_w_m2_k4']*t**3
        q=self.heat_rate(t,wall);derivative=slope*dtdu
        return [derivative,derivative,derivative/wall,(slope*(1/t-1/wall)-q/t**2)*dtdu]
