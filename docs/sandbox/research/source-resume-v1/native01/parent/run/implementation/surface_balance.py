"""Shared numerical film/radiation surface balance; no material coefficients."""
from collections.abc import Callable
import math
from .exchanges import BoundaryHeat,boundary_heat
from .programmed_gas_heat import SurfacePolicy


def solve_surface_balance(
    *, cell_temperature_k: float, gas_temperature_k: float,
    radiation_temperature_k: float, area_m2: float,
    convection_w_m2_k: float, emissivity: float,
    stefan_boltzmann_w_m2_k4: float, policy: SurfacePolicy,
    conductive_into_cell: Callable[[float], float], zero_conductivity: bool,
    error_type: type[Exception],
) -> tuple[float, BoundaryHeat, float, float, float, int, str]:
    """Return surface, heat, inward conduction, residual, limit, count, status.

    The caller binds the actual geometry, area, coefficient sources and error
    type. Its conduction callback must be finite, continuous, nondecreasing
    in surface temperature and zero at cell temperature. The caller certifies
    these physical requirements; this numerical routine provides no material
    admission or source binding. Backend callback exceptions propagate intact.
    SurfacePolicy keeps its existing class identity and numerical thresholds.
    """
    def balance(surface):
        heat = boundary_heat(
            surface_temperature_k=surface, gas_temperature_k=gas_temperature_k,
            radiation_temperature_k=radiation_temperature_k, area_m2=area_m2,
            convection_w_m2_k=convection_w_m2_k, emissivity=emissivity,
            stefan_boltzmann_w_m2_k4=stefan_boltzmann_w_m2_k4)
        # Caller binds geometry and sign: surface -> cell.
        into = conductive_into_cell(surface)
        residual = math.fsum((into, -heat.convective_in_w, -heat.radiative_in_w))
        scale = max(abs(into), abs(heat.convective_in_w), abs(heat.radiative_in_w))
        limit = policy.absolute_residual_w + policy.relative_residual*scale
        if not math.isfinite(residual) or not math.isfinite(limit):
            raise error_type('nonfinite_surface_balance')
        return heat, into, residual, limit

    if convection_w_m2_k == 0 and emissivity == 0:
        return cell_temperature_k, *balance(cell_temperature_k), 0, (
            'insulated_surface_undetermined' if zero_conductivity else 'adiabatic')
    low = min(cell_temperature_k, gas_temperature_k, radiation_temperature_k)
    high = max(cell_temperature_k, gas_temperature_k, radiation_temperature_k)
    for endpoint in (low, high):
        values = balance(endpoint)
        if abs(values[2]) <= values[3]:
            return endpoint, *values, 0, 'balanced'
    for iteration in range(1, policy.maximum_iterations+1):
        middle = low/2 + high/2
        if middle == low or middle == high:
            raise error_type('surface_root_unresolvable_in_float')
        values = balance(middle)
        if abs(values[2]) <= values[3]:
            return middle, *values, iteration, 'balanced'
        if values[2] < 0:
            low = middle
        else:
            high = middle
    raise error_type('surface_iteration_limit')
