"""Actual source dry inverses with manufactured geometry; no native EOS."""
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction as F
import math
from types import SimpleNamespace

import pytest

from test_source_dry_pressure import dry
from sludge_sandbox.mass_wet_storage import wet_fluid_pressure_bounds
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.rigid_storage import RigidStorage
from sludge_sandbox.source_dry_pressure import enclose_source_dry_pressure
from sludge_sandbox.source_dry_shared_pressure import (
    declare_source_shared_dry_volume, enclose_source_dry_pressure_pair,
)
from sludge_sandbox.source_wet_storage import SourceWetStorage


@pytest.fixture(scope='module')
def endpoints(dry):
    storage, state, inverse = dry
    a = enclose_source_dry_pressure(storage, state, inverse)
    # Same live parameter, different dry inventories and temperature.
    state_b = storage.state(0., (.2, .2, .00100000001), 0.)
    point_b = storage.evaluate(state_b, 330.00000001)
    state_b = replace(state_b, internal_energy_j=point_b.total_internal_energy_j)
    inverse_b = storage.invert(state_b, InversePolicy(1e-6, 1e-6, 100))
    b = enclose_source_dry_pressure(storage, state_b, inverse_b)
    return a, b


def pair(endpoints):
    a, b = endpoints
    return enclose_source_dry_pressure_pair(a, b,
        shared_volume=declare_source_shared_dry_volume(a.storage))


def test_full_temperature_shared_volume_corners_and_negative_difference(endpoints):
    result = pair(endpoints)
    a, b = endpoints
    assert result.status == 'conditional_shared_dry_pressure_enclosure'
    assert result.bound_pa <= result.independent_bound_pa
    assert all(type(v) is F for v in (result.bound_pa, result.joint_bound_pa,
                                      result.independent_bound_pa))
    errors = sum((part.retained_error_pa for part in result.error_parts), F())
    intervals = (a.continuation.temperature_interval_k, b.continuation.temperature_interval_k)
    na, nb = (sum(map(F, end.state.gas_amounts_mol), F()) for end in endpoints)
    r = F(a.inverse.point.fluid.mechanical.gas_constant_j_mol_k)
    corners = []
    for ta in (*intervals[0], sum(intervals[0])/2):
        for tb in (*intervals[1], sum(intervals[1])/2):
            for volume in (*result.shared_volume.volume_interval_m3, F(a.storage.volume.value_m3)):
                delta = r*(na*ta-nb*tb)/volume
                corners.append(delta)
                for error in (-errors, F(), errors):
                    assert result.joint_interval_pa[0] <= delta+error <= result.joint_interval_pa[1]
    assert min(corners) < 0
    assert result.joint_bound_pa == max(map(abs, result.joint_interval_pa))
    reverse = pair((b, a))
    assert reverse.joint_interval_pa == (-result.joint_interval_pa[1], -result.joint_interval_pa[0])
    assert reverse.joint_bound_pa == result.joint_bound_pa
    assert not result.source_certified and not result.event_admitted and not result.material_qualified
    result.check()


def test_equal_endpoint_retains_temperature_and_representation_errors(endpoints):
    a = endpoints[0]
    result = pair((a, a))
    assert result.joint_bound_pa > 0
    assert all(part.actual_fluid_error_pa > 0 and part.box_rounding_error_pa > 0
               for part in result.error_parts)
    assert result.shared_volume.volume_interval_m3 == (
        F(a.storage.volume.value_m3)-F(a.storage.volume.error_m3),
        F(a.storage.volume.value_m3)+F(a.storage.volume.error_m3))


@pytest.mark.parametrize('copy_volume', [False, True])
def test_equal_content_independent_storage_is_not_shared(endpoints, copy_volume):
    a, b = endpoints
    storage = replace(b.storage, volume=replace(b.storage.volume) if copy_volume else b.storage.volume)
    assert storage.model_identity == a.storage.model_identity
    other = enclose_source_dry_pressure(storage, b.state, b.inverse)
    other.check()  # Old individual evidence remains valid.
    with pytest.raises(ValueError, match='same_live_source_storage_and_volume_required'):
        pair((a, other))


