"""Manufactured liquid seam; actual source inverse, no native EOS."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from test_source_wet_storage import setup
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_inverse_pressure import enclose_source_inverse_pressure


@pytest.fixture(scope='module')
def actual_wet_pair():
    with pytest.MonkeyPatch.context() as patch:
        old, _, calls = setup(patch)
        envelope = replace(old.fluid_template.envelope, liquid_v_error_m3_mol=1e-15,
                           liquid_abs_du_dp_bound_j_mol_pa=1e-6)
        storage = replace(old, fluid_template=replace(old.fluid_template,envelope=envelope),
                          volume=replace(old.volume,error_m3=1e-12))
        endpoints = []
        for temperature, gas in ((330.,(.2,.2,.001)), (330.000001,(.2,.200001,.001))):
            state = storage.state(.2,gas,0.)
            point = storage.evaluate(state,temperature)
            state = replace(state,internal_energy_j=point.total_internal_energy_j)
            inverse = storage.invert(state,InversePolicy(1e-6,1e-6,100))
            endpoints.append(enclose_source_inverse_pressure(storage,state,inverse))
        yield storage, tuple(endpoints), calls


def test_new_wet_pair_api_is_explicit():
    from sludge_sandbox.source_wet_shared_pressure import (
        declare_source_shared_wet_volume, collect_source_wet_pressure_pair,
        enclose_source_wet_pressure_pair,
    )
    assert all(callable(f) for f in (declare_source_shared_wet_volume,
        collect_source_wet_pressure_pair,enclose_source_wet_pressure_pair))


def test_actual_inverse_pair_and_passive_check(actual_wet_pair,monkeypatch):
    from sludge_sandbox.source_wet_shared_pressure import (
        declare_source_shared_wet_volume, collect_source_wet_pressure_pair,
    )
    from sludge_sandbox.water_properties import WaterProperties
    storage, endpoints, calls = actual_wet_pair
    before = len(calls)
    pair = collect_source_wet_pressure_pair(*endpoints,
        shared_volume=declare_source_shared_wet_volume(storage))
    assert len(calls)-before == len(pair.evidence.attempts) == 4
    assert pair.status == 'conditional_shared_wet_pressure_enclosure', pair.reason
    assert pair.bound_pa == pair.joint_bound_pa > 0
    assert type(pair.bound_pa) is F
    assert pair.endpoints[0] is endpoints[0] and pair.endpoints[1] is endpoints[1]
    assert pair.independent_bound_pa == abs(F(endpoints[0].inverse.point.pressure_pa)-F(endpoints[1].inverse.point.pressure_pa))+sum((e.continuation.radius_pa for e in endpoints),F())
    assert all(p.machine_residual_bound_m3 > 0 and p.actual_fluid_error_pa > 0
               and p.retained_report_error_pa > p.actual_fluid_error_pa for p in pair.error_parts)
    for part in pair.error_parts:
        assert part.low_root_sign_lower_m3 >= 0 >= part.high_root_sign_upper_m3
        assert part.machine_residual_bound_m3 == part.liquid_rounding_residual_m3+part.gas_rounding_residual_m3+part.sum_rounding_residual_m3
        assert part.added_temperature_error_pa >= 0
    def forbidden(*args,**kwargs):
        pytest.fail('passive pair.check made an EOS call')
    monkeypatch.setattr(WaterProperties,'state_tp',forbidden)
    pair.check()
    assert not pair.source_certified and not pair.event_admitted and not pair.material_qualified


def collect(actual_wet_pair, *, endpoints=None, **kwargs):
    from sludge_sandbox.source_wet_shared_pressure import (
        declare_source_shared_wet_volume, collect_source_wet_pressure_pair,
    )
    storage, original, _ = actual_wet_pair
    return collect_source_wet_pressure_pair(*(original if endpoints is None else endpoints),
        shared_volume=declare_source_shared_wet_volume(storage),**kwargs)


def test_independent_constant_liquid_root_oracle_full_T_and_shared_V(actual_wet_pair):
    pair = collect(actual_wet_pair)
    # Independent exact constant-v closure. The seam's native division can be
    # slightly different from the printed 1.8e-5, contained by original epsilon.
    for fraction in (F(),F(1,3),F(1)):
        vlo,vhi = pair.shared_volume.volume_interval_m3
        volume = vlo+(vhi-vlo)*fraction
        for ta in pair.endpoints[0].continuation.temperature_interval_k:
            for tb in pair.endpoints[1].continuation.temperature_interval_k:
                values = []
                for endpoint,t in zip(pair.endpoints,(ta,tb)):
                    n = sum(map(F,endpoint.state.gas_amounts_mol),F())
                    values.append(n*endpoint.continuation.inputs[2]*t/
                        (volume-F(endpoint.state.liquid_water_mol)*F(1.8e-5)))
                assert abs(values[0]-values[1]) <= pair.bound_pa
    reverse = collect(actual_wet_pair,endpoints=tuple(reversed(pair.endpoints)))
    assert reverse.residual_interval_m3 == (-pair.residual_interval_m3[1],-pair.residual_interval_m3[0])
    assert reverse.bound_pa == pair.bound_pa
    assert pair.residual_interval_m3[0] < 0  # Signed gas numerator is retained.


def test_same_endpoint_dedup_keeps_independent_errors_and_machine_margin(actual_wet_pair):
    _,endpoints,calls = actual_wet_pair
    before = len(calls)
    pair = collect(actual_wet_pair,endpoints=(endpoints[0],endpoints[0]))
    assert len(calls)-before == len(pair.evidence.attempts) == 2
    assert pair.error_parts[0].actual_fluid_error_pa == pair.error_parts[1].actual_fluid_error_pa > 0
    assert pair.bound_pa > 2*pair.error_parts[0].actual_fluid_error_pa
    assert pair.root_difference_bound_pa > 0  # Independent epsilon does not cancel.
    assert pair.error_parts[0].machine_residual_bound_m3 > 0
    pair.check()


def test_full_support_is_outward_and_new_temperature_margin_retained(actual_wet_pair):
    pair = collect(actual_wet_pair)
    support = pair.evidence.support
    exactlo = min(box[0] for box in support.reported_pressure_boxes_pa)
    exacthi = max(box[1] for box in support.reported_pressure_boxes_pa)
    assert support.interval_pa[0] <= exactlo <= exacthi <= support.interval_pa[1]
    assert all(F(float(x)) == x for x in support.interval_pa)
    assert any(p.added_temperature_error_pa > 0 for p in pair.error_parts)
    for endpoint,part in zip(pair.endpoints,pair.error_parts):
        pressure = F(endpoint.inverse.point.pressure_pa)
        expected_radius = max(F(endpoint.inverse.point.pressure_error_pa),
            *(abs(pressure-x) for x in support.interval_pa))
        assert part.continuation.inputs[-1] == expected_radius
        assert part.original_temperature_error_pa == endpoint.continuation.slope_pa_k*F(endpoint.inverse.temperature_error_bound_k)
    with pytest.raises(ValueError):
        replace(pair,error_parts=(replace(pair.error_parts[0],added_temperature_error_pa=F()),
                                 pair.error_parts[1])).check()


def test_equal_content_distinct_storage_or_volume_has_no_shared_identity(actual_wet_pair):
    from sludge_sandbox.source_wet_shared_pressure import (
        declare_source_shared_wet_volume, collect_source_wet_pressure_pair,
    )
    storage,endpoints,calls = actual_wet_pair
    declaration = declare_source_shared_wet_volume(storage)
    for clone in (replace(storage),replace(storage,volume=replace(storage.volume))):
        assert clone.model_identity == storage.model_identity
        endpoint = enclose_source_inverse_pressure(clone,endpoints[1].state,endpoints[1].inverse)
        before = len(calls)
        with pytest.raises(ValueError,match='same_live'):
            collect_source_wet_pressure_pair(endpoints[0],endpoint,shared_volume=declaration)
        assert len(calls) == before
    for changed in (replace(declaration,volume=replace(storage.volume)),
                    replace(declaration,object_identity=(True,id(storage.volume))),
                    replace(declaration,source_certified=True)):
        with pytest.raises(ValueError): changed.check()


def test_saved_error_surplus_rejects_new_shared_but_preserves_single_end(actual_wet_pair):
    storage,endpoints,calls = actual_wet_pair
    endpoint = endpoints[0]
    point = replace(endpoint.inverse.point,pressure_error_pa=endpoint.inverse.point.pressure_error_pa+.01)
    changed = enclose_source_inverse_pressure(storage,endpoint.state,replace(endpoint.inverse,point=point))
    changed.check()  # Original single-end API intentionally admits a surplus.
    before = len(calls)
    with pytest.raises(ValueError,match='decomposition_changed'):
        collect(actual_wet_pair,endpoints=(changed,endpoints[1]))
    assert len(calls) == before


@pytest.mark.parametrize('field,value',[
    ('joint_bound_pa',F()), ('bound_pa',0.), ('source_certified',True),
    ('material_qualified',True), ('event_admitted',True),
    ('qualification','source_certified'), ('assumptions',()),
])
def test_derived_values_types_and_qualification_tampering_rejected(actual_wet_pair,field,value):
    pair = collect(actual_wet_pair)
    with pytest.raises(ValueError): replace(pair,**{field:value}).check()


def test_saved_observation_and_full_evidence_tampering_rejected(actual_wet_pair):
    pair = collect(actual_wet_pair)
    evidence = pair.evidence
    observation = evidence.attempts[0]
    for changed in (replace(observation,pressure_pa=observation.pressure_pa+1.),
                    replace(observation,state=replace(observation.state,density_kg_m3=100.)),
                    replace(observation,ratio_projection_m3_mol=F()),
                    replace(observation,ordinal=True),
                    replace(observation,declared_volume_error_m3_mol=F())):
        bad = replace(evidence,attempts=(changed,)+evidence.attempts[1:])
        with pytest.raises(ValueError): replace(pair,evidence=bad).check()
    for bad in (replace(evidence,attempts=evidence.attempts[:-1]),
                replace(evidence,assumptions=()),
                replace(evidence,support=replace(evidence.support,endpoint_indices=((0,1),(0,1))))):
        with pytest.raises(ValueError): replace(pair,evidence=bad).check()


def test_root_existence_failure_retains_four_observations(actual_wet_pair,monkeypatch):
    from sludge_sandbox.water_properties import WaterProperties
    original = WaterProperties.state_tp
    def changed(w,t,p,*,phase):
        # Explicit adversarial manufactured observation inconsistent with the
        # old closure, not a new native-water evaluation or a source certificate.
        return replace(original(w,t,p,phase=phase),density_kg_m3=2000.)
    monkeypatch.setattr(WaterProperties,'state_tp',changed)
    pair = collect(actual_wet_pair)
    assert pair.status == 'unresolved' and pair.reason == 'source_shared_wet_root_existence_unresolved'
    assert len(pair.evidence.attempts) == 4 and pair.bound_pa is None
    pair.check()


@pytest.mark.parametrize('cancel_at',[0,1,3])
def test_cancellation_before_unique_requests_retains_actual_prefix(actual_wet_pair,cancel_at):
    from sludge_sandbox.source_wet_shared_pressure import SourceWetPairCollectionError
    _,_,calls = actual_wet_pair
    seen = 0
    def cancel():
        nonlocal seen
        answer = seen == cancel_at
        seen += 1
        return answer
    before = len(calls)
    with pytest.raises(SourceWetPairCollectionError) as error:
        collect(actual_wet_pair,cancel=cancel)
    result = error.value
    assert result.stage == 'cancel' and len(result.attempts) == cancel_at
    assert len(calls)-before == cancel_at
    assert all(a.state is not None and a.failure_type is None for a in result.attempts)
    assert result.__cause__ is not None


@pytest.mark.parametrize('mode',['raises','wrong_return','postprocess'])
def test_failed_actual_request_or_return_validation_is_preserved(actual_wet_pair,monkeypatch,mode):
    from sludge_sandbox.water_properties import WaterProperties
    import sludge_sandbox.source_wet_shared_pressure as module
    original = WaterProperties.state_tp
    produced = []
    def changed(w,t,p,*,phase):
        if len(produced) == 1 and mode == 'raises':
            raise TimeoutError('manufactured request budget exhausted')
        state = original(w,t,p,phase=phase)
        if len(produced) == 1 and mode == 'wrong_return':
            state = replace(state,temperature_k=t+1.)
        produced.append(state)
        return state
    monkeypatch.setattr(WaterProperties,'state_tp',changed)
    if mode == 'postprocess':
        def fail(*args,**kwargs): raise RuntimeError('manufactured assessment failure')
        monkeypatch.setattr(module,'enclose_source_wet_pressure_pair',fail)
    with pytest.raises(module.SourceWetPairCollectionError) as error:
        collect(actual_wet_pair)
    result = error.value
    assert result.__cause__ is not None
    if mode == 'postprocess':
        assert result.stage == 'enclose' and len(result.attempts) == 4
        assert all(a.state is state for a,state in zip(result.attempts,produced))
    else:
        assert len(result.attempts) == 2 and result.attempts[0].state is produced[0]
        assert result.attempts[-1].failure_type is not None
        assert result.attempts[-1].state is (None if mode == 'raises' else produced[-1])


def test_full_box_normal_guard_not_only_saved_observations():
    from sludge_sandbox.source_wet_shared_pressure import _normal_interval, _UnresolvedBox
    import sys
    low, high = F(sys.float_info.min),F(sys.float_info.max)
    _normal_interval(low,high)
    for values in ((low/2,F(1)),(F(1),high*2),(F(),F(1))):
        with pytest.raises(_UnresolvedBox): _normal_interval(*values)


def test_actual_fluid_surplus_is_retained_after_original_decomposition(actual_wet_pair):
    from sludge_sandbox.mass_wet_storage import wet_fluid_pressure_bounds
    storage,endpoints,_ = actual_wet_pair
    endpoint = endpoints[0]
    # Explicit conservative saved-record stress case: inflate both caloric
    # envelopes and eT consistently. No test or event threshold is loosened.
    fluid = replace(endpoint.inverse.point.fluid,
                    pressure_error_bound_pa=endpoint.inverse.point.fluid.pressure_error_bound_pa+.1,
                    energy_error_bound_j=endpoint.inverse.point.fluid.energy_error_bound_j+1.)
    global_error,extra,total = wet_fluid_pressure_bounds(storage.fluid_template,fluid,
        endpoint.state.gas_amounts_mol,endpoint.inverse.point.temperature_k,F(storage.volume.error_m3))
    point = replace(endpoint.inverse.point,fluid=fluid,global_pressure_error_pa=float(global_error),
        extra_pressure_error_pa=float(extra),pressure_error_pa=total,
        energy_error_j=endpoint.inverse.point.energy_error_j+2.)
    inverse = replace(endpoint.inverse,point=point,temperature_error_bound_k=1.)
    changed = enclose_source_inverse_pressure(storage,endpoint.state,inverse)
    pair = collect(actual_wet_pair,endpoints=(changed,changed))
    assert pair.status == 'conditional_shared_wet_pressure_enclosure', pair.reason
    assert pair.error_parts[0].actual_fluid_error_pa == F(fluid.pressure_error_bound_pa) > changed.initial_bounds_pa[0]
    assert pair.error_parts[0].retained_report_error_pa >= F(fluid.pressure_error_bound_pa)
    assert pair.error_parts[0].original_temperature_error_pa == changed.continuation.slope_pa_k
    pair.check()


def test_actual_positive_tiny_liquid_inventory_is_unresolved_not_dry(actual_wet_pair):
    storage,_,_ = actual_wet_pair
    # Extra manufactured normal-range stress input, not an altered tolerance.
    state = storage.state(1e-310,(.2,.2,.001),0.)
    point = storage.evaluate(state,330.)
    state = replace(state,internal_energy_j=point.total_internal_energy_j)
    inverse = storage.invert(state,InversePolicy(1e-6,1e-6,100))
    endpoint = enclose_source_inverse_pressure(storage,state,inverse)
    pair = collect(actual_wet_pair,endpoints=(endpoint,endpoint))
    assert endpoint.state.liquid_water_mol > 0
    assert pair.status == 'unresolved' and pair.reason == 'source_shared_wet_rounding_box_not_normal'
    assert len(pair.evidence.attempts) == 2 and pair.bound_pa is None
    assert not pair.event_admitted
    pair.check()


def test_original_endpoint_domain_unresolved_makes_no_new_requests(actual_wet_pair):
    storage,endpoints,calls = actual_wet_pair
    endpoint = enclose_source_inverse_pressure(storage,endpoints[0].state,
        replace(endpoints[0].inverse,temperature_error_bound_k=100.))
    before = len(calls)
    pair = collect(actual_wet_pair,endpoints=(endpoint,endpoints[1]))
    assert pair.status == 'unresolved' and pair.reason == 'source_wet_endpoint_domain_unresolved'
    assert not pair.evidence.attempts and len(calls) == before and pair.bound_pa is None
    pair.check()


@pytest.mark.parametrize('value',[None,True,0.,()])
def test_invalid_endpoint_types_rejected_before_requests(actual_wet_pair,value):
    _,endpoints,calls = actual_wet_pair
    before = len(calls)
    with pytest.raises(ValueError): collect(actual_wet_pair,endpoints=(value,endpoints[1]))
    assert len(calls) == before


@pytest.mark.parametrize('change_stage',['cancel','return'])
def test_transient_original_water_limits_cannot_be_mixed_then_restored(actual_wet_pair,monkeypatch,change_stage):
    from sludge_sandbox.source_wet_shared_pressure import SourceWetPairCollectionError
    from sludge_sandbox.water_properties import WaterProperties
    storage,_,calls = actual_wet_pair
    water = storage.water
    original_limits = water.numerical_limits
    altered = replace(original_limits,pressure_relative=original_limits.pressure_relative*2)
    original_query = WaterProperties.state_tp
    checks = 0
    returned = []
    def cancel():
        nonlocal checks
        object.__setattr__(water,'numerical_limits',
            altered if change_stage == 'cancel' and checks == 0 else original_limits)
        checks += 1
        return False
    def query(w,t,p,*,phase):
        state = original_query(w,t,p,phase=phase)
        returned.append(state)
        if change_stage == 'return' and len(returned) == 1:
            object.__setattr__(water,'numerical_limits',altered)
        return state
    monkeypatch.setattr(WaterProperties,'state_tp',query)
    before = len(calls)
    try:
        with pytest.raises(SourceWetPairCollectionError) as error:
            collect(actual_wet_pair,cancel=cancel)
        outcome = error.value
        assert outcome.__cause__ is not None
        if change_stage == 'cancel':
            assert outcome.stage == 'validate_inputs' and not outcome.attempts
            assert len(calls) == before
        else:
            assert outcome.stage == 'validate_return' and len(outcome.attempts) == 1
            assert outcome.attempts[0].state is returned[0]
            assert outcome.attempts[0].failure_type is not None
            assert len(calls)-before == 1
    finally:
        object.__setattr__(water,'numerical_limits',original_limits)
    storage._check()
