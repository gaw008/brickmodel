"""Phase caloric storage and equilibrated axial thermo-viscoelastic skeleton.

The only strain direction is the slab thickness, at fixed face area. Elastic
Helmholtz energy gives entropy and internal energy by differentiation. Quartz
latent heat is a declared smooth two-state free-energy approximation. Its
temperature-dependent fraction also drives an assumed effective axial
eigenstrain, not a measured pure-phase volume jump or hysteresis law.
An assumed metakaolin-carried disordered phase contributes to the same molar
thermodynamic properties and positive sintering mobility. Finite log-odds
relaxation can retain a nonequilibrium glass proxy on cooling; zero relaxation
time selects the preceding equilibrium model.
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
        self.modulus_exponent=self.p('solid.dry_fraction_modulus_exponent','1')
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
        self.liquid_width=self.p('liquid.transition_width','K')
        self.liquid_gain=self.p('liquid.mobility_gain','1')
        self.ordered_barrier=self.p('sintering.ordered_structure_barrier','J/mol')
        self.liquid_mixing=self.liquid_latent*self.liquid_width/self.liquid_tc**2
        self.liquid_reference=self.liquid_phase(np.asarray(self.Tr))
        self.liquid_tau=self.p('liquid.relaxation_time_ref','s')
        self.liquid_activation=self.p('liquid.relaxation_activation_energy','J/mol')
        self.kinetic_liquid=self.liquid_tau>0 and self.liquid_active>0
        if self.kinetic_liquid:
            # The log-odds is a physical coordinate before gas and extents.
            # Zero relaxation time retains the previous equilibrium system.
            self.gas_offset+=self.n
            self.extent_offset+=self.n
            self.last+=self.n

    def liquid_equilibrium_log_odds(self,T):
        return self.liquid_latent/self.liquid_mixing*(1/self.liquid_tc-1/T)

    def liquid_order(self,q):
        """Disordered fraction, molar entropy and dx/dq without clipping."""
        positive=q.real>=0
        small=np.exp(np.where(positive,-q,q))
        x=np.where(positive,1/(1+small),small/(1+small))
        other=np.where(positive,small/(1+small),1/(1+small))
        correction=np.log1p(small)
        log_x=np.where(positive,-correction,q-correction)
        log_other=np.where(positive,-q-correction,-correction)
        entropy=x*self.liquid_latent/self.liquid_tc-self.liquid_mixing*(x*log_x+other*log_other)
        return x,entropy,small/(1+small)**2

    def liquid_coordinate_rate(self,T,fields):
        rate=np.exp(-self.liquid_activation/self.R*(1/T-1/self.liquid_tc))/self.liquid_tau
        return rate*(self.liquid_equilibrium_log_odds(T)-fields[9])

    def liquid_relaxation(self,T,ns,fields):
        """Internal relaxation at fixed carrier amount; carrier birth inherits x.

        U_phase=N*L*(x-x_ref), S_phase=N*(s(x)-s_ref), N=active*n_matrix.
        The same averaged molar properties account for x*dN when chemical
        reactions create carrier. Only N*dx is an internal relaxation source.
        """
        _,_,slope=self.liquid_order(fields[9])
        xdot=slope*self.liquid_coordinate_rate(T,fields)
        amount=self.liquid_active*ns[:,self.matrix]
        entropy_rate=amount*(self.liquid_latent/self.liquid_tc-self.liquid_mixing*fields[9])*xdot
        production=-amount*self.liquid_mixing*(fields[9]-self.liquid_equilibrium_log_odds(T))*xdot
        return -amount*self.liquid_latent*xdot,entropy_rate,production,xdot

    def liquid_phase(self,T):
        """Equilibrium two-state proxy carried by the metakaolin inventory.

        The phases share composition and molar volume. This assumed fluxed
        matrix proxy is not the melting curve of pure metakaolin.
        """
        q=self.liquid_latent/self.liquid_mixing*(1/self.liquid_tc-1/T)
        x=np.where(q.real>=0,1/(1+np.exp(-q)),np.exp(q)/(1+np.exp(q)))
        softplus=np.where(q.real>=0,q+np.log1p(np.exp(-q)),np.log1p(np.exp(q)))
        entropy=x*self.liquid_latent/self.liquid_tc+self.liquid_mixing*(softplus-x*q)
        cp=self.liquid_latent**2/(self.liquid_mixing*T**2)*x*(1-x)
        return x,entropy,cp

    def liquid_state(self,T,ns,fields):
        x=self.liquid_order(fields[9])[0] if self.kinetic_liquid else self.liquid_phase(T)[0]
        liquid_moles=self.liquid_active*ns[:,self.matrix]*x
        dry_volume=ns@self.v-ns[:,self.water_index]*self.v[self.water_index]
        fraction=liquid_moles*self.v[self.matrix]/dry_volume
        return liquid_moles,fraction,np.exp(self.liquid_gain*fraction)

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

    def thermo(self,T):
        h,s=super().thermo(T)
        _,hq,sq=self.quartz_thermo(T)
        h[...,self.quartz]=self.h0[self.quartz]+hq
        s[...,self.quartz]=self.s0[self.quartz]+sq
        x,phase_s,_=self.liquid_phase(T)
        h[...,self.matrix]+=self.liquid_active*self.liquid_latent*(x-self.liquid_reference[0])
        s[...,self.matrix]+=self.liquid_active*(phase_s-self.liquid_reference[1])
        return h,s

    def state_thermo(self,T,fields):
        h,s=self.thermo(T)
        if self.kinetic_liquid:
            x,entropy,_=self.liquid_order(fields[9])
            eq_x,eq_entropy,_=self.liquid_phase(T)
            h[:,self.matrix]+=self.liquid_active*self.liquid_latent*(x-eq_x)
            s[:,self.matrix]+=self.liquid_active*(entropy-eq_entropy)
        return h,s

    def caloric_capacity(self,T,ns,ng):
        cpq,_,_=self.quartz_thermo(T)
        capacity=super().caloric_capacity(T,ns,ng)+ns[:,self.quartz]*(cpq-self.cp[self.quartz])
        if not self.kinetic_liquid:
            capacity+=ns[:,self.matrix]*self.liquid_active*self.liquid_phase(T)[2]
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
            if self.modulus_exponent != 0:
                elastic=self.elastic_response(f,T,ns,vs+pore)
                force=elastic['stress']+self.P-pressure+cap
                denominator=elastic['tangent']*pore+pressure-cap/3
            z-=force/denominator
        pore=self.vp0*np.exp(z)
        surface=self.es0*np.exp(2*z/3)
        return f,T,ns,vs+pore,pore,surface,2/3*surface/pore

    def elastic_strain(self,f,T,bulk):
        return bulk/self.b0-1-self.thermal_strain(T)[0]-f[6]+self.initial_elastic_strain

    def elastic_response(self,f,T,ns,bulk):
        """Derivatives of F=V0*K(D/V)*e**2/2 in independent T, V, D, eta.

        D excludes liquid water. K0 refers to the initial dry-solid fraction;
        e0 balances the initial capillary traction. No dense-solid modulus,
        damage variable, clipping or extra dissipative heat is introduced.
        """
        dry=ns@self.dry_v
        exponent=self.modulus_exponent
        modulus=self.modulus*(dry/bulk/self.initial_dry_fraction)**exponent
        kv=-exponent*modulus/bulk
        kd=exponent*modulus/dry
        kvv=exponent*(exponent+1)*modulus/bulk**2
        kvd=-exponent*kd/bulk
        eps=self.elastic_strain(f,T,bulk)
        stress=modulus*eps+self.b0*kv*eps**2/2
        tangent=modulus/self.b0+2*kv*eps+self.b0*kvv*eps**2/2
        return {'modulus':modulus,'dry_fraction':dry/bulk,'eps':eps,'kv':kv,'kd':kd,
                'stress':stress,'tangent':tangent,
                'strain_coupling':modulus+self.b0*kv*eps,
                'stress_dry_derivative':kd*eps+self.b0*kvd*eps**2/2,
                'free_dry_derivative':self.b0*kd*eps**2/2}

    def skeleton_chemical_potential(self,fields,T,ns,bulk):
        if self.modulus_exponent == 0:
            return super().skeleton_chemical_potential(fields,T,ns,bulk)
        elastic=self.elastic_response(fields,T,ns,bulk)
        return elastic['free_dry_derivative'][:,None]*self.dry_v

    def mechanical_rates(self,f,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug):
        if self.modulus_exponent != 0:
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
        capacity=self.caloric_capacity(T,ns,ng)
        effective=capacity+self.modulus*self.b0*T*(eps*beta_second-beta_prime**2)+T*a**2/d
        power=heat+flow-np.sum(us*dns,axis=1)-np.sum(ug*dng,axis=1)+cap*dvs
        power+=self.modulus*self.b0*(eps+T*beta_prime)*eta_dot-T*a*rest/d
        phase_sdot=0.;phase_production=0.
        if self.kinetic_liquid:
            phase_power,phase_entropy,phase_production,_=self.liquid_relaxation(T,ns,f)
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
        dvs=dns@self.v
        ddry=dns@self.dry_v
        d=elastic['tangent']+(pressure-cap/3)/pore
        a=elastic['strain_coupling']*beta_prime+pressure/T
        rest=(elastic['strain_coupling']*eta_dot-elastic['stress_dry_derivative']*ddry
              +self.R*T/pore*dng.sum(axis=1)+(pressure-cap/3)/pore*dvs)
        capacity=self.caloric_capacity(T,ns,ng)
        effective=capacity+modulus*self.b0*T*(eps*beta_second-beta_prime**2)+T*a**2/d
        dry_energy_derivative=self.b0*elastic['kd']*(eps**2/2+T*beta_prime*eps)
        power=heat+flow-np.sum(us*dns,axis=1)-np.sum(ug*dng,axis=1)+cap*dvs
        power+=modulus*self.b0*(eps+T*beta_prime)*eta_dot-dry_energy_derivative*ddry-T*a*rest/d
        phase_sdot=0.;phase_production=0.
        if self.kinetic_liquid:
            phase_power,phase_entropy,phase_production,_=self.liquid_relaxation(T,ns,f)
            power+=phase_power
            phase_sdot=phase_entropy.sum()
        dT=power/effective
        db=(a*dT+rest)/d
        dpore=db-dvs
        elastic_sdot=self.b0*((elastic['kv']*db+elastic['kd']*ddry)*beta_prime*eps
            +modulus*(beta_prime*(db/self.b0-beta_prime*dT-eta_dot)+eps*beta_second*dT))
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
            dy[9*self.n:self.gas_offset]=self.liquid_coordinate_rate(f[0]*self.Tr,f)
        return dy

    def additional_storage(self,f,T,bulk):
        eps=self.elastic_strain(f,T,bulk)
        modulus=self.modulus
        if self.modulus_exponent != 0:
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
            power,_,production,xdot=self.liquid_relaxation(T,ns,f)
            phase_fields={'liquid_log_odds':f[9].tolist(),
                'liquid_disordered_fraction':self.liquid_order(f[9])[0].tolist(),
                'liquid_equilibrium_fraction':self.liquid_phase(T)[0].tolist(),
                'liquid_relaxation_fraction_rate_per_s':xdot.tolist(),
                'liquid_relaxation_power_w':power.tolist(),
                'liquid_relaxation_entropy_w_k':production.tolist(),
                'liquid_relaxation_entropy_per_active_mole_w_mol_k':(-self.liquid_mixing*(f[9]-self.liquid_equilibrium_log_odds(T))*xdot).tolist()}
        return {**phase_fields,'quartz_beta_fraction':self.phase(T)[0].tolist(),
                'ordered_active_fraction_of_dry_condensed_volume':ordered.tolist(),
                'structure_viscosity_ratio':viscosity_ratio.tolist(),
                'effective_axial_sintering_viscosity_pa_s':(1/inverse_viscosity).tolist(),
                'sintering_dissipation_coefficient_w_k_pa2':(self.b0*inverse_viscosity/T).tolist(),
                'effective_liquid_moles':liquid.tolist(),
                'effective_liquid_fraction_of_dry_condensed_volume':fraction.tolist(),
                'liquid_sintering_mobility_multiplier':mobility.tolist(),
                'reversible_thermal_strain':thermal.tolist(),
                'quartz_transition_strain':transition.tolist(),
                'effective_expansion_coefficient_per_k':slope.tolist(),
                'permanent_sintering_strain':f[6].tolist(),
                'dry_solid_fraction_of_bulk':elastic['dry_fraction'].tolist(),
                'effective_axial_modulus_pa':elastic['modulus'].tolist(),
                'elastic_bulk_tangent_pa_m3':elastic['tangent'].tolist(),
                'elastic_composition_potential_j_mol':self.skeleton_chemical_potential(f,T,ns,bulk).tolist(),
                'sintering_thermodynamic_force_pa':(elastic['modulus']*elastic['eps']).tolist(),
                'effective_axial_stress_pa':elastic['stress'].tolist()}

    def summarize(self,times,states):
        report,fields=super().summarize(times,states)
        residual=report['state_domain']['maximum_mechanical_equilibrium_residual_pa']
        report['solid_approximation']='Effective constant-area axial equilibrium skeleton with assumed dry-solid-fraction-dependent stiffness K=K0*((D/V)/(D_initial/V0))**m. D excludes liquid water; K0 is the initial effective modulus. Helmholtz volume/composition derivatives enter mechanical equilibrium and reaction chemical potentials. No measured porous stiffness, stress-dependent phase equilibrium, hysteresis, bending, damage or fracture.'
        report['thermodynamics']['elastic_storage']="F_el=K(D/V)*V0*epsilon^2/2; epsilon=V/V0-1-beta(T)-eta+e0; K0*(e0-m*e0^2/2)=prestress; S_el=K*V0*beta'(T)*epsilon; U_el=F_el+T*S_el. F_V=K*epsilon+V0*K_V*epsilon^2/2; mu_el_i=V0*K_D*epsilon^2*v_dry_i/2; -F_eta/V0=K*epsilon drives sintering. All partials use fixed T,V,D,eta as appropriate; zero m recovers constant K."
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
            report['liquid_approximation']='Finite-rate disordered/ordered two-state proxy carried by an assumed fraction of current metakaolin, sharing composition and molar volume. Log-odds q relaxes toward q_eq(T) with Arrhenius rate; x=logistic(q). Phase energy N*L*x and entropy N*[x*L/Tm-b*(x*log(x)+(1-x)*log(1-x))] use the preceding reference offsets. Carrier formation inherits the local x, accounted for through averaged molar h/s and reaction affinity; only N*dx is internal phase relaxation. No independent crystallization/nucleation law, measured glass transition, mineral phase diagram, phase volume jump or liquid transport. Retained disordered material on cooling is a glass proxy, not measured glass yield; sintering uses the separately declared effective structure-dependent viscosity.'
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
        report['mechanical_equilibrium_relative']=residual/self.P
        report['physical_consistency_passed']=bool(report['physical_consistency_passed'] and residual/self.P<self.p('acceptance.balance_relative','1'))
        return report,fields

    def integrate(self):
        report,fields=super().integrate()
        report['dimension_check']['identities'] += ['K*V0*epsilon^2=J','K*V0*beta_prime*epsilon=J/K','K*V0*T*(epsilon*beta_second-beta_prime^2)=J/K','n_q*v_q/V0=1','L*w/Tc^2=J/mol/K','dh_quartz/dT=Cp_quartz=T*ds_quartz/dT']
        report['dimension_check']['identities'] += ['L_liquid*w_liquid/Tm^2=J/mol/K','n_matrix*active_fraction*x*volume/dry_condensed_volume=1','exp(gain*liquid_fraction)=1']
        report['dimension_check']['identities'] += ['E_order*phi_ordered/(R*T)=1; zeta=cap*V0/(ks*pore)*dimensionless=Pa*s','eta_dot=force/zeta=1/s; V0*force*eta_dot/T=W/K; positive zeta implies nonnegative mechanical dissipation']
        report['dimension_check']['identities'] += ['D/V=1; K0*((D/V)/(D0/V0))**m=Pa; F_V=Pa; F_VV=Pa/m3; F_D*v_dry=J/mol','S=-F_T; U=F+T*S; eta_dot=(-F_eta/V0)/zeta; production=V0*(K*epsilon)**2/(zeta*T)=W/K']
        if self.kinetic_liquid:
            report['dimension_check']['identities'] += ['q=log(x/(1-x))=1; dq/dt=(q_eq-q)*exp(-E/R*(1/T-1/Tm))/tau=1/s','N*L*dx/dt=W; -N*b*(q-q_eq)*dx/dt=W/K','dU=U_T*dT+U_n*dn+N*L*dx; fixed-x latent Cp=0; no double-counted equilibrium Cp']
        else:
            report['dimension_check']['identities'] += ['dh_matrix/dT=Cp_matrix=T*ds_matrix/dT']
        return report,fields
