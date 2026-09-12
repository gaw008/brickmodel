"""Root-retention checks for the limited scalar contraction, without integration."""

from fractions import Fraction as F

import pytest

from test_independent_storage import constants, energy, plate
from thermoelastic_energy_storage import ThermoelasticEnergyStorage, _sqrt_bounds


@pytest.mark.parametrize("temperatures", [(290.0, 290.0), (310.0, 310.0), (290.0, 310.0), (291.1, 308.6)])
@pytest.mark.parametrize("bits", [8, 160])
def test_original_b_root_remains_in_contracted_feasible_interval(
    temperatures: tuple[float, float], bits: int,
) -> None:
    p = plate()
    storage = ThermoelasticEnergyStorage(p)
    volume, capacity, modulus, alpha, reference = constants(p)
    coupling = modulus * alpha**2
    lower_t, upper_t = map(F, p.temperature_bounds_k)
    known_root = (sum(map(F, temperatures), F()) / 2) ** 2
    target_density = tuple(value / volume + capacity * reference for value in energy(p, temperatures))

    def h(value: F) -> F:
        return capacity * value - coupling * value**2

    lower_q = max(lower_t**2, *((value - h(upper_t)) / coupling for value in target_density))
    upper_q = min(upper_t**2, *((value - h(lower_t)) / coupling for value in target_density))
    assert lower_q <= known_root <= upper_q
    midpoint = (lower_q + upper_q) / 2
    _, scalar_enclosure = storage._scalar(midpoint, target_density, bits)
    mean_enclosure = (_sqrt_bounds(lower_q, bits)[0], _sqrt_bounds(upper_q, bits)[1])
    contracted_lower, contracted_upper = storage._interval_newton(
        lower_q, upper_q, midpoint, scalar_enclosure, mean_enclosure, bits,
    )
    assert lower_q <= contracted_lower <= known_root <= contracted_upper <= upper_q
    if lower_q == upper_q:
        assert contracted_lower == contracted_upper == known_root
