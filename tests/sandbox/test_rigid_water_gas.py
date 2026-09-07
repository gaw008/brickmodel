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


def test_final_numerical_bracket_is_actual_small_interval_with_eos_endpoint_residuals(water):
    from scipy.optimize import brentq
    t,nl,ng,volume=300.,1.,.01,1e-4
    m=model(water,volume,policy=policy(pressure_tolerance_pa=.001))
    result=m.evaluate_at_temperature(t,nl,{'N2':ng,'H2O':0})
    low,high=result.final_numerical_pressure_bracket_pa
    assert result.pressure_bracket_pa==(1e4,1e6)
    assert low<=result.pressure_pa<=high
    assert high-low<=m.policy.pressure_tolerance_pa
    assert result.pressure_pa==low+(high-low)/2
    def residual(p):
        rho=water.state_tp(t,p,phase='liquid').density_kg_m3
        return math.fsum((nl*water.reference.molar_mass_kg_mol/rho,ng*R*t/p,-volume))
    endpoints=(residual(low),residual(high))
    assert result.final_bracket_volume_residuals_m3==pytest.approx(endpoints,rel=0,abs=1e-18)
    assert endpoints[0]>=0 and endpoints[1]<=0
    reference=brentq(residual,1e4,1e6,xtol=1e-8)
    assert low<=reference<=high
    assert result.pressure_solution_path=='liquid_bisection'
    assert result.pressure_bracket_qualification=='numerical_forward_function_only_excludes_eos_error'


def test_zero_liquid_final_bracket_is_analytic_rounded_single_point(water,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('zero liquid must not query water EOS')
    monkeypatch.setattr(type(water),'state_tp',forbidden)
    result=model(water).evaluate_at_temperature(1000,0,{'N2':.01,'H2O':.005})
    assert result.final_numerical_pressure_bracket_pa==(result.pressure_pa,result.pressure_pa)
    assert result.final_bracket_volume_residuals_m3==(result.volume_residual_m3,)*2
    assert result.pressure_solution_path=='pure_gas_analytic_rounded'
    assert result.pressure_bracket_qualification=='numerical_forward_function_only_excludes_eos_error'


def test_failed_bracket_refinement_has_no_success_state(water):
    with pytest.raises(RigidClosureNumericalError,match='pressure_iteration_limit'):
        model(water,1e-4,policy=policy(maximum_iterations=1)).evaluate_at_temperature(
            300,1,{'N2':.01,'H2O':0})


@pytest.mark.parametrize('bracket',[(1e5,1e6),(1e4,1e5)])
def test_exact_numeric_endpoint_returns_explicit_degenerate_bracket(water,bracket):
    pressure=1e5;temperature=300.
    state=water.state_tp(temperature,pressure,phase='liquid')
    liquid_volume=state.molar_mass_kg_mol/state.density_kg_m3
    ng=liquid_volume*pressure/(R*temperature)
    gas_volume=ng*R*temperature/pressure
    volume=liquid_volume+gas_volume
    assert math.fsum((liquid_volume,gas_volume,-volume))==0
    result=model(water,volume,bracket=bracket).evaluate_at_temperature(
        temperature,1,{'N2':ng,'H2O':0})
    assert result.pressure_pa==pressure
    assert result.iterations==0
    assert result.pressure_bracket_pa==bracket
    assert result.final_numerical_pressure_bracket_pa==(pressure,pressure)
    assert result.final_bracket_volume_residuals_m3==(0.,0.)
    assert result.pressure_solution_path=='liquid_exact_numerical_endpoint'
    assert result.pressure_bracket_qualification=='numerical_forward_function_only_excludes_eos_error'


def test_legacy_state_constructor_keeps_new_diagnostics_explicitly_unavailable(water):
    from dataclasses import fields
    from sludge_sandbox.rigid_water_gas import RigidWaterGasState
    result=model(water).evaluate_at_temperature(1000,0,{'N2':.01,'H2O':0})
    new={'final_numerical_pressure_bracket_pa','final_bracket_volume_residuals_m3',
         'pressure_solution_path','pressure_bracket_qualification'}
    old=RigidWaterGasState(**{f.name:getattr(result,f.name) for f in fields(result) if f.name not in new})
    assert old.pressure_pa==result.pressure_pa
    assert old.final_numerical_pressure_bracket_pa is None
    assert old.final_bracket_volume_residuals_m3 is None
    assert old.pressure_solution_path=='not_recorded'
    assert old.pressure_bracket_qualification=='not_recorded_legacy_constructor'
