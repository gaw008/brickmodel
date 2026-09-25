"""Laesecke and Muzny (2017), dilute CO2 viscosity, equation 4 only.

Input is positive temperature in kelvin. The caller supplies the selected
source coefficients and admitted temperature domain. No density, critical,
mixture, or porous correction is included.
"""
import math


class CarbonDioxideDiluteViscosity:
    def __init__(self, parameters):
        self.coefficients = tuple(float(v) for v in parameters['coefficients'])
        self.factor = float(parameters['experimental_scaling_factor'])
        self.unit = float(parameters['millipascal_to_pascal'])
        self.temperature_scale = float(parameters['kelvin_scale'])

    def value_and_temperature_derivative(self, temperature_k):
        t = temperature_k / self.temperature_scale
        a0, a1, a2, a3, a4, a5, a6 = self.coefficients
        sixth, root = t**(1/6), math.sqrt(t)
        third = sixth*sixth
        first_exp, second_exp = math.exp(a3*third), math.exp(-third)
        denominator = a0 + a1*sixth + a2*first_exp + (a4+a5*third)*second_exp + a6*root
        slope_times_t = (a1*sixth/6 + a2*first_exp*a3*third/3
            + (a5-a4-a5*third)*third*second_exp/3 + a6*root/2)
        viscosity = self.unit*self.factor*root/denominator
        derivative = viscosity*(0.5-slope_times_t/denominator)/temperature_k
        return viscosity, derivative

    def viscosity_pa_s(self, temperature_k):
        return self.value_and_temperature_derivative(temperature_k)[0]

    def temperature_derivative_pa_s_k(self, temperature_k):
        return self.value_and_temperature_derivative(temperature_k)[1]
