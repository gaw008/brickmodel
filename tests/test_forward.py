from __future__ import annotations

import math
from pathlib import Path

import pytest

from sludge_vme.config import load_case
from sludge_vme.models import simulate


ROOT = Path(__file__).resolve().parents[1]
CASE = load_case(ROOT / "examples" / "tiny_synthetic.json")


def assert_conservation(result) -> None:
    assert result.conservation["mass_relative_residual"] < 1e-8
    assert result.conservation["max_element_relative_residual"] < 1e-8
    assert result.conservation["reduced_effective_enthalpy_ode_relative_residual"] < 1e-4


def test_l0_forward_is_conservative_bounded_and_reports_proxies() -> None:
    result = simulate(CASE, "L0")
    assert result.status.code == "success", result.status.message
    assert result.fidelity == "L0"
    assert_conservation(result)
    temperatures = result.fields["temperature"]["values"]
    assert all(1.0 < value < 3000.0 and math.isfinite(value) for value in temperatures)
    assert 0.0 <= result.summary["open_porosity"]["value"] <= 1.0
    assert 0.0 <= result.summary["liquid_fraction"]["value"] <= 1.0
    assert result.summary["strength_proxy_Pa"]["proxy"] is True
    assert result.summary["environmental_status"]["status"] == "not_evaluated"
    assert "thermo_database_gap" in result.flags


def test_l1_forward_resolves_spatial_gradient_and_grid_check() -> None:
    result = simulate(CASE, "L1")
    assert result.status.code == "success", result.status.message
    assert_conservation(result)
    assert len(result.coordinates["x_m"]) == 21
    assert len(result.fields["temperature"]["values"][-1]) == 21
    assert result.summary["max_center_surface_temperature_difference_K"]["value"] >= 0.0
    assert result.solver_statistics["method"] in {"BDF", "Radau"}
    assert "grid_convergence" in result.solver_statistics
    assert result.solver_statistics["grid_convergence"]["cells"] == [21, 41]


def test_speed_mapping_and_disabled_reaction_metamorphic_cases() -> None:
    base = simulate(CASE, "L0", {"grid_check": False})
    slower = simulate(CASE, "L0", {"speed_ratio": 0.8, "grid_check": False})
    assert slower.summary["residence_time_s"]["value"] == pytest.approx(base.summary["residence_time_s"]["value"] / 0.8)
    off = simulate(CASE, "L0", {"reactions_enabled": False, "grid_check": False})
    assert sum(off.summary["released_gas_kg_per_kg_dry"]["value"].values()) == pytest.approx(0.0, abs=1e-12)
    assert all(value == pytest.approx(0.0, abs=1e-12) for value in off.summary["reaction_completion"]["value"].values())
