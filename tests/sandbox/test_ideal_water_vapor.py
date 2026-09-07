"""A derived ideal caloric bridge; not mixture/material qualification."""
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
import math

import pytest

from sludge_sandbox.ideal_water_vapor import IdealWaterVapor, IdealWaterVaporError
from sludge_sandbox.water_properties import WaterDomainError, WaterSourceError

pytest.importorskip('iapws')
DATA = Path(__file__).resolve().parents[2] / 'data/sandbox/water'
R = 8.31446261815324

@pytest.fixture
def vapor():
    return IdealWaterVapor(DATA)

@pytest.mark.parametrize('temperature', [293., 298.15, 373.15, 500.])
def test_native_enthalpy_is_preserved_without_second_offset(vapor, temperature):
    native = vapor._water.ideal_vapor(temperature)
    assert vapor.enthalpy_j_mol(temperature) == native.enthalpy_j_mol
    assert vapor.internal_energy_j_mol(temperature) == native.enthalpy_j_mol - R*temperature
    assert vapor.cp_j_mol_k(temperature) == native.cp_j_kg_k*native.molar_mass_kg_mol
    assert vapor.cv_j_mol_k(temperature) == vapor.cp_j_mol_k(temperature)-R
    delta = R-vapor.reference.native_molar_gas_constant_j_mol_k
    assert vapor.internal_energy_difference_j_mol(temperature) == -delta*temperature
    assert vapor.internal_energy_j_mol(temperature)-native.internal_energy_j_mol == pytest.approx(-delta*temperature, abs=5e-11)
    assert vapor.cv_difference_j_mol_k == -delta


def test_anchor_identity_sources_and_no_unearned_equilibrium(vapor):
    assert vapor.enthalpy_j_mol(298.15) == pytest.approx(-241826.4, abs=1e-9)
    assert vapor.gas_constant_j_mol_k == R
    assert vapor.species_id == 'H2O'
    assert vapor.temperature_range_k == (293.,500.)
    assert vapor.method_id == 'derived_iapws95_ideal_water_fixed_r_bridge_v1'
    assert vapor.source_ids == vapor.reference.source_ids + ('nist-codata-2022',)
    assert vapor.mixture_qualification == 'not_established'
    assert vapor.classification == 'derived_from_evidence'
    assert not hasattr(vapor, 'entropy_j_mol_k')
    assert not hasattr(vapor, 'saturation_pressure_pa')
    assert len(vapor.source_asset_sha256) == 5
    with pytest.raises(FrozenInstanceError):vapor.gas_constant_j_mol_k = 1
    with pytest.raises(TypeError):vapor.source_asset_sha256['x'] = 'fake'

@pytest.mark.parametrize('temperature',[294.,350.,450.,499.])
def test_caloric_derivatives(vapor,temperature):
    step=.01
    dh=(vapor.enthalpy_j_mol(temperature+step)-vapor.enthalpy_j_mol(temperature-step))/(2*step)
    du=(vapor.internal_energy_j_mol(temperature+step)-vapor.internal_energy_j_mol(temperature-step))/(2*step)
    assert dh == pytest.approx(vapor.cp_j_mol_k(temperature),abs=2e-7)
    assert du == pytest.approx(vapor.cv_j_mol_k(temperature),abs=2e-7)

@pytest.mark.parametrize('temperature',[292.,501.,math.nan,math.inf,True,'300'])
def test_domain(vapor,temperature):
    with pytest.raises(WaterDomainError):vapor.enthalpy_j_mol(temperature)

@pytest.mark.parametrize('bad',[None,object(),SimpleNamespace()])
def test_cannot_inject_unverified_provider(bad):
    with pytest.raises(IdealWaterVaporError):IdealWaterVapor(bad)


def test_missing_sources_are_not_defaulted(tmp_path):
    with pytest.raises(WaterSourceError):IdealWaterVapor(tmp_path)

@pytest.mark.parametrize('constant',[0.,1.,1e300,math.nan,math.inf])
def test_no_arbitrary_gas_constant_input(constant):
    with pytest.raises(TypeError):IdealWaterVapor(DATA,gas_constant_j_mol_k=constant)

@pytest.mark.parametrize('field,value', [('cp_j_kg_k',math.inf),('cp_j_kg_k',1.),('native_enthalpy_j_kg',math.nan)])
def test_invalid_backend_values_are_rejected(vapor,monkeypatch,field,value):
    from dataclasses import replace
    original=type(vapor._water).ideal_vapor
    def corrupt(self,temperature):return replace(original(self,temperature),**{field:value})
    monkeypatch.setattr(type(vapor._water),'ideal_vapor',corrupt)
    with pytest.raises(IdealWaterVaporError):vapor.internal_energy_j_mol(300)


def test_changed_reference_is_rejected(vapor,monkeypatch):
    from dataclasses import replace
    original=type(vapor._water).ideal_vapor
    def corrupt(self,temperature):
        state=original(self,temperature)
        return replace(state,reference=replace(state.reference,energy_offset_j_mol=0))
    monkeypatch.setattr(type(vapor._water),'ideal_vapor',corrupt)
    with pytest.raises(IdealWaterVaporError,match='reference'):vapor.enthalpy_j_mol(300)