def test_declaration_binds_original_volume_object_and_complete_content(endpoints):
    a = endpoints[0]
    declaration = declare_source_shared_dry_volume(a.storage)
    with pytest.raises(FrozenInstanceError):
        declaration.storage_identity = 'changed'
    for changed in (replace(declaration, volume=replace(declaration.volume)),
                    replace(declaration, storage=replace(declaration.storage)),
                    replace(declaration, volume_interval_m3=(F(1), F(2))),
                    replace(declaration, input_binding='changed'),
                    replace(declaration, source_ids=()),
                    replace(declaration, object_identity=(True, True)),
                    replace(declaration, material_qualified=True)):
        with pytest.raises(ValueError):
            changed.check()


@pytest.mark.parametrize('field', ['global_pressure_error_pa', 'extra_pressure_error_pa', 'pressure_error_pa'])
def test_original_conservative_surplus_cannot_be_assigned_to_shared_volume(endpoints, field):
    a, b = endpoints
    point = replace(a.inverse.point, **{field: math.nextafter(getattr(a.inverse.point, field), math.inf)})
    altered = enclose_source_dry_pressure(a.storage, a.state, replace(a.inverse, point=point))
    altered.check()  # The pre-existing independent check allows larger bounds.
    with pytest.raises(ValueError, match='source_shared_dry_pressure_decomposition_changed'):
        pair((altered, b))


def test_actual_fluid_surplus_is_retained_with_rebuilt_original_decomposition(endpoints):
    a, b = endpoints
    fluid = replace(a.inverse.point.fluid, pressure_error_bound_pa=1e-7)
    global_error, extra, total = wet_fluid_pressure_bounds(a.storage.fluid_template,
        fluid, a.state.gas_amounts_mol, a.inverse.point.temperature_k, F(a.storage.volume.error_m3))
    point = replace(a.inverse.point, fluid=fluid, global_pressure_error_pa=float(global_error),
                    extra_pressure_error_pa=float(extra), pressure_error_pa=total)
    altered = enclose_source_dry_pressure(a.storage, a.state, replace(a.inverse, point=point))
    result = pair((altered, b))
    parts = result.error_parts[0]
    assert parts.actual_fluid_error_pa == F(1e-7) > altered.initial_bounds_pa[0]
    assert parts.projection_error_pa == abs(F(total)-F(1e-7)-extra)
    assert parts.retained_error_pa >= F(1e-7)
    assert result.joint_bound_pa > pair(endpoints).joint_bound_pa
    result.check()


def test_full_temperature_domain_exit_is_unresolved(endpoints):
    a, b = endpoints
    altered = enclose_source_dry_pressure(a.storage, a.state,
                                         replace(a.inverse, temperature_error_bound_k=25.))
    result = pair((altered, b))
    assert result.status == 'unresolved'
    assert result.bound_pa is result.joint_bound_pa is result.independent_bound_pa is None
    assert result.reason == 'source_dry_endpoint_domain_unresolved'
    result.check()


@pytest.mark.parametrize('field,value', [
    ('bound_pa', 0.), ('joint_bound_pa', True), ('independent_bound_pa', F()),
    ('joint_interval_pa', (F(), F())), ('status', 'accepted'),
    ('qualification', 'material_certified'), ('source_certified', True),
    ('event_admitted', True), ('material_qualified', True), ('input_binding', 'changed'),
])
def test_result_fields_cannot_be_tampered(endpoints, field, value):
    with pytest.raises(ValueError):
        replace(pair(endpoints), **{field: value}).check()


def test_endpoint_and_error_parts_cannot_be_tampered(endpoints):
    result = pair(endpoints)
    changed = replace(result.error_parts[0], box_rounding_error_pa=F())
    with pytest.raises(ValueError):
        replace(result, error_parts=(changed, result.error_parts[1])).check()
    a, b = endpoints
    with pytest.raises(ValueError):
        replace(result, endpoints=(replace(a, source_certified=True), b)).check()
    with pytest.raises(ValueError):
        replace(result, endpoints=(b, a)).check()


