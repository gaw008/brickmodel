"""Prescribed-temperature vented spherical pore, Wadsworth2016 EqS5.

This open-gas limiting geometry assumes unrestricted gas escape. Viscosity
is an explicitly interpreted VFT relation, not a measured brick law. The
positive-radius domain ends at finite capillary time; there is no modeled
closed-pore tail or empirical residual-porosity correction.
"""
import numpy as np
from scipy.integrate import solve_ivp


def vft_viscosity(temperature, coefficients):
    return 10**(coefficients['A']+coefficients['B_k']/(np.asarray(temperature)-coefficients['C_k']))


def capillary_clock(times, temperatures, initial_radius, surface_tension, coefficients, order):
    """Integrate each piecewise-linear recorded temperature interval."""
    t, temperature = np.asarray(times), np.asarray(temperatures)
    nodes, weights = np.polynomial.legendre.leggauss(order)
    midpoint = (temperature[1:]+temperature[:-1])/2
    half = (temperature[1:]-temperature[:-1])/2
    sampled = midpoint[:, None]+half[:, None]*nodes
    increments = np.diff(t)/2*((1/vft_viscosity(sampled, coefficients))@weights)
    return np.concatenate(([0.0], np.cumsum(increments)*surface_tension/initial_radius))


class VentedPoreClock:
    def __init__(self, initial_porosity, numerics, tolerance_factor, step_factor):
        self.initial_porosity = initial_porosity
        self.k = initial_porosity/(1-initial_porosity)

        def radius_rate(clock, radius):
            return -0.5*(1+self.k*radius**3)

        def closure(clock, radius):
            return radius[0]

        closure.terminal = True
        closure.direction = -1
        # 2*integral_0^1 dx/(1+k*x^3) < 2 for positive k.
        self.solution = solve_ivp(radius_rate, (0.0, 2.0), [1.0],
            method=numerics['method'], rtol=numerics['relative_tolerance']*tolerance_factor,
            atol=numerics['absolute_tolerance']*tolerance_factor,
            first_step=numerics['first_clock_step'], max_step=numerics['maximum_clock_step']*step_factor,
            events=closure, dense_output=True)
        self.closure_clock = float(self.solution.t_events[0][0])

    def at_clock(self, clock):
        """Evaluate inside 0 <= clock < closure_clock, selected by the caller."""
        radius = float(self.solution.sol(clock)[0])
        phi = self.initial_porosity
        normalized = radius**3/(1-phi+phi*radius**3)
        return {'radius_fraction': radius, 'normalized_porosity': normalized}
