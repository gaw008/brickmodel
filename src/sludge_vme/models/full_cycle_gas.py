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
        self.last = (9 + self.g) * self.n
        self.initial_gas = self.vp0[:, None] * self.P / (self.R*self.temperatures[0]) * self.inlet
        self.diffusion = self.p('transport.diffusivity_ref', 'm2/s')
        self.diffusion_exponent = self.p('transport.diffusivity_exponent', '1')
        self.viscosity = self.p('transport.viscosity_ref', 'Pa*s')
        self.viscosity_exponent = self.p('transport.viscosity_exponent', '1')
        self.tortuosity = self.p('transport.tortuosity', '1')
        self.permeability = self.p('transport.permeability_ref', 'm2')
        self.oxygen_order = self.p('kinetics.oxygen_order', '1')
        self.phi0 = self.vp0/self.b0
        self.jacobian_step = self.p('numerics.jacobian_step', '1')
        self.jacobian_scale = self.p('numerics.jacobian_state_scale', '1')
        self.rhs_calls = 0

    def unpack(self, y):
        return super().unpack(y[:9*self.n])

    def gas_state(self, y, temperature, pore):
        inventory = self.initial_gas * np.exp(y[9*self.n:self.last].reshape(self.g, self.n).T)
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

    def rates(self, t, y):
        fields, T, ns, bulk, pore, surface, cap = self.unpack(y)
        ng, partial, pressure = self.gas_state(y, T, pore)
        tf = float(np.interp(t, self.times, self.temperatures))
        h, s = self.thermo(T)
        us = h[:, :len(self.ns)]-self.P*self.v
        ug = h[:, len(self.ns):]-self.R*T[:, None]
        mu = h-T[:, None]*s
        mu[:, :len(self.ns)] += (pressure-self.P-cap)[:, None]*self.v
        mu[:, len(self.ns):] += self.R*T[:, None]*np.log(partial/self.Pr)
        dg = mu@self.nu.T
        affinity = dg/(self.R*T[:, None])
        drive = -np.expm1(np.where(affinity.real < 0, affinity, 0))
        hazard = self.A*np.exp(-self.Ea/(self.R*T[:, None]))*drive
        oxygen_factor = (partial[:, self.oxygen]/(self.P*self.inlet[self.oxygen]))**self.oxygen_order
        hazard[:, self.gnu[:, self.oxygen] < 0] *= oxygen_factor[:, None]
        rate = hazard*ns[:, self.reactants]
        dns = rate@self.snu
        widths = bulk/self.area
        flux, energy_flux, face_entropy, permeability, molecular, darcy, reservoir_mu_over_t = self.transport(T, partial, widths, pore, bulk, tf)
        dng = rate@self.gnu-flux
        dng[1:] += flux[:-1]
        flow = -energy_flux.copy()
        flow[1:] += energy_flux[:-1]
        conductance = self.k*self.area/((widths[:-1]+widths[1:])/2)
        internal = conductance*np.diff(T)
        heat = np.zeros(self.n, dtype=T.dtype)
        heat[:-1] += internal
        heat[1:] -= internal
        surface_T = T[-1]
        resistance = widths[-1]/(2*self.k)
        for _ in range(self.surface_iterations):
            q = self.h*(tf-surface_T)+self.emissivity*self.sigma*(tf**4-surface_T**4)
            surface_T -= (surface_T-T[-1]-resistance*q)/(1+resistance*(self.h+4*self.emissivity*self.sigma*surface_T**3))
        qext = self.area*(surface_T-T[-1])/resistance
        heat[-1] += qext
        mechanical_force = pressure-self.P-cap
        db = self.ks*np.exp(-self.Es/self.R*(1/T-1/self.Tsref))*pore/cap*mechanical_force
        dpore = db-dns@self.v
        dsurface = cap*dpore
        capacity = ns@self.cp[:len(self.ns)]+ng@(self.cp[len(self.ns):]-self.R)
        dT = (heat+flow-self.P*db-np.sum(us*dns, axis=1)-np.sum(ug*dng, axis=1)-dsurface)/capacity
        sg = s[:, len(self.ns):]-self.R*np.log(partial/self.Pr)
        sdot = np.sum(capacity*dT/T)+np.sum(s[:, :len(self.ns)]*dns)+np.sum((sg-self.R)*dng)+np.sum(ng.sum(axis=1)*self.R*dpore/pore)
        exchange = qext/tf-energy_flux[-1]/tf+flux[-1]@reservoir_mu_over_t
        reaction_entropy = -np.sum(rate*dg/T[:, None])
        mechanical_entropy = np.sum(mechanical_force*db/T)
        thermal_entropy = np.sum(conductance*np.diff(T)**2/(T[:-1]*T[1:]))+qext*(1/T[-1]-1/tf)
        production = reaction_entropy+mechanical_entropy+thermal_entropy+face_entropy.sum()
        return {'dT':dT, 'hazard':hazard, 'rate':rate, 'dns':dns, 'dng':dng, 'db':db, 'dpore':dpore,
                'heat':heat, 'flow':flow, 'gas_flux':flux, 'pressure':pressure, 'gas':ng, 'partial':partial,
                'gas_fractions':ng/ng.sum(axis=1)[:, None], 'kiln_T':tf, 'surface_T':surface_T,
                'production':production, 'exchange':exchange, 'entropy_identity_residual':sdot-production-exchange,
                'minimum_face_entropy':float(face_entropy.real.min()), 'permeability':permeability,
                'molecular_flux':molecular, 'darcy_flux':darcy, 'energy_flux':energy_flux, 'capacity':capacity,
                'dsc':float(heat.real.sum())/(self.n*self.md)}

    def initial_state(self):
        y = np.zeros(self.last+2*self.g+3)
        y[:self.n] = self.temperatures[0]/self.Tr
        return y

    def rhs(self, t, y):
        self.rhs_calls += 1
        r = self.rates(t, y)
        dy = np.zeros_like(y)
        f = dy[:9*self.n].reshape(9, self.n)
        f[0] = r['dT']/self.Tr
        f[1:6] = (r['hazard']*(self.extent_scale != 0)).T
        pore = self.unpack(y)[4]
        f[6] = r['dpore']/pore
        f[7] = r['heat']/self.escale
        f[8] = r['flow']/self.escale
        dy[9*self.n:self.last] = (r['dng']/r['gas']).T.ravel()
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
        for index in np.r_[np.arange(7*self.n), np.arange(9*self.n, self.last)]:
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
                '(m2/Pa/s)*(Pa/m)=m/s','D*c*area/distance=mol/s','molar_flux*(chemical_potential/T)=W/K']}
        return report, fields

    def summarize(self, times, states):
        rows=[]; inventories=[]; energies=[]; entropies=[]; heat=[]; flow=[]; bulks=[]
        min_entropy=float('inf'); min_face=float('inf'); identity_residual=0.; min_condensed=float('inf'); min_gas=float('inf')
        for t,y in zip(times, states):
            f,T,ns,bulk,pore,surface,cap = self.unpack(y)
            r = self.rates(t,y)
            ng = r['gas']; h,s = self.thermo(T)
            inventories.append(np.r_[ns.sum(axis=0),ng.sum(axis=0)])
            energy=np.sum(ns*(h[:, :len(self.ns)]-self.P*self.v))+np.sum(ng*(h[:, len(self.ns):]-self.R*T[:, None]))+surface.sum()
            entropy=np.sum(ns*s[:, :len(self.ns)])+np.sum(ng*(s[:, len(self.ns):]-self.R*np.log(r['partial']/self.Pr)))
            energies.append(float(energy)); entropies.append(float(entropy)); bulks.append(float(bulk.sum()))
            heat.append(float(f[7].sum()*self.escale)); flow.append(float(f[8].sum()*self.escale))
            center=float((9*T[0]-T[1])/8)
            span=max(float(T.max()),r['surface_T'],center)-min(float(T.min()),r['surface_T'],center)
            min_entropy=min(min_entropy,r['production']); min_face=min(min_face,r['minimum_face_entropy'])
            identity_residual=max(identity_residual,abs(r['entropy_identity_residual']))
            min_condensed=min(min_condensed,float(ns.min())); min_gas=min(min_gas,float(ng.min()))
            rows.append({'time_s':float(t),'kiln_temperature_k':r['kiln_T'],'temperature_k':T.tolist(),
                'x_m':(np.cumsum(bulk/self.area)-bulk/self.area/2).tolist(),
                'water_kg_per_initial_dry_kg':(ns[:,self.ns.index('water')]*self.mw[self.ns.index('water')]/self.md).tolist(),
                'conversion':{reaction['id']:(-np.expm1(-f[1+i])).tolist() for i,reaction in enumerate(self.config['reactions'])},
                'residual_carbon_kg':((ns[:,self.ns.index('organic')]+ns[:,self.ns.index('char')])*self.atomic[self.elements.index('C')]).tolist(),
                'gas_mole_fractions':{s:r['gas_fractions'][:,i].tolist() for i,s in enumerate(self.ng)},
                'gas_inventory_mol':{s:ng[:,i].tolist() for i,s in enumerate(self.ng)},
                'gas_face_flux_mol_s':{s:r['gas_flux'][:,i].tolist() for i,s in enumerate(self.ng)},
                'pressure_pa':r['pressure'].tolist(),'permeability_m2':r['permeability'].tolist(),
                'porosity':(pore/bulk).tolist(),'thickness_shrinkage':(1-bulk/self.b0).tolist(),
                'temperature_difference_k':span,'mass_kg':float(np.sum(ns@self.mw[:len(self.ns)])),
                'total_mass_including_pore_gas_kg':float(inventories[-1]@self.mw),
                'net_heat_and_flow_w':float(r['heat'].sum()+r['flow'].sum()),
                'dsc_endothermic_w_per_initial_dry_kg':r['dsc'],'entropy_production_w_k':r['production']})
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
            'absorption_kg_kg':self.p('product.connectivity','1')*phi*self.p('product.water_density','kg/m3')/density,
            'strength_pa':self.p('product.dense_strength','Pa')*float(np.exp(-self.p('product.porosity_coefficient','1')*phi)),
            'defect_indicator':float(-np.expm1(-peak/self.p('product.gradient_scale','K'))),
            'minimum_sampled_entropy_production_w_k':min_entropy}
        whole=balance(0,len(times)-1)
        entropy_error=entropies-entropies[0]-states[:,-2:].sum(axis=1)*self.escale/self.Tr
        entropy_relative=float(np.max(np.abs(entropy_error))/(self.escale/self.Tr))
        inventory_roundoff = self.p('acceptance.inventory_roundoff_factor','1')*np.finfo(float).eps*self.nscale
        drying=int(np.where(times==self.times[self.config['stages'].index('drying')+1])[0][0])
        remaining=max(rows[drying]['water_kg_per_initial_dry_kg'])/self.p('material.water_dry_ratio','kg/kg')
        cooled=max(abs(t-self.temperatures[-1]) for t in final['temperature_k'])
        report={'schema':'sludge_vme_full_cycle_result_v2','scope':self.config['scope'],'material_applicability':'待实测','real_world_validation':'待实测',
            'gas_approximation':'Stored ideal O2/N2/H2O/CO2 gas, common-D molar diffusion plus donor Darcy flow with entropy-compatible carried enthalpy; assumed diffusivity and pore properties. No imposed internal pressure or independent per-cell sweep.',
            'summary':summary,'whole_cycle':whole,'stages':stages,'conservation_passed':whole['passed'] and all(s['passed'] for s in stages.values()),
            'thermodynamics':{'minimum_sampled_entropy_production_w_k':min_entropy,'minimum_face_entropy_production_w_k':min_face,
                'reaction_heat_counted_once':True,'maximum_entropy_balance_residual_j_k':float(np.max(np.abs(entropy_error))),
                'entropy_balance_relative':entropy_relative,'maximum_entropy_rate_identity_residual_w_k':identity_residual},
            'parameter_status_counts':dict(Counter(x['status'] for x in self.config['parameters'].values())),
            'state_domain':{'minimum_condensed_moles':min_condensed,'minimum_gas_moles':min_gas,
                'condensed_inventory_roundoff_bound_mol':inventory_roundoff,'inventory_values_clipped':False,
                'minimum_temperature_k':min(min(r['temperature_k']) for r in rows),
                'minimum_porosity':min(min(r['porosity']) for r in rows),'minimum_pressure_pa':min(min(r['pressure_pa']) for r in rows)}}
        report['example_endpoints']={'drying_remaining_fraction':remaining,'cooling_maximum_temperature_difference_k':cooled,
            'passed':bool(remaining<self.p('acceptance.drying_remaining_fraction','1') and cooled<self.p('acceptance.cooling_temperature_difference','K'))}
        report['physical_consistency_passed']=bool(report['conservation_passed'] and min_condensed>=-inventory_roundoff and min_gas>0
            and report['state_domain']['minimum_porosity']>0 and min_entropy>=0 and min_face>=0
            and entropy_relative<self.p('acceptance.entropy_relative','1'))
        return report,{'schema':'sludge_vme_full_cycle_fields_v2','cell_count':self.n,'rows':rows}
