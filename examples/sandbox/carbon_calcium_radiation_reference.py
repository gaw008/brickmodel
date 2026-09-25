"""Independent SI-constant and direct fourth-power radiation arithmetic."""
import mpmath as mp


class RadiationSource:
    def __init__(self, parameters):
        self.parameters = parameters
        source = parameters['source']
        with mp.workdps(source['source_decimal_precision']):
            self.sigma_decimal = str(2 * mp.pi ** 5 * mp.mpf(str(source['boltzmann_j_k'])) ** 4
                / (15 * mp.mpf(str(source['planck_j_s'])) ** 3 * mp.mpf(str(source['light_speed_m_s'])) ** 2))
        self.sigma = float(self.sigma_decimal)

    def flux(self, temperature, reservoir):
        p = self.parameters
        coefficient = p['emissivity'] * p['area_m2'] * self.sigma
        heat = coefficient * (reservoir ** 4 - temperature ** 4)
        body, bath = heat / temperature, -heat / reservoir
        return {'energy_in_w': heat, 'body_entropy_rate_w_k': body,
            'reservoir_entropy_rate_w_k': bath, 'entropy_production_w_k': body + bath,
            'temperature_derivative_w_k': -4 * coefficient * temperature ** 3,
            'reservoir_temperature_k': reservoir}

    def decimal_flux(self, temperature, reservoir_temperature, precision):
        with mp.workdps(precision):
            p = self.parameters
            t, reservoir = mp.mpf(str(temperature)), mp.mpf(str(reservoir_temperature))
            coefficient = mp.mpf(str(p['emissivity'])) * mp.mpf(str(p['area_m2'])) * mp.mpf(self.sigma_decimal)
            heat = coefficient * (reservoir ** 4 - t ** 4)
            return {'energy_in_w': heat, 'body_entropy_rate_w_k': heat / t,
                'reservoir_entropy_rate_w_k': -heat / reservoir,
                'entropy_production_w_k': heat / t - heat / reservoir,
                'temperature_derivative_w_k': mp.diff(lambda x: coefficient * (reservoir ** 4 - x ** 4), t)}
