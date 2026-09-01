from __future__ import annotations

import pytest

from sludge_vme.thermo.minimal_backend import MinimalGibbsBackend


def test_minimal_gibbs_backend_conserves_elements_and_lowers_gibbs() -> None:
    backend = MinimalGibbsBackend(source_hash="manufactured")
    result = backend.equilibrate(
        T_K=1000.0,
        P_Pa=101325.0,
        element_inventory={"A": 1.0},
        candidate_phases=[
            {"id": "A_high", "formula": {"A": 1.0}, "gibbs_J_mol": 5.0},
            {"id": "A_low", "formula": {"A": 1.0}, "gibbs_J_mol": -10.0},
        ],
    )
    assert result.status == "success"
    assert result.phase_amounts["A_low"] == pytest.approx(1.0, abs=1e-9)
    assert result.element_residual["A"] == pytest.approx(0.0, abs=1e-9)
    assert result.gibbs_after_J <= result.gibbs_before_J + 1e-9
    assert result.coverage_score == 1.0


def test_missing_phase_metadata_reduces_coverage_without_fake_success() -> None:
    backend = MinimalGibbsBackend(source_hash="manufactured")
    result = backend.equilibrate(
        900.0,
        101325.0,
        {"A": 1.0},
        [{"id": "known", "formula": {"A": 1.0}, "gibbs_J_mol": 0.0}, {"id": "missing"}],
    )
    assert result.status == "success_with_coverage_gap"
    assert result.coverage_score == pytest.approx(0.5)
    assert result.missing_phases == ["missing"]
