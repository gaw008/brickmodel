"""Finite pore gas coupled to the full-cycle condensed-phase model.

Symmetric pair molar diffusion and donor Darcy flow use analytic conjugate
carried enthalpy for linear gas Cp, shared by energy and entropy accounts.
This is a continuum mixture approximation without a Knudsen or Soret model.
Stored energy is U_s + U_g + pore surface energy; the only external mechanical
power is -P_external*dV_bulk. Reaction and phase energies are not added twice.
"""
from collections import Counter
from itertools import combinations
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csc_matrix

from .full_cycle import FullCycle
from .full_cycle_diagnostics import drying_water_diagnostics, free_water_ledger


class FiniteGasFullCycle(FullCycle):
    def __init__(self, config):
        super().__init__(config)
        self.g = len(self.ng)
        self.gas_program_scale = self.p('gas.program_scale', '1')
        targets = np.array([[self.p('gas.stage.'+stage+'.'+s, '1') for s in self.ng]
                            for stage in config['stages']])
        if np.any(targets <= 0) or np.any(abs(targets.sum(axis=1)-1) > np.finfo(float).eps*self.g):
            raise ValueError('positive stage gas mole fractions must sum to one')
        self.gas_knots = np.vstack((self.inlet, self.inlet+self.gas_program_scale*(targets-self.inlet)))
        self.gas_offset = 9 * self.n
        self.extent_offset = self.gas_offset + self.g * self.n
        self.last = self.extent_offset + self.nr*self.n
        self.initial_gas = self.vp0[:, None] * self.P / (self.R*self.temperatures[0]) * self.inlet
        self.diffusion = self.p('transport.diffusivity_ref', 'm2/s')
        self.diffusion_exponent = self.p('transport.diffusivity_exponent', '1')
        self.gas_pairs = list(combinations(range(self.g), 2))
        self.gas_pair_names = [self.ng[i]+'_'+self.ng[j] for i,j in self.gas_pairs]
        self.pair_factors = np.array([self.p('transport.pair_factor.'+name, '1') for name in self.gas_pair_names])
        self.viscosity = self.p('transport.viscosity_ref', 'Pa*s')
        self.viscosity_exponent = self.p('transport.viscosity_exponent', '1')
        self.gas_cp_slope = np.array([self.p('species.'+s+'.cp_slope', 'J/mol/K2') for s in self.ng])
        self.water_cp_slope = self.p('species.water.cp_slope', 'J/mol/K2')
        self.viscosity_mixing = self.p('transport.viscosity_mixing_fraction', '1')
        self.viscosity_factors = np.array([self.p('transport.viscosity_factor.'+s, '1') for s in self.ng])
        gas_mw = self.mw[len(self.ns):]
        mass_ratio = gas_mw[:, None]/gas_mw[None, :]
        viscosity_ratio = self.viscosity_factors[:, None]/self.viscosity_factors[None, :]
        self.viscosity_phi = (1+np.sqrt(viscosity_ratio)/mass_ratio**0.25)**2/np.sqrt(8*(1+mass_ratio))
        self.tortuosity = self.p('transport.tortuosity', '1')
        self.tortuosity_exponent = self.p('transport.tortuosity_porosity_exponent', '1')
        self.permeability = self.p('transport.permeability_ref', 'm2')
        self.water_mobility = self.p('transport.liquid_water_mobility', 'm2/s')
        self.water_mobility_activation = self.p('transport.liquid_water_activation_energy', 'J/mol')
        self.retention_matrix = self.p('water.retention_scale', 'kg/kg')*self.md/self.mw[self.water_index]
        self.site_survival = self.p('water.site_survival_fraction', '1')
        self.kaolin = self.ns.index('kaolin')
        self.site_slope = np.zeros(self.n)
        if self.retention_matrix != 0 and self.site_survival != 1:
            if np.any(self.initial[:,self.kaolin] <= 0):
                raise ValueError('evolving retention sites require positive initial kaolin')
            self.site_slope = self.retention_matrix*(1-self.site_survival)/self.initial[:,self.kaolin]
        self.binding_energy = self.p('water.binding_energy', 'J/mol')
        self.binding_cp = self.p('water.binding_heat_capacity', 'J/mol/K')
        self.evaporation = [r['id'] for r in config['reactions']].index('evaporation')
        self.condensation_factor = self.p('kinetics.condensation.factor', '1')
        self.carbonation_factor = self.p('kinetics.carbonation.factor', '1')
        self.decarbonation = [r['id'] for r in config['reactions']].index('decarbonation')
        self.calcite, self.lime = self.ns.index('calcite'), self.ns.index('lime')
        self.co2 = self.ng.index('CO2')
        self.calcium_pool = self.initial[:,self.calcite]+self.initial[:,self.lime]
        if self.carbonation_factor != 0 and np.any(self.calcium_pool <= 0):
            raise ValueError('reversible carbonation requires a positive calcite/lime pool')
        self.oxygen_order = self.p('kinetics.oxygen_order', '1')
        self.oxygen_reference = self.p('kinetics.oxygen_reference_pressure', 'Pa')
        self.phi0 = self.vp0/self.b0
        self.jacobian_step = self.p('numerics.jacobian_step', '1')
        self.jacobian_scale = self.p('numerics.jacobian_state_scale', '1')
        self.rhs_calls = 0

    def unpack(self, y):
        return super().unpack(y[:9*self.n])

    def condensed_state(self, fields):
        ns = super().condensed_state(fields)
        if self.carbonation_factor != 0:
            # Replace calcite log-depletion by its fraction of conserved Ca.
            # Either pure-phase endpoint can regenerate the missing phase.
            ns[:,self.calcite] = self.calcium_pool*fields[3]
            ns[:,self.lime] = self.calcium_pool*(1-fields[3])
        return ns

    def chemical_coordinate_rates(self, hazard, rate):
        depletion, char = super().chemical_coordinate_rates(hazard,rate)
        if self.carbonation_factor != 0:
            depletion[2] = -rate[:,self.decarbonation]/self.calcium_pool
        return depletion, char

    def carbonate_rate(self, T, ns, partial, affinity):
        """Signed CaCO3 -> CaO + CO2 exchange with donor availability.

        Each branch opposes the same pure-phase chemical affinity. Reverse
        exchange consumes CaO and scales with local CO2 activity; it vanishes
        with either reactant. The conserved two-solid pool has inward rates
        at both pure-phase endpoints, without inventory floors or clipping.
        This phenomenological net law is not a microscopic flux-ratio model.
        """
        forward = affinity.real <= 0
        drive = -np.expm1(np.where(forward,affinity,0))
        reverse = -np.expm1(np.where(forward,0,-affinity))
        kinetic = self.A[self.decarbonation]*np.exp(-self.Ea[self.decarbonation]/(self.R*T))
        return kinetic*(ns[:,self.calcite]*drive-self.carbonation_factor*ns[:,self.lime]
                        *partial[:,self.co2]/self.Pr*reverse)

    def gas_state(self, y, temperature, pore):
        inventory = self.initial_gas * np.exp(y[self.gas_offset:self.extent_offset].reshape(self.g, self.n).T)
        partial = inventory*self.R*temperature[:, None]/pore[:, None]
        return inventory, partial, partial.sum(axis=1)

    def boundary_composition(self, t):
        """Prescribed reservoir on the thermal-stage clock, independent of pore state.

        Linear interpolation preserves positive, normalized mole fractions.
        Initial pore inventory is unchanged; only boundary exchange changes.
        """
        return np.array([np.interp(t,self.times,self.gas_knots[:,i]) for i in range(self.g)])

    def gas_diffusivity(self, thermal_mean, pressure, phi):
        """Positive face closure using the preceding arithmetic gas porosity.

        tau=1+(tau_initial-1)*(phi_initial/phi)**a. For the declared
        tau_initial>1 and a>=0, narrowing gas pores raises tau above one.
        a=0 recovers constant tortuosity; this is an effective transport
        factor, not a measured path-length ratio or a percolation model.
        """
        face_phi = np.r_[(phi[:-1]+phi[1:])/2, phi[-1]]
        reference_phi = np.r_[(self.phi0[:-1]+self.phi0[1:])/2, self.phi0[-1]]
        tortuosity = 1+(self.tortuosity-1)*(reference_phi/face_phi)**self.tortuosity_exponent
        diffusion = self.diffusion*(thermal_mean/self.Tr)**self.diffusion_exponent*self.Pr/pressure*face_phi/tortuosity
        return diffusion, tortuosity

    def molecular_transport(self, yl, yr, conductance):
        """Positive symmetric pair exchange in the molar frame.

        Pair i,j transfers C*f_ij*(yLi*yRj-yRi*yLj) to species i and its
        opposite to j. Its entropy is C*f_ij*R*(a-b)*log(a/b)>=0.
        Unit factors reduce algebraically to the preceding common-D law;
        evaluate that limit directly to preserve the previous arithmetic.
        This pair mobility model is not an inversion of Maxwell-Stefan
        friction equations and the factors are not measured binary D data.
        """
        if np.all(self.pair_factors == 1):
            return conductance[:, None]*(yl-yr)
        molecular = np.zeros_like(yl)
        for (i,j), factor in zip(self.gas_pairs, self.pair_factors):
            exchange = conductance*factor*(yl[:,i]*yr[:,j]-yr[:,i]*yl[:,j])
            molecular[:,i] += exchange
            molecular[:,j] -= exchange
        return molecular

    def gas_viscosity(self, temperature, fractions):
        """Low-pressure Wilke mixture with declared common temperature power.

        Pure viscosities are base(T)*factor_i, so their ratios and Wilke
        phi_ij are temperature independent. Positive mole fractions and
        coefficients give positive mixture viscosity. The root mixing
        fraction interpolates from the preceding base law (zero) to Wilke
        (one); intermediate values are an assumed model interpolation.
        Pure reference factors and the shared power are not measured fits.
        """
        base = self.viscosity*(temperature/self.Tr)**self.viscosity_exponent
        if self.viscosity_mixing == 0:
            return base
        relative = np.sum(fractions*self.viscosity_factors/(fractions@self.viscosity_phi.T), axis=-1)
        return base*((1-self.viscosity_mixing)+self.viscosity_mixing*relative)

    def gas_molar_cp(self, T):
        return self.cp[len(self.ns):]+(T[..., None]-self.Tr)*self.gas_cp_slope

    def water_background_cp(self, T):
        return self.cp[self.water_index]+self.water_cp_slope*(T-self.Tr)

    def thermo(self, T):
        """Reference-anchored integrals of Cp=c_ref+a*(T-T_ref).

        Gas and liquid-water slopes are assumed, not fitted calorimetric
        curves. Only finite-inventory hosts use this extension; binding
        and solid subclass contributions remain separate.
        """
        h, s = super().thermo(T)
        if np.any(self.gas_cp_slope != 0):
            delta = T[..., None]-self.Tr
            h[..., len(self.ns):] += self.gas_cp_slope*delta**2/2
            s[..., len(self.ns):] += self.gas_cp_slope*(delta-self.Tr*np.log(T[..., None]/self.Tr))
        if self.water_cp_slope != 0:
            delta = T-self.Tr
            h[..., self.water_index] += self.water_cp_slope*delta**2/2
            s[..., self.water_index] += self.water_cp_slope*(delta-self.Tr*np.log(T/self.Tr))
        return h, s

    def water_carried_enthalpy(self, tl, tr, thermal_mean):
        """Background face h conjugate to the same integrated liquid h/s.

        Mechanical and retention-binding contributions are added by
        water_transport. The equal-temperature limit is the local h.
        """
        hw = self.h0[self.water_index]+self.cp[self.water_index]*(thermal_mean-self.Tr)
        if self.water_cp_slope != 0:
            hw += self.water_cp_slope*(tl*tr-2*self.Tr*thermal_mean+self.Tr**2)/2
        return hw

    def gas_carried_enthalpy(self, tl, tr, thermal_mean):
        """Conjugate face enthalpy, not h evaluated at the thermal mean.

        For linear Cp, cancellation of standard-state mu/T differences
        requires h*=h_ref+c_ref*(Theta-Tr)+a*(Tl*Tright-2*Tr*Theta+Tr**2)/2.
        Its equal-temperature limit is the local h. No division by the
        face temperature difference is needed, including in the Jacobian.
        """
        hg = self.h0[len(self.ns):]+(thermal_mean[:, None]-self.Tr)*self.cp[len(self.ns):]
        if np.any(self.gas_cp_slope != 0):
            hg += (tl*tr-2*self.Tr*thermal_mean+self.Tr**2)[:, None]*self.gas_cp_slope/2
        return hg

    def transport(self, T, partial, widths, pore, bulk, tf, inlet):
        """Molar-frame pair exchange and pressure-driven donor advection.

        Pair contributions conserve total diffusive moles. Donor Darcy
        entropy retains its pressure and nonnegative composition KL terms.
        The analytic carried enthalpy cancels the standard caloric part
        of mu/T, including the new linear-Cp contribution.
        """
        tl = T
        tr = np.r_[T[1:], tf]
        pl = partial
        pr = np.vstack((partial[1:], inlet*self.P))
        distance = np.r_[(widths[:-1]+widths[1:])/2, widths[-1]/2]
        ratio = (tl-tr)/tr
        thermal_mean = tl*np.divide(np.log1p(ratio), ratio, out=np.ones_like(ratio), where=ratio != 0)
        hg = self.gas_carried_enthalpy(tl, tr, thermal_mean)
        pressure_l = pl.sum(axis=1)
        pressure_r = pr.sum(axis=1)
        pressure = (pressure_l+pressure_r)/2
        yl = pl/pressure_l[:, None]
        yr = pr/pressure_r[:, None]
        phi = pore/bulk
        permeability = self.permeability*(phi/self.phi0)**3*((1-self.phi0)/(1-phi))**2
        face_perm = np.r_[(widths[:-1]+widths[1:])/(widths[:-1]/permeability[:-1]+widths[1:]/permeability[1:]), permeability[-1]]
        diffusion, tortuosity = self.gas_diffusivity(thermal_mean, pressure, phi)
        concentration = pressure/(self.R*thermal_mean)
        molecular = self.molecular_transport(yl, yr, self.area*(diffusion*concentration/distance))
        viscosity = self.gas_viscosity(thermal_mean, (yl+yr)/2)
        velocity = face_perm/viscosity*(pressure_l-pressure_r)/distance
        donor_concentrations = np.where((velocity.real >= 0)[:, None], pl/(self.R*tl[:, None]), pr/(self.R*tr[:, None]))
        darcy = self.area*velocity[:, None]*donor_concentrations
        flux = molecular+darcy
        energy = np.sum(flux*hg, axis=1)
        force = self.R*np.log(pl/pr)
        entropy = np.sum(flux*force, axis=1)
        hin,sin = self.thermo(np.asarray(tf))
        reservoir_mu_over_t = hin[len(self.ns):]/tf-sin[len(self.ns):]+self.R*np.log(inlet*self.P/self.Pr)
        return flux, energy, entropy, permeability, molecular, darcy, reservoir_mu_over_t, diffusion, tortuosity, viscosity

    def retention_sites(self, fields):
        """Immobile equivalents: persistent sites plus kaolin-carried sites.

        N=N0*(r+(1-r)*n_kaolin/n_kaolin_initial), with declared positive r.
        Sites add no mass or state; their composition derivative is site_slope.
        """
        return self.retention_matrix*(self.site_survival+(1-self.site_survival)*np.exp(-fields[2]))

    def water_fractions(self, fields):
        """Stable mixing logs, including the explicit zero-retention limit."""
        log_water = np.log(self.initial[:,self.water_index])-fields[1]
        sites = self.retention_sites(fields)
        if self.retention_matrix == 0:
            return np.zeros_like(log_water), np.zeros_like(log_water), sites
        q = log_water-np.log(sites)
        positive = q.real >= 0
        correction = np.log1p(np.exp(np.where(positive, -q, q)))
        log_activity = np.where(positive, -correction, q-correction)
        log_matrix_fraction = np.where(positive, -q-correction, -correction)
        return log_activity, log_matrix_fraction, sites

    def water_retention(self, fields):
        """Ideal mixing F=-T*S with current immobile matrix equivalents."""
        log_activity, log_matrix_fraction, sites = self.water_fractions(fields)
        water = np.exp(np.log(self.initial[:,self.water_index])-fields[1])
        entropy = -self.R*(water*log_activity+sites*log_matrix_fraction)
        return log_activity, entropy

    def water_binding(self,T,fields):
        """Saturating binding F=g*a(T), distinct from ideal mixing.

        Storage uses g=N*n/(n+N); water and site derivatives use
        dg/dn=(N/(n+N))**2 and dg/dN=(n/(n+N))**2. The kaolin
        derivative includes both mixing and binding, via dN/dn_kaolin.
        g is an energy weight, not a second water inventory.
        """
        log_activity,log_matrix_fraction,sites=self.water_fractions(fields)
        matrix_fraction=-np.expm1(log_activity)
        water=np.exp(np.log(self.initial[:,self.water_index])-fields[1])
        amount=water*matrix_fraction
        slope=matrix_fraction**2
        entropy_coefficient=self.binding_cp*np.log(T/self.Tr)
        enthalpy_coefficient=-self.binding_energy+self.binding_cp*(T-self.Tr)
        free_coefficient=enthalpy_coefficient-T*entropy_coefficient
        site_weight=self.site_slope*np.exp(2*log_activity)
        site_entropy=-self.R*self.site_slope*log_matrix_fraction+site_weight*entropy_coefficient
        site_enthalpy=site_weight*enthalpy_coefficient
        return {'amount':amount,'slope':slope,'free_coefficient':free_coefficient,
                'energy':amount*enthalpy_coefficient,'entropy':amount*entropy_coefficient,
                'capacity':amount*self.binding_cp,'mu':slope*free_coefficient,
                'partial_h':slope*enthalpy_coefficient,'partial_s':slope*entropy_coefficient,
                'sites':sites,'kaolin_mu':site_enthalpy-T*site_entropy,
                'kaolin_h':site_enthalpy,'kaolin_s':site_entropy}

    def water_phase_drive(self, affinity):
        """Signed seeded phase exchange, with affinity=(mu_vapor-mu_water)/(RT).

        Forward evaporation is unchanged; reverse exchange scales with the
        existing liquid inventory and uses the same Arrhenius coefficient.
        Both branches oppose affinity and have bounded log-inventory rates.
        At unit reverse factor their paired one-way flux ratio is exp(-affinity).
        There is no dry-surface nucleation or independently fitted interface area.
        """
        evaporation = affinity.real <= 0
        forward = -np.expm1(np.where(evaporation, affinity, 0))
        reverse = np.expm1(np.where(evaporation, 0, -affinity))
        return forward+self.condensation_factor*reverse

    def water_mobility_resistance(self, T):
        """D_ref/D(T) for the declared reference-anchored Arrhenius law."""
        return np.exp(self.water_mobility_activation/self.R*(1/T-1/self.Tr))

    def water_transport(self, fields, T, bulk, pressure, cap):
        """Closed liquid boundary, shared flux down the same water potential.

        mu=h-T*s+v*(p-P-cap)+R*T*log(mixing_activity)+mu_binding.
        Carried enthalpy includes the arithmetic mean mechanical contribution;
        the analytic linear-Cp face enthalpy cancels background caloric terms.
        Ideal mixing adds R*difference(log(activity)) to the entropy force,
        but no carried excess enthalpy. Binding adds mean(g')*h_binding(Tmean)
        to carried enthalpy and difference(g')*mean(a(T)/T) to the force.
        These satisfy the same nonisothermal face entropy identity. J=L*F
        gives nonnegative L*F**2.

        Each half-cell resistance uses its local D(T) and water concentration.
        L=2*area/[R*(width_left/(D_left*c_left)+width_right/(D_right*c_right))].
        Temperature changes a kinetic coefficient, not the driving potential,
        transported enthalpy or stored energy. Zero activation recovers constant D.

        Harmonic availability is evaluated in scaled log inventory coordinates.
        J/n on each side is obtained algebraically before multiplying by n,
        retaining finite coordinate rates even after physical water underflows.
        """
        tl, tr = T[:-1], T[1:]
        ratio = (tl-tr)/tr
        thermal_mean = tl*np.divide(np.log1p(ratio), ratio, out=np.ones_like(ratio), where=ratio != 0)
        potential = pressure-self.P-cap
        force = self.v[self.water_index]*(potential[:-1]-potential[1:])*(1/tl+1/tr)/2
        log_activity, _ = self.water_retention(fields)
        force += self.R*(log_activity[:-1]-log_activity[1:])
        carried_h = (self.water_carried_enthalpy(tl,tr,thermal_mean)
                     +self.v[self.water_index]*(potential[:-1]+potential[1:])/2)
        binding=self.water_binding(T,fields)
        force+=(binding['slope'][:-1]-binding['slope'][1:])*(binding['free_coefficient'][:-1]/tl+binding['free_coefficient'][1:]/tr)/2
        carried_h+=(binding['slope'][:-1]+binding['slope'][1:])/2*(-self.binding_energy+self.binding_cp*(thermal_mean-self.Tr))
        log_water = np.log(self.initial[:,self.water_index])-fields[1]
        scale = np.where(log_water[:-1].real >= log_water[1:].real, log_water[:-1], log_water[1:])
        left, right = np.exp(log_water[:-1]-scale), np.exp(log_water[1:]-scale)
        width = bulk/self.area
        resistance = self.water_mobility_resistance(T)
        denominator = (width[:-1]*bulk[:-1]*right*resistance[:-1]
                       +width[1:]*bulk[1:]*left*resistance[1:])
        common = 2*self.area*self.water_mobility/self.R*force/denominator
        flux = common*np.exp(scale)*left*right
        coordinate_rate = np.zeros_like(T)
        coordinate_rate[:-1] += common*right
        coordinate_rate[1:] -= common*left
        inventory_rate = np.zeros_like(T)
        inventory_rate[:-1] -= flux
        inventory_rate[1:] += flux
        energy = flux*carried_h
        power = np.zeros_like(T)
        power[:-1] -= energy
        power[1:] += energy
        return flux, energy, flux*force, inventory_rate, power, coordinate_rate

    def rates(self, t, y):
        fields, T, ns, bulk, pore, surface, cap = self.unpack(y)
        ng, partial, pressure = self.gas_state(y, T, pore)
        tf = float(np.interp(t, self.times, self.temperatures))
        inlet = self.boundary_composition(t)
        h, s = self.state_thermo(T, fields)
        us = h[:, :len(self.ns)]-self.P*self.v
        ug = h[:, len(self.ns):]-self.R*T[:, None]
        mu = h-T[:, None]*s
        mu[:, :len(self.ns)] += (pressure-self.P-cap)[:, None]*self.v
        mu[:, :len(self.ns)] += self.skeleton_chemical_potential(fields,T,ns,bulk)
        mu[:, len(self.ns):] += self.R*T[:, None]*np.log(partial/self.Pr)
        log_activity, retention_entropy = self.water_retention(fields)
        binding=self.water_binding(T,fields)
        mu[:,self.water_index] += self.R*T*log_activity+binding['mu']
        mu[:,self.kaolin] += binding['kaolin_mu']
        us[:,self.water_index] += binding['partial_h']
        us[:,self.kaolin] += binding['kaolin_h']
        dg = mu@self.nu.T
        affinity = dg/(self.R*T[:, None])
        drive = -np.expm1(np.where(affinity.real < 0, affinity, 0))
        drive[:,self.evaporation] = self.water_phase_drive(affinity[:,self.evaporation])
        hazard = self.A*np.exp(-self.Ea/(self.R*T[:, None]))*drive
        oxygen_factor = (partial[:, self.oxygen]/self.oxygen_reference)**self.oxygen_order
        hazard[:, self.gnu[:, self.oxygen] < 0] *= oxygen_factor[:, None]
        rate = hazard*ns[:, self.reactants]
        if self.carbonation_factor != 0:
            rate[:,self.decarbonation] = self.carbonate_rate(T,ns,partial,affinity[:,self.decarbonation])
        dns = rate@self.snu
        widths = bulk/self.area
        flux, energy_flux, face_entropy, permeability, molecular, darcy, reservoir_mu_over_t, diffusion, tortuosity, viscosity = self.transport(T, partial, widths, pore, bulk, tf, inlet)
        molecular_entropy = np.sum(molecular*self.R*np.log(partial/np.vstack((partial[1:],inlet*self.P))), axis=1)
        dng = rate@self.gnu-flux
        dng[1:] += flux[:-1]
        flow = -energy_flux.copy()
        flow[1:] += energy_flux[:-1]
        water_flux, water_energy, water_entropy, water_rate, water_power, water_coordinate = self.water_transport(fields,T,bulk,pressure,cap)
        dns[:,self.water_index] += water_rate
        flow += water_power
        heat, surface_T, qext, conductance, conductivity = self.state_heat_transfer(T, ns, bulk, tf, fields)
        mechanical = self.mechanical_rates(fields,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug)
        dT,db,dpore,capacity,extra_sdot,mechanical_entropy,coordinate_rate = mechanical
        sg = s[:, len(self.ns):]-self.R*np.log(partial/self.Pr)
        sdot = np.sum(capacity*dT/T)+np.sum(s[:, :len(self.ns)]*dns)+np.sum((sg-self.R)*dng)+np.sum(ng.sum(axis=1)*self.R*dpore/pore)+extra_sdot
        sdot -= self.R*np.sum(log_activity*dns[:,self.water_index])
        sdot += np.sum(binding['partial_s']*dns[:,self.water_index])
        sdot += np.sum(binding['kaolin_s']*dns[:,self.kaolin])
        exchange = qext/tf-energy_flux[-1]/tf+flux[-1]@reservoir_mu_over_t
        reaction_entropy = -np.sum(rate*dg/T[:, None])
        thermal_entropy = np.sum(conductance*np.diff(T)**2/(T[:-1]*T[1:]))+qext*(1/T[-1]-1/tf)
        production = reaction_entropy+mechanical_entropy+thermal_entropy+face_entropy.sum()+water_entropy.sum()
        return {'dT':dT, 'hazard':hazard, 'rate':rate, 'dns':dns, 'dng':dng, 'db':db, 'dpore':dpore,
                'heat':heat, 'flow':flow, 'gas_flux':flux, 'pressure':pressure, 'gas':ng, 'partial':partial,
                'gas_fractions':ng/ng.sum(axis=1)[:, None], 'kiln_T':tf, 'surface_T':surface_T,
                'boundary_gas_fractions':inlet, 'reservoir_mu_over_t':reservoir_mu_over_t,
                'production':production, 'exchange':exchange, 'entropy_identity_residual':sdot-production-exchange,
                'minimum_face_entropy':float(face_entropy.real.min()), 'permeability':permeability,
                'gas_face_diffusivity':diffusion, 'gas_face_tortuosity':tortuosity,
                'gas_face_viscosity':viscosity,
                'molecular_entropy':molecular_entropy,
                'molecular_flux':molecular, 'darcy_flux':darcy, 'energy_flux':energy_flux, 'capacity':capacity,
                'water_flux':water_flux, 'water_energy_flux':water_energy, 'water_entropy':water_entropy,
                'water_coordinate_rate':water_coordinate,
                'water_log_activity':log_activity+binding['mu']/(self.R*T),
                'water_mixing_log_activity':log_activity,
                'water_retention_entropy':retention_entropy+binding['entropy'], 'water_binding':binding,
                'retention_site_rate':self.site_slope*dns[:,self.kaolin],
                'water_phase_affinity':dg[:,self.evaporation],
                'water_phase_entropy':-rate[:,self.evaporation]*dg[:,self.evaporation]/T,
                'carbonate_affinity':dg[:,self.decarbonation],
                'carbonate_entropy':-rate[:,self.decarbonation]*dg[:,self.decarbonation]/T,
                'dsc':float(heat.real.sum())/(self.n*self.md), 'coordinate_rate':coordinate_rate,
                'pore':pore, 'conductivity':conductivity, 'effective_capacity':self.effective_capacity,
                'mechanical_residual':self.mechanical_residual}

    def state_heat_transfer(self,T,ns,bulk,tf,fields):
        return self.heat_transfer(T,ns,bulk,tf)

    def state_thermo(self,T,fields):
        return self.thermo(T)

    def skeleton_chemical_potential(self,fields,T,ns,bulk):
        return np.zeros_like(ns)

    def caloric_capacity(self,T,ns,ng):
        capacity=ns@self.cp[:len(self.ns)]+ng@(self.cp[len(self.ns):]-self.R)
        if np.any(self.gas_cp_slope != 0):
            capacity+=np.sum(ng*(T[:, None]-self.Tr)*self.gas_cp_slope,axis=1)
        if self.water_cp_slope != 0:
            capacity+=ns[:,self.water_index]*self.water_cp_slope*(T-self.Tr)
        if self.retention_matrix != 0:
            water=ns[:,self.water_index]
            sites=self.retention_matrix*self.site_survival+self.site_slope*ns[:,self.kaolin]
            capacity+=self.binding_cp*water*sites/(water+sites)
        return capacity

    def mechanical_rates(self,f,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug):
        force=pressure-self.P-cap
        db=self.ks*np.exp(-self.Es/self.R*(1/T-1/self.Tsref))*pore/cap*force
        dpore=db-dns@self.v
        capacity=self.caloric_capacity(T,ns,ng)
        dT=(heat+flow-self.P*db-np.sum(us*dns,axis=1)-np.sum(ug*dng,axis=1)-cap*dpore)/capacity
        self.effective_capacity=capacity
        self.mechanical_residual=np.zeros_like(T)
        return dT,db,dpore,capacity,0.,np.sum(force*db/T),dpore/pore

    def additional_storage(self,f,T,bulk):
        return np.zeros_like(T),np.zeros_like(T)

    def solid_fields(self,f,T,bulk):
        return {}

    def initial_state(self):
        y = np.zeros(self.last+2*self.g+3)
        y[:self.n] = self.temperatures[0]/self.Tr
        y[5*self.n:6*self.n] = self.initial[:,self.char]/self.chemical_scale
        if self.carbonation_factor != 0:
            y[3*self.n:4*self.n] = self.initial[:,self.calcite]/self.calcium_pool
        return y

    def rhs(self, t, y):
        self.rhs_calls += 1
        r = self.rates(t, y)
        dy = np.zeros_like(y)
        f = dy[:self.gas_offset].reshape(-1, self.n)
        f[0] = r['dT']/self.Tr
        f[1:5], f[5] = self.chemical_coordinate_rates(r['hazard'],r['rate'])
        f[1] += r['water_coordinate_rate']
        f[6] = r['coordinate_rate']
        f[7] = r['heat']/self.escale
        f[8] = r['flow']/self.escale
        dy[self.gas_offset:self.extent_offset] = (r['dng']/r['gas']).T.ravel()
        dy[self.extent_offset:self.last] = r['rate'].T.ravel()/self.chemical_scale
        boundary = r['gas_flux'][-1]
        dy[self.last:self.last+self.g] = np.where(boundary.real < 0, -boundary, 0)/self.nscale
        dy[self.last+self.g:self.last+2*self.g] = np.where(boundary.real > 0, boundary, 0)/self.nscale
        dy[-3] = -self.P*r['db'].sum()/self.escale
        dy[-2:] = np.array([r['production'],r['exchange']])*self.Tr/self.escale
        return dy

    def jacobian(self, t, y):
        # The integrated diagnostic ledgers never feed back into physical RHS.
        # Their exact zero columns are supplied, not repeatedly differentiated.
        result = np.zeros((len(y), len(y)))
        for index in np.r_[np.arange(7*self.n), np.arange(9*self.n, self.extent_offset)]:
            trial = y.astype(complex)
            step = self.jacobian_step*max(abs(y[index]), self.jacobian_scale)
            trial[index] += 1j*step
            result[:, index] = self.rhs(t, trial).imag/step
        return csc_matrix(result)

    def integrate(self):
        started = time.monotonic()
        step = self.p('numerics.output_step', 's')
        times = np.unique(np.r_[np.arange(0, self.times[-1], step), self.times])
        state = self.initial_state()
        observed_times = []; observed_states = []; evaluations = 0; jacobians = 0
        for i, name in enumerate(self.config['stages']):
            a, b = self.times[i:i+2]
            observe = times[(times >= a) & (times <= b)]
            sol = solve_ivp(self.rhs, (a,b), state, method='BDF', jac=self.jacobian, t_eval=observe,
                max_step=self.p('numerics.max_step','s'), rtol=self.p('numerics.rtol','1'), atol=self.p('numerics.atol','1'))
            if not sol.success:
                raise RuntimeError(f'{name}: {sol.message}')
            keep = slice(None) if i == 0 else slice(1,None)
            observed_times.extend(sol.t[keep]); observed_states.extend(sol.y.T[keep])
            state = sol.y[:,-1]
            evaluations += sol.nfev; jacobians += sol.njev
            print(f'full-cycle {name}: t={b:g}s, elapsed={time.monotonic()-started:.2f}s, RHS calls={self.rhs_calls}',flush=True)
        report, fields = self.summarize(np.array(observed_times), np.array(observed_states))
        report['elapsed_s'] = time.monotonic()-started
        report['solver'] = {'method':'BDF','jacobian':'physical-state complex step on active constitutive branches; exact zero ledger columns',
            'nfev':evaluations,'njev':jacobians,'actual_rhs_calls_including_jacobian':self.rhs_calls,'cells':self.n,
            'restart_policy':'Carry all states and ledgers continuously across declared process-segment endpoints; restart BDF history.'}
        report['dimension_check'] = {'passed':True,'consumed_parameter_units':self.used_units,
            'identities':['nRT/V=Pa','Cp-R=Cv (J/mol/K)','mol*(kg/mol)=kg','J=mol*(J/mol)','W*s=J','Pa*m3=J',
                '(m2/Pa/s)*(Pa/m)=m/s','D*c*area/distance=mol/s','molar_flux*(chemical_potential/T)=W/K',
                'Wilke Phi and species viscosity ratios are dimensionless; sum(y_i*mu_i/sum(y_j*Phi_ij))=Pa*s',
                'solid_volume/bulk_volume=1; liquid_volume/bulk_volume=1',
                'k_ref*(solid_fraction/reference_fraction)^m*(1+b*liquid_fraction)=W/m/K',
                'sigma*(pore_diameter)*T^3=W/m/K; gas_porosity*exchange_factor=1',
                'liquid_force=m3/mol*Pa/K=J/mol/K; mobility=D*area*concentration/(R*distance)=mol2*K/J/s',
                'liquid_flux=mobility*force=mol/s; liquid_flux*carried_enthalpy=W; liquid_flux*force=W/K',
                'retention_scale*initial_dry_mass/M_water=mol; n/(n+N)=1; R*T*log(activity)=J/mol',
                'F_mix=R*T*(n*log(activity)+N*log(matrix_fraction))=J; S_mix=-F_mix/T=J/K; U_mix=0',
                'N=N0*r+c*n_kaolin=mol; c=N0*(1-r)/n_kaolin_initial=1; dN/dt=c*dn_kaolin/dt=mol/s',
                'partial_kaolin_h=c*(n/(n+N))^2*h_binding=J/mol; partial_kaolin_s=c*(-R*log(N/(n+N))+(n/(n+N))^2*s_binding)=J/mol/K',
                'phase_affinity=delta_mu/(R*T)=1; Arrhenius_rate*water_moles*phase_drive=mol/s',
                '-net_phase_rate*delta_mu/T=W/K; signed phase extent has units mol',
                'Ca_pool=n_calcite+n_lime=mol; dx_calcite/dt=-net_decarbonation_rate/Ca_pool=1/s',
                'carbonate_reverse_rate=k*n_lime*(p_CO2/P_ref)*factor*(1-exp(-affinity))=mol/s',
                'area/(half_width_left/k_left+half_width_right/k_right)=W/K',
                'g=N*n/(n+N)=mol; g_prime=(N/(n+N))^2=1; a(T)=J/mol; F_binding=g*a=J',
                'U_binding=g*(-E+C*(T-Tr))=J; S_binding=g*C*log(T/Tr)=J/K; Cp_binding=g*C=J/K',
                'mu_binding=a*g_prime=J/mol; partial_h=g_prime*(-E+C*(T-Tr))=J/mol',
                'binding_face_force=difference(g_prime)*mean(a(T)/T)=J/mol/K; J*force=W/K',
                'reservoir_y(t)=linear_interpolation_of_mole_fractions=1; sum(y)=1; y*P=Pa',
                'outward_boundary_molar_flux*reservoir_mu/T=W/K; changing external y creates no internal inventory source',
                'tau_face=1+(tau_initial-1)*(phi_initial_face/phi_face)^a=1; D_eff=D_free*phi_face/tau_face=m2/s',
                'D_pair=f_pair*D_eff=m2/s; C_pair=area*D_pair*concentration/distance=mol/s',
                'pair_flux=C_pair*(yLi*yRj-yRi*yLj)=mol/s; pair_entropy=R*pair_flux*log(yLi*yRj/(yRi*yLj))=W/K']}
        return report, fields

    def water_phase_affinity_decomposition(self,fields,T,ns,bulk,cap,r,h,s):
        """Report independently evaluated evaporation-affinity contributions.

        Every sign comes from the existing evaporation stoichiometry. The
        background h/s already include the model's reference conventions;
        this adds no thermodynamic law or correction to the forward model.
        """
        vapor=self.ng.index('H2O')
        vapor_column=len(self.ns)+vapor
        water_stoich=self.snu[self.evaporation,self.water_index]
        vapor_stoich=self.gnu[self.evaporation,vapor]
        kaolin_stoich=self.snu[self.evaporation,self.kaolin]
        reaction_volume=self.snu[self.evaporation]@self.v
        skeleton=self.skeleton_chemical_potential(fields,T,ns,bulk)
        binding=r['water_binding']
        terms={
            'liquid_water_background':water_stoich*(h[:,self.water_index]-T*s[:,self.water_index]),
            'vapor_background':vapor_stoich*(h[:,vapor_column]-T*s[:,vapor_column]),
            'vapor_partial_pressure':vapor_stoich*self.R*T*np.log(r['partial'][:,vapor]/self.Pr),
            'mechanical_pressure':reaction_volume*(r['pressure']-self.P),
            'capillary':-reaction_volume*cap,
            'skeleton_composition':skeleton@self.snu[self.evaporation],
            'ideal_water_mixing':water_stoich*self.R*T*r['water_mixing_log_activity'],
            'water_binding':water_stoich*binding['mu'],
            'retention_site_composition':kaolin_stoich*binding['kaolin_mu'],
        }
        summed=sum(terms.values())
        cells=[]
        for i in range(self.n):
            cells.append({
                'identity':'simulation', 'constitutive_identity':'assumed',
                'sign_convention':'Evaporation affinity is mu_vapor-mu_liquid_water; each contribution is weighted by the existing signed reaction stoichiometry.',
                'contribution_unit':'J/mol',
                'stoichiometry':self.config['reactions'][self.evaporation]['stoichiometry'].copy(),
                'inputs':{
                    'temperature_k':float(T[i]), 'gas_constant_j_mol_k':self.R,
                    'liquid_water_background_h_j_mol':float(h[i,self.water_index]),
                    'liquid_water_background_s_j_mol_k':float(s[i,self.water_index]),
                    'vapor_background_h_j_mol':float(h[i,vapor_column]),
                    'vapor_background_s_j_mol_k':float(s[i,vapor_column]),
                    'vapor_partial_pressure_pa':float(r['partial'][i,vapor]),
                    'reference_pressure_pa':self.Pr, 'pore_gas_pressure_pa':float(r['pressure'][i]),
                    'external_pressure_pa':self.P, 'capillary_pressure_pa':float(cap[i]),
                    'liquid_water_molar_volume_m3_mol':float(self.v[self.water_index]),
                    'reaction_condensed_volume_m3_mol':float(reaction_volume),
                    'water_mixing_log_activity':float(r['water_mixing_log_activity'][i]),
                    'water_binding_mu_j_mol':float(binding['mu'][i]),
                    'water_binding_free_coefficient_j_mol':float(binding['free_coefficient'][i]),
                    'water_binding_partial_weight':float(binding['slope'][i]),
                    'retention_site_kaolin_mu_j_mol':float(binding['kaolin_mu'][i]),
                    'skeleton_mu_j_mol':{name:float(skeleton[i,j]) for j,name in enumerate(self.ns)},
                },
                'contributions_j_mol':{name:float(value[i]) for name,value in terms.items()},
                'summed_affinity_j_mol':float(summed[i]),
                'original_affinity_j_mol':float(r['water_phase_affinity'][i]),
                'reconstruction_residual_j_mol':float(summed[i]-r['water_phase_affinity'][i]),
                'interpretation':'Same drying-end state, existing assumed constitutive laws; an arithmetic decomposition, not material validation or a new equilibrium calculation.',
            })
        return cells

    def summarize(self, times, states):
        rows=[]; inventories=[]; energies=[]; entropies=[]; heat=[]; flow=[]; bulks=[]
        minimum_capacity=float('inf'); maximum_mechanical_residual=0.
        min_entropy=float('inf'); min_face=float('inf'); min_water_face=float('inf'); identity_residual=0.; min_condensed=float('inf'); min_gas=float('inf')
        for t,y in zip(times, states):
            f,T,ns,bulk,pore,surface,cap = self.unpack(y)
            r = self.rates(t,y)
            radiative_conductivity = self.pore_radiative_conductivity(T,ns,bulk)
            ng = r['gas']; h,s = self.state_thermo(T,f)
            if t == self.times[self.config['stages'].index('drying')+1]:
                drying_affinity_decomposition=self.water_phase_affinity_decomposition(f,T,ns,bulk,cap,r,h,s)
            inventories.append(np.r_[ns.sum(axis=0),ng.sum(axis=0)])
            energy=np.sum(ns*(h[:, :len(self.ns)]-self.P*self.v))+np.sum(ng*(h[:, len(self.ns):]-self.R*T[:, None]))+surface.sum()
            entropy=np.sum(ns*s[:, :len(self.ns)])+np.sum(ng*(s[:, len(self.ns):]-self.R*np.log(r['partial']/self.Pr)))
            entropy+=r['water_retention_entropy'].sum()
            energy+=r['water_binding']['energy'].sum()
            extra_u,extra_s=self.additional_storage(f,T,bulk)
            energy+=extra_u.sum(); entropy+=extra_s.sum()
            minimum_capacity=min(minimum_capacity,float(np.min(r['effective_capacity'])))
            maximum_mechanical_residual=max(maximum_mechanical_residual,float(np.max(np.abs(r['mechanical_residual']))))
            energies.append(float(energy)); entropies.append(float(entropy)); bulks.append(float(bulk.sum()))
            heat.append(float(f[7].sum()*self.escale)); flow.append(float(f[8].sum()*self.escale))
            center=float((9*T[0]-T[1])/8)
            span=max(float(T.max()),r['surface_T'],center)-min(float(T.min()),r['surface_T'],center)
            min_entropy=min(min_entropy,r['production']); min_face=min(min_face,r['minimum_face_entropy'])
            min_water_face=min(min_water_face,float(r['water_entropy'].min()))
            identity_residual=max(identity_residual,abs(r['entropy_identity_residual']))
            min_condensed=min(min_condensed,float(ns.min())); min_gas=min(min_gas,float(ng.min()))
            rows.append({'time_s':float(t),'kiln_temperature_k':r['kiln_T'],'temperature_k':T.tolist(),
                'kiln_gas_mole_fractions':dict(zip(self.ng,r['boundary_gas_fractions'].tolist())),
                'outward_boundary_gas_enthalpy_w':float(r['energy_flux'][-1]),
                'reservoir_mu_over_t_j_mol_k':dict(zip(self.ng,r['reservoir_mu_over_t'].tolist())),
                'boundary_entropy_exchange_w_k':float(r['exchange']),
                'x_m':(np.cumsum(bulk/self.area)-bulk/self.area/2).tolist(),
                'water_kg_per_initial_dry_kg':(ns[:,self.ns.index('water')]*self.mw[self.ns.index('water')]/self.md).tolist(),
                'liquid_water_inventory_mol':ns[:,self.water_index].tolist(),
                'water_activity':np.exp(r['water_log_activity']).tolist(),
                'water_log_activity':r['water_log_activity'].tolist(),
                'water_mixing_log_activity':r['water_mixing_log_activity'].tolist(),
                'water_retention_entropy_j_k':r['water_retention_entropy'].tolist(),
                'water_binding_energy_j':r['water_binding']['energy'].tolist(),
                'water_binding_entropy_j_k':r['water_binding']['entropy'].tolist(),
                'water_binding_capacity_j_k':r['water_binding']['capacity'].tolist(),
                'water_background_molar_cp_j_mol_k':self.water_background_cp(T).tolist(),
                'liquid_water_cell_mobility_m2_s':(self.water_mobility/self.water_mobility_resistance(T)).tolist(),
                'water_binding_effective_moles':r['water_binding']['amount'].tolist(),
                'water_binding_partial_enthalpy_j_mol':r['water_binding']['partial_h'].tolist(),
                'water_retention_sites_mol':r['water_binding']['sites'].tolist(),
                'water_retention_site_rate_mol_s':r['retention_site_rate'].tolist(),
                'water_site_kaolin_mu_j_mol':r['water_binding']['kaolin_mu'].tolist(),
                'water_net_phase_change_mol_s':r['rate'][:,self.evaporation].tolist(),
                'water_phase_affinity_j_mol':r['water_phase_affinity'].tolist(),
                'water_phase_entropy_w_k':r['water_phase_entropy'].tolist(),
                'internal_liquid_water_face_flux_mol_s':r['water_flux'].tolist(),
                'internal_liquid_water_face_energy_flux_w':r['water_energy_flux'].tolist(),
                'internal_liquid_water_face_entropy_w_k':r['water_entropy'].tolist(),
                **self.reaction_fields(y),
                'char_inventory_mol':ns[:,self.char].tolist(),
                'calcite_inventory_mol':ns[:,self.calcite].tolist(),
                'lime_inventory_mol':ns[:,self.lime].tolist(),
                'net_decarbonation_rate_mol_s':r['rate'][:,self.decarbonation].tolist(),
                'carbonate_affinity_j_mol':r['carbonate_affinity'].tolist(),
                'carbonate_entropy_w_k':r['carbonate_entropy'].tolist(),
                'residual_carbon_kg':((ns[:,self.ns.index('organic')]+ns[:,self.ns.index('char')])*self.atomic[self.elements.index('C')]).tolist(),
                'gas_mole_fractions':{s:r['gas_fractions'][:,i].tolist() for i,s in enumerate(self.ng)},
                'gas_inventory_mol':{s:ng[:,i].tolist() for i,s in enumerate(self.ng)},
                'gas_face_flux_mol_s':{s:r['gas_flux'][:,i].tolist() for i,s in enumerate(self.ng)},
                'pressure_pa':r['pressure'].tolist(),'permeability_m2':r['permeability'].tolist(),
                'gas_face_diffusivity_m2_s':r['gas_face_diffusivity'].tolist(),
                'gas_face_tortuosity':r['gas_face_tortuosity'].tolist(),
                'gas_pair_diffusivity_m2_s':{name:(r['gas_face_diffusivity']*factor).tolist() for name,factor in zip(self.gas_pair_names,self.pair_factors)},
                'gas_molecular_face_flux_mol_s':{s:r['molecular_flux'][:,i].tolist() for i,s in enumerate(self.ng)},
                'gas_molecular_face_molar_sum_mol_s':r['molecular_flux'].sum(axis=1).tolist(),
                'gas_molecular_face_entropy_w_k':r['molecular_entropy'].tolist(),
                'gas_face_viscosity_pa_s':r['gas_face_viscosity'].tolist(),
                'gas_molar_cp_j_mol_k':{s:self.gas_molar_cp(T)[:,i].tolist() for i,s in enumerate(self.ng)},
                'effective_conductivity_w_m_k':r['conductivity'].tolist(),
                'pore_radiative_conductivity_w_m_k':radiative_conductivity.tolist(),
                'background_conductivity_w_m_k':(r['conductivity']-radiative_conductivity).tolist(),
                'liquid_water_volume_fraction':(ns[:,self.water_index]*self.v[self.water_index]/bulk).tolist(),
                'total_pore_volume_fraction':((pore+ns[:,self.water_index]*self.v[self.water_index])/bulk).tolist(),
                'porosity':(pore/bulk).tolist(),'thickness_shrinkage':(1-bulk/self.b0).tolist(),
                'temperature_difference_k':span,'mass_kg':float(np.sum(ns@self.mw[:len(self.ns)])),
                'total_mass_including_pore_gas_kg':float(inventories[-1]@self.mw),
                'net_heat_and_flow_w':float(r['heat'].sum()+r['flow'].sum()),
                'dsc_endothermic_w_per_initial_dry_kg':r['dsc'],'entropy_production_w_k':r['production'], **self.solid_fields(f,T,bulk)})
        inventories=np.array(inventories); energies=np.array(energies); entropies=np.array(entropies)
        heat=np.array(heat); flow=np.array(flow); bulks=np.array(bulks)
        gasin=states[:, self.last:self.last+self.g]*self.nscale
        gasout=states[:, self.last+self.g:self.last+2*self.g]*self.nscale
        gasbalance=gasin-gasout; work=states[:,-3]*self.escale
        mass=inventories@self.mw; elements=inventories@self.atom
        def balance(i,j):
            di=inventories[i:j+1]-inventories[i]; dg=gasbalance[i:j+1]-gasbalance[i]
            merror=di@self.mw-dg@self.mw[len(self.ns):]
            eerror=di@self.atom-dg@self.atom[len(self.ns):]
            element_scale=np.maximum(elements[0],(gasin[j]-gasin[i])@self.atom[len(self.ns):])
            element_rel=np.divide(np.abs(eerror),element_scale,out=np.zeros_like(eerror),where=element_scale!=0)
            energy_scale=max(float(np.ptp(heat[i:j+1])+np.ptp(flow[i:j+1])+np.ptp(work[i:j+1])),self.escale)
            uerror=energies[i:j+1]-energies[i]-(heat[i:j+1]-heat[i])-(flow[i:j+1]-flow[i])-(work[i:j+1]-work[i])
            rel={'mass':float(np.max(np.abs(merror))/mass[0]),'elements':float(element_rel.max()),'energy':float(np.max(np.abs(uerror))/energy_scale)}
            return {'relative_residuals':rel,'passed':max(rel.values())<self.p('acceptance.balance_relative','1'),
                    'energy_scale_j':energy_scale,'maximum_energy_residual_j':float(np.max(np.abs(uerror))),
                    'outer_pressure_work_j':float(work[j]-work[i]),'total_internal_and_surface_energy_change_j':float(energies[j]-energies[i]),
                    'pressure_work_integration_residual_j':float(work[j]-work[i]+self.P*(bulks[j]-bulks[i]))}
        vapor_index=self.ng.index('H2O')
        def interval_free_water(a,b):
            return free_water_ledger(self.config,rows[a],rows[b],
                boundary_in_mol=gasin[b,vapor_index]-gasin[a,vapor_index],
                boundary_out_mol=gasout[b,vapor_index]-gasout[a,vapor_index])
        stages={}
        for i,name in enumerate(self.config['stages']):
            a=int(np.where(times==self.times[i])[0][0]); b=int(np.where(times==self.times[i+1])[0][0]); stages[name]=balance(a,b)
            stages[name]['free_water_ledger']=interval_free_water(a,b)
        final=rows[-1]; phi=float(np.average(final['porosity'],weights=self.unpack(states[-1])[3]))
        product_mass=final['mass_kg']; density=product_mass/bulks[-1]; peak=max(r['temperature_difference_k'] for r in rows)
        summary={'mass_kg':product_mass,'total_mass_including_pore_gas_kg':float(mass[-1]),'density_kg_m3':float(density),
            'loss_on_ignition_dry_fraction':float(1-product_mass/(self.n*self.md)),'porosity':phi,
            'residual_carbon_kg':float(sum(final['residual_carbon_kg'])),'shrinkage':float(1-bulks[-1]/bulks[0]),'peak_temperature_difference_k':peak,
            'peak_overpressure_pa':max(max(r['pressure_pa'])-self.P for r in rows),
            'minimum_sampled_gas_face_diffusivity_m2_s':min(min(r['gas_face_diffusivity_m2_s']) for r in rows),
            'maximum_sampled_gas_face_diffusivity_m2_s':max(max(r['gas_face_diffusivity_m2_s']) for r in rows),
            'minimum_sampled_gas_face_tortuosity':min(min(r['gas_face_tortuosity']) for r in rows),
            'maximum_sampled_gas_face_tortuosity':max(max(r['gas_face_tortuosity']) for r in rows),
            'minimum_sampled_gas_pair_diffusivity_m2_s':min(min(v) for r in rows for v in r['gas_pair_diffusivity_m2_s'].values()),
            'maximum_sampled_gas_pair_diffusivity_m2_s':max(max(v) for r in rows for v in r['gas_pair_diffusivity_m2_s'].values()),
            'maximum_molecular_molar_sum_mol_s':max(max(abs(v) for v in r['gas_molecular_face_molar_sum_mol_s']) for r in rows),
            'minimum_molecular_face_entropy_w_k':min(min(r['gas_molecular_face_entropy_w_k']) for r in rows),
            'minimum_sampled_gas_face_viscosity_pa_s':min(min(r['gas_face_viscosity_pa_s']) for r in rows),
            'maximum_sampled_gas_face_viscosity_pa_s':max(max(r['gas_face_viscosity_pa_s']) for r in rows),
            'minimum_sampled_gas_molar_cp_j_mol_k':min(min(v) for r in rows for v in r['gas_molar_cp_j_mol_k'].values()),
            'maximum_sampled_gas_molar_cp_j_mol_k':max(max(v) for r in rows for v in r['gas_molar_cp_j_mol_k'].values()),
            'minimum_sampled_water_background_cp_j_mol_k':min(min(r['water_background_molar_cp_j_mol_k']) for r in rows),
            'maximum_sampled_water_background_cp_j_mol_k':max(max(r['water_background_molar_cp_j_mol_k']) for r in rows),
            'minimum_sampled_liquid_water_mobility_m2_s':min(min(r['liquid_water_cell_mobility_m2_s']) for r in rows),
            'maximum_sampled_liquid_water_mobility_m2_s':max(max(r['liquid_water_cell_mobility_m2_s']) for r in rows),
            'liquid_water_activation_energy_j_mol':self.water_mobility_activation,
            'peak_internal_liquid_water_flux_mol_s':max(max(abs(x) for x in r['internal_liquid_water_face_flux_mol_s']) for r in rows),
            'final_retained_liquid_water_kg':sum(final['water_kg_per_initial_dry_kg'])*self.md,
            'peak_water_retention_entropy_j_k':max(sum(r['water_retention_entropy_j_k']) for r in rows),
            'initial_water_binding_energy_j':sum(rows[0]['water_binding_energy_j']),
            'final_water_binding_energy_j':sum(final['water_binding_energy_j']),
            'peak_water_binding_excess_capacity_j_k':max(sum(r['water_binding_capacity_j_k']) for r in rows),
            'initial_retention_sites_mol':sum(rows[0]['water_retention_sites_mol']),
            'final_retention_sites_mol':sum(final['water_retention_sites_mol']),
            'peak_retention_site_loss_mol_s':max(-sum(r['water_retention_site_rate_mol_s']) for r in rows),
            'peak_net_condensation_mol_s':max(sum(max(-x,0.) for x in r['water_net_phase_change_mol_s']) for r in rows),
            'peak_net_evaporation_mol_s':max(sum(max(x,0.) for x in r['water_net_phase_change_mol_s']) for r in rows),
            'initial_calcite_mol':sum(rows[0]['calcite_inventory_mol']),
            'final_calcite_mol':sum(final['calcite_inventory_mol']),
            'final_lime_mol':sum(final['lime_inventory_mol']),
            'peak_net_carbonation_mol_s':max(sum(max(-x,0.) for x in r['net_decarbonation_rate_mol_s']) for r in rows),
            'peak_net_decarbonation_mol_s':max(sum(max(x,0.) for x in r['net_decarbonation_rate_mol_s']) for r in rows),
            'initial_volume_mean_conductivity_w_m_k':float(np.average(rows[0]['effective_conductivity_w_m_k'],weights=self.unpack(states[0])[3])),
            'final_volume_mean_conductivity_w_m_k':float(np.average(final['effective_conductivity_w_m_k'],weights=self.unpack(states[-1])[3])),
            'minimum_sampled_conductivity_w_m_k':min(min(r['effective_conductivity_w_m_k']) for r in rows),
            'maximum_sampled_conductivity_w_m_k':max(max(r['effective_conductivity_w_m_k']) for r in rows),
            'peak_pore_radiative_conductivity_w_m_k':max(max(r['pore_radiative_conductivity_w_m_k']) for r in rows),
            'peak_pore_radiative_fraction_of_conductivity':max(max(np.array(r['pore_radiative_conductivity_w_m_k'])/r['effective_conductivity_w_m_k']) for r in rows),
            'absorption_kg_kg':self.p('product.connectivity','1')*phi*self.p('product.water_density','kg/m3')/density,
            'strength_pa':self.p('product.dense_strength','Pa')*float(np.exp(-self.p('product.porosity_coefficient','1')*phi)),
            'defect_indicator':float(-np.expm1(-peak/self.p('product.gradient_scale','K'))),
            'minimum_sampled_entropy_production_w_k':min_entropy}
        summary['peak_char_inventory_kg'] = max(sum(r['char_inventory_mol'])*self.mw[self.char] for r in rows)
        summary['reaction_totals_mol'] = {name:float(sum(values)) for name,values in final['reaction_extent_mol'].items()}
        whole=balance(0,len(times)-1)
        whole['free_water_ledger']=interval_free_water(0,len(times)-1)
        entropy_error=entropies-entropies[0]-states[:,-2:].sum(axis=1)*self.escale/self.Tr
        entropy_relative=float(np.max(np.abs(entropy_error))/(self.escale/self.Tr))
        inventory_roundoff = self.p('acceptance.inventory_roundoff_factor','1')*np.finfo(float).eps*self.nscale
        inventory_solver_budget=self.p('numerics.atol','1')*max(self.chemical_scale,float(np.max(self.extent_scale@np.abs(self.snu))))
        inventory_budget=inventory_roundoff+inventory_solver_budget
        drying=int(np.where(times==self.times[self.config['stages'].index('drying')+1])[0][0])
        remaining=max(rows[drying]['water_kg_per_initial_dry_kg'])/self.p('material.water_dry_ratio','kg/kg')
        cooled=max(abs(t-self.temperatures[-1]) for t in final['temperature_k'])
        report={'schema':'sludge_vme_full_cycle_result_v2','scope':self.config['scope'],'material_applicability':'待实测','real_world_validation':'待实测',
            'kiln_gas_program':{'mode':'prescribed piecewise-linear external reservoir',
                'scale':self.gas_program_scale,'time_s':self.times.tolist(),
                'mole_fractions':{s:self.gas_knots[:,i].tolist() for i,s in enumerate(self.ng)},
                'status':'assumed','limitation':'No kiln combustion, circulation or finite external inventory. Reservoir composition enters boundary partial pressure, donor transport and entropy exchange at the same time; stored pore gas is never reset. External composition changes add no separate internal energy source. Gas-storage-zero historical host remains constant-inlet.'},
            'gas_approximation':'Stored ideal O2/N2/H2O/CO2 gas, symmetric pair molar exchange plus donor Darcy flow with entropy-compatible carried enthalpy; assumed diffusivity and pore properties. No imposed internal pressure or independent per-cell sweep.',
            'gas_diffusion_approximation':'D_base=D_ref*(T_face/T_ref)^b*(P_ref/P_face)*phi_face/tau_face; tau_face=1+(tau_initial-1)*(phi_initial_face/phi_face)^a. D_pair=f_pair*D_base, with positive symmetric assumed root factors. J_ij=area*D_pair*c/distance*(yLi*yRj-yRi*yLj), J_ji=-J_ij; species flux is its pair sum. Total molecular molar flux is zero algebraically, and each pair entropy is R*C_pair*(a-b)*log(a/b)>=0. Shared carried enthalpy is unchanged. Unit pair factors recover the preceding common-D law; a=0 removes only evolving tortuosity. Original gas_face_diffusivity output now denotes the common base scale, not every pair D. Arithmetic gas face porosity is retained, exterior porosity is the outer cell. No extra state, storage or heat source. This is a phenomenological pair mobility, not measured binary diffusion, full Maxwell-Stefan, dusty-gas, connected-pore, Knudsen or Soret transport. Darcy remains a separate closure; parameter ranges and correlations are not identified.',
            'gas_pair_factors':dict(zip(self.gas_pair_names,self.pair_factors.tolist())),
            'gas_viscosity_approximation':'Low-pressure Wilke mixture: mu_i=mu_ref*f_i*(T/T_ref)^b; Phi_ij=[1+sqrt(f_i/f_j)*(M_j/M_i)^(1/4)]^2/sqrt(8*(1+M_i/M_j)); mu_W=sum(y_i*mu_i/sum(y_j*Phi_ij)). Face composition is the arithmetic mean of adjacent mole fractions (including the external reservoir), evaluated at the existing reciprocal-log thermal mean. mu_face=(1-alpha)*mu_base+alpha*mu_W; alpha=0 exactly restores the preceding law. Nominal alpha=1. Positive coefficients preserve donor Darcy direction and its entropy structure, without extra storage or viscous heat addition. All pure reference factors and their common temperature exponent remain assumed. Face averaging is not a resolved variable-viscosity pore resistance; no pressure correction, slip, Knudsen, species-specific viscosity curves or material validation. New factors are fixed, not identified or range-covered by current UQ/calibration.',
            'gas_viscosity_factors':dict(zip(self.ng,self.viscosity_factors.tolist())),
            'gas_caloric_approximation':'Finite-inventory gas Cp_i=c_ref_i+a_i*(T-Tr); h_i=h_ref_i+c_ref_i*(T-Tr)+a_i*(T-Tr)^2/2; s_i=s_ref_i+c_ref_i*ln(T/Tr)+a_i*((T-Tr)-Tr*ln(T/Tr)). Ideal-gas stored u=h-RT and Cv=Cp-R; reaction affinities, reservoir mu/T and energy/entropy share these functions. Conjugate face enthalpy h*=h_ref+c_ref*(Theta-Tr)+a*(Tl*Tright-2*Tr*Theta+Tr^2)/2 cancels standard-state thermal mu/T differences exactly; it is not h(Theta). No extra reaction heat or new state. Four nonnegative slopes and reference Cp values remain assumed; new slopes fixed in paired UQ/synthetic fit, ranges and correlations not covered. Zero slopes exactly restore the previous constant-Cp host. No fitted spectroscopic/calorimetric curve, dissociation, nonideal gas or material validation. Historical gas-storage-zero host is unchanged.',
            'gas_cp_slopes_j_mol_k2':dict(zip(self.ng,self.gas_cp_slope.tolist())),
            'water_caloric_approximation':'Liquid-water background Cp=c_ref+a*(T-Tr), with reference-anchored integrals h=h_ref+c_ref*(T-Tr)+a*(T-Tr)^2/2 and s=s_ref+c_ref*ln(T/Tr)+a*((T-Tr)-Tr*ln(T/Tr)). Same h/s enter stored u=h-P*v, phase-exchange affinity and energy/entropy accounts. Conjugate liquid-face background enthalpy h*=h_ref+c_ref*(Theta-Tr)+a*(Tl*Tright-2*Tr*Theta+Tr^2)/2 cancels standard-state mu/T differences; it is not h(Theta). Mechanical, mixing and retention-binding contributions remain separate. No new state, extra latent heat, or water equation of state. Reference Cp and slope are assumed; slope fixed in paired UQ and synthetic fit, its range and correlations not covered or identified. Zero water slope restores previous water calorics, preserving other slopes. No high-temperature liquid stability, critical-point behavior, hysteresis or material validation. Historical gas-storage-zero host is unchanged.',
            'water_cp_slope_j_mol_k2':self.water_cp_slope,
            'carbonate_approximation':'Signed CaCO3 -> CaO + CO2 exchange with a conserved local calcite/lime pool. For positive carbonation factor the calcite fraction is a linear inventory coordinate, allowing regeneration from zero; raw numerical excursions are retained under the existing inventory budget, without clipping. For a=delta_mu/(R*T)<=0, rate=k*n_calcite*(1-exp(a)); for a>0, rate=-factor*k*n_lime*(p_CO2/P_ref)*(1-exp(-a)). Reverse k reuses the assumed decarbonation Arrhenius law. No separate carbonation heat, empirical equilibrium pressure, mixing entropy, interface barrier or product-layer diffusion. Pure-phase affinity uses the existing formation properties and mechanical potential. This is a phenomenological net-rate law, not measured kinetics or microscopic detailed balance. Zero factor exactly restores the previous irreversible log-depletion coordinates. Swept-gas historical mode remains irreversible.',
            'thermal_approximation':'Background k=k_ref*(dry_solid_fraction/initial_dry_solid_fraction)^m*(1+b*liquid_water_volume_fraction), plus local pore-wall radiative k=4*sigma*factor*length*gas_porosity*T^3. Length is 2*r_initial*(pore_volume/initial_pore_volume)^(1/3), independent of mesh width. The assumed exchange factor includes wall emissivity and geometry; one local equilibrium temperature, no spectral/nonlocal photon or participating-gas radiation. Shared face and external half-cell resistances use total k; exterior furnace radiation remains a separate boundary exchange. No extra stored photon energy or separate radiation heat source. No intrinsic mineral conductivity law; coefficients unmeasured.',
            'liquid_water_transport_approximation':'Migration and seeded phase exchange share mechanical, ideal-mixing and energetic-binding water potential. D(T)=D_ref*exp[-E/R*(1/T-1/Tr)] enters each half-cell resistance, L=2*A/[R*(dx_left/(D_left*c_left)+dx_right/(D_right*c_right))]. Nonnegative L multiplies the unchanged shared-face entropy force, so J*F=L*F^2. E=0 restores constant mobility; D_ref=0 removes migration. Activation is assumed and fixed in paired UQ/synthetic fitting, not range-covered or identified. Temperature-dependent mobility adds no storage, heat of transport or Soret force. Carried enthalpy uses the analytic linear-Cp conjugate background with reciprocal-log thermal mean, arithmetic mean mechanical potential times molar volume, and mean binding composition derivative times binding enthalpy at the thermal mean. Binding force is difference(g_prime)*mean(a(T)/T), satisfying the same nonisothermal entropy identity. No independent heat of transport. Log water inventory permits influx/loss; zero exterior/center liquid flow. No measured hydraulic law, dry-surface nucleation, hysteresis or humidity-cycle validation.',
            'water_retention_approximation':'Ideal mixing plus F_b=g*a(T), g=N*n/(n+N), a=-E+C*(T-Tr-T*ln(T/Tr)). Sites N=N0*(r+(1-r)*n_kaolin/n_kaolin_initial) have a declared persistent fraction r and a fraction lost with kaolin dehydroxylation. They add no matter or independent state. Both mixing and binding composition derivatives enter kaolin chemical potential, partial energy and entropy; no separate site-loss heat source. Storage U/S/Cp uses g, water partials use (N/(n+N))^2, site partials use (n/(n+N))^2 times dN/dn_kaolin. Positive residual sites are a physical hypothesis over the declared range, not a numerical inventory floor. No measured site counts, complete site disappearance, independent site kinetics, regeneration, sintering-dependent sites or hysteresis. r=1 recovers preceding fixed sites; zero N removes all retention; E=C=0 removes energetic binding only.',
            'water_phase_exchange_approximation':'Let a=(mu_vapor-mu_water)/(R*T), k=A_evap*exp(-E_evap/(R*T)). Net vapor source is k*n_water*(1-exp(a)) for a<=0, and -factor*k*n_water*(1-exp(-a)) for a>0. Unit factor gives paired forward/backward flux ratio exp(-a). Both directions use the same stoichiometry and formation-energy ledger, without extra latent heat. Reverse prefactor is proportional to existing liquid: positive seeded water can regrow, but exactly dry-surface nucleation is absent. Log water inventory and its finite signed hazard are retained without floors. No measured condensation coefficient, interface area or accommodation law; reverse factor fixed in UQ.',
            'reaction_approximation':'Competing organic oxidation and lumped CH2O -> C + H2O carbonization share the organic inventory. Char inventory receives carbonization products and loses oxidation products; it is not overwritten by an initial-char depletion formula. All pathways use the same stoichiometry, formation-energy reference and affinity. No complete pyrolysis spectrum or distinct char reactivity populations. Conversion denominators are initial reactant moles, except char oxidation uses initial char plus potential organic carbon.',
            'summary':summary,'whole_cycle':whole,'stages':stages,'conservation_passed':whole['passed'] and all(s['passed'] for s in stages.values()),
            'thermodynamics':{'minimum_sampled_entropy_production_w_k':min_entropy,'minimum_face_entropy_production_w_k':min_face,
                'minimum_liquid_water_face_entropy_production_w_k':min_water_face,
                'minimum_water_phase_entropy_production_w_k':min(min(r['water_phase_entropy_w_k']) for r in rows),
                'evaporation_extent_is_signed_net_phase_transfer':True,
                'water_binding_energy_counted_once':True,
                'site_composition_derivatives_counted_once':True,
                'carbonate_reaction_heat_counted_once':True,
                'minimum_carbonate_entropy_production_w_k':min(min(r['carbonate_entropy_w_k']) for r in rows),
                'reaction_heat_counted_once':True,'maximum_entropy_balance_residual_j_k':float(np.max(np.abs(entropy_error))),
                'entropy_balance_relative':entropy_relative,'maximum_entropy_rate_identity_residual_w_k':identity_residual},
            'parameter_status_counts':dict(Counter(x['status'] for x in self.config['parameters'].values())),
            'state_domain':{'minimum_effective_heat_capacity_j_k_per_cell':minimum_capacity,
                'maximum_mechanical_equilibrium_residual_pa':maximum_mechanical_residual,
                'minimum_condensed_moles':min_condensed,'minimum_gas_moles':min_gas,
                'condensed_inventory_roundoff_bound_mol':inventory_roundoff,
                'condensed_inventory_solver_resolution_mol':inventory_solver_budget,
                'condensed_inventory_acceptance_bound_mol':inventory_budget,'inventory_values_clipped':False,
                'minimum_temperature_k':min(min(r['temperature_k']) for r in rows),
                'minimum_porosity':min(min(r['porosity']) for r in rows),'minimum_pressure_pa':min(min(r['pressure_pa']) for r in rows)}}
        drying_start=int(np.where(times==self.times[self.config['stages'].index('drying')])[0][0])
        report['drying_water_diagnostics']=drying_water_diagnostics(
            self.config,rows[drying_start],rows[drying],
            boundary_in_mol=gasin[drying,vapor_index]-gasin[drying_start,vapor_index],
            boundary_out_mol=gasout[drying,vapor_index]-gasout[drying_start,vapor_index])
        for cell,decomposition in zip(report['drying_water_diagnostics']['end_state_cells'],drying_affinity_decomposition):
            cell['affinity_decomposition']=decomposition
        report['example_endpoints']={'drying_remaining_fraction':remaining,'cooling_maximum_temperature_difference_k':cooled,
            'passed':bool(remaining<self.p('acceptance.drying_remaining_fraction','1') and cooled<self.p('acceptance.cooling_temperature_difference','K'))}
        report['physical_consistency_passed']=bool(report['conservation_passed'] and min_condensed>=-inventory_budget and min_gas>0
            and minimum_capacity>0 and report['state_domain']['minimum_porosity']>0 and min_entropy>=0 and min_face>=0 and min_water_face>=0
            and entropy_relative<self.p('acceptance.entropy_relative','1'))
        return report,{'schema':'sludge_vme_full_cycle_fields_v2','cell_count':self.n,'rows':rows}
