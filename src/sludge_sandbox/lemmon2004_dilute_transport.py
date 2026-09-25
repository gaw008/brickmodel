"""Pure N2/O2 zero-density transport from Lemmon and Jacobsen (2004).

The caller supplies the recorded paper coefficients and unit conversions.
Returns SI properties and derivatives; no pressure or pore correction is implied.
"""
import math


def dilute_transport(temperature_k, species, parameters):
    item = parameters['species'][species]
    b = [float(value) for value in parameters['collision_log_coefficients']]
    log_reduced = math.log(temperature_k/float(item['well_depth_over_kb_k']))
    log_omega = sum(value*log_reduced**i for i, value in enumerate(b))
    log_omega_slope = sum(i*b[i]*log_reduced**(i-1) for i in range(1, len(b)))
    viscosity_micro = (float(parameters['viscosity_prefactor'])
        * math.sqrt(float(item['molar_mass_g_mol'])*temperature_k)
        / (float(item['diameter_nm'])**2*math.exp(log_omega)))
    viscosity_slope_micro = viscosity_micro*(0.5-log_omega_slope)/temperature_k
    tau = float(item['critical_temperature_k'])/temperature_k
    multiplier = float(item['conductivity_viscosity_coefficient'])
    terms = [(float(coefficient), float(exponent)) for coefficient, exponent in item['conductivity_terms']]
    conductivity_milli = multiplier*viscosity_micro + sum(a*tau**power for a, power in terms)
    conductivity_slope_milli = multiplier*viscosity_slope_micro - sum(
        a*power*tau**power/temperature_k for a, power in terms)
    eta_scale = float(parameters['unit_conversion']['micro_pa_s_to_pa_s'])
    lambda_scale = float(parameters['unit_conversion']['milli_w_m_k_to_w_m_k'])
    return {'viscosity_pa_s': viscosity_micro*eta_scale,
            'viscosity_temperature_derivative_pa_s_k': viscosity_slope_micro*eta_scale,
            'conductivity_w_m_k': conductivity_milli*lambda_scale,
            'conductivity_temperature_derivative_w_m_k2': conductivity_slope_milli*lambda_scale}
