"""Conditional numerical pressure propagation, not material validation."""
from dataclasses import replace
from fractions import Fraction as F
from types import MappingProxyType

import pytest

from test_source_endpoint_comparison import actual_trials
from test_depletion_integration import policies
from sludge_sandbox.source_endpoint_comparison import compare_source_trial_endpoints
from sludge_sandbox.source_inverse_pressure import (
    propagate_declared_pressure, enclose_source_inverse_pressure, propagate_source_trial_pressure,
)
from sludge_sandbox.source_wet_storage import SourceWetStorage
from sludge_sandbox.exact_source_column import ExactSourceColumn


def pure(**changes):
    values=dict(nl=F(1,4),ng=F(1,2),gas_constant=F(8),abs_uP_bound=F(1,10000),
                temperature=F(330),temperature_error=F(1,1000000),
                pressure=F(1000000),pressure_error=F(1,1000),
                temperature_domain_k=(F(310),F(350)),pressure_domain_pa=(F(100000),F(10000000)))
    values.update(changes)
    return propagate_declared_pressure(**values)


def test_exact_global_then_bootstrap_and_no_input_error_dropped():
    result=pure()
    assert result.status=='conditional_pressure_enclosure'
    assert result.global_slope_pa_k > result.slope_pa_k > 0
    assert result.global_radius_pa > result.radius_pa > F(1,1000)
    assert result.global_interval_pa[0] < result.interval_pa[0] < result.interval_pa[1] < result.global_interval_pa[1]
    assert not result.source_certified and result.assumptions
    result.check()


@pytest.mark.parametrize('changes,reason',[
    ({'temperature_error':F(21)},'temperature_interval_outside_declared_domain'),
    ({'pressure_domain_pa':(F(999999),F(1000001)), 'temperature_error':F(1)},'temperature_continuation_pressure_domain_exit'),
    ({'pressure':F(100000), 'pressure_error':F()},'temperature_continuation_pressure_domain_exit'),
])
def test_missing_continuation_margin_preserves_unresolved(changes,reason):
    result=pure(**changes)
    assert result.status=='unresolved' and result.reason==reason
    assert result.radius_pa is None and not result.source_certified
    result.check()


def test_zero_T_error_and_gas_only_are_explicit_algebraic_limits():
    result=pure(nl=F(),temperature_error=F())
    assert result.radius_pa==F(1,1000)
    assert result.global_slope_pa_k==F(10000000,310)
    result.check()


@pytest.mark.parametrize('changes',[
    {'ng':F()},{'nl':F(-1)},{'temperature_error':F(-1)},
    {'abs_uP_bound':F(-1)},{'pressure_error':0.},
    {'temperature_domain_k':(F(350),F(310))},
])
def test_invalid_or_inexact_pure_inputs_rejected(changes):
    with pytest.raises(ValueError):
        pure(**changes)


def source_endpoint(trial):
    evaluation=trial.captures[2].evaluation
    return trial.adapter.column.storages[0],evaluation.source_states[0],evaluation.source_evaluation.cells[0].inverse


def test_actual_source_bridge_and_trial_layer_use_no_new_physics(actual_trials,monkeypatch):
    def forbidden(*args,**kwargs):
        pytest.fail('pressure propagation performed a new physical evaluation')
    monkeypatch.setattr(ExactSourceColumn,'evaluate',forbidden)
    monkeypatch.setattr(SourceWetStorage,'evaluate',forbidden)
    monkeypatch.setattr(SourceWetStorage,'invert',forbidden)
    for trial in actual_trials:
        comparison=compare_source_trial_endpoints(trial,event_policy=policies()[1])
        before=comparison.gates
        result=propagate_source_trial_pressure(comparison)
        assert result.maximum_conditional_bound_pa >= comparison.differences.maxima[3]
        assert result.conditional_gate==(result.maximum_conditional_bound_pa<=F(policies()[1].pressure_absolute_pa))
        assert comparison.gates==before and comparison.full_inverse_pressure_gate=='unresolved'
        assert not result.source_certified and not result.event_admitted
        for pair in result.endpoint_bounds:
            for bound in pair:
                assert bound.continuation.status=='conditional_pressure_enclosure'
        result.check()


def test_missing_policy_keeps_conditional_gate_unknown(actual_trials):
    comparison=compare_source_trial_endpoints(actual_trials[0],event_policy=None)
    result=propagate_source_trial_pressure(comparison)
    assert result.maximum_conditional_bound_pa is not None and result.conditional_gate is None
    result.check()


@pytest.mark.parametrize('field',['pressure_error_pa','global_pressure_error_pa','extra_pressure_error_pa',
                                  'energy_error_j'])
