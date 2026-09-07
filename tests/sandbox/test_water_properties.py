"""Pure-water source verification, distinct from any wet-sludge qualification."""

from dataclasses import FrozenInstanceError
import json
import math
from pathlib import Path
import shutil
from types import SimpleNamespace
import warnings

import pytest

from sludge_sandbox.water_properties import (
    WaterCompatibilityError,
    WaterDomainError,
    WaterNumericalError,
    WaterSourceError,
    load_water_properties,
)

iapws = pytest.importorskip("iapws")
DATA = Path(__file__).resolve().parents[2] / "data/sandbox/water"
OFFICIAL = json.loads((DATA / "official_verification.json").read_text())["checks"]


@pytest.fixture
def water():
    return load_water_properties(DATA)


@pytest.mark.parametrize("check", OFFICIAL)
def test_pinned_backend_official_33_check_points(water, check):
    """275/625 K verify the pinned backend only, without widening adapter bounds."""
    if "density_kg_m3" in check:
        raw = iapws.IAPWS95(T=500, rho=838.025)
        props = raw._phi0(raw.Tc / 500, 838.025 / raw.rhoc) | raw._phir(raw.Tc / 500, 838.025 / raw.rhoc)
    else:
        raw = iapws.IAPWS95(T=check["temperature_k"], x=0.5)
        props = dict(pressure_mpa=raw.P, rho_liquid_kg_m3=raw.Liquid.rho,
                     rho_vapor_kg_m3=raw.Gas.rho, h_liquid_kj_kg=raw.Liquid.h,
                     h_vapor_kj_kg=raw.Gas.h, s_liquid_kj_kg_k=raw.Liquid.s,
                     s_vapor_kj_kg_k=raw.Gas.s)
    assert props[check["property"]] == pytest.approx(check["expected_printed"], rel=1e-8, abs=1e-11)


def test_adapter_saturation_matches_official_450k_row_in_si(water):
    pair = water.saturation_pair(450)
    assert pair.pressure_pa == pytest.approx(932203.564, rel=1e-8)
    assert pair.liquid.phase == "liquid"
    assert pair.vapor.phase == "vapor"
    assert pair.liquid.density_kg_m3 == pytest.approx(890.341250, rel=1e-8)
    assert pair.vapor.density_kg_m3 == pytest.approx(4.81200360, rel=1e-8)
    assert pair.liquid.native_enthalpy_j_kg == pytest.approx(749161.585, rel=1e-8)
    assert pair.vapor.native_enthalpy_j_kg == pytest.approx(2774410.78, rel=1e-8)
    assert abs(pair.equilibrium_gibbs_difference_j_kg) <= water.numerical_limits.gibbs_absolute_j_kg


@pytest.mark.parametrize("temperature", [293, 298.15, 373.15, 450, 500])
def test_one_offset_preserves_latent_heat_and_pressure_work(water, temperature):
    pair = water.saturation_pair(temperature)
    for state in (pair.liquid, pair.vapor):
        assert state.reference is water.reference
        assert state.enthalpy_j_mol - state.native_enthalpy_j_kg * state.molar_mass_kg_mol == pytest.approx(water.reference.energy_offset_j_mol, abs=1e-9)
        assert state.internal_energy_j_mol - state.native_internal_energy_j_kg * state.molar_mass_kg_mol == pytest.approx(water.reference.energy_offset_j_mol, abs=1e-9)
        assert state.enthalpy_j_mol - state.internal_energy_j_mol == pytest.approx(state.pressure_pa * state.molar_mass_kg_mol / state.density_kg_m3, abs=1e-9)
        assert state.source_ids == water.reference.source_ids
        assert state.material_qualification == "pure_water_only"
    assert pair.latent_enthalpy_j_mol == pytest.approx(
        (pair.vapor.native_enthalpy_j_kg - pair.liquid.native_enthalpy_j_kg) * water.reference.molar_mass_kg_mol, abs=1e-9)


