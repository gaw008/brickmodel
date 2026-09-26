"""Quartz caloric storage and equilibrated axial thermo-viscoelastic skeleton.

The only strain direction is the slab thickness, at fixed face area. Elastic
Helmholtz energy gives entropy and internal energy by differentiation. Quartz
latent heat is a declared smooth two-state free-energy approximation, with no
phase-volume jump or new claim about high-temperature polymorph stability.
"""
import numpy as np

from .full_cycle_gas import FiniteGasFullCycle


class ThermoelasticFullCycle(FiniteGasFullCycle):
    def __init__(self, config):
        super().__init__(config)
        self.p('solid.thermoelastic','1')
        self.quartz=self.ns.index('silica')
        self.tc=self.p('quartz.transition_temperature','K')
        self.latent=self.p('quartz.latent_heat','J/mol')
        self.width=self.p('quartz.transition_width','K')
        self.shomate_scale=self.p('quartz.shomate_scale','K')
        self.ca=np.array([self.p('quartz.alpha.'+c,'J/mol/K') for c in 'ABCDE'])
        self.cb=np.array([self.p('quartz.beta.'+c,'J/mol/K') for c in 'ABCDE'])
        self.mixing=self.latent*self.width/self.tc**2
        self.modulus=self.p('solid.axial_modulus','Pa')
        self.alpha=self.p('solid.thermal_expansion','1/K')
        self.mechanical_iterations=int(self.p('numerics.mechanical_iterations','1'))
        self.initial_prestress=-2/3*self.es0/self.vp0
        self.phase0=self.phase(np.asarray(self.Tr))

    def phase(self,T):
        q=self.latent/self.mixing*(1/self.tc-1/T)
        x=np.where(q.real>=0,1/(1+np.exp(-q)),np.exp(q)/(1+np.exp(q)))
        softplus=np.where(q.real>=0,q+np.log1p(np.exp(-q)),np.log1p(np.exp(q)))
        entropy=x*self.latent/self.tc+self.mixing*(softplus-x*q)
        cp=self.latent**2/(self.mixing*T**2)*x*(1-x)
        return x,entropy,cp

    def polynomial(self,T,coefficients):
        t=T/self.shomate_scale
        a,b,c,d,e=coefficients
        cp=a+b*t+c*t**2+d*t**3+e/t**2
        h=self.shomate_scale*(a*t+b*t**2/2+c*t**3/3+d*t**4/4-e/t)
        s=a*np.log(t)+b*t+c*t**2/2+d*t**3/3-e/(2*t**2)
        return cp,h,s

    def quartz_thermo(self,T):
        cp_a,h_a,s_a=self.polynomial(T,self.ca)
        cp_b,h_b,s_b=self.polynomial(T,self.cb)
        _,h0,s0=self.polynomial(self.Tr,self.ca)
        _,ha,sa=self.polynomial(self.tc,self.ca)
        _,hb,sb=self.polynomial(self.tc,self.cb)
        low=T.real<self.tc
        x,phase_s,phase_cp=self.phase(T)
        cp=np.where(low,cp_a,cp_b)+phase_cp
        h=np.where(low,h_a-h0,ha-h0+h_b-hb)+self.latent*(x-self.phase0[0])
        s=np.where(low,s_a-s0,sa-s0+s_b-sb)+phase_s-self.phase0[1]
        return cp,h,s

    def thermo(self,T):
        h,s=super().thermo(T)
        _,hq,sq=self.quartz_thermo(T)
        h[...,self.quartz]=self.h0[self.quartz]+hq
        s[...,self.quartz]=self.s0[self.quartz]+sq
        return h,s

    def caloric_capacity(self,T,ns,ng):
        cpq,_,_=self.quartz_thermo(T)
        return super().caloric_capacity(T,ns,ng)+ns[:,self.quartz]*(cpq-self.cp[self.quartz])

    def unpack(self,y):
        f=y[:9*self.n].reshape(9,self.n)
        T=f[0]*self.Tr
        ns=self.initial+(-np.expm1(-f[1:6].T)*self.extent_scale)@self.snu
        ns[:,self.reactants]=self.extent_scale*np.exp(-f[1:6].T)
        vs=ns@self.v
        ng=self.initial_gas*np.exp(y[9*self.n:self.last].reshape(self.g,self.n).T)
        thermal=self.alpha*(T-self.temperatures[0])
        z=f[6]+thermal
        for _ in range(self.mechanical_iterations):
            pore=self.vp0*np.exp(z)
            surface=self.es0*np.exp(2*z/3)
            cap=2/3*surface/pore
            pressure=ng.sum(axis=1)*self.R*T/pore
            strain=(vs+pore)/self.b0-1
            stress=self.modulus*(strain-thermal-f[6])+self.initial_prestress
            force=stress+self.P-pressure+cap
            z-=force/(self.modulus*pore/self.b0+pressure-cap/3)
        pore=self.vp0*np.exp(z)
        surface=self.es0*np.exp(2*z/3)
        return f,T,ns,vs+pore,pore,surface,2/3*surface/pore

    def elastic_strain(self,f,T,bulk):
        return bulk/self.b0-1-self.alpha*(T-self.temperatures[0])-f[6]+self.initial_prestress/self.modulus

    def mechanical_rates(self,f,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug):
        eps=self.elastic_strain(f,T,bulk)
        force=pressure-self.P-cap
        eta_dot=self.ks*np.exp(-self.Es/self.R*(1/T-1/self.Tsref))*pore/(cap*self.b0)*force
        dvs=dns@self.v
        d=self.modulus/self.b0+(pressure-cap/3)/pore
        a=self.modulus*self.alpha+pressure/T
        rest=self.modulus*eta_dot+self.R*T/pore*dng.sum(axis=1)+(pressure-cap/3)/pore*dvs
        capacity=self.caloric_capacity(T,ns,ng)
        effective=capacity-self.modulus*self.b0*T*self.alpha**2+T*a**2/d
        power=heat+flow-np.sum(us*dns,axis=1)-np.sum(ug*dng,axis=1)+cap*dvs
        power+=self.modulus*self.b0*(eps+T*self.alpha)*eta_dot-T*a*rest/d
        dT=power/effective
        db=(a*dT+rest)/d
        dpore=db-dvs
        elastic_sdot=self.modulus*self.b0*self.alpha*(db/self.b0-self.alpha*dT-eta_dot)
        self.effective_capacity=effective
        self.mechanical_residual=self.modulus*eps-force
        production=np.sum(self.modulus*self.b0*eps*eta_dot/T)
        return dT,db,dpore,capacity,elastic_sdot.sum(),production,eta_dot

    def additional_storage(self,f,T,bulk):
        eps=self.elastic_strain(f,T,bulk)
        entropy=self.modulus*self.b0*self.alpha*eps
        energy=self.modulus*self.b0*eps**2/2+T*entropy
        return energy,entropy

    def solid_fields(self,f,T,bulk):
        return {'quartz_beta_fraction':self.phase(T)[0].tolist(),
                'reversible_thermal_strain':(self.alpha*(T-self.temperatures[0])).tolist(),
                'permanent_sintering_strain':f[6].tolist(),
                'effective_axial_stress_pa':(self.modulus*self.elastic_strain(f,T,bulk)).tolist()}

    def summarize(self,times,states):
        report,fields=super().summarize(times,states)
        residual=report['state_domain']['maximum_mechanical_equilibrium_residual_pa']
        report['solid_approximation']='Effective constant-area axial equilibrium skeleton; constant assumed modulus and expansion. NIST quartz Cp plus a smooth two-state latent free energy; no phase volume jump, hysteresis, bending or fracture.'
        report['thermodynamics']['elastic_storage']='F_el=K*V0*epsilon^2/2; S_el=K*V0*alpha*epsilon; U_el=F_el+T*S_el'
        report['thermodynamics']['quartz_latent_heat_counted_once']=True
        report['summary']['peak_reversible_thermal_strain']=max(max(r['reversible_thermal_strain']) for r in fields['rows'])
        report['summary']['peak_quartz_beta_fraction']=max(max(r['quartz_beta_fraction']) for r in fields['rows'])
        report['mechanical_equilibrium_relative']=residual/self.P
        report['physical_consistency_passed']=bool(report['physical_consistency_passed'] and residual/self.P<self.p('acceptance.balance_relative','1'))
        return report,fields

    def integrate(self):
        report,fields=super().integrate()
        report['dimension_check']['identities'] += ['K*V0*epsilon^2=J','K*V0*alpha*epsilon=J/K','L*w/Tc^2=J/mol/K','dh_quartz/dT=Cp_quartz=T*ds_quartz/dT']
        return report,fields
