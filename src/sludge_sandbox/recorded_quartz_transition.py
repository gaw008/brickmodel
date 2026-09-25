"""Standard-pressure quartz calorimetry with an explicit latent-heat interval.

Cp coefficients are unchanged source fits. Reference constants and the phase
join are explicit source-derived choices, reviewed separately against JANAF.
No volume model, kinetics, hysteresis or brick mineral fraction is implied.
"""
import math

from scipy.optimize import brentq


class RecordedQuartzTransition:
    def __init__(self, source_facts, parameters):
        self.facts = source_facts; self.parameters = parameters
        self.coefficients = [tuple(map(float, segment['coefficients'])) for segment in source_facts['segments']]
        reference = parameters['reference']; transition = parameters['phase_transition']
        self.t0 = reference['temperature_k']; self.h0 = reference['enthalpy_j_mol']; self.s0 = reference['entropy_j_mol_k']
        self.tt = transition['temperature_k']; self.latent = transition['latent_enthalpy_j_mol']
        self.scale = parameters['caloric_representation']['temperature_scale_k']
        self.domain = parameters['caloric_representation']['domain_k']
        dh, ds = self.integrals(0, self.t0, self.tt)
        self.ha = self.h0+dh; self.sa = self.s0+ds
        self.hb = self.ha+self.latent; self.sb = self.sa+self.latent/self.tt

    def integrals(self, phase, start_k, end_k):
        a,b,c,d,e,*_ = self.coefficients[phase]
        x,y = start_k/self.scale,end_k/self.scale; u = y-x
        dh = self.scale*u*math.fsum((a,b*(x+y)/2,c*(x*x+x*y+y*y)/3,
                                    d*(x+y)*(x*x+y*y)/4,e/(x*y)))
        ds = math.fsum((a*math.log1p(u/x),u*math.fsum((b,c*(x+y)/2,d*(x*x+x*y+y*y)/3,
                                                     e*(x+y)/(2*x*x*y*y)))))
        return dh, ds

    def cp(self, phase, temperature_k):
        a,b,c,d,e,*_ = self.coefficients[phase]; x = temperature_k/self.scale
        return math.fsum((a,b*x,c*x*x,d*x*x*x,e/(x*x)))

    def pure_state(self, phase, temperature_k):
        base_t,base_h,base_s = (self.t0,self.h0,self.s0) if phase==0 else (self.tt,self.hb,self.sb)
        dh,ds = self.integrals(phase,base_t,temperature_k)
        return {'temperature_k':temperature_k,'enthalpy_j_mol':base_h+dh,'entropy_j_mol_k':base_s+ds,
                'cp_j_mol_k':self.cp(phase,temperature_k),'beta_fraction':float(phase),
                'phase':self.parameters['caloric_representation']['phase_names'][phase]}

    def from_enthalpy(self, enthalpy_j_mol):
        h = enthalpy_j_mol; policy = self.parameters['numerics']
        if self.ha<=h<=self.hb:
            fraction = (h-self.ha)/self.latent
            return {'temperature_k':self.tt,'enthalpy_j_mol':h,'entropy_j_mol_k':self.sa+(h-self.ha)/self.tt,
                    'cp_j_mol_k':None,'beta_fraction':fraction,'phase':'coexistence'}
        phase = 0 if h<self.ha else 1
        bracket = (self.domain[0],self.tt) if phase==0 else (self.tt,self.domain[1])
        t = brentq(lambda value:self.pure_state(phase,value)['enthalpy_j_mol']-h,*bracket,
                   xtol=policy['temperature_inverse_absolute_k'],rtol=policy['temperature_inverse_relative'],
                   maxiter=policy['root_maximum_iterations'])
        result = self.pure_state(phase,t);result['constitutive_enthalpy_j_mol'] = result['enthalpy_j_mol']
        result['enthalpy_j_mol'] = h
        return result