def test_reference_anchor_and_native_constants_are_explicit_and_frozen(water):
    ideal = water.ideal_vapor(298.15)
    assert ideal.enthalpy_j_mol == pytest.approx(-241826.4, abs=1e-9)
    assert water.reference.energy_offset_j_mol == pytest.approx(-287728.9703011956, abs=1e-7)
    assert water.reference.native_specific_gas_constant_j_kg_k == pytest.approx(461.51805, abs=1e-9)
    assert water.reference.native_molar_gas_constant_j_mol_k == pytest.approx(8.314371357587, abs=1e-12)
    assert water.reference.molar_mass_kg_mol == pytest.approx(0.018015268, abs=1e-17)
    with pytest.raises(FrozenInstanceError):
        ideal.temperature_k = 299
    with pytest.raises(FrozenInstanceError):
        water.reference.energy_offset_j_mol = 0
    with pytest.raises(TypeError):
        water.source_asset_sha256["IAPWS95-2018.pdf"] = "fake"


def test_current_universal_gas_constant_cannot_be_silently_mixed(water):
    existing = 8.31446261815324
    assert water.reference.relative_gas_constant_difference(existing) == pytest.approx(-1.0976123224204493e-5)
    with pytest.raises(WaterCompatibilityError, match="gas_constant"):
        water.reference.require_same_gas_constant(existing)
    water.reference.require_same_gas_constant(water.reference.native_molar_gas_constant_j_mol_k)


def test_wrong_phase_at_500k_one_bar_is_a_domain_error(water):
    with pytest.raises(WaterDomainError, match="unstable_requested_phase"):
        water.state_tp(500, 100000, phase="liquid")
    vapor = water.state_tp(500, 100000, phase="vapor")
    assert vapor.density_kg_m3 < 1
    assert vapor.phase == "vapor"
    with pytest.raises(WaterDomainError, match="unstable_requested_phase"):
        water.state_tp(293, 100000, phase="vapor")


def test_liquid_tp_uses_pressure_not_saturated_density(water):
    liquid = water.state_tp(298.15, 100000, phase="liquid")
    assert liquid.native_enthalpy_j_kg == pytest.approx(104918.89282781036, abs=1e-5)
    assert liquid.enthalpy_j_mol == pytest.approx(-285838.82832863927, abs=1e-6)
    assert liquid.density_kg_m3 > water.saturation_pair(298.15).liquid.density_kg_m3


def test_tp_saturation_is_explicitly_ambiguous(water):
    pressure = water.saturation_pair(300).pressure_pa
    for phase in ("liquid", "vapor"):
        with pytest.raises(WaterDomainError, match="use_saturation_pair"):
            water.state_tp(300, pressure, phase=phase)


def test_ideal_internal_energy_is_derived_and_never_uses_upstream_u0(water, monkeypatch):
    # Raising on writes as well as reads proves no full upstream state constructor
    # is needed for this independent ideal-Helmholtz calculation.
    def forbidden(_):
        raise AssertionError("quarantined upstream ideal API")
    monkeypatch.setattr(iapws.IAPWS95, "u0", property(forbidden), raising=False)
    monkeypatch.setattr(iapws.IAPWS95, "a0", property(forbidden), raising=False)
    ideal = water.ideal_vapor(300)
    assert ideal.method_id == "derived_iapws95_ideal_helmholtz"
    assert ideal.native_internal_energy_j_kg == pytest.approx(2412975.6545980154, abs=1e-6)
    assert ideal.enthalpy_j_mol - ideal.internal_energy_j_mol == pytest.approx(
        water.reference.native_molar_gas_constant_j_mol_k * 300, abs=1e-9)
    assert not hasattr(ideal, "u0")
    assert not hasattr(ideal, "a0")


@pytest.mark.parametrize("temperature", [275, 292.99, 500.01, 625, 0, -1, float("nan"), float("inf"), True, "300", 10**1000])
def test_public_temperature_domain_never_extrapolates(water, temperature):
    for method in (water.saturation_pair, water.ideal_vapor):
        with pytest.raises(WaterDomainError):
            method(temperature)


