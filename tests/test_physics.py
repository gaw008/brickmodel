from __future__ import annotations

import math

import pytest

from sludge_vme.physics.kinetics import arrhenius_rate_constant, first_order_extent
from sludge_vme.physics.transport import effective_conductivity_ensemble, kozeny_carman_permeability
from sludge_vme.physics.sintering import reduced_sintering_rate


def test_first_order_arrhenius_matches_analytic_solution() -> None:
    temperature = 900.0
    rate = arrhenius_rate_constant(1.2e5, 80000.0, temperature)
    elapsed = 120.0
    assert first_order_extent(elapsed, temperature, 1.2e5, 80000.0) == pytest.approx(1.0 - math.exp(-rate * elapsed))


def test_transport_closures_are_positive_bounded_and_distinct() -> None:
    permeability = kozeny_carman_permeability(30e-6, 0.35, 180.0, sphericity=0.7)
    assert 0.0 < permeability < 1e-8
    closures = effective_conductivity_ensemble(2.5, 0.03, 0.35)
    assert set(closures) == {"maxwell_eucken", "parallel_series_midpoint"}
    assert all(item.value_W_m_K > 0 for item in closures.values())
    assert closures["maxwell_eucken"].value_W_m_K != pytest.approx(closures["parallel_series_midpoint"].value_W_m_K)
    with pytest.raises(ValueError):
        kozeny_carman_permeability(30e-6, 1.0, 180.0)


def test_reduced_sintering_rate_is_finite_and_increases_with_temperature() -> None:
    cold = reduced_sintering_rate(900.0, 0.2, 30e-6)
    hot = reduced_sintering_rate(1250.0, 0.2, 30e-6)
    assert 0.0 <= cold < hot
    assert math.isfinite(hot)
