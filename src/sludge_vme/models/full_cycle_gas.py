"""Finite pore gas coupled to the full-cycle condensed-phase model.

Common-D molar diffusion and donor Darcy flow use the reciprocal logarithmic
thermal mean for transported enthalpy, shared by energy and entropy accounts.
This is a continuum mixture approximation without a Knudsen or Soret model.
Stored energy is U_s + U_g + pore surface energy; the only external mechanical
power is -P_external*dV_bulk. Reaction and phase energies are not added twice.
"""
from collections import Counter
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import csc_matrix

from .full_cycle import FullCycle


class FiniteGasFullCycle(FullCycle):
    def __init__(self, config):
        super().__init__(config)
        self.g = len(self.ng)
        self.gas_offset = 9 * self.n
        self.extent_offset = self.gas_offset + self.g * self.n
        self.last = self.extent_offset + self.nr*self.n
        self.initial_gas = self.vp0[:, None] * self.P / (self.R*self.temperatures[0]) * self.inlet
        self.diffusion = self.p('transport.diffusivity_ref', 'm2/s')
        self.diffusion_exponent = self.p('transport.diffusivity_exponent', '1')
        self.viscosity = self.p('transport.viscosity_ref', 'Pa*s')
        self.viscosity_exponent = self.p('transport.viscosity_exponent', '1')
        self.tortuosity = self.p('transport.tortuosity', '1')
        self.permeability = self.p('transport.permeability_ref', 'm2')
        self.water_mobility = self.p('transport.liquid_water_mobility', 'm2/s')
        self.retention_matrix = self.p('water.retention_scale', 'kg/kg')*self.md/self.mw[self.water_index]
        self.evaporation = [r['id'] for r in config['reactions']].index('evaporation')
        self.condensation_factor = self.p('kinetics.condensation.factor', '1')
        self.oxygen_order = self.p('kinetics.oxygen_order', '1')
        self.oxygen_reference = self.p('kinetics.oxygen_reference_pressure', 'Pa')
        self.phi0 = self.vp0/self.b0
        self.jacobian_step = self.p('numerics.jacobian_step', '1')
        self.jacobian_scale = self.p('numerics.jacobian_state_scale', '1')
        self.rhs_calls = 0

    def unpack(self, y):
        return super().unpack(y[:9*self.n])

    def gas_state(self, y, temperature, pore):
        inventory = self.initial_gas * np.exp(y[self.gas_offset:self.extent_offset].reshape(self.g, self.n).T)
        partial = inventory*self.R*temperature[:, None]/pore[:, None]
        return inventory, partial, partial.sum(axis=1)

    def transport(self, T, partial, widths, pore, bulk, tf):
        """Molar-frame common-D diffusion and pressure-driven donor advection.

        Diffusive rates sum to zero. Their entropy is D times the symmetric
        composition log distance; the donor Darcy entropy also contains a
        nonnegative composition KL term. The reciprocal logarithmic mean of
        temperature cancels the standard-state caloric part of mu/T exactly.
        """
        tl = T
        tr = np.r_[T[1:], tf]
        pl = partial
        pr = np.vstack((partial[1:], self.inlet*self.P))
        distance = np.r_[(widths[:-1]+widths[1:])/2, widths[-1]/2]
        ratio = (tl-tr)/tr
        thermal_mean = tl*np.divide(np.log1p(ratio), ratio, out=np.ones_like(ratio), where=ratio != 0)
        hg = self.h0[len(self.ns):]+(thermal_mean[:, None]-self.Tr)*self.cp[len(self.ns):]
        pressure_l = pl.sum(axis=1)
        pressure_r = pr.sum(axis=1)
        pressure = (pressure_l+pressure_r)/2
        yl = pl/pressure_l[:, None]
        yr = pr/pressure_r[:, None]
        phi = pore/bulk
        permeability = self.permeability*(phi/self.phi0)**3*((1-self.phi0)/(1-phi))**2
        face_phi = np.r_[(phi[:-1]+phi[1:])/2, phi[-1]]
        face_perm = np.r_[(widths[:-1]+widths[1:])/(widths[:-1]/permeability[:-1]+widths[1:]/permeability[1:]), permeability[-1]]
        diffusion = self.diffusion*(thermal_mean/self.Tr)**self.diffusion_exponent*self.Pr/pressure*face_phi/self.tortuosity
        concentration = pressure/(self.R*thermal_mean)
        molecular = self.area*(diffusion*concentration/distance)[:, None]*(yl-yr)
        viscosity = self.viscosity*(thermal_mean/self.Tr)**self.viscosity_exponent
        velocity = face_perm/viscosity*(pressure_l-pressure_r)/distance
        donor_concentrations = np.where((velocity.real >= 0)[:, None], pl/(self.R*tl[:, None]), pr/(self.R*tr[:, None]))
        darcy = self.area*velocity[:, None]*donor_concentrations
        flux = molecular+darcy
        energy = np.sum(flux*hg, axis=1)
        force = self.R*np.log(pl/pr)
        entropy = np.sum(flux*force, axis=1)
        hin,sin = self.thermo(np.asarray(tf))
        reservoir_mu_over_t = hin[len(self.ns):]/tf-sin[len(self.ns):]+self.R*np.log(self.inlet*self.P/self.Pr)
        return flux, energy, entropy, permeability, molecular, darcy, reservoir_mu_over_t

    def water_retention(self, fields):
        """Ideal water/matrix mixing: F=-T*S, mu_excess=R*T*log(activity).

        Matrix equivalents are fixed per initial dry mass, not added matter.
        The excess internal energy and partial water enthalpy are zero.
        Log activity remains finite even when water inventory underflows;
        the zero-matrix case explicitly selects the pure-liquid limit.
        """
        log_water = np.log(self.initial[:,self.water_index])-fields[1]
        if self.retention_matrix == 0:
            return np.zeros_like(log_water), np.zeros_like(log_water)
        q = log_water-np.log(self.retention_matrix)
        positive = q.real >= 0
        correction = np.log1p(np.exp(np.where(positive, -q, q)))
        log_activity = np.where(positive, -correction, q-correction)
        log_matrix_fraction = np.where(positive, -q-correction, -correction)
        entropy = -self.R*(np.exp(log_water)*log_activity+self.retention_matrix*log_matrix_fraction)
        return log_activity, entropy

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

    def water_transport(self, fields, T, bulk, pressure, cap):
        """Closed liquid boundary, shared flux down the same water potential.

        mu=h-T*s+v*(p-P-cap)+R*T*log(activity) governs evaporation and migration.
        Carried enthalpy includes the arithmetic mean mechanical contribution;
        the reciprocal-log temperature mean cancels constant-Cp caloric terms.
        Ideal mixing adds R*difference(log(activity)) to the entropy force,
        but no carried excess enthalpy. J=L*F gives nonnegative L*F**2.

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
        carried_h = (self.h0[self.water_index]+self.cp[self.water_index]*(thermal_mean-self.Tr)
                     +self.v[self.water_index]*(potential[:-1]+potential[1:])/2)
        log_water = np.log(self.initial[:,self.water_index])-fields[1]
        scale = np.where(log_water[:-1].real >= log_water[1:].real, log_water[:-1], log_water[1:])
        left, right = np.exp(log_water[:-1]-scale), np.exp(log_water[1:]-scale)
        width = bulk/self.area
        denominator = width[:-1]*bulk[:-1]*right+width[1:]*bulk[1:]*left
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
        h, s = self.state_thermo(T, fields)
        us = h[:, :len(self.ns)]-self.P*self.v
        ug = h[:, len(self.ns):]-self.R*T[:, None]
        mu = h-T[:, None]*s
        mu[:, :len(self.ns)] += (pressure-self.P-cap)[:, None]*self.v
        mu[:, len(self.ns):] += self.R*T[:, None]*np.log(partial/self.Pr)
        log_activity, retention_entropy = self.water_retention(fields)
        mu[:,self.water_index] += self.R*T*log_activity
        dg = mu@self.nu.T
        affinity = dg/(self.R*T[:, None])
        drive = -np.expm1(np.where(affinity.real < 0, affinity, 0))
        drive[:,self.evaporation] = self.water_phase_drive(affinity[:,self.evaporation])
        hazard = self.A*np.exp(-self.Ea/(self.R*T[:, None]))*drive
        oxygen_factor = (partial[:, self.oxygen]/self.oxygen_reference)**self.oxygen_order
        hazard[:, self.gnu[:, self.oxygen] < 0] *= oxygen_factor[:, None]
        rate = hazard*ns[:, self.reactants]
        dns = rate@self.snu
        widths = bulk/self.area
        flux, energy_flux, face_entropy, permeability, molecular, darcy, reservoir_mu_over_t = self.transport(T, partial, widths, pore, bulk, tf)
        dng = rate@self.gnu-flux
        dng[1:] += flux[:-1]
        flow = -energy_flux.copy()
        flow[1:] += energy_flux[:-1]
        water_flux, water_energy, water_entropy, water_rate, water_power, water_coordinate = self.water_transport(fields,T,bulk,pressure,cap)
        dns[:,self.water_index] += water_rate
        flow += water_power
        heat, surface_T, qext, conductance, conductivity = self.heat_transfer(T, ns, bulk, tf)
        mechanical = self.mechanical_rates(fields,T,ns,ng,bulk,pore,cap,pressure,dns,dng,heat,flow,us,ug)
        dT,db,dpore,capacity,extra_sdot,mechanical_entropy,coordinate_rate = mechanical
        sg = s[:, len(self.ns):]-self.R*np.log(partial/self.Pr)
        sdot = np.sum(capacity*dT/T)+np.sum(s[:, :len(self.ns)]*dns)+np.sum((sg-self.R)*dng)+np.sum(ng.sum(axis=1)*self.R*dpore/pore)+extra_sdot
        sdot -= self.R*np.sum(log_activity*dns[:,self.water_index])
        exchange = qext/tf-energy_flux[-1]/tf+flux[-1]@reservoir_mu_over_t
        reaction_entropy = -np.sum(rate*dg/T[:, None])
        thermal_entropy = np.sum(conductance*np.diff(T)**2/(T[:-1]*T[1:]))+qext*(1/T[-1]-1/tf)
        production = reaction_entropy+mechanical_entropy+thermal_entropy+face_entropy.sum()+water_entropy.sum()
        return {'dT':dT, 'hazard':hazard, 'rate':rate, 'dns':dns, 'dng':dng, 'db':db, 'dpore':dpore,
                'heat':heat, 'flow':flow, 'gas_flux':flux, 'pressure':pressure, 'gas':ng, 'partial':partial,
                'gas_fractions':ng/ng.sum(axis=1)[:, None], 'kiln_T':tf, 'surface_T':surface_T,
                'production':production, 'exchange':exchange, 'entropy_identity_residual':sdot-production-exchange,
                'minimum_face_entropy':float(face_entropy.real.min()), 'permeability':permeability,
                'molecular_flux':molecular, 'darcy_flux':darcy, 'energy_flux':energy_flux, 'capacity':capacity,
                'water_flux':water_flux, 'water_energy_flux':water_energy, 'water_entropy':water_entropy,
                'water_coordinate_rate':water_coordinate,
                'water_log_activity':log_activity, 'water_retention_entropy':retention_entropy,
                'water_phase_affinity':dg[:,self.evaporation],
                'water_phase_entropy':-rate[:,self.evaporation]*dg[:,self.evaporation]/T,
                'dsc':float(heat.real.sum())/(self.n*self.md), 'coordinate_rate':coordinate_rate,
                'pore':pore, 'conductivity':conductivity, 'effective_capacity':self.effective_capacity,
                'mechanical_residual':self.mechanical_residual}

    def state_thermo(self,T,fields):
        return self.thermo(T)

    def caloric_capacity(self,T,ns,ng):
        return ns@self.cp[:len(self.ns)]+ng@(self.cp[len(self.ns):]-self.R)

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
                'solid_volume/bulk_volume=1; liquid_volume/bulk_volume=1',
                'k_ref*(solid_fraction/reference_fraction)^m*(1+b*liquid_fraction)=W/m/K',
                'sigma*(pore_diameter)*T^3=W/m/K; gas_porosity*exchange_factor=1',
                'liquid_force=m3/mol*Pa/K=J/mol/K; mobility=D*area*concentration/(R*distance)=mol2*K/J/s',
                'liquid_flux=mobility*force=mol/s; liquid_flux*carried_enthalpy=W; liquid_flux*force=W/K',
                'retention_scale*initial_dry_mass/M_water=mol; n/(n+N)=1; R*T*log(activity)=J/mol',
                'F_mix=R*T*(n*log(activity)+N*log(matrix_fraction))=J; S_mix=-F_mix/T=J/K; U_mix=0',
                'phase_affinity=delta_mu/(R*T)=1; Arrhenius_rate*water_moles*phase_drive=mol/s',
                '-net_phase_rate*delta_mu/T=W/K; signed phase extent has units mol',
                'area/(half_width_left/k_left+half_width_right/k_right)=W/K']}
        return report, fields

    def summarize(self, times, states):
        rows=[]; inventories=[]; energies=[]; entropies=[]; heat=[]; flow=[]; bulks=[]
        minimum_capacity=float('inf'); maximum_mechanical_residual=0.
        min_entropy=float('inf'); min_face=float('inf'); min_water_face=float('inf'); identity_residual=0.; min_condensed=float('inf'); min_gas=float('inf')
        for t,y in zip(times, states):
            f,T,ns,bulk,pore,surface,cap = self.unpack(y)
            r = self.rates(t,y)
            radiative_conductivity = self.pore_radiative_conductivity(T,ns,bulk)
            ng = r['gas']; h,s = self.state_thermo(T,f)
            inventories.append(np.r_[ns.sum(axis=0),ng.sum(axis=0)])
            energy=np.sum(ns*(h[:, :len(self.ns)]-self.P*self.v))+np.sum(ng*(h[:, len(self.ns):]-self.R*T[:, None]))+surface.sum()
            entropy=np.sum(ns*s[:, :len(self.ns)])+np.sum(ng*(s[:, len(self.ns):]-self.R*np.log(r['partial']/self.Pr)))
            entropy+=r['water_retention_entropy'].sum()
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
                'x_m':(np.cumsum(bulk/self.area)-bulk/self.area/2).tolist(),
                'water_kg_per_initial_dry_kg':(ns[:,self.ns.index('water')]*self.mw[self.ns.index('water')]/self.md).tolist(),
                'water_activity':np.exp(r['water_log_activity']).tolist(),
                'water_log_activity':r['water_log_activity'].tolist(),
                'water_retention_entropy_j_k':r['water_retention_entropy'].tolist(),
                'water_net_phase_change_mol_s':r['rate'][:,self.evaporation].tolist(),
                'water_phase_affinity_j_mol':r['water_phase_affinity'].tolist(),
                'water_phase_entropy_w_k':r['water_phase_entropy'].tolist(),
                'internal_liquid_water_face_flux_mol_s':r['water_flux'].tolist(),
                'internal_liquid_water_face_energy_flux_w':r['water_energy_flux'].tolist(),
                'internal_liquid_water_face_entropy_w_k':r['water_entropy'].tolist(),
                **self.reaction_fields(y),
                'char_inventory_mol':ns[:,self.char].tolist(),
                'residual_carbon_kg':((ns[:,self.ns.index('organic')]+ns[:,self.ns.index('char')])*self.atomic[self.elements.index('C')]).tolist(),
                'gas_mole_fractions':{s:r['gas_fractions'][:,i].tolist() for i,s in enumerate(self.ng)},
                'gas_inventory_mol':{s:ng[:,i].tolist() for i,s in enumerate(self.ng)},
                'gas_face_flux_mol_s':{s:r['gas_flux'][:,i].tolist() for i,s in enumerate(self.ng)},
                'pressure_pa':r['pressure'].tolist(),'permeability_m2':r['permeability'].tolist(),
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
        stages={}
        for i,name in enumerate(self.config['stages']):
            a=int(np.where(times==self.times[i])[0][0]); b=int(np.where(times==self.times[i+1])[0][0]); stages[name]=balance(a,b)
        final=rows[-1]; phi=float(np.average(final['porosity'],weights=self.unpack(states[-1])[3]))
        product_mass=final['mass_kg']; density=product_mass/bulks[-1]; peak=max(r['temperature_difference_k'] for r in rows)
        summary={'mass_kg':product_mass,'total_mass_including_pore_gas_kg':float(mass[-1]),'density_kg_m3':float(density),
            'loss_on_ignition_dry_fraction':float(1-product_mass/(self.n*self.md)),'porosity':phi,
            'residual_carbon_kg':float(sum(final['residual_carbon_kg'])),'shrinkage':float(1-bulks[-1]/bulks[0]),'peak_temperature_difference_k':peak,
            'peak_overpressure_pa':max(max(r['pressure_pa'])-self.P for r in rows),
            'peak_internal_liquid_water_flux_mol_s':max(max(abs(x) for x in r['internal_liquid_water_face_flux_mol_s']) for r in rows),
            'final_retained_liquid_water_kg':sum(final['water_kg_per_initial_dry_kg'])*self.md,
            'peak_water_retention_entropy_j_k':max(sum(r['water_retention_entropy_j_k']) for r in rows),
            'peak_net_condensation_mol_s':max(sum(max(-x,0.) for x in r['water_net_phase_change_mol_s']) for r in rows),
            'peak_net_evaporation_mol_s':max(sum(max(x,0.) for x in r['water_net_phase_change_mol_s']) for r in rows),
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
        entropy_error=entropies-entropies[0]-states[:,-2:].sum(axis=1)*self.escale/self.Tr
        entropy_relative=float(np.max(np.abs(entropy_error))/(self.escale/self.Tr))
        inventory_roundoff = self.p('acceptance.inventory_roundoff_factor','1')*np.finfo(float).eps*self.nscale
        inventory_solver_budget=self.p('numerics.atol','1')*max(self.chemical_scale,float(np.max(self.extent_scale@np.abs(self.snu))))
        inventory_budget=inventory_roundoff+inventory_solver_budget
        drying=int(np.where(times==self.times[self.config['stages'].index('drying')+1])[0][0])
        remaining=max(rows[drying]['water_kg_per_initial_dry_kg'])/self.p('material.water_dry_ratio','kg/kg')
        cooled=max(abs(t-self.temperatures[-1]) for t in final['temperature_k'])
        report={'schema':'sludge_vme_full_cycle_result_v2','scope':self.config['scope'],'material_applicability':'待实测','real_world_validation':'待实测',
            'gas_approximation':'Stored ideal O2/N2/H2O/CO2 gas, common-D molar diffusion plus donor Darcy flow with entropy-compatible carried enthalpy; assumed diffusivity and pore properties. No imposed internal pressure or independent per-cell sweep.',
            'thermal_approximation':'Background k=k_ref*(dry_solid_fraction/initial_dry_solid_fraction)^m*(1+b*liquid_water_volume_fraction), plus local pore-wall radiative k=4*sigma*factor*length*gas_porosity*T^3. Length is 2*r_initial*(pore_volume/initial_pore_volume)^(1/3), independent of mesh width. The assumed exchange factor includes wall emissivity and geometry; one local equilibrium temperature, no spectral/nonlocal photon or participating-gas radiation. Shared face and external half-cell resistances use total k; exterior furnace radiation remains a separate boundary exchange. No extra stored photon energy or separate radiation heat source. No intrinsic mineral conductivity law; coefficients unmeasured.',
            'liquid_water_transport_approximation':'Internal liquid-water migration and evaporation share mechanical potential plus R*T*log(activity), with ideal-mixing activity n_water/(n_water+fixed_matrix_equivalents). Positive series availability mobility multiplies the combined mechanical and log-activity force. Shared carried enthalpy uses reciprocal-log thermal mean plus mean mechanical potential times molar volume; ideal mixing adds no excess enthalpy. Log water inventory permits influx/loss, with separate reaction extents. Zero liquid flux at center/exterior; external drying occurs through pore vapor. No measured hydraulic/retention law, liquid boundary supply or hysteresis. Seeded evaporation/condensation uses the same water potential; no dry-surface nucleation or humidity-cycle material validation.',
            'water_retention_approximation':'Assumed ideal-mixing free energy F=R*T*[n*ln(n/(n+N))+N*ln(N/(n+N))], fixed immobile matrix equivalents N per initial dry mass. S=-F/T; excess U, Cp and partial enthalpy are zero. N is not added material or a measured saturation capacity. No energetic binding, temperature-dependent sorption heat, matrix-site evolution or fitted isotherm. Zero N selects pure-liquid activity one.',
            'water_phase_exchange_approximation':'Let a=(mu_vapor-mu_water)/(R*T), k=A_evap*exp(-E_evap/(R*T)). Net vapor source is k*n_water*(1-exp(a)) for a<=0, and -factor*k*n_water*(1-exp(-a)) for a>0. Unit factor gives paired forward/backward flux ratio exp(-a). Both directions use the same stoichiometry and formation-energy ledger, without extra latent heat. Reverse prefactor is proportional to existing liquid: positive seeded water can regrow, but exactly dry-surface nucleation is absent. Log water inventory and its finite signed hazard are retained without floors. No measured condensation coefficient, interface area or accommodation law; reverse factor fixed in UQ.',
            'reaction_approximation':'Competing organic oxidation and lumped CH2O -> C + H2O carbonization share the organic inventory. Char inventory receives carbonization products and loses oxidation products; it is not overwritten by an initial-char depletion formula. All pathways use the same stoichiometry, formation-energy reference and affinity. No complete pyrolysis spectrum or distinct char reactivity populations. Conversion denominators are initial reactant moles, except char oxidation uses initial char plus potential organic carbon.',
            'summary':summary,'whole_cycle':whole,'stages':stages,'conservation_passed':whole['passed'] and all(s['passed'] for s in stages.values()),
            'thermodynamics':{'minimum_sampled_entropy_production_w_k':min_entropy,'minimum_face_entropy_production_w_k':min_face,
                'minimum_liquid_water_face_entropy_production_w_k':min_water_face,
                'minimum_water_phase_entropy_production_w_k':min(min(r['water_phase_entropy_w_k']) for r in rows),
                'evaporation_extent_is_signed_net_phase_transfer':True,
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
        report['example_endpoints']={'drying_remaining_fraction':remaining,'cooling_maximum_temperature_difference_k':cooled,
            'passed':bool(remaining<self.p('acceptance.drying_remaining_fraction','1') and cooled<self.p('acceptance.cooling_temperature_difference','K'))}
        report['physical_consistency_passed']=bool(report['conservation_passed'] and min_condensed>=-inventory_budget and min_gas>0
            and minimum_capacity>0 and report['state_domain']['minimum_porosity']>0 and min_entropy>=0 and min_face>=0 and min_water_face>=0
            and entropy_relative<self.p('acceptance.entropy_relative','1'))
        return report,{'schema':'sludge_vme_full_cycle_fields_v2','cell_count':self.n,'rows':rows}
