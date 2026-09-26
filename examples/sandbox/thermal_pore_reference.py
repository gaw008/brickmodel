"""High-precision gas/source functions and boundary-stress reference.

This reference does not call the production thermal or mechanical model.
Temperature rate is reconstructed from total energy gradients, rather than
the production gas-compression-plus-dissipation expression.
"""
import mpmath as mp


class ThermalPoreReference:
    def __init__(self, settings, sources, amount):
        self.p = {key: mp.mpf(str(value)) for key, value in settings['model'].items()}
        phase = sources['thermal_source']['phases'][settings['gas_species']]
        self.coefficients = list(map(mp.mpf, phase['cp_coefficient_strings']))
        self.h0 = mp.mpf(phase['reference_enthalpy_j_mol'])
        self.s0 = mp.mpf(phase['reference_entropy_j_mol_k'])
        self.n = mp.mpf(amount)
        self.r = self.p['gas_constant_j_mol_k']
        self.t0 = self.p['reference_temperature_k']
        self.capacity = self.p['matrix_volume_m3']*self.p['matrix_volumetric_cv_j_m3_k']

    def cp(self, t):
        a, b, c, d, e = self.coefficients
        return a+b*t+c/t**2+d/mp.sqrt(t)+e*t**2

    def standard(self, t):
        a, b, c, d, e = self.coefficients
        primitive_h = lambda x: a*x+b*x*x/2-c/x+2*d*mp.sqrt(x)+e*x**3/3
        primitive_s = lambda x: a*mp.log(x)+b*x-c/(2*x*x)-2*d/mp.sqrt(x)+e*x*x/2
        return self.h0+primitive_h(t)-primitive_h(self.t0), self.s0+primitive_s(t)-primitive_s(self.t0)

    def energy_entropy(self, a, t):
        p = self.p; v = 4*mp.pi*a**3/3
        pressure = self.n*self.r*t/v; h, s = self.standard(t)
        energy = self.n*(h-self.r*t)+self.capacity*(t-self.t0)+4*mp.pi*p['surface_tension_n_m']*a*a
        entropy = self.n*(s-self.r*mp.log(pressure/p['standard_pressure_pa']))+self.capacity*mp.log(t/self.t0)
        return energy, entropy

    def at_state(self, a, t, bath, conductance):
        p = self.p; eta, gamma, po = [p[k] for k in ['viscosity_pa_s', 'surface_tension_n_m', 'outside_pressure_pa']]
        v = 4*mp.pi*a**3/3; outer = ((v+p['matrix_volume_m3'])*3/(4*mp.pi))**(mp.mpf(1)/3)
        pressure = self.n*self.r*t/v
        matrix_pressure, c = mp.lu_solve(mp.matrix([[1, 4*eta/outer**3], [1, 4*eta/a**3]]), mp.matrix([po, pressure-2*gamma/a]))
        adot = c/a**2; dv = 4*mp.pi*c
        # Exact radial integral of 2 eta e:e, independent of a_dot-squared form.
        dissipation = 16*mp.pi*eta*c*c*(1/a**3-1/outer**3)
        heat = conductance*(bath-t); work = -po*dv
        cv = self.n*(self.cp(t)-self.r)+self.capacity
        tdot = (heat+work-8*mp.pi*gamma*a*adot)/cv
        energy, entropy = self.energy_entropy(a, t)
        entropy_rate = cv/t*tdot+3*self.n*self.r/a*adot
        bath_entropy_rate = -heat/bath
        return {'radius_m': a, 'temperature_k': t, 'gas_pressure_pa': pressure,
                'radius_rate_m_s': adot, 'temperature_rate_k_s': tdot,
                'matrix_pressure_pa': matrix_pressure, 'outer_radius_m': outer,
                'radial_velocity_constant_m3_s': c, 'pore_volume_m3': v,
                'porosity': v/(v+p['matrix_volume_m3']), 'cv_j_k': cv,
                'internal_energy_j': energy, 'entropy_j_k': entropy,
                'heat_in_w': heat, 'external_work_in_w': work,
                'viscous_dissipation_w': dissipation,
                'entropy_rate_w_k': entropy_rate, 'bath_entropy_rate_w_k': bath_entropy_rate,
                'entropy_production_w_k': entropy_rate+bath_entropy_rate,
                'viscous_entropy_production_w_k': dissipation/t,
                'heat_entropy_production_w_k': heat*(1/t-1/bath)}
