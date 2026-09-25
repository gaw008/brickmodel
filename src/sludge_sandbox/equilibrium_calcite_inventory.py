"""Isobaric equilibrium flash with mobile total carbon and retained Ca / N2."""
import math

from scipy.optimize import brentq


class CalciteInventoryCell:
    def __init__(self,reaction,nitrogen,config,cell):
        self.reaction=reaction;self.nitrogen=nitrogen;self.config=config
        self.calcium=cell['calcium_mol'];self.carrier=cell['nitrogen_mol']
        self.pressure=config['total_pressure_pa'];self.domain=tuple(config['temperature_domain_k'])
        self.reactant=reaction.phases[config['reactant_phase']];self.product=reaction.phases[config['product_phase']]
        self.gas=reaction.phases[reaction.gas_phase]

    def at_temperature(self,temperature_k,carbon_mol):
        t=temperature_k;r=self.reaction.gas_constant_j_mol_k;standard=self.reaction.standard(t)
        peq=self.reaction.standard_pressure_pa*math.exp(-standard['reaction']['gibbs_j_mol']/(r*t))
        if peq>=self.pressure:
            co2=carbon_mol;calcite=0.;lime=self.calcium;phase='lime';dc_dt=0.;dc_dc=1.
        else:
            equilibrium_co2=self.carrier*peq/(self.pressure-peq)
            if carbon_mol<=equilibrium_co2:
                co2=carbon_mol;calcite=0.;lime=self.calcium;phase='lime';dc_dt=0.;dc_dc=1.
            elif carbon_mol-self.calcium>=equilibrium_co2:
                calcite=self.calcium;lime=0.;co2=carbon_mol-self.calcium;phase='calcite';dc_dt=0.;dc_dc=1.
            else:
                co2=equilibrium_co2;calcite=carbon_mol-co2;lime=(self.calcium-carbon_mol)+co2;phase='coexistence';dc_dc=0.
                dc_dt=self.carrier*self.pressure*peq/(self.pressure-peq)**2*standard['reaction']['enthalpy_j_mol']/(r*t*t)
        nt=co2+self.carrier;pc=self.pressure*co2/nt;pn=self.pressure*self.carrier/nt
        a=standard['phases'][self.config['reactant_phase']];b=standard['phases'][self.config['product_phase']]
        c=standard['phases'][self.reaction.gas_phase];n=self.nitrogen.standard(t)
        amounts=(calcite,lime,co2,self.carrier);phases=(a,b,c,n)
        h=math.fsum(q*s['enthalpy_j_mol'] for q,s in zip(amounts,phases,strict=True))
        cp=math.fsum(q*s['cp_j_mol_k'] for q,s in zip(amounts,phases,strict=True))
        entropy=math.fsum(q*s['entropy_j_mol_k'] for q,s in zip(amounts,phases,strict=True))
        entropy-=r*(co2*math.log(pc/self.reaction.standard_pressure_pa)+self.carrier*math.log(pn/self.reaction.standard_pressure_pa))
        mu=c['gibbs_j_mol']+r*t*math.log(pc/self.reaction.standard_pressure_pa)
        return {'temperature_k':t,'carbon_mol':carbon_mol,'enthalpy_j':h,'entropy_j_k':entropy,'phase':phase,
            'calcite_mol':calcite,'lime_mol':lime,'co2_mol':co2,'nitrogen_mol':self.carrier,
            'co2_partial_pressure_pa':pc,'equilibrium_cp_j_k':cp+standard['reaction']['enthalpy_j_mol']*dc_dt,
            'enthalpy_carbon_derivative_j_mol':c['enthalpy_j_mol'] if dc_dc==1. else a['enthalpy_j_mol']-b['enthalpy_j_mol'],
            'carbon_chemical_potential_j_mol':mu,'co2_partial_enthalpy_j_mol':c['enthalpy_j_mol'],
            'gas_occupied_volume_m3':nt*r*t/self.pressure}

    def state(self,carbon_mol,enthalpy_j):
        p=self.config['numerics']
        t=brentq(lambda t:self.at_temperature(t,carbon_mol)['enthalpy_j']-enthalpy_j,*self.domain,
            xtol=p['temperature_inverse_absolute_k'],rtol=p['temperature_inverse_relative'],maxiter=p['temperature_inverse_iterations'])
        state=self.at_temperature(t,carbon_mol);state['constitutive_enthalpy_j']=state['enthalpy_j'];state['enthalpy_j']=enthalpy_j
        return state


def reactive_carbon_face(left,right,parameters):
    tl,tr=left['temperature_k'],right['temperature_k'];mu_l=left['carbon_chemical_potential_j_mol'];mu_r=right['carbon_chemical_potential_j_mol']
    h=(left['co2_partial_enthalpy_j_mol']+right['co2_partial_enthalpy_j_mol'])/2
    force=math.fsum((mu_l/tl,-mu_r/tr,h*(1/tr-1/tl)))
    flow=parameters['carbon_mobility_mol2_k_j_s']*force;heat=parameters['heat_conductance_w_k']*(tl-tr)
    return {'carbon_flow_mol_s':flow,'enthalpy_flow_w':math.fsum((heat,h*flow)),'conductive_heat_w':heat,
        'face_co2_enthalpy_j_mol':h,'chemical_thermal_force_j_mol_k':force,
        'entropy_production_w_k':heat*(1/tr-1/tl)+parameters['carbon_mobility_mol2_k_j_s']*force*force}
