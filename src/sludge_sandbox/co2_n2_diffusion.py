"""Crusius et al. 2018 dilute CO2-N2 diffusion correlation, equations13/14.

Caller supplies positive pressure and temperature inside the admitted150-2000K
range. Equimolar fit omits the reported small composition dependence. The ideal
conversion D=(rho_m D)RT/p does not introduce a dense-gas correction.
"""
import math


class CarbonDioxideNitrogenDiffusion:
    def __init__(self, parameters):
        c=parameters['constants']; coefficients=parameters['coefficients']
        self.r=float(c['boltzmann_j_k'])*float(c['avogadro_mol_inverse'])
        self.temperature_scale=float(c['kelvin_scale'])
        self.scale=float(c['rho_diffusivity_scale_mol_m_s'])
        self.a=float(coefficients['constant'])
        self.b=float(coefficients['inverse_sixth_power'])
        self.c=float(coefficients['sixth_power_exponential'])

    def molar_density_diffusivity(self, temperature_k):
        t=temperature_k/self.temperature_scale
        sixth=t**(1/6)
        denominator=self.a+self.b/sixth+self.c*sixth*math.exp(-sixth*sixth)
        return self.scale*math.sqrt(t)/denominator

    def diffusivity_m2_s(self, temperature_k, pressure_pa):
        return self.molar_density_diffusivity(temperature_k)*self.r*temperature_k/pressure_pa

    def temperature_derivative_m2_s_k(self, temperature_k, pressure_pa):
        t=temperature_k/self.temperature_scale
        sixth=t**(1/6)
        exponential=math.exp(-sixth*sixth)
        denominator=self.a+self.b/sixth+self.c*sixth*exponential
        derivative=(-self.b/sixth+self.c*sixth*exponential*(1-2*sixth*sixth))/(6*t)
        return self.diffusivity_m2_s(temperature_k,pressure_pa)*(1.5/t-derivative/denominator)/self.temperature_scale
