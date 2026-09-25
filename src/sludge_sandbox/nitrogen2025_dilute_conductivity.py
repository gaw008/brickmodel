"""Zero-density N2 conductivity, Sotiriadou, Assael and Huber (2025), Eq. 2.

Coefficients, temperature scale and unit conversion are explicit inputs. This
term alone provides neither finite-density nor pore-scale conductivity.
"""


def _polynomial_and_slope(coefficients, argument):
    value, slope = float(coefficients[-1]), 0.0
    for coefficient in reversed(coefficients[:-1]):
        slope = slope*argument + value
        value = value*argument + float(coefficient)
    return value, slope


def dilute_conductivity(temperature_k, parameters):
    scale = float(parameters['critical_temperature_k'])
    reduced = temperature_k/scale
    numerator, numerator_slope = _polynomial_and_slope(
        parameters['numerator_ascending'], reduced)
    denominator, denominator_slope = _polynomial_and_slope(
        parameters['denominator_ascending'], reduced)
    conversion = float(parameters['milli_w_to_w'])
    value = numerator/denominator
    slope = (numerator_slope - value*denominator_slope)/denominator/scale
    return {'conductivity_w_m_k': conversion*value,
            'conductivity_temperature_derivative_w_m_k2': conversion*slope}
