from pathlib import Path
import math
from dataclasses import FrozenInstanceError

import pytest
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential,WaterChemicalError

pytest.importorskip('iapws')
DATA=Path(__file__).resolve().parents[2]/'data/sandbox/water'

@pytest.fixture
def model():return WaterChemicalPotential(DATA)

@pytest.mark.parametrize('t',[298.15,350.,450.])
def test_standard_entropy_native_formula_and_caloric_derivative(model,t):
    w=model.water;delta=1e5/(w.reference.native_specific_gas_constant_j_kg_k*t*322)
    tau=647.096/t;phi=w._model._phi0(tau,delta)
    expected=w.reference.native_molar_gas_constant_j_mol_k*(tau*phi['fiot']-phi['fio'])
    state=model.ideal_vapor(t,1e5)
    assert state.entropy_j_mol_k==pytest.approx(expected,rel=0,abs=1e-10)
    dt=.01
    ds=(model.ideal_vapor(t+dt,1e5).entropy_j_mol_k-model.ideal_vapor(t-dt,1e5).entropy_j_mol_k)/(2*dt)
    assert ds==pytest.approx(model.vapor.cp_j_mol_k(t)/t,rel=0,abs=1e-7)
    assert state.enthalpy_j_mol==model.vapor.enthalpy_j_mol(t)

@pytest.mark.parametrize('t,p',[(298.15,1000.),(350.,1e4),(450.,1e5)])
def test_gas_chemical_pressure_derivative(model,t,p):
    dp=p*1e-4
    derivative=(model.ideal_vapor(t,p+dp).chemical_potential_j_mol-model.ideal_vapor(t,p-dp).chemical_potential_j_mol)/(2*dp)
    assert derivative==pytest.approx(model.vapor.gas_constant_j_mol_k*t/p,rel=2e-7,abs=1e-9)

@pytest.mark.parametrize('t,p',[(298.15,1e5),(350.,1e6),(450.,1e7)])
def test_liquid_chemical_pressure_derivative(model,t,p):
    dp=max(100.,p*1e-4)
    derivative=(model.liquid_tp(t,p+dp).chemical_potential_j_mol-model.liquid_tp(t,p-dp).chemical_potential_j_mol)/(2*dp)
    state=model.water.state_tp(t,p,phase='liquid')
    assert derivative==pytest.approx(state.molar_mass_kg_mol/state.density_kg_m3,rel=1e-4,abs=1e-8)
    result=model.equilibrium_at_liquid_tp(t,p)
    assert abs(result.chemical_potential_residual_j_mol)<=1e-7
    assert result.phase_enthalpy_difference_j_mol==result.vapor.enthalpy_j_mol-result.liquid.enthalpy_j_mol

@pytest.mark.parametrize('t',[298.15,350.,450.])
def test_saturation_liquid_equilibrium_is_derived_not_native_psat(model,t):
    out=model.equilibrium_at_saturation(t)
    liq=model.saturated_liquid(t)
    standard=model.ideal_vapor(t,1e5)
    expected=1e5*math.exp((liq.chemical_potential_j_mol-standard.chemical_potential_j_mol)/(model.vapor.gas_constant_j_mol_k*t))
    assert out.equilibrium_partial_pressure_pa==pytest.approx(expected,rel=1e-12,abs=0)
    assert abs(out.chemical_potential_residual_j_mol)<=1e-7
    assert out.equilibrium_partial_pressure_pa!=model.water.saturation_pair(t).pressure_pa
    assert 'not_sludge' in out.qualification

@pytest.mark.parametrize('p',[0.,-1.,math.inf,math.nan,True])
def test_invalid_gas_partial_pressure(model,p):
    with pytest.raises(WaterChemicalError):model.ideal_vapor(300,p)


def test_immutable_and_reference_sources(model):
    out=model.equilibrium_at_liquid_tp(300,1e5)
    with pytest.raises(FrozenInstanceError):out.equilibrium_partial_pressure_pa=0
    assert 'nist-codata-2022' in out.source_ids
    for result in (model,out,out.liquid,out.vapor):
        assert result.method_id==model.method_id
        assert result.classification=='derived_from_evidence'
    assert out.liquid.entropy_reference==out.vapor.entropy_reference
    assert out.vapor.reference_pressure_pa==1e5
    assert not hasattr(out,'sludge_water_activity')

@pytest.mark.parametrize('t,p',[(300.,1000.),(350.,1e4),(450.,1e5)])
def test_gas_mu_temperature_derivative_is_negative_entropy(model,t,p):
    dt=.01
    derivative=(model.ideal_vapor(t+dt,p).chemical_potential_j_mol-model.ideal_vapor(t-dt,p).chemical_potential_j_mol)/(2*dt)
    assert derivative==pytest.approx(-model.ideal_vapor(t,p).entropy_j_mol_k,rel=0,abs=1e-6)

@pytest.mark.parametrize('t,s0,peq',[
    (300.,125.73719510996519,3530.8482218640897),
    (350.,130.93580655498917,41329.66820114837),
    (400.,135.48372149678266,239279.93100786887),
    (450.,139.54504406348235,875680.8989204273),
    (500.,143.22900616155832,2342446.518059965),
])
def test_independent_reviewer_native_phi0_reference(model,t,s0,peq):
    assert model.ideal_vapor(t,1e5).entropy_j_mol_k==pytest.approx(s0,rel=0,abs=1e-9)
    assert model.equilibrium_at_saturation(t).equilibrium_partial_pressure_pa==pytest.approx(peq,rel=0,abs=1e-5)


def test_positive_subnormal_pressure_has_finite_mu_without_clipping(model):
    result=model.ideal_vapor(300,math.ulp(0.))
    assert result.partial_pressure_pa==math.ulp(0.)
    assert math.isfinite(result.chemical_potential_j_mol)
    assert result.chemical_potential_j_mol<model.ideal_vapor(300,1e-200).chemical_potential_j_mol

@pytest.mark.parametrize('t',[292.,501.,math.nan,math.inf,True])
def test_original_temperature_domain_is_preserved(model,t):
    from sludge_sandbox.water_properties import WaterDomainError
    with pytest.raises(WaterDomainError):model.ideal_vapor(t,1e5)
    with pytest.raises(WaterDomainError):model.equilibrium_at_saturation(t)

@pytest.mark.parametrize('field,value',[('fio',math.nan),('fiot',math.inf)])
def test_nonfinite_entropy_derivative_rejected(model,monkeypatch,field,value):
    original=model.water._model._phi0
    monkeypatch.setattr(model.water._model,'_phi0',lambda *a:original(*a)|{field:value})
    with pytest.raises(WaterChemicalError):model.ideal_vapor(300,1e5)


def test_common_energy_offset_cancels_from_mu_difference(model):
    t=350.;gas=model.ideal_vapor(t,1e4);liquid=model.liquid_tp(t,1e5)
    native_g=model.vapor._water.ideal_vapor(t)
    native_delta=(liquid.state.native_enthalpy_j_kg*model.reference.molar_mass_kg_mol-t*liquid.entropy_j_mol_k
                  -native_g.native_enthalpy_j_kg*model.reference.molar_mass_kg_mol+t*gas.entropy_j_mol_k)
    assert liquid.chemical_potential_j_mol-gas.chemical_potential_j_mol==pytest.approx(native_delta,rel=0,abs=1e-7)


def test_reference_pressure_not_configurable(model):
    with pytest.raises(TypeError):WaterChemicalPotential(DATA,reference_pressure_pa=2e5)
    with pytest.raises(FrozenInstanceError):model.reference_pressure_pa=2e5