def test_strict_public_classes_and_passive_check(endpoints, monkeypatch):
    a, b = endpoints
    declaration = declare_source_shared_dry_volume(a.storage)
    def forbidden(*args, **kwargs):
        pytest.fail('new physical evaluation during passive shared evidence check')
    monkeypatch.setattr(SourceWetStorage, 'evaluate', forbidden)
    monkeypatch.setattr(SourceWetStorage, 'invert', forbidden)
    monkeypatch.setattr(RigidStorage, 'evaluate_at_temperature', forbidden)
    for invalid in (None, SimpleNamespace(**vars(a)), True):
        with pytest.raises(ValueError):
            enclose_source_dry_pressure_pair(invalid, b, shared_volume=declaration)
    with pytest.raises(ValueError):
        enclose_source_dry_pressure_pair(a, b, shared_volume=None)
    with pytest.raises(ValueError):
        declare_source_shared_dry_volume(SimpleNamespace(**vars(a.storage)))
    result = enclose_source_dry_pressure_pair(a, b, shared_volume=declaration)
    declaration.check()
    result.check()


def test_original_sum_and_entire_box_rounding_are_exact_fractions(endpoints):
    result = pair(endpoints)
    for end, parts in zip(endpoints, result.error_parts):
        exact_n = sum(map(F, end.state.gas_amounts_mol), F())
        nhat = F(math.fsum(end.state.gas_amounts_mol))
        r = F(end.inverse.point.fluid.mechanical.gas_constant_j_mol_k)
        nr = F(float(nhat)*float(r))
        high = end.continuation.temperature_interval_k[1]
        vmin = end.continuation.volume_interval_m3[0]
        def outward_spacing(value):
            binary = float(value)
            if F(binary) < value:
                binary = math.nextafter(binary, math.inf)
            return F(math.ulp(binary))
        product_error = outward_spacing(abs(nr)*high)
        expected = ((abs(nhat-exact_n)*r+abs(nr-nhat*r))*high+product_error)/vmin
        expected += outward_spacing((abs(nr)*high+product_error)/vmin)
        assert parts.inventory_sum_error_mol == abs(nhat-exact_n)
        assert parts.inventory_R_product_error_j_k == abs(nr-nhat*r)
        assert parts.box_rounding_error_pa == expected
        assert end.continuation.inputs[0] == exact_n
    assert any(part.inventory_sum_error_mol > 0 for part in result.error_parts)


def test_same_content_volume_object_replacement_invalidates_existing_declaration(endpoints):
    local = replace(endpoints[0].storage)
    declaration = declare_source_shared_dry_volume(local)
    object.__setattr__(local, 'volume', replace(local.volume))
    assert local.model_identity == declaration.storage_identity
    with pytest.raises(ValueError, match='same_live_source_storage_and_volume_required'):
        declaration.check()


def test_ulp_bound_is_outward_at_binade_and_rejects_unproved_range():
    from sludge_sandbox.source_dry_shared_pressure import _spacing
    below_two = F(2)-F(1, 2**54)
    assert _spacing(below_two) == F(math.ulp(2.))
    for invalid in (F(2**2048), F(1, 2**2048)):
        with pytest.raises(ValueError, match='rounding_box'):
            _spacing(invalid)


def test_selected_bound_does_not_discard_new_full_box_machine_error(endpoints):
    a = endpoints[0]
    storage = replace(a.storage, volume=replace(a.storage.volume, error_m3=0.))
    state = storage.state(0., a.state.gas_amounts_mol, 0.)
    point = storage.evaluate(state, 330.)
    state = replace(state, internal_energy_j=point.total_internal_energy_j)
    inverse = storage.invert(state, InversePolicy(1e-6, 1e-6, 100))
    bound = enclose_source_dry_pressure(storage, state, inverse)
    result = pair((bound, bound))
    # With exact volume, the new additional machine-error allowance makes its
    # target wider. A min with the old independent target would discard it.
    assert result.joint_bound_pa > result.independent_bound_pa
    assert result.bound_pa == result.joint_bound_pa
    result.check()
