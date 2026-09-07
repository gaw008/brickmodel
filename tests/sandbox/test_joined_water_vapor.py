"""Joined source curves retain model differences and conditional numerical scope."""
from pathlib import Path
from decimal import Decimal,localcontext
from dataclasses import FrozenInstanceError
import math
import pytest
from sludge_sandbox.joined_water_vapor import JoinedWaterVapor,JoinedWaterVaporError

ROOT=Path(__file__).resolve().parents[2]
@pytest.fixture(scope='module')
def model():return JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
    low_enthalpy_error_j_mol=1e-8,numerical_error_source_ids=('manufactured:declared-low-domain-bound',))

@pytest.mark.parametrize('t',[293.,298.15,350.,500.])
def test_low_is_original_model(model,t):
    for name in ('enthalpy_j_mol','internal_energy_j_mol','cp_j_mol_k','cv_j_mol_k'):
        assert getattr(model,name)(t)==getattr(model.low_model,name)(t)

@pytest.mark.parametrize('t',[501.,1000.,1700.,3000.,6000.])
def test_independent_decimal_integral(model,t):
    with localcontext() as ctx:
        ctx.prec=60
        result=Decimal.from_float(model.low_model.enthalpy_j_mol(500.))
        for segment in model.source_gas.segments:
            lo,hi=segment.temperature_range_k
            if t<=lo:break
            a,b,c,d,e,*_=map(Decimal.from_float,segment.coefficients)
            x=Decimal.from_float(lo)/1000;y=Decimal.from_float(min(t,hi))/1000
            result+=1000*(a*(y-x)+b*(y*y-x*x)/2+c*(y**3-x**3)/3+d*(y**4-x**4)/4+e*(1/x-1/y))
        assert model.enthalpy_j_mol(t)==pytest.approx(float(result),rel=0,abs=1e-8)
        expected_u=result-Decimal.from_float(model.gas_constant_j_mol_k)*Decimal.from_float(t)
        assert model.internal_energy_j_mol(t)==pytest.approx(float(expected_u),rel=0,abs=1e-8)

@pytest.mark.parametrize('t',[500.,1700.])
def test_seams_keep_h_continuity_and_cp_jump(model,t):
    assert model.enthalpy_j_mol(math.nextafter(t,-math.inf))<=model.enthalpy_j_mol(t)
    assert model.enthalpy_j_mol(t)<=model.enthalpy_j_mol(math.nextafter(t,math.inf))
    high=next(s for s in model.segments if s.temperature_range_k[0]==t)
    assert high.enthalpy_j_mol(t)==pytest.approx(model.enthalpy_j_mol(t),rel=0,abs=1e-9)
    assert any(j.temperature_k==t for j in model.cp_jumps)

@pytest.mark.parametrize('t',[350.,501.,1000.,2000.,5999.])
def test_identities_derivative_and_proven_bound(model,t):
    h=model.enthalpy_j_mol(t);u=model.internal_energy_j_mol(t);r=model.gas_constant_j_mol_k
    assert abs(h-u-r*t)<=2e-10
    assert model.cv_j_mol_k(t)>=model.cv_lower_bound_j_mol_k>0
    derivative=(model.enthalpy_j_mol(t+.01)-model.enthalpy_j_mol(t-.01))/.02
    assert derivative==pytest.approx(model.cp_j_mol_k(t),rel=0,abs=1e-6)

@pytest.mark.parametrize('t',[292.,6001.,math.nan,math.inf,True])
def test_domain_rejected(model,t):
    with pytest.raises(ValueError):model.enthalpy_j_mol(t)


def test_immutable_error_and_source_contract(model):
    with pytest.raises(FrozenInstanceError):model.low_enthalpy_error_j_mol=1
    high=model.numerical_error(2000.)
    assert high.anchor_enthalpy_error_j_mol==1e-8
    assert high.integral_arithmetic_error_j_mol==0
    assert high.enthalpy_error_j_mol>=1e-8
    assert high.internal_energy_error_j_mol>=1e-8
    assert 'conditional' in high.qualification
    assert model.low_model.source_asset_sha256!=model.source_asset_sha256
    assert not hasattr(model,'entropy_j_mol_k')


def test_equivalent_loads_have_semantic_identity_and_hash(model):
    other=JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
        low_enthalpy_error_j_mol=1e-8,numerical_error_source_ids=('manufactured:declared-low-domain-bound',))
    assert model.low_model is not other.low_model
    assert model==other and hash(model)==hash(other)
    changed=JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
        low_enthalpy_error_j_mol=1e-7,numerical_error_source_ids=('manufactured:declared-low-domain-bound',))
    assert changed.identity!=model.identity


def test_modified_high_source_rejected_before_loader(tmp_path):
    import shutil
    for name in ('nist_gases_v1.json','sources.json'):
        shutil.copy(ROOT/'data/sandbox/thermochemistry'/name,tmp_path/name)
    path=tmp_path/'nist_gases_v1.json';path.write_text(path.read_text()+' ')
    with pytest.raises(JoinedWaterVaporError,match='source_hash_mismatch'):
        JoinedWaterVapor(ROOT/'data/sandbox/water',tmp_path,low_enthalpy_error_j_mol=1e-8,
            numerical_error_source_ids=('manufactured:bound',))

@pytest.mark.parametrize('error',[-1.,math.nan,math.inf,True])
def test_invalid_declared_error_rejected(error):
    with pytest.raises(JoinedWaterVaporError):
        JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
            low_enthalpy_error_j_mol=error,numerical_error_source_ids=('manufactured:bound',))


def test_original_cp_and_each_offset_retained(model):
    for branch,offset in zip(model.segments,model.segment_offsets):
        t=sum(branch.temperature_range_k)/2
        assert model.cp_j_mol_k(t)==branch.source_segment.cp_j_mol_k(t)
        assert model.enthalpy_j_mol(t)-branch.source_segment.enthalpy_j_mol(t)==pytest.approx(
            offset.enthalpy_offset_j_mol,rel=0,abs=1e-9)
    assert abs(model.segment_offsets[0].enthalpy_offset_j_mol)>.1
    assert model.numerical_error(500.).anchor_enthalpy_error_j_mol<1e-6


def test_upward_error_budget_overflow_is_not_success():
    import sys
    huge=JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
        low_enthalpy_error_j_mol=sys.float_info.max,numerical_error_source_ids=('manufactured:overflow-probe',))
    with pytest.raises(JoinedWaterVaporError,match='unrepresentable'):
        huge.numerical_error(600.)


def test_fraction_conversion_overflow_has_joined_error():
    from fractions import Fraction
    from sludge_sandbox.joined_water_vapor import _out
    with pytest.raises(JoinedWaterVaporError,match='unrepresentable'):_out(Fraction(10)**400,upper=True)
