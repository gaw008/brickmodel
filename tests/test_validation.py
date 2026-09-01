from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sludge_vme.config import load_case
from sludge_vme.units import degc_to_k, dry_mass_from_wet
from sludge_vme.validation import validate_case


ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = ROOT / "examples" / "tiny_synthetic.json"


def test_temperature_and_dry_basis_conversions() -> None:
    assert degc_to_k(25.0) == pytest.approx(298.15)
    assert dry_mass_from_wet(10.0, 0.30) == pytest.approx(7.0)
    with pytest.raises(ValueError):
        dry_mass_from_wet(1.0, 1.0)


def test_synthetic_case_is_valid_and_normalized() -> None:
    case = load_case(CASE_PATH)
    report = validate_case(case)
    assert report.valid, report.errors
    assert max(abs(value) for value in report.normalized_simplex_residuals.values()) < 1e-8
    assert report.source_coverage > 0.7


def test_validator_reports_precise_paths_for_bad_simplex_psd_and_shape(tmp_path: Path) -> None:
    raw = json.loads(CASE_PATH.read_text())
    raw["feedstocks"]["sludge"]["components"][0]["fraction"] = -0.1
    raw["feedstocks"]["sludge"]["particle_size_distribution"]["d10_m"] = 1e-3
    raw["feedstocks"]["sludge"]["morphology"]["sphericity"] = 1.2
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(raw))
    report = validate_case(load_case(path))
    paths = {item.path for item in report.errors}
    assert "$.feedstocks.sludge.components[0].fraction" in paths
    assert "$.feedstocks.sludge.particle_size_distribution" in paths
    assert "$.feedstocks.sludge.morphology.sphericity" in paths


def test_validator_rejects_declared_double_count(tmp_path: Path) -> None:
    raw = json.loads(CASE_PATH.read_text())
    raw["feedstocks"]["sludge"]["declared_double_counts"] = ["organic_pseudo_A"]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(raw))
    report = validate_case(load_case(path))
    assert any(item.code == "element_double_count" for item in report.errors)
    assert report.element_double_count_checks["sludge"] == "failed"


def test_load_rejects_missing_basis(tmp_path: Path) -> None:
    raw = json.loads(CASE_PATH.read_text())
    del raw["basis"]
    path = tmp_path / "missing_basis.json"
    path.write_text(json.dumps(raw))
    report = validate_case(load_case(path))
    assert any(item.path == "$.basis" for item in report.errors)
