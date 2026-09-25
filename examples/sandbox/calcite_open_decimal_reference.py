"""Independent high-precision evaluation of the declared open-column equations.

This research reference fixes each selected phase branch. It is not a time
integrator and does not assign more significant figures to source data.
"""
from mpmath import mp


class DecimalOpenColumn:
    def __init__(self, column, nominal_states, nominal_contact, segment, settings,time_s=None):
        self.column = column
        self.settings = settings
        self.segment = segment
        self.time_s = time_s
        self.nominal = nominal_states
        self.surface_initial = tuple(mp.mpf(float(v)) for v in nominal_contact['root_coordinates'])
        self.r = mp.mpf(column.cells[0].reaction.gas_constant_j_mol_k)
        self.p0 = mp.mpf(column.cells[0].p0)
        self.reference_n = mp.mpf(column.reference_nitrogen)
        self.tolerance = mp.mpf(settings['root_tolerance'])

    def standard(self, phase, t):
        a, b, c, d, e = map(mp.mpf, phase.coefficients)
        t0 = mp.mpf(phase.reference_temperature_k)
        h = (mp.mpf(phase.reference_enthalpy_j_mol)+a*(t-t0)+b*(t*t-t0*t0)/2
             +c*(1/t0-1/t)+2*d*(mp.sqrt(t)-mp.sqrt(t0))+e*(t**3-t0**3)/3)
        s = (mp.mpf(phase.reference_entropy_j_mol_k)+a*mp.log(t/t0)+b*(t-t0)
             +c*(1/t0**2-1/t**2)/2+2*d*(1/mp.sqrt(t0)-1/mp.sqrt(t))+e*(t*t-t0*t0)/2)
        return h, s

    def gas_state(self, cell, t, pc, pn, nc, nn):
        hc, sc = self.standard(cell.gas, t)
        hn, sn = self.standard(cell.nitrogen, t)
        return {'t': t, 'pc': pc, 'pn': pn, 'nc': nc, 'nn': nn,
                'hc': hc, 'hn': hn,
                'mc': hc-t*sc+self.r*t*mp.log(pc/self.p0),
                'mn': hn-t*sn+self.r*t*mp.log(pn/self.p0)}

    def partition(self, cell, t, dc, nn, nc):
        ca, v, vc, vl = map(mp.mpf, (cell.calcium, cell.volume, cell.vc, cell.vl))
        lime = nc-dc
        calcite = ca-lime
        vg = v-calcite*vc-lime*vl
        pc, pn = nc*self.r*t/vg, nn*self.r*t/vg
        ha, sa = self.standard(cell.reactant, t)
        hb, sb = self.standard(cell.product, t)
        hc, sc = self.standard(cell.gas, t)
        hn, _ = self.standard(cell.nitrogen, t)
        energy = calcite*(ha-self.p0*vc)+lime*(hb-self.p0*vl)+nc*(hc-self.r*t)+nn*(hn-self.r*t)
        affinity = hb+hc-ha-t*(sb+sc-sa)-(pc+pn-self.p0)*(vc-vl)+self.r*t*mp.log(pc/self.p0)
        state = self.gas_state(cell, t, pc, pn, nc, nn)
        state.update(energy=energy, affinity=affinity, calcite=calcite, lime=lime)
        return state

    def state(self, i, values):
        cell = self.column.cells[i]
        carbon, logn, energy = values
        dc = mp.mpf(cell.calcium)*mp.expm1(carbon) if self.column.log_carbon else carbon
        nn = self.reference_n*mp.exp(logn)
        nominal = self.nominal[i]
        phase = nominal['phase']
        t0 = mp.mpf(nominal['temperature_k'])
        if phase == 'coexistence':
            def equations(t, logg):
                state = self.partition(cell, t, dc, nn, mp.exp(logg))
                return ((state['energy']-energy)/mp.mpf(cell.volume), state['affinity'])
            t, logg = mp.findroot(equations, (t0, mp.log(mp.mpf(nominal['co2_mol']))),
                                 tol=self.tolerance, maxsteps=self.settings['maximum_root_steps'])
            nc = mp.exp(logg)
        else:
            nc = dc if phase == 'calcite' else mp.mpf(cell.calcium)+dc
            t = mp.findroot(lambda value: (self.partition(cell, value, dc, nn, nc)['energy']-energy)/mp.mpf(cell.volume),
                            t0, solver='newton', tol=self.tolerance, maxsteps=self.settings['maximum_root_steps'])
        return self.partition(cell, t, dc, nn, nc)

    def face(self, left, right, parameters):
        tl, tr = left['t'], right['t']
        hc, hn = (left['hc']+right['hc'])/2, (left['hn']+right['hn'])/2
        yc = left['mc']/tl-right['mc']/tr+hc*(1/tr-1/tl)
        yn = left['mn']/tl-right['mn']/tr+hn*(1/tr-1/tl)
        x = (left['nc']/(left['nc']+left['nn'])+right['nc']/(right['nc']+right['nn']))/2
        y = 1-x
        bulk = mp.mpf(parameters['bulk_mobility_mol2_k_j_s'])
        counter = mp.mpf(parameters['counter_mobility_mol2_k_j_s'])
        nc = (bulk*x*x+counter)*yc+(bulk*x*y-counter)*yn
        nn = (bulk*x*y-counter)*yc+(bulk*y*y+counter)*yn
        energy = mp.mpf(parameters['heat_conductance_w_k'])*(tl-tr)+hc*nc+hn*nn
        sl = (-energy+left['mc']*nc+left['mn']*nn)/tl
        sr = (energy-right['mc']*nc-right['mn']*nn)/tr
        return [nc, nn, energy, sl, sr]

    def rates(self, values):
        n = self.column.count
        states = [self.state(i, values[3*i:3*i+3]) for i in range(n)]
        out = [mp.mpf(0) for _ in values]
        for i in range(n-1):
            face = self.face(states[i], states[i+1], self.column.internal_face_parameters[i])
            for j in range(3):
                out[3*i+j] -= face[j]
                out[3*i+3+j] += face[j]
            out[-1] += face[3]+face[4]
        if 'continuous_boundary_program' in self.column.settings:
            program = self.column.settings['continuous_boundary_program'];i = self.segment
            a,b = map(mp.mpf,program['knot_times_s'][i:i+2]);weight = (mp.mpf(self.time_s)-a)/(b-a)
            def interpolate(values):
                return (1-weight)*mp.mpf(values[i])+weight*mp.mpf(values[i+1])
            index = program['species_order'].index('CO2')
            t,p,wall = [interpolate(program[k]) for k in ('gas_temperature_k','total_pressure_pa','radiation_temperature_k')]
            x = interpolate([row[index] for row in program['mole_fractions']])
        else:
            program = self.column.settings['boundary_program'][self.segment]
            t, p, x, wall = [mp.mpf(program[k]) for k in ('gas_temperature_k', 'pressure_pa', 'co2_mole_fraction', 'radiation_temperature_k')]
        cell = self.column.cells[-1]
        reservoir = self.gas_state(cell, t, p*x, p*(1-x), x, 1-x)
        boundary = self.column.boundary.surface
        factor = mp.mpf(boundary.radiation_factor)

        def surface(t, logp, logit):
            p = self.p0*mp.exp(logp)
            x = 1/(1+mp.exp(-logit))
            state = self.gas_state(cell, t, p*x, p*(1-x), x, 1-x)
            inner = self.face(states[-1], state, boundary.interior)
            outer = self.face(state, reservoir, boundary.exterior)
            radiation = factor*(wall**4-t**4)
            return inner, outer, radiation

        def balance(t, logp, logit):
            inner, outer, radiation = surface(t, logp, logit)
            residual = [inner[i]-outer[i] for i in range(3)]
            residual[2] += radiation
            return tuple(value/mp.mpf(scale) for value, scale in zip(residual, boundary.parameters['numerics']['balance_scales_carbon_nitrogen_energy'], strict=True))

        solution = mp.findroot(balance, self.surface_initial, tol=self.tolerance, maxsteps=self.settings['maximum_root_steps'])
        inner, outer, radiation = surface(*solution)
        for j in range(3):
            out[3*(n-1)+j] -= inner[j]
            out[3*n+j] = inner[j]
            out[3*n+3+j] = outer[j]
        out[3*n+6] = radiation
        out[3*n+7] = outer[4]
        out[3*n+8] = -radiation/wall
        out[-1] += inner[3]+inner[4]+outer[3]+outer[4]+radiation*(1/solution[0]-1/wall)
        for i, state in enumerate(states):
            if self.column.log_carbon:out[3*i] /= mp.mpf(self.column.cells[i].calcium)*mp.exp(values[3*i])
            out[3*i+1] /= state['nn']
        return out, states
