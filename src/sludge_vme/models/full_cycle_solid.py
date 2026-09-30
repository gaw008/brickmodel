"""Phase caloric storage and equilibrated axial thermo-viscoelastic skeleton.

The only strain direction is the slab thickness, at fixed face area. Elastic
Helmholtz energy gives entropy and internal energy by differentiation. Quartz
latent heat is a declared smooth two-state free-energy approximation. Its
temperature-dependent fraction also drives an assumed effective axial
eigenstrain, not a measured pure-phase volume jump or hysteresis law.
An assumed metakaolin-carried disordered phase contributes to the same molar
thermodynamic properties and positive sintering mobility. Finite log-odds
relaxation can retain a nonequilibrium glass proxy on cooling. Its effective
axial eigenstrain and reciprocal stress feedback follow the same Helmholtz
energy, including an assumed phase-dependent effective modulus and constant
disordered-minus-ordered heat capacity contrast. Zero
relaxation time selects the uncoupled equilibrium model only with zero
matrix eigenstrain amplitude and zero phase modulus contrast.
"""
import numpy as np

from .full_cycle_gas import FiniteGasFullCycle
from .full_cycle import source_caloric_coefficients, source_caloric_integrals
from .full_cycle_diagnostics import caloric_source_domain_coverage


class ThermoelasticFullCycle(FiniteGasFullCycle):
    def __init__(self, config):
        super().__init__(config)
        self.p('solid.thermoelastic','1')
        self.quartz=self.ns.index('silica')
        self.dry_caloric_indices=np.array([i for i in range(len(self.ns)) if i not in (self.water_index,self.quartz)])
        self.mineral_caloric_indices=np.array([self.ns.index(name) for name in config['caloric_background']['minerals']])
        self.mineral_caloric_coefficients=source_caloric_coefficients(self, config['caloric_background']['minerals'])
        self.linear_dry_indices=np.array([i for i in self.dry_caloric_indices if i not in self.mineral_caloric_indices])
        self.dry_cp_slope=np.array([self.p('species.'+self.ns[i]+'.cp_slope','J/mol/K2') for i in self.linear_dry_indices])
        self.linear_dry_columns=[list(self.dry_caloric_indices).index(i) for i in self.linear_dry_indices]
        self.mineral_dry_columns=[list(self.dry_caloric_indices).index(i) for i in self.mineral_caloric_indices]
        self.tc=self.p('quartz.transition_temperature','K')
        self.latent=self.p('quartz.latent_heat','J/mol')
        self.width=self.p('quartz.transition_width','K')
        self.shomate_scale=self.p('quartz.shomate_scale','K')
        self.ca=np.array([self.p('quartz.alpha.'+c,'J/mol/K') for c in 'ABCDE'])
        self.cb=np.array([self.p('quartz.beta.'+c,'J/mol/K') for c in 'ABCDE'])
        self.mixing=self.latent*self.width/self.tc**2
        self.modulus=self.p('solid.axial_modulus','Pa')
        self.modulus_exponent=self.p('solid.dry_fraction_modulus_exponent','1')
        self.phase_modulus_contrast=self.p('solid.phase_modulus_contrast','1')
        self.dry_v=self.v.copy()
        self.dry_v[self.water_index]=0
        self.initial_dry_fraction=(self.initial@self.dry_v)/self.b0
        self.alpha=self.p('solid.thermal_expansion','1/K')
        self.quartz_strain=self.p('quartz.axial_transition_strain','1')
        self.quartz_reference_fraction=self.initial[:,self.quartz]*self.v[self.quartz]/self.b0
        self.initial_phase_fraction=self.phase(np.asarray(self.temperatures[0]))[0]
        self.mechanical_iterations=int(self.p('numerics.mechanical_iterations','1'))
        self.initial_prestress=-2/3*self.es0/self.vp0
        self.initial_elastic_strain=self.initial_prestress/self.modulus
        if self.modulus_exponent != 0:
            # Stable small root of K0*(e0-m*e0**2/2)=initial_prestress.
            self.initial_elastic_strain*=2/(1+np.sqrt(1-2*self.modulus_exponent*self.initial_elastic_strain))
        self.phase0=self.phase(np.asarray(self.Tr))
        self.matrix=self.ns.index('metakaolin')
        self.liquid_active=self.p('liquid.active_matrix_fraction','1')
        self.liquid_tc=self.p('liquid.transition_temperature','K')
        self.liquid_latent=self.p('liquid.latent_heat','J/mol')
        self.liquid_cp=self.p('liquid.heat_capacity_contrast','J/mol/K')
        self.liquid_width=self.p('liquid.transition_width','K')
        self.liquid_gain=self.p('liquid.mobility_gain','1')
        self.phase_conductivity_contrast=self.p('thermal.phase_conductivity_contrast','1')
        self.dry_conductivity_temperature_exponent=self.p('thermal.dry_temperature_exponent','1')
        self.ordered_barrier=self.p('sintering.ordered_structure_barrier','J/mol')
        self.liquid_mixing=self.liquid_latent*self.liquid_width/self.liquid_tc**2
        self.liquid_reference=self.liquid_phase(np.asarray(self.Tr))
        self.liquid_tau=self.p('liquid.relaxation_time_ref','s')
        self.liquid_activation=self.p('liquid.relaxation_activation_energy','J/mol')
        self.liquid_strain=self.p('liquid.axial_transition_strain','1')
        self.kinetic_liquid=self.liquid_tau>0 and self.liquid_active>0
        if (self.liquid_strain != 0 or self.phase_modulus_contrast != 0) and self.liquid_active > 0 and not self.kinetic_liquid:
            raise ValueError('Matrix elastic phase coupling requires positive liquid.relaxation_time_ref; set eigenstrain and phase modulus contrast to zero for the uncoupled algebraic model')
        if self.kinetic_liquid:
            # The log-odds is a physical coordinate before gas and extents.
            # Zero relaxation time retains the previous equilibrium system.
            self.gas_offset+=self.n
            self.extent_offset+=self.n
            self.last+=self.n

    def liquid_equilibrium_log_odds(self,T):
        if self.liquid_cp == 0:
            return self.liquid_latent/self.liquid_mixing*(1/self.liquid_tc-1/T)
        enthalpy,entropy=self.liquid_contrast(T)
        return (entropy-enthalpy/T)/self.liquid_mixing

    def liquid_contrast(self,T):
        """Disordered-minus-ordered h/s, referenced at the declared Tm.

        The constant Cp contrast is assumed. dh/dT=c=T*ds/dT, and
        dh(Tm)=L, ds(Tm)=L/Tm preserve the equal-free-energy temperature.
        """
        return (self.liquid_latent+self.liquid_cp*(T-self.liquid_tc),
                self.liquid_latent/self.liquid_tc+self.liquid_cp*np.log(T/self.liquid_tc))

    def liquid_order(self,q):
        """Fraction, zero-Cp-contrast entropy and dx/dq without clipping."""
        positive=q.real>=0
        small=np.exp(np.where(positive,-q,q))
        x=np.where(positive,1/(1+small),small/(1+small))
        other=np.where(positive,small/(1+small),1/(1+small))
        correction=np.log1p(small)
        log_x=np.where(positive,-correction,q-correction)
        log_other=np.where(positive,-q-correction,-correction)
        entropy=x*self.liquid_latent/self.liquid_tc-self.liquid_mixing*(x*log_x+other*log_other)
        return x,entropy,small/(1+small)**2

    def elastic_phase_affinity(self,elastic):
        """Elastic F_x/N, finite even when the active carrier amount is zero."""
        force=elastic['modulus']*elastic['eps']
        affinity=-self.liquid_strain*self.v[self.matrix]*force
        if self.phase_modulus_contrast != 0:
            affinity=affinity-self.v[self.matrix]*self.phase_modulus_contrast*elastic['modulus']*elastic['eps']**2/2
        return affinity

    def liquid_driving_log_odds(self,T,fields,elastic_affinity):
        drive=fields[9]-self.liquid_equilibrium_log_odds(T)
        if self.liquid_strain != 0 or self.phase_modulus_contrast != 0:
            drive=drive+elastic_affinity/(self.liquid_mixing*T)
        return drive

    def liquid_coordinate_rate(self,T,fields,elastic_affinity):
        rate=np.exp(-self.liquid_activation/self.R*(1/T-1/self.liquid_tc))/self.liquid_tau
        return -rate*self.liquid_driving_log_odds(T,fields,elastic_affinity)

    def liquid_relaxation(self,T,ns,fields,elastic_affinity):
        """Internal relaxation at fixed carrier amount; carrier birth inherits x.

        U_phase=N*(x*dh-h_ref), S_phase=N*(s(T,x)-s_ref), N=active*n_matrix.
        The same averaged molar properties account for x*dN when chemical
        reactions create carrier. Only N*dx is an internal relaxation source.
        The returned power and entropy rate are caloric; elastic storage is
        differentiated in mechanical_rates. Production uses the total phase
        affinity, including -v_matrix*K*(a*epsilon+g*epsilon**2/2)
        per active mole. g is the phase modulus contrast.
        """
        _,_,slope=self.liquid_order(fields[9])
        xdot=slope*self.liquid_coordinate_rate(T,fields,elastic_affinity)
        amount=self.liquid_active*ns[:,self.matrix]
        enthalpy,entropy=self.liquid_contrast(T)
        entropy_rate=amount*(entropy-self.liquid_mixing*fields[9])*xdot
        production=-amount*self.liquid_mixing*self.liquid_driving_log_odds(T,fields,elastic_affinity)*xdot
        return -amount*enthalpy*xdot,entropy_rate,production,xdot

    def phase_reference_volume(self,fields,ns):
        """C=N*v_matrix*(x-x_ref)/V0 and its carrier/x partials.

        A fixed reference volume makes this an effective small-strain law,
        not a current-volume mixture rule or independent phase inventory.
        """
        if self.liquid_active == 0:
            zero=np.zeros_like(ns[:,self.matrix])
            return zero,zero,zero
        x=self.liquid_order(fields[9])[0]
        coefficient=self.liquid_active*self.v[self.matrix]/self.b0
        birth=coefficient*(x-self.liquid_reference[0])
        return ns[:,self.matrix]*birth,birth,coefficient*ns[:,self.matrix]

    def phase_eigenstrain(self,fields,ns):
        """B, dB/dn_matrix and dB/dx at fixed reference volume V0.

        The active carrier is born at local x. B has no direct temperature
        derivative at fixed q; both composition and internal-state rates enter
        its total derivative. Species molar volumes remain unchanged.
        """
        if self.liquid_strain == 0 or self.liquid_active == 0:
            zero=np.zeros_like(ns[:,self.matrix])
            return zero,zero,zero
        x=self.liquid_order(fields[9])[0]
        coefficient=self.liquid_strain*self.liquid_active*self.v[self.matrix]/self.b0
        birth=coefficient*(x-self.liquid_reference[0])
        return ns[:,self.matrix]*birth,birth,coefficient*ns[:,self.matrix]

    def liquid_phase(self,T):
        """Equilibrium two-state proxy carried by the metakaolin inventory.

        The phases share composition and molar volume. This assumed fluxed
        matrix proxy is not the melting curve of pure metakaolin.
        """
        q=self.liquid_equilibrium_log_odds(T)
        x=np.where(q.real>=0,1/(1+np.exp(-q)),np.exp(q)/(1+np.exp(q)))
        softplus=np.where(q.real>=0,q+np.log1p(np.exp(-q)),np.log1p(np.exp(q)))
        entropy=x*self.liquid_latent/self.liquid_tc+self.liquid_mixing*(softplus-x*q)
        cp=self.liquid_latent**2/(self.liquid_mixing*T**2)*x*(1-x)
        if self.liquid_cp != 0:
            enthalpy,_=self.liquid_contrast(T)
            entropy+=x*self.liquid_cp*np.log(T/self.liquid_tc)
            cp=x*self.liquid_cp+enthalpy**2/(self.liquid_mixing*T**2)*x*(1-x)
        return x,entropy,cp

    def liquid_state(self,T,ns,fields):
        x=self.liquid_order(fields[9])[0] if self.kinetic_liquid else self.liquid_phase(T)[0]
        liquid_moles=self.liquid_active*ns[:,self.matrix]*x
        dry_volume=ns@self.v-ns[:,self.water_index]*self.v[self.water_index]
        fraction=liquid_moles*self.v[self.matrix]/dry_volume
        return liquid_moles,fraction,np.exp(self.liquid_gain*fraction)

    def dry_temperature_conductivity_factor(self,T):
        """Assumed dry-skeleton transport factor on a finite positive-T domain."""
        if self.dry_conductivity_temperature_exponent == 0:
            return np.ones_like(T)
        return (T/self.Tr)**self.dry_conductivity_temperature_exponent

    def phase_conductivity(self,T,ns,bulk,fields):
        """Assumed phase effect on dry-skeleton conduction, without new storage.

        phi_d is disordered active volume divided by current dry condensed
        volume. Phase and temperature factors change only the dry term; liquid-water
        enhancement and pore radiation retain their separate preceding laws.
        This is an effective closure, not a constituent mixing rule.
        """
        _,fraction,_=self.liquid_state(T,ns,fields)
        factor=np.exp(-self.phase_conductivity_contrast*fraction)
        water_fraction=ns[:,self.water_index]*self.v[self.water_index]/bulk
        dry_fraction=(ns@self.v)/bulk-water_fraction
        dry_conductivity=self.k*(dry_fraction/self.dry_solid_fraction0)**self.conductivity_exponent
        if self.dry_conductivity_temperature_exponent == 0:
            background=dry_conductivity*(factor+self.conductivity_moisture_gain*water_fraction)
        else:
            background=dry_conductivity*(self.dry_temperature_conductivity_factor(T)*factor+self.conductivity_moisture_gain*water_fraction)
        return background,factor

    def state_heat_transfer(self,T,ns,bulk,tf,fields):
        if self.phase_conductivity_contrast == 0 and self.dry_conductivity_temperature_exponent == 0:
            return super().state_heat_transfer(T,ns,bulk,tf,fields)
        background,_=self.phase_conductivity(T,ns,bulk,fields)
        conductivity=background+self.pore_radiative_conductivity(T,ns,bulk)
        return self.heat_transfer_from_conductivity(T,bulk,tf,conductivity)

    def sintering_response(self,T,ns,fields,pore,cap):
        """Inverse effective axial viscosity and ordered-structure penalty.

        The active carrier's ordered volume raises the kinetic barrier; the
        preceding disordered-volume multiplier remains a prefactor. This
        positive kinetic coefficient adds no stored energy or phase heat.
        """
        liquid,_,multiplier=self.liquid_state(T,ns,fields)
        dry_volume=ns@self.v-ns[:,self.water_index]*self.v[self.water_index]
        ordered=(self.liquid_active*ns[:,self.matrix]-liquid)*self.v[self.matrix]/dry_volume
        viscosity_ratio=np.exp(self.ordered_barrier*ordered/(self.R*T))
        mobility=self.ks*np.exp(-self.Es/self.R*(1/T-1/self.Tsref))*multiplier*pore/(cap*self.b0)
        return mobility/viscosity_ratio,ordered,viscosity_ratio

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

    def dry_background_cp(self,T):
        """Reference-anchored Cp of non-quartz dry species, before phase terms."""
        cp=np.broadcast_to(self.cp[self.dry_caloric_indices],T.shape+(len(self.dry_caloric_indices),)).astype(np.result_type(T,float),copy=True)
        cp[...,self.linear_dry_columns]+=(T[...,None]-self.Tr)*self.dry_cp_slope
        cp[...,self.mineral_dry_columns]=source_caloric_integrals(T,self.mineral_caloric_coefficients,self.Tr)[0]
        return cp

    def thermo(self,T):
        h,s=super().thermo(T)
        if np.any(self.dry_cp_slope != 0):
            delta=T[...,None]-self.Tr
            h[...,self.linear_dry_indices]+=self.dry_cp_slope*delta**2/2
            s[...,self.linear_dry_indices]+=self.dry_cp_slope*(delta-self.Tr*np.log(T[...,None]/self.Tr))
        _,mineral_h,mineral_s=source_caloric_integrals(T,self.mineral_caloric_coefficients,self.Tr)
        h[...,self.mineral_caloric_indices]=self.h0[self.mineral_caloric_indices]+mineral_h
        s[...,self.mineral_caloric_indices]=self.s0[self.mineral_caloric_indices]+mineral_s
        _,hq,sq=self.quartz_thermo(T)
        h[...,self.quartz]=self.h0[self.quartz]+hq
        s[...,self.quartz]=self.s0[self.quartz]+sq
        x,phase_s,_=self.liquid_phase(T)
        h[...,self.matrix]+=self.liquid_active*self.liquid_latent*(x-self.liquid_reference[0])
        if self.liquid_cp != 0:
            h[...,self.matrix]+=self.liquid_active*self.liquid_cp*(x*(T-self.liquid_tc)-self.liquid_reference[0]*(self.Tr-self.liquid_tc))
        s[...,self.matrix]+=self.liquid_active*(phase_s-self.liquid_reference[1])
        return h,s

    def state_thermo(self,T,fields):
        h,s=self.thermo(T)
        if self.kinetic_liquid:
            x,entropy,_=self.liquid_order(fields[9])
            eq_x,eq_entropy,_=self.liquid_phase(T)
            h[:,self.matrix]+=self.liquid_active*self.liquid_latent*(x-eq_x)
            if self.liquid_cp != 0:
                h[:,self.matrix]+=self.liquid_active*self.liquid_cp*(T-self.liquid_tc)*(x-eq_x)
                entropy=entropy+x*self.liquid_cp*np.log(T/self.liquid_tc)
            s[:,self.matrix]+=self.liquid_active*(entropy-eq_entropy)
        return h,s

    def state_caloric_capacity(self,T,ns,ng,fields):
        cpq,_,_=self.quartz_thermo(T)
        capacity=super().caloric_capacity(T,ns,ng)+ns[:,self.quartz]*(cpq-self.cp[self.quartz])
        if np.any(self.dry_cp_slope != 0):
            capacity+=np.sum(ns[:,self.linear_dry_indices]*(T[:,None]-self.Tr)*self.dry_cp_slope,axis=1)
        mineral_cp=source_caloric_integrals(T,self.mineral_caloric_coefficients,self.Tr)[0]
        capacity+=np.sum(ns[:,self.mineral_caloric_indices]*(mineral_cp-self.cp[self.mineral_caloric_indices]),axis=1)
        if not self.kinetic_liquid:
            capacity+=ns[:,self.matrix]*self.liquid_active*self.liquid_phase(T)[2]
        elif self.liquid_cp != 0:
            capacity+=ns[:,self.matrix]*self.liquid_active*self.liquid_order(fields[9])[0]*self.liquid_cp
        return capacity

    def thermal_strain(self,T):
        """Effective eigenstrain and its first two temperature derivatives.

        The silica inventory is inert in the declared reaction network, so
        its reference-volume fraction is constant. The phase fraction follows
        the existing caloric law; stress-induced transition shifts are omitted.
        """
        x=self.phase(T)[0]
        slope=self.latent/(self.mixing*T**2)
        dx=x*(1-x)*slope
        ddx=dx*((1-2*x)*slope-2/T)
        amplitude=self.quartz_strain*self.quartz_reference_fraction
        transition=amplitude*(x-self.initial_phase_fraction)
        return (self.alpha*(T-self.temperatures[0])+transition,
                self.alpha+amplitude*dx,amplitude*ddx,transition)

    def unpack(self,y):
        f=y[:self.gas_offset].reshape(-1,self.n)
        T=f[0]*self.Tr
        ns=self.condensed_state(f)
        vs=ns@self.v
        ng=self.initial_gas*np.exp(y[self.gas_offset:self.extent_offset].reshape(self.g,self.n).T)
        thermal=self.thermal_strain(T)[0]
        thermal=thermal+self.phase_eigenstrain(f,ns)[0]
        z=f[6]+thermal
        for _ in range(self.mechanical_iterations):
            pore=self.vp0*np.exp(z)
            surface=self.es0*np.exp(2*z/3)
            cap=2/3*surface/pore
            pressure=ng.sum(axis=1)*self.R*T/pore
            strain=(vs+pore)/self.b0-1
            stress=self.modulus*(strain-thermal-f[6])+self.initial_prestress
            force=stress+self.P-pressure+cap
            denominator=self.modulus*pore/self.b0+pressure-cap/3
            if self.modulus_exponent != 0 or (self.phase_modulus_contrast != 0 and self.liquid_active != 0):
                elastic=self.elastic_response(f,T,ns,vs+pore)
                force=elastic['stress']+self.P-pressure+cap
                denominator=elastic['tangent']*pore+pressure-cap/3
            z-=force/denominator
        pore=self.vp0*np.exp(z)
        surface=self.es0*np.exp(2*z/3)
        return f,T,ns,vs+pore,pore,surface,2/3*surface/pore

    def elastic_strain(self,f,T,bulk,ns=None):
        strain=bulk/self.b0-1-self.thermal_strain(T)[0]-f[6]+self.initial_elastic_strain
        if self.liquid_strain != 0 and self.liquid_active != 0:
            if ns is None:
                ns=self.condensed_state(f)
            strain=strain-self.phase_eigenstrain(f,ns)[0]
        return strain

    def elastic_response(self,f,T,ns,bulk):
        """V/D derivatives of F=V0*K(D/V,C)*e**2/2 at fixed C and B.

        D excludes liquid water. K0 refers to the initial dry-solid fraction;
        e0 balances the initial capillary traction. No dense-solid modulus,
        damage variable, clipping or extra dissipative heat is introduced.
        Direct D derivatives hold C and B fixed; their carrier and x partials
        are included separately in chemical potential and mechanical rates.
        """
        dry=ns@self.dry_v
        exponent=self.modulus_exponent
        modulus=self.modulus*(dry/bulk/self.initial_dry_fraction)**exponent
        if self.phase_modulus_contrast != 0:
            modulus=modulus*np.exp(-self.phase_modulus_contrast*self.phase_reference_volume(f,ns)[0])
        kv=-exponent*modulus/bulk
        kd=exponent*modulus/dry
        kvv=exponent*(exponent+1)*modulus/bulk**2
        kvd=-exponent*kd/bulk
        eps=self.elastic_strain(f,T,bulk,ns)
        stress=modulus*eps+self.b0*kv*eps**2/2
        tangent=modulus/self.b0+2*kv*eps+self.b0*kvv*eps**2/2
        return {'modulus':modulus,'dry_fraction':dry/bulk,'eps':eps,'kv':kv,'kd':kd,
                'stress':stress,'tangent':tangent,
                'strain_coupling':modulus+self.b0*kv*eps,
                'stress_dry_derivative':kd*eps+self.b0*kvd*eps**2/2,
                'free_dry_derivative':self.b0*kd*eps**2/2}

    def skeleton_chemical_potential(self,fields,T,ns,bulk):
        if self.modulus_exponent == 0 and self.liquid_strain == 0 and self.phase_modulus_contrast == 0:
            return super().skeleton_chemical_potential(fields,T,ns,bulk)
        elastic=self.elastic_response(fields,T,ns,bulk)
        potential=elastic['free_dry_derivative'][:,None]*self.dry_v
        birth=self.phase_eigenstrain(fields,ns)[1]
        potential[:,self.matrix]-=self.b0*elastic['modulus']*elastic['eps']*birth
        if self.phase_modulus_contrast != 0:
            phase_birth=self.phase_reference_volume(fields,ns)[1]
            potential[:,self.matrix]-=self.b0*self.phase_modulus_contrast*elastic['modulus']*elastic['eps']**2/2*phase_birth
        return potential

    def mechanical_rates(self,f,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug):
        if self.modulus_exponent != 0 or ((self.liquid_strain != 0 or self.phase_modulus_contrast != 0) and self.liquid_active != 0):
            return self.porous_mechanical_rates(f,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug)
        eps=self.elastic_strain(f,T,bulk)
        _,beta_prime,beta_second,_=self.thermal_strain(T)
        force=pressure-self.P-cap
        mobility,_,_=self.sintering_response(T,ns,f,pore,cap)
        eta_dot=mobility*force
        dvs=dns@self.v
        d=self.modulus/self.b0+(pressure-cap/3)/pore
        a=self.modulus*beta_prime+pressure/T
        rest=self.modulus*eta_dot+self.R*T/pore*dng.sum(axis=1)+(pressure-cap/3)/pore*dvs
        capacity=self.state_caloric_capacity(T,ns,ng,f)
        effective=capacity+self.modulus*self.b0*T*(eps*beta_second-beta_prime**2)+T*a**2/d
        power=heat+flow-np.sum(us*dns,axis=1)-np.sum(ug*dng,axis=1)+cap*dvs
        power+=self.modulus*self.b0*(eps+T*beta_prime)*eta_dot-T*a*rest/d
        phase_sdot=0.;phase_production=0.
        if self.kinetic_liquid:
            phase_power,phase_entropy,phase_production,_=self.liquid_relaxation(T,ns,f,0.)
            power+=phase_power
            phase_sdot=phase_entropy.sum()
        dT=power/effective
        db=(a*dT+rest)/d
        dpore=db-dvs
        elastic_sdot=self.modulus*self.b0*(beta_prime*(db/self.b0-beta_prime*dT-eta_dot)+eps*beta_second*dT)
        self.effective_capacity=effective
        self.mechanical_residual=self.modulus*eps-force
        production=np.sum(self.modulus*self.b0*eps*eta_dot/T)+np.sum(phase_production)
        return dT,db,dpore,capacity,elastic_sdot.sum()+phase_sdot,production,eta_dot

    def porous_mechanical_rates(self,f,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug):
        elastic=self.elastic_response(f,T,ns,bulk)
        modulus,eps=elastic['modulus'],elastic['eps']
        _,beta_prime,beta_second,_=self.thermal_strain(T)
        mobility,_,_=self.sintering_response(T,ns,f,pore,cap)
        # -F_eta/V0 differs from F_V when K depends on current volume.
        sintering_force=modulus*eps
        eta_dot=mobility*sintering_force
        phase_sdot=0.;phase_production=0.;phase_power=0.;phase_strain_rate=0.
        phase_modulus_rate=0.
        if self.kinetic_liquid:
            phase_power,phase_entropy,phase_production,xdot=self.liquid_relaxation(T,ns,f,self.elastic_phase_affinity(elastic))
            phase_sdot=phase_entropy.sum()
            _,birth,state_derivative=self.phase_eigenstrain(f,ns)
            phase_strain_rate=birth*dns[:,self.matrix]+state_derivative*xdot
            if self.phase_modulus_contrast != 0:
                _,phase_birth,phase_derivative=self.phase_reference_volume(f,ns)
                phase_rate=phase_birth*dns[:,self.matrix]+phase_derivative*xdot
                # K_C*Cdot at fixed V,D; Bdot is already retained separately.
                phase_modulus_rate=-self.phase_modulus_contrast*modulus*phase_rate
        # -F_eta and -F_B are identical; B has both carrier and phase rates.
        inelastic_rate=eta_dot+phase_strain_rate
        dvs=dns@self.v
        ddry=dns@self.dry_v
        d=elastic['tangent']+(pressure-cap/3)/pore
        a=elastic['strain_coupling']*beta_prime+pressure/T
        rest=(elastic['strain_coupling']*inelastic_rate-elastic['stress_dry_derivative']*ddry
              +self.R*T/pore*dng.sum(axis=1)+(pressure-cap/3)/pore*dvs)
        if self.phase_modulus_contrast != 0:
            rest-=elastic['stress']/modulus*phase_modulus_rate
        capacity=self.state_caloric_capacity(T,ns,ng,f)
        effective=capacity+modulus*self.b0*T*(eps*beta_second-beta_prime**2)+T*a**2/d
        dry_energy_derivative=self.b0*elastic['kd']*(eps**2/2+T*beta_prime*eps)
        power=heat+flow-np.sum(us*dns,axis=1)-np.sum(ug*dng,axis=1)+cap*dvs
        power+=modulus*self.b0*(eps+T*beta_prime)*inelastic_rate-dry_energy_derivative*ddry-T*a*rest/d
        if self.phase_modulus_contrast != 0:
            power-=self.b0*(eps**2/2+T*beta_prime*eps)*phase_modulus_rate
        power+=phase_power
        dT=power/effective
        db=(a*dT+rest)/d
        dpore=db-dvs
        elastic_sdot=self.b0*((elastic['kv']*db+elastic['kd']*ddry)*beta_prime*eps
            +modulus*(beta_prime*(db/self.b0-beta_prime*dT-inelastic_rate)+eps*beta_second*dT))
        if self.phase_modulus_contrast != 0:
            elastic_sdot+=self.b0*phase_modulus_rate*beta_prime*eps
        self.effective_capacity=effective
        self.mechanical_residual=elastic['stress']-(pressure-self.P-cap)
        production=np.sum(self.b0*sintering_force*eta_dot/T)+np.sum(phase_production)
        return dT,db,dpore,capacity,elastic_sdot.sum()+phase_sdot,production,eta_dot

    def initial_state(self):
        state=super().initial_state()
        if self.kinetic_liquid:
            state[9*self.n:self.gas_offset]=self.liquid_equilibrium_log_odds(self.temperatures[0])
        return state

    def rhs(self,t,y):
        dy=super().rhs(t,y)
        if self.kinetic_liquid:
            f=y[:self.gas_offset].reshape(-1,self.n)
            affinity=0.
            if self.liquid_strain != 0 or self.phase_modulus_contrast != 0:
                _,T,ns,bulk,_,_,_=self.unpack(y)
                elastic=self.elastic_response(f,T,ns,bulk)
                affinity=self.elastic_phase_affinity(elastic)
            dy[9*self.n:self.gas_offset]=self.liquid_coordinate_rate(f[0]*self.Tr,f,affinity)
        return dy

    def additional_storage(self,f,T,bulk):
        eps=self.elastic_strain(f,T,bulk)
        modulus=self.modulus
        if self.modulus_exponent != 0 or self.phase_modulus_contrast != 0:
            modulus=self.elastic_response(f,T,self.condensed_state(f),bulk)['modulus']
        entropy=modulus*self.b0*self.thermal_strain(T)[1]*eps
        energy=modulus*self.b0*eps**2/2+T*entropy
        return energy,entropy

    def solid_fields(self,f,T,bulk):
        thermal,slope,_,transition=self.thermal_strain(T)
        ns=self.condensed_state(f)
        liquid,fraction,mobility=self.liquid_state(T,ns,f)
        pore=bulk-ns@self.v
        cap=2/3*self.es0*(pore/self.vp0)**(2/3)/pore
        inverse_viscosity,ordered,viscosity_ratio=self.sintering_response(T,ns,f,pore,cap)
        elastic=self.elastic_response(f,T,ns,bulk)
        phase_fields={}
        if self.kinetic_liquid:
            affinity=self.elastic_phase_affinity(elastic)
            power,_,production,xdot=self.liquid_relaxation(T,ns,f,affinity)
            driving=self.liquid_driving_log_odds(T,f,affinity)
            phase_fields={'liquid_log_odds':f[9].tolist(),
                'liquid_disordered_fraction':self.liquid_order(f[9])[0].tolist(),
                'liquid_equilibrium_fraction':self.liquid_phase(T)[0].tolist(),
                'liquid_relaxation_fraction_rate_per_s':xdot.tolist(),
                'liquid_relaxation_power_w':power.tolist(),
                'liquid_relaxation_entropy_w_k':production.tolist(),
                'liquid_relaxation_entropy_per_active_mole_w_mol_k':(-self.liquid_mixing*driving*xdot).tolist(),
                'liquid_total_phase_affinity_j_per_active_mol':(self.liquid_mixing*T*driving).tolist(),
                'liquid_elastic_phase_affinity_j_per_active_mol':affinity.tolist()}
        stiffness_ratio=np.ones_like(T)
        if self.phase_modulus_contrast != 0:
            stiffness_ratio=np.exp(-self.phase_modulus_contrast*self.phase_reference_volume(f,ns)[0])
        contrast_h,contrast_s=self.liquid_contrast(T)
        phase_x=self.liquid_order(f[9])[0] if self.kinetic_liquid else self.liquid_phase(T)[0]
        background,phase_conductivity_factor=self.phase_conductivity(T,ns,bulk,f)
        temperature_factor=self.dry_temperature_conductivity_factor(T)
        if self.dry_conductivity_temperature_exponent == 0:
            background_reference=self.effective_conductivity(ns,bulk)
            temperature_reference=background
        else:
            water_fraction=ns[:,self.water_index]*self.v[self.water_index]/bulk
            dry_fraction=(ns@self.v)/bulk-water_fraction
            dry_conductivity=self.k*(dry_fraction/self.dry_solid_fraction0)**self.conductivity_exponent
            background_reference=dry_conductivity*(temperature_factor+self.conductivity_moisture_gain*water_fraction)
            temperature_reference=dry_conductivity*(phase_conductivity_factor+self.conductivity_moisture_gain*water_fraction)
        return {**phase_fields,'quartz_beta_fraction':self.phase(T)[0].tolist(),
                'dry_phase_conductivity_factor':phase_conductivity_factor.tolist(),
                'dry_temperature_conductivity_factor':temperature_factor.tolist(),
                'temperature_background_conductivity_ratio':(background/temperature_reference).tolist(),
                'temperature_background_conductivity_change_w_m_k':(background-temperature_reference).tolist(),
                'phase_background_conductivity_ratio':(background/background_reference).tolist(),
                'phase_background_conductivity_change_w_m_k':(background-background_reference).tolist(),
                'liquid_enthalpy_contrast_j_mol':contrast_h.tolist(),
                'liquid_entropy_contrast_j_mol_k':contrast_s.tolist(),
                'liquid_frozen_phase_capacity_j_k':(self.liquid_active*ns[:,self.matrix]*phase_x*self.liquid_cp).tolist(),
                'dry_background_molar_cp_j_mol_k':{self.ns[i]:self.dry_background_cp(T)[:,j].tolist() for j,i in enumerate(self.dry_caloric_indices)},
                'matrix_fixed_phase_molar_cp_j_mol_k':(self.dry_background_cp(T)[:,list(self.dry_caloric_indices).index(self.matrix)]+self.liquid_active*phase_x*self.liquid_cp).tolist(),
                'ordered_active_fraction_of_dry_condensed_volume':ordered.tolist(),
                'structure_viscosity_ratio':viscosity_ratio.tolist(),
                'effective_axial_sintering_viscosity_pa_s':(1/inverse_viscosity).tolist(),
                'sintering_dissipation_coefficient_w_k_pa2':(self.b0*inverse_viscosity/T).tolist(),
                'effective_liquid_moles':liquid.tolist(),
                'effective_liquid_fraction_of_dry_condensed_volume':fraction.tolist(),
                'liquid_sintering_mobility_multiplier':mobility.tolist(),
                'reversible_thermal_strain':thermal.tolist(),
                'quartz_transition_strain':transition.tolist(),
                'matrix_phase_eigenstrain':self.phase_eigenstrain(f,ns)[0].tolist(),
                'effective_expansion_coefficient_per_k':slope.tolist(),
                'permanent_sintering_strain':f[6].tolist(),
                'dry_solid_fraction_of_bulk':elastic['dry_fraction'].tolist(),
                'effective_axial_modulus_pa':elastic['modulus'].tolist(),
                'phase_modulus_ratio':stiffness_ratio.tolist(),
                'elastic_bulk_tangent_pa_m3':elastic['tangent'].tolist(),
                'elastic_composition_potential_j_mol':self.skeleton_chemical_potential(f,T,ns,bulk).tolist(),
                'sintering_thermodynamic_force_pa':(elastic['modulus']*elastic['eps']).tolist(),
                'effective_axial_stress_pa':elastic['stress'].tolist()}

    def summarize(self,times,states):
        report,fields=super().summarize(times,states)
        report['dry_caloric_approximation']='Calcite/lime use source five-term Cp with reference-anchored analytic h/s; other non-quartz dry backgrounds retain their assumed linear Cp. Quartz, matrix phase, elasticity and binding remain separate. No added state or reaction heat. Source-domain extrapolation explicitly assumed; original linear-Cp UQ/fit evidence is historical.'
        report['dry_cp_slopes_j_mol_k2']={self.ns[i]:float(a) for i,a in zip(self.linear_dry_indices,self.dry_cp_slope)}
        report['summary']['minimum_sampled_dry_background_cp_j_mol_k']=min(min(v) for r in fields['rows'] for v in r['dry_background_molar_cp_j_mol_k'].values())
        report['summary']['maximum_sampled_dry_background_cp_j_mol_k']=max(max(v) for r in fields['rows'] for v in r['dry_background_molar_cp_j_mol_k'].values())
        residual=report['state_domain']['maximum_mechanical_equilibrium_residual_pa']
        report['solid_approximation']='Effective constant-area axial equilibrium skeleton with assumed dry-solid-fraction and matrix-phase-dependent stiffness and finite-rate matrix eigenstrain. D excludes liquid water; K0 is the initial effective modulus. Same Helmholtz energy supplies volume, composition and internal-phase derivatives. No measured porous stiffness, mineral phase diagram, bending, damage or fracture.'
        report['thermodynamics']['elastic_storage']="F_el=K(D/V,C)*V0*epsilon^2/2; K=K0*((D/V)/(D0/V0))^m*exp(-g*C); C=N*v_matrix*(x-x_ref)/V0; epsilon=V/V0-1-beta(T)-B(n,x)-eta+e0; K0*(e0-m*e0^2/2)=prestress; S_el=K*V0*beta'(T)*epsilon at fixed x,n; U_el=F_el+T*S_el. F_V=K*epsilon+V0*K_V*epsilon^2/2; mu_el_i=V0*K_D*epsilon^2*v_dry_i/2-V0*K*epsilon*B_ni-V0*g*K*epsilon^2*C_ni/2; -F_eta/V0=K*epsilon drives sintering. Direct D partials hold C and B fixed; Bdot and Cdot retain carrier birth and phase relaxation in U/S and equilibrium; Kdot=K_V*Vdot+K_D*Ddot-g*K*Cdot."
        report['thermodynamics']['thermal_eigenstrain']='beta(T)=alpha*(T-T_initial)+e_q*(n_q_initial*v_q/V0)*(x_beta(T)-x_beta(T_initial)); fixed-strain elastic heat capacity=K*V0*T*(epsilon*beta_second-beta_prime^2)'
        report['thermodynamics']['quartz_latent_heat_counted_once']=True
        report['thermodynamics']['liquid_latent_heat_counted_once']=True
        report['liquid_approximation']='Reversible equilibrium two-state fluxed-matrix proxy carried by a declared fraction of current metakaolin. Both states retain the same Al2Si2O7 composition and molar volume. State-dependent h, s, Cp and reaction affinity share one free energy; positive exp(gain*liquid dry-condensed volume fraction) multiplies existing sintering mobility. Assumed parameters; not pure metakaolin melting, a mineral phase diagram, finite-rate vitrification or quenched-glass retention.'
        report['summary']['peak_effective_liquid_moles']=max(sum(r['effective_liquid_moles']) for r in fields['rows'])
        report['summary']['peak_local_effective_liquid_fraction']=max(max(r['effective_liquid_fraction_of_dry_condensed_volume']) for r in fields['rows'])
        report['summary']['peak_liquid_mobility_multiplier']=max(max(r['liquid_sintering_mobility_multiplier']) for r in fields['rows'])
        report['summary']['final_effective_liquid_moles']=float(sum(fields['rows'][-1]['effective_liquid_moles']))
        report['liquid_kinetic_mode']=self.kinetic_liquid
        if self.kinetic_liquid:
            report['liquid_approximation']='Finite-rate disordered/ordered two-state proxy carried by an assumed fraction of current metakaolin, sharing composition and molar volume. Log-odds q relaxes toward q_eq(T) with Arrhenius rate; x=logistic(q). Phase energy N*x*dh(T) and entropy N*[x*ds(T)-b*(x*log(x)+(1-x)*log(1-x))] use constant reference offsets at Tr. Carrier formation inherits local x through averaged molar h/s and reaction affinity; N*dh*xdot is internal relaxation, and N*x*c is the extra fixed-phase heat capacity. No independent crystallization/nucleation law, measured glass transition, mineral phase diagram, phase volume jump or liquid transport. Retained disordered material on cooling is a glass proxy, not measured glass yield; sintering uses the separately declared effective structure-dependent viscosity.'
            phase_min=min(min(r['liquid_relaxation_entropy_w_k']) for r in fields['rows'])
            coefficient_min=min(min(r['liquid_relaxation_entropy_per_active_mole_w_mol_k']) for r in fields['rows'])
            report['thermodynamics']['minimum_liquid_relaxation_entropy_production_w_k']=phase_min
            report['thermodynamics']['minimum_liquid_relaxation_entropy_per_active_mole_w_mol_k']=coefficient_min
            report['thermodynamics']['liquid_relaxation_entropy_domain']='Nonnegative per-active-mole kinetic dissipation, with carrier inventory subject to the existing declared inventory error budget. Raw extensive entropy is retained, including signed values from near-zero carrier roundoff; no clipping or new tolerance.'
            report['thermodynamics']['liquid_fixed_state_heat_capacity_excludes_equilibrium_latent_peak']=True
            report['summary']['final_retained_disordered_moles']=report['summary']['final_effective_liquid_moles']
            report['summary']['final_retained_disordered_mass_kg']=report['summary']['final_effective_liquid_moles']*self.mw[self.matrix]
            report['summary']['maximum_liquid_fraction_lag']=max(max(abs(np.array(r['liquid_disordered_fraction'])-r['liquid_equilibrium_fraction'])) for r in fields['rows'])
            report['summary']['peak_liquid_relaxation_power_w']=max(sum(abs(v) for v in r['liquid_relaxation_power_w']) for r in fields['rows'])
            report['physical_consistency_passed']=bool(report['physical_consistency_passed'] and coefficient_min>=0)
        report['summary']['peak_reversible_thermal_strain']=max(max(r['reversible_thermal_strain']) for r in fields['rows'])
        report['summary']['peak_quartz_beta_fraction']=max(max(r['quartz_beta_fraction']) for r in fields['rows'])
        report['summary']['peak_quartz_transition_strain']=max(max(r['quartz_transition_strain']) for r in fields['rows'])
        report['summary']['final_quartz_transition_strain']=float(np.mean(fields['rows'][-1]['quartz_transition_strain']))
        report['summary']['peak_effective_expansion_coefficient_per_k']=max(max(r['effective_expansion_coefficient_per_k']) for r in fields['rows'])
        report['sintering_viscosity_approximation']='Effective axial viscosity zeta=(cap*V0/(ks*pore))*exp(Es/R*(1/T-1/Tref)-gain*phi_disordered+E_order*phi_ordered/(R*T)). phi_ordered is the active carrier ordered volume divided by dry condensed volume. Kinetic barrier and existing disordered prefactor are assumed, not measured melt viscosity, glass transition, non-Arrhenius rheology or independent crystal kinetics. No viscosity storage or extra heat source; force=-F_eta/V0=K*epsilon, dissipation V0*force^2/(zeta*T). Force differs from equilibrium stress F_V with variable K. E_order=0 removes only the ordered barrier.'
        report['summary']['peak_ordered_active_volume_fraction']=max(max(r['ordered_active_fraction_of_dry_condensed_volume']) for r in fields['rows'])
        report['summary']['peak_structure_viscosity_ratio']=max(max(r['structure_viscosity_ratio']) for r in fields['rows'])
        report['summary']['minimum_effective_axial_sintering_viscosity_pa_s']=min(min(r['effective_axial_sintering_viscosity_pa_s']) for r in fields['rows'])
        report['thermodynamics']['minimum_sintering_dissipation_coefficient_w_k_pa2']=min(min(r['sintering_dissipation_coefficient_w_k_pa2']) for r in fields['rows'])
        report['thermodynamics']['structure_viscosity_adds_no_storage']=True
        report['summary']['minimum_effective_axial_modulus_pa']=min(min(r['effective_axial_modulus_pa']) for r in fields['rows'])
        report['summary']['maximum_effective_axial_modulus_pa']=max(max(r['effective_axial_modulus_pa']) for r in fields['rows'])
        report['thermodynamics']['minimum_elastic_bulk_tangent_pa_m3']=min(min(r['elastic_bulk_tangent_pa_m3']) for r in fields['rows'])
        report['thermodynamics']['dry_fraction_modulus_exponent']=self.modulus_exponent
        report['thermodynamics']['water_direct_elastic_composition_derivative_zero']=True
        report['matrix_phase_eigenstrain_approximation']='B=a*N*v_matrix*(x-x_ref)/V0, N=active*n_matrix, x_ref=stress-free phase fraction at Tr. Signed assumed effective axial strain; species composition and molar volumes unchanged. A_phase=b*T*(q-q_eq)-v_matrix*K*(a*epsilon+g*epsilon^2/2) per active mole; qdot=-k*A_phase/(b*T), so production=N*k*x*(1-x)*A_phase^2/(b*T^2). Carrier birth enters mu_el_matrix and Bdot. Nonzero a or g with active carrier requires finite positive relaxation time; coupled algebraic equilibrium is outside scope. Quartz remains the preceding temperature-prescribed proxy. No measured molar-volume jump, crystallization or glass yield.'
        report['thermodynamics']['phase_modulus_contrast']=self.phase_modulus_contrast
        report['thermodynamics']['liquid_heat_capacity_contrast_j_mol_k']=self.liquid_cp
        report['thermal_approximation']='Nonradiative k=k_ref*(dry_solid_fraction/initial_dry_solid_fraction)^m*[(T/Tr)^a*exp(-gk*phi_disordered)+b*liquid_water_volume_fraction]. phi_disordered=N*x*v_matrix/V_dry uses the current dry condensed volume; gk is an assumed signed effective log contrast. The assumed temperature power and phase factor change only the dry term; the liquid-water enhancement is unchanged. The preceding local pore-wall radiative k is added separately, with one shared face flux and outer half-cell resistance using total k. No new stored energy, phase heat or separate radiation source; no measured constituent conductivity, anisotropy or phase-resolved mixing rule.'
        report['phase_conductivity_approximation']='gk=thermal.phase_conductivity_contrast is fixed in the paired UQ and synthetic fit. Positive gk lowers the dry-skeleton conductivity at fixed composition, volume and temperature as the disordered fraction rises; negative gk raises it. Zero gk removes only the phase factor; zero active carrier also removes the phase factor. The phase background ratio and change compare against gk=0 at the same temperature exponent, composition, volume and temperature. Both gk=0 and a=0 restore the preceding heat-transfer path. No empirical direction or magnitude is established for real brick.'
        report['temperature_conductivity_approximation']='a=thermal.dry_temperature_exponent defines the assumed dry-skeleton factor (T/Tr)^a on the finite positive-temperature domain of this model. It multiplies neither the liquid-water enhancement nor pore radiation and adds no state, stored energy, heat capacity or heat source. The temperature background ratio and change compare against a=0 at the same phase state, composition, volume and temperature. Zero a exactly restores the preceding phase-conductivity arithmetic. a is fixed in conditional UQ and synthetic calibration, not identified by those calculations; no measured temperature law or unrestricted-temperature extrapolation is established.'
        report['summary']['minimum_dry_temperature_conductivity_factor']=min(min(r['dry_temperature_conductivity_factor']) for r in fields['rows'])
        report['summary']['maximum_dry_temperature_conductivity_factor']=max(max(r['dry_temperature_conductivity_factor']) for r in fields['rows'])
        report['summary']['final_mean_temperature_background_conductivity_ratio']=float(np.mean(fields['rows'][-1]['temperature_background_conductivity_ratio']))
        report['summary']['peak_absolute_temperature_conductivity_change_w_m_k']=max(max(abs(np.asarray(r['temperature_background_conductivity_change_w_m_k']))) for r in fields['rows'])
        report['summary']['minimum_dry_phase_conductivity_factor']=min(min(r['dry_phase_conductivity_factor']) for r in fields['rows'])
        report['summary']['maximum_dry_phase_conductivity_factor']=max(max(r['dry_phase_conductivity_factor']) for r in fields['rows'])
        report['summary']['final_mean_phase_background_conductivity_ratio']=float(np.mean(fields['rows'][-1]['phase_background_conductivity_ratio']))
        report['summary']['peak_absolute_phase_conductivity_change_w_m_k']=max(max(abs(np.asarray(r['phase_background_conductivity_change_w_m_k']))) for r in fields['rows'])
        report['phase_heat_capacity_approximation']='Constant assumed c=Cp_disordered-Cp_ordered per active matrix mole. dh=L+c*(T-Tm); ds=L/Tm+c*ln(T/Tm); q_eq=(ds-dh/T)/b. Fixed-phase Cp increment=x*c; stress-free equilibrium Cp increment=x*c+dh^2*x*(1-x)/(b*T^2). Carrier h/s, reaction potentials and phase relaxation use the same free energy and Tr reference offsets. No measured calorimetry, glass transition or new state. c is fixed in conditional UQ and synthetic fit.'
        report['summary']['peak_frozen_phase_capacity_j_k']=max(sum(r['liquid_frozen_phase_capacity_j_k']) for r in fields['rows'])
        report['summary']['final_frozen_phase_capacity_j_k']=sum(fields['rows'][-1]['liquid_frozen_phase_capacity_j_k'])
        report['thermodynamics']['minimum_matrix_fixed_phase_molar_cp_j_mol_k']=min(min(r['matrix_fixed_phase_molar_cp_j_mol_k']) for r in fields['rows'])
        report['phase_modulus_approximation']='K=K_porosity*exp(-g*C), C=N*v_matrix*(x-x_ref)/V0. Same fixed-reference-volume phase measure as B=a*C, with no direct temperature dependence at fixed x,n. g is assumed and fixed in the conditional UQ and synthetic fit. Distinguishes ordered/disordered contributions at fixed carrier amount; not a measured constituent modulus, glass transition, damage or phase-resolved mixture law. Zero g restores the preceding phase-eigenstrain model.'
        report['summary']['minimum_phase_modulus_ratio']=min(min(r['phase_modulus_ratio']) for r in fields['rows'])
        report['summary']['maximum_phase_modulus_ratio']=max(max(r['phase_modulus_ratio']) for r in fields['rows'])
        report['summary']['final_mean_phase_modulus_ratio']=float(np.mean(fields['rows'][-1]['phase_modulus_ratio']))
        report['thermodynamics']['matrix_phase_eigenstrain_amplitude']=self.liquid_strain
        report['summary']['peak_absolute_matrix_phase_eigenstrain']=max(max(abs(np.array(r['matrix_phase_eigenstrain']))) for r in fields['rows'])
        report['summary']['final_mean_matrix_phase_eigenstrain']=float(np.mean(fields['rows'][-1]['matrix_phase_eigenstrain']))
        if self.kinetic_liquid:
            report['liquid_approximation'] += ' Matrix elastic phase affinity shifts the kinetic target through the same free energy; liquid_equilibrium_fraction and maximum_liquid_fraction_lag retain their stress-free caloric reference and are not the coupled equilibrium solution.'
            report['summary']['peak_absolute_elastic_phase_affinity_j_per_active_mol']=max(max(abs(np.array(r['liquid_elastic_phase_affinity_j_per_active_mol']))) for r in fields['rows'])
        report['mechanical_equilibrium_relative']=residual/self.P
        report['physical_consistency_passed']=bool(report['physical_consistency_passed'] and residual/self.P<self.p('acceptance.balance_relative','1'))
        report['caloric_source_domains'].update(caloric_source_domain_coverage(self, fields['rows'], self.config['caloric_background']['minerals']))
        return report,fields

    def integrate(self):
        report,fields=super().integrate()
        report['dimension_check']['identities'] += ['K*V0*epsilon^2=J','K*V0*beta_prime*epsilon=J/K','K*V0*T*(epsilon*beta_second-beta_prime^2)=J/K','n_q*v_q/V0=1','L*w/Tc^2=J/mol/K','dh_quartz/dT=Cp_quartz=T*ds_quartz/dT']
        report['dimension_check']['identities'] += ['L_liquid*w_liquid/Tm^2=J/mol/K','n_matrix*active_fraction*x*volume/dry_condensed_volume=1','exp(gain*liquid_fraction)=1']
        report['dimension_check']['identities'] += ['E_order*phi_ordered/(R*T)=1; zeta=cap*V0/(ks*pore)*dimensionless=Pa*s','eta_dot=force/zeta=1/s; V0*force*eta_dot/T=W/K; positive zeta implies nonnegative mechanical dissipation']
        report['dimension_check']['identities'] += ['D/V=1; K0*((D/V)/(D0/V0))**m=Pa; F_V=Pa; F_VV=Pa/m3; F_D*v_dry=J/mol','S=-F_T; U=F+T*S; eta_dot=(-F_eta/V0)/zeta; production=V0*(K*epsilon)**2/(zeta*T)=W/K']
        report['dimension_check']['identities'] += ['C=N*v_matrix*(x-x_ref)/V0=1; exp(-g*C)=1; K_C=-g*K=Pa; V0*K_C*Cdot=J/s']
        if self.kinetic_liquid:
            report['dimension_check']['identities'] += ['q=log(x/(1-x))=1; A_phase=b*T*(q-q_eq)-v_matrix*K*(a*epsilon+g*epsilon^2/2)=J/mol; dq/dt=-k*A_phase/(b*T)=1/s','N*dh(T)*dx/dt=W; -N*A_phase*dx/dt/T=W/K','B=a*N*v_matrix*(x-x_ref)/V0=1; Bdot=B_n*ndot+B_x*xdot=1/s; fixed-x phase Cp=N*x*c=J/K; no double-counted equilibrium latent peak']
        else:
            report['dimension_check']['identities'] += ['dh_matrix/dT=Cp_matrix=T*ds_matrix/dT']
        report['dimension_check']['identities'] += ['dh=L+c*(T-Tm)=J/mol; ds=L/Tm+c*ln(T/Tm)=J/mol/K; d(dh)/dT=c=T*d(ds)/dT','q_eq=(ds-dh/T)/b=1; Cp_phase_equilibrium=x*c+dh^2*x*(1-x)/(b*T^2)=J/mol/K']
        report['dimension_check']['identities'] += ['phi_disordered=N*x*v_matrix/V_dry=1; exp(-gk*phi_disordered)=1; dry_k*(phase_factor+b*phi_water)=W/m/K','G_face=area/(half_width_left/k_left+half_width_right/k_right)=W/K; shared heat cancels internally; G_face*(T_right-T_left)^2/(T_left*T_right)=W/K']
        return report,fields
