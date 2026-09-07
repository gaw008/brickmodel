"""Planar pure-water/ideal-gas volume closure, not a sludge capillary model."""
from pathlib import Path
import math

import pytest

from sludge_sandbox.rigid_water_gas import RigidWaterGas, PressurePolicy, RigidClosureDomainError, RigidClosureNumericalError
from sludge_sandbox.water_properties import load_water_properties

pytest.importorskip('iapws')
DATA=Path(__file__).resolve().parents[2]/'data/sandbox/water'
R=8.31446261815324
ASSUMPTION='planar_interface_no_capillary_pressure'

@pytest.fixture
def water():return load_water_properties(DATA)


def policy(**kwargs):return PressurePolicy(**({'volume_tolerance_m3':1e-13,'pressure_tolerance_pa':1e-5,'maximum_iterations':150}|kwargs))


def model(water,volume=1e-3,bracket=(1e4,1e6),**kwargs):
    return RigidWaterGas(water,('N2','H2O'),volume,bracket,ASSUMPTION,kwargs.get('policy',policy()))


def test_gas_only_analytic_and_zero_water_high_temperature(water):
    m=model(water)
    result=m.evaluate_at_temperature(1000,0,{'N2':.01,'H2O':.005})
    assert result.pressure_pa==pytest.approx(.015*R*1000/1e-3,rel=0,abs=1e-9)
    assert result.gas_volume_m3==1e-3
    assert result.liquid_volume_m3==0
    assert result.partial_pressures_pa['H2O']==pytest.approx(result.pressure_pa/3,rel=0,abs=1e-9)
    assert result.gas_inventory_mol=={'N2':.01,'H2O':.005}
    with pytest.raises(TypeError):result.gas_inventory_mol['N2']=0


def test_real_water_closure_matches_known_state_and_independent_brentq(water):
    from scipy.optimize import brentq
    t=300.;p=123456.;nl=20.;ng=.01
    rho=water.state_tp(t,p,phase='liquid').density_kg_m3
    volume=nl*water.reference.molar_mass_kg_mol/rho+ng*R*t/p
    m=model(water,volume,bracket=(1e4,1e6))
    result=m.evaluate_at_temperature(t,nl,{'N2':ng,'H2O':0.})
    reference=brentq(lambda pressure:nl*water.reference.molar_mass_kg_mol/water.state_tp(t,pressure,phase='liquid').density_kg_m3+ng*R*t/pressure-volume,1e4,1e6,xtol=1e-7)
    assert result.pressure_pa==pytest.approx(reference,rel=0,abs=1e-5)
    assert result.pressure_pa==pytest.approx(p,rel=0,abs=1e-5)
    assert abs(result.volume_residual_m3)<=m.policy.volume_tolerance_m3
    assert abs(result.pressure_residual_pa)<=m.policy.pressure_tolerance_pa
    assert result.liquid_pressure_pa==result.pressure_pa
    assert result.partial_pressures_pa['H2O']==0
    assert result.liquid_inventory_mol==nl


def test_liquid_compression_feedback_is_not_saturation_density(water):
    t=300.;p=8e7;nl=20.;ng=.01
    liq=water.state_tp(t,p,phase='liquid')
    volume=nl*liq.molar_mass_kg_mol/liq.density_kg_m3+ng*R*t/p
    out=model(water,volume,bracket=(1e7,1e8),policy=policy(pressure_tolerance_pa=.1)).evaluate_at_temperature(t,nl,{'N2':ng,'H2O':0})
    assert out.pressure_pa==pytest.approx(p,rel=0,abs=.1)
    saturation_volume=nl*liq.molar_mass_kg_mol/water.saturation_pair(t).liquid.density_kg_m3
    assert out.liquid_volume_m3<saturation_volume
    assert saturation_volume>volume  # Low-pressure overfill does not rule out compression closure.


def test_no_gas_or_negative_inventory_or_missing_carrier_rejected(water):
    m=model(water)
    for inventory in ({'N2':0,'H2O':0},{'N2':-1,'H2O':1},{'H2O':.01},{'N2':.01,'H2O':0,'CO2':0}):
        with pytest.raises(RigidClosureDomainError):m.evaluate_at_temperature(300,1,inventory)


def test_no_stable_liquid_root_and_insufficient_volume(water):
    with pytest.raises(RigidClosureDomainError):model(water).evaluate_at_temperature(500,1,{'N2':.01,'H2O':0})
    with pytest.raises(RigidClosureDomainError,match='bracket|volume'):
        model(water,1e-8).evaluate_at_temperature(300,20,{'N2':.01,'H2O':0})


@pytest.mark.parametrize('bad',[True,-1,math.nan,math.inf])
def test_invalid_liquid_inventory(water,bad):
    with pytest.raises(RigidClosureDomainError):model(water).evaluate_at_temperature(300,bad,{'N2':.01,'H2O':0})


def test_unresolvable_float_pressure_precision_fails(water):
    m=model(water,policy=policy(pressure_tolerance_pa=1e-30))
    with pytest.raises(RigidClosureNumericalError,match='precision'):
        m.evaluate_at_temperature(300,1,{'N2':.01,'H2O':0})


def test_extreme_finite_gas_inventory_overflow_is_structured(water):
    with pytest.raises(RigidClosureNumericalError):model(water).evaluate_at_temperature(300,0,{'N2':1e308,'H2O':1e308})


@pytest.mark.parametrize('t,nl,ng,volume,expected,bracket',[
    (300.,1.,.01,1e-4,304469.3135400322,(1e4,1e6)),
    (450.,1.,.1,1e-4,4687356.680552809,(1e6,1e7)),
    (300.,10.,.1,2e-4,12345746.54129325,(1e6,2e7)),
])
def test_independent_review_pressure_reference(water,t,nl,ng,volume,expected,bracket):
    result=model(water,volume,bracket=bracket,policy=policy(pressure_tolerance_pa=.001)).evaluate_at_temperature(t,nl,{'N2':ng,'H2O':0})
    assert result.pressure_pa==pytest.approx(expected,rel=0,abs=.001)


def test_missing_physical_assumption_is_not_defaulted(water):
    with pytest.raises(RigidClosureDomainError):RigidWaterGas(water,('N2',),1e-3,(1e4,1e6),'sludge_capillary_unknown',policy())


def test_iteration_limit_is_numerical_failure_not_no_physical_root(water):
    with pytest.raises(RigidClosureNumericalError,match='iteration'):
        model(water,policy=policy(maximum_iterations=1)).evaluate_at_temperature(300,1,{'N2':.01,'H2O':0})


def test_representable_trace_partial_pressure_is_not_lost_in_intermediate_ratio(water):
    volume=1e50*R*300/1e100
    m=model(water,volume,bracket=(1e99,1e101),policy=policy(volume_tolerance_m3=1e-50,pressure_tolerance_pa=1e90))
    result=m.evaluate_at_temperature(300,0,{'N2':1e50,'H2O':1e-300})
    assert result.partial_pressures_pa['H2O']==pytest.approx(1e-250,rel=1e-14,abs=0)