@pytest.mark.parametrize("pressure", [0, -1, 100000001, float("nan"), float("inf"), True, "100000"])
def test_invalid_or_undeclared_pressure_domain(water, pressure):
    with pytest.raises(WaterDomainError):
        water.state_tp(300, pressure, phase="liquid")


def test_bad_phase_name_is_rejected(water):
    with pytest.raises(WaterDomainError):
        water.state_tp(300, 100000, phase="mud_water")


def test_source_hash_change_is_rejected(tmp_path):
    copied = tmp_path / "water"
    shutil.copytree(DATA, copied)
    (copied / "source_facts.json").write_text("{}")
    with pytest.raises(WaterSourceError, match="source_hash"):
        load_water_properties(copied)


def test_missing_source_and_wrong_runtime_version_are_rejected(tmp_path, monkeypatch):
    with pytest.raises(WaterSourceError):
        load_water_properties(tmp_path)
    monkeypatch.setattr(iapws, "__version__", "1.5.6")
    with pytest.raises(WaterSourceError, match="version"):
        load_water_properties(DATA)


def test_solver_nonconvergence_is_distinct_from_physical_domain(water, monkeypatch):
    monkeypatch.setattr(water._backend, "IAPWS95", lambda **_: SimpleNamespace(status=0, msg="failed to converge"))
    with pytest.raises(WaterNumericalError, match="status"):
        water.saturation_pair(300)


def test_solver_warning_is_not_silently_accepted(water, monkeypatch):
    original = water._backend.IAPWS95
    def warned(**kwargs):
        warnings.warn("solver stalled", RuntimeWarning)
        return original(**kwargs)
    monkeypatch.setattr(water._backend, "IAPWS95", warned)
    with pytest.raises(WaterNumericalError, match="warning"):
        water.saturation_pair(300)


@pytest.mark.parametrize("field,delta", [("h", 1), ("u", 1), ("s", 1), ("rho", 1)])
def test_corrupted_backend_state_fails_conservation_or_equilibrium(water, monkeypatch, field, delta):
    original = water._backend.IAPWS95
    def corrupted(**kwargs):
        result = original(**kwargs)
        setattr(result.Liquid, field, getattr(result.Liquid, field) + delta)
        return result
    monkeypatch.setattr(water._backend, "IAPWS95", corrupted)
    with pytest.raises(WaterNumericalError):
        water.saturation_pair(300)


def test_nonfinite_backend_result_is_not_a_valid_state(water, monkeypatch):
    original = water._backend.IAPWS95
    def corrupted(**kwargs):
        result = original(**kwargs)
        result.Gas.rho = math.nan
        return result
    monkeypatch.setattr(water._backend, "IAPWS95", corrupted)
    with pytest.raises(WaterNumericalError):
        water.saturation_pair(300)


@pytest.mark.parametrize('field', ['h', 's'])
def test_nonfinite_independent_eos_value_cannot_bypass_comparison(water, monkeypatch, field):
    original = water._model._Helmholtz
    def corrupt(*args, **kwargs):
        return original(*args, **kwargs) | {field: math.nan}
    monkeypatch.setattr(water._model, '_Helmholtz', corrupt)
    with pytest.raises(WaterNumericalError):
        water.saturation_pair(300)


@pytest.mark.parametrize('cp,cv', [(1e308, 1e308), (1, 2), (20, 10)])
def test_phase_heat_capacities_must_be_finite_and_match_helmholtz(water, monkeypatch, cp, cv):
    original = water._backend.IAPWS95
    def corrupted(**kwargs):
        result = original(**kwargs)
        result.Liquid.cp, result.Liquid.cv = cp, cv
        return result
    monkeypatch.setattr(water._backend, 'IAPWS95', corrupted)
    with pytest.raises(WaterNumericalError):
        water.saturation_pair(300)