def test_underreported_source_errors_rejected(actual_trials,field):
    storage,state,inverse=source_endpoint(actual_trials[2])
    if field=='extra_pressure_error_pa' and getattr(inverse.point,field)==0:
        # This manufactured fixture has exact zero available-volume error.
        point=replace(inverse.point,available_volume_error_m3=1e-9)
    else:
        point=replace(inverse.point,**{field:0.})
    with pytest.raises(ValueError):
        enclose_source_inverse_pressure(storage,state,replace(inverse,point=point))


def test_low_T_error_with_inflated_capacity_is_rejected(actual_trials):
    storage,state,inverse=source_endpoint(actual_trials[0])
    changed=replace(inverse,temperature_error_bound_k=inverse.temperature_error_bound_k/10,
                    point=replace(inverse.point,minimum_heat_capacity_j_k=inverse.point.minimum_heat_capacity_j_k*100))
    with pytest.raises(ValueError,match='caloric_accounting'):
        enclose_source_inverse_pressure(storage,state,changed)


def test_jointly_lowered_residual_resolution_and_pressure_error_rejected(actual_trials):
    storage,state,inverse=source_endpoint(actual_trials[0])
    mech=replace(inverse.point.fluid.mechanical,volume_residual_m3=0.,volume_resolution_m3=0.)
    point=replace(inverse.point,fluid=replace(inverse.point.fluid,mechanical=mech,pressure_error_bound_pa=0.),
                  pressure_error_pa=0.,global_pressure_error_pa=0.,extra_pressure_error_pa=0.)
    with pytest.raises(ValueError):
        enclose_source_inverse_pressure(storage,state,replace(inverse,point=point))


def test_tampered_result_truncated_pairs_and_qualifications_rejected(actual_trials):
    comparison=compare_source_trial_endpoints(actual_trials[0],event_policy=policies()[1])
    result=propagate_source_trial_pressure(comparison)
    for changed in (replace(result,event_admitted=True), replace(result,source_certified=True),
                    replace(result,endpoint_bounds=((result.endpoint_bounds[0][0],),)),
                    replace(result,maximum_conditional_bound_pa=F())):
        with pytest.raises(ValueError):
            changed.check()
    bound=result.endpoint_bounds[0][0]
    with pytest.raises(ValueError):
        replace(bound,continuation=replace(bound.continuation,radius_pa=F())).check()


def test_source_state_and_provider_binding_rejected(actual_trials):
    storage,state,inverse=source_endpoint(actual_trials[0])
    with pytest.raises(ValueError):
        enclose_source_inverse_pressure(storage,replace(state,liquid_water_mol=state.liquid_water_mol/2),inverse)
    with pytest.raises(ValueError):
        enclose_source_inverse_pressure(replace(storage,dry_mass_kg=storage.dry_mass_kg*2),state,inverse)


@pytest.mark.parametrize('field,value', [
    ('liquid_pressure_pa',None), ('liquid_pressure_pa',1.),
    ('liquid_pressure_pa','fraction'), ('gas_constant_j_mol_k','fraction'),
])
def test_saved_planar_pressure_and_constant_have_exact_runtime_identity(actual_trials,field,value):
    storage,state,inverse=source_endpoint(actual_trials[0])
    mechanical=inverse.point.fluid.mechanical
    if value=='fraction':
        value=F(getattr(mechanical,field))
    point=replace(inverse.point,fluid=replace(inverse.point.fluid,
                   mechanical=replace(mechanical,**{field:value})))
    with pytest.raises(ValueError,match='model_binding'):
        enclose_source_inverse_pressure(storage,state,replace(inverse,point=point))


@pytest.mark.parametrize('field,value',[
    ('source_ids',()), ('qualification','source_certified_material_pressure'),
    ('fit_error',0.), ('solid_volume_m3',1.), ('total_enthalpy_j',1.),
])
def test_original_source_point_unknowns_and_provenance_cannot_be_upgraded(actual_trials,field,value):
    storage,state,inverse=source_endpoint(actual_trials[0])
    with pytest.raises(ValueError,match='metadata_changed'):
        enclose_source_inverse_pressure(storage,state,replace(inverse,point=replace(inverse.point,**{field:value})))


def test_saved_asset_mapping_representation_preserves_exact_source_contents(actual_trials):
    storage,state,inverse=source_endpoint(actual_trials[0])
    mechanical=inverse.point.fluid.mechanical
    expected=enclose_source_inverse_pressure(storage,state,inverse)
    for mapping in (dict,MappingProxyType):
        assets=dict(mechanical.source_asset_sha256)
        def changed(values):
            return replace(inverse,point=replace(inverse.point,fluid=replace(inverse.point.fluid,
                mechanical=replace(mechanical,source_asset_sha256=mapping(values)))))
        bound=enclose_source_inverse_pressure(storage,state,changed(assets))
        assert bound.continuation==expected.continuation
        bound.check()
        assets[next(iter(assets))]='0'*64
        with pytest.raises(ValueError,match='model_binding'):
            enclose_source_inverse_pressure(storage,state,changed(assets))
