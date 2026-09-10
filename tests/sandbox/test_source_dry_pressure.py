"""Dry source pressure bounds: manufactured geometry, actual source caloric inverse."""
from dataclasses import replace
from fractions import Fraction as F
from types import MappingProxyType, SimpleNamespace

import pytest

from test_source_wet_storage import setup
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.rigid_storage import RigidStorage
from sludge_sandbox.source_dry_pressure import (
    enclose_source_dry_pressure, propagate_declared_dry_pressure,
)
from sludge_sandbox.source_inverse_pressure import enclose_source_inverse_pressure
from sludge_sandbox.source_wet_storage import SourceWetStorage


def pure(**changes):
    inputs = dict(ng=F(1), gas_constant=F(8), temperature=F(320),
                  temperature_error=F(2), volume=F(4), volume_error=F(1),
                  pressure=F(640), pressure_error=F(220),
                  temperature_domain_k=(F(310), F(350)),
                  pressure_domain_pa=(F(100), F(2000)))
    inputs.update(changes)
    return propagate_declared_dry_pressure(**inputs)


def test_exact_T_volume_corners_and_original_pressure_error_are_retained():
    result = pure()
    assert result.status == 'conditional_dry_pressure_enclosure'
    assert result.temperature_interval_k == (F(318), F(322))
    assert result.volume_interval_m3 == (F(3), F(5))
    assert result.analytic_interval_pa == (F(8)*318/5, F(8)*322/3)
    assert result.slope_pa_k == F(8, 3)
    assert result.radius_pa >= F(220) + F(8, 3)*2
    for temperature in (F(318), F(320), F(322)):
        for volume in (F(3), F(4), F(5)):
            assert result.interval_pa[0] <= 8*temperature/volume <= result.interval_pa[1]
    assert not result.source_certified and 'dry' in result.qualification
    result.check()


def test_zero_error_limit_preserves_exact_ideal_gas_pressure():
    result = pure(temperature_error=F(), volume_error=F(), pressure_error=F())
    assert result.interval_pa == (F(640), F(640)) and result.radius_pa == 0
    result.check()


@pytest.mark.parametrize('changes,reason', [
    ({'temperature_error': F(11)}, 'temperature_interval_outside_declared_domain'),
    ({'pressure_domain_pa': (F(500), F(700))}, 'dry_pressure_interval_outside_declared_domain'),
])
def test_complete_domain_exit_is_unresolved_not_a_shrunken_interval(changes, reason):
    result = pure(**changes)
    assert result.status == 'unresolved' and result.reason == reason
    assert result.interval_pa is result.radius_pa is None
    result.check()


@pytest.mark.parametrize('changes', [
    {'ng': F()}, {'gas_constant': True}, {'temperature_error': 0.},
    {'volume': F()}, {'volume_error': F(-1)}, {'volume_error': F(4)},
    {'pressure_error': F(-1)}, {'temperature_domain_k': (310., 350.)},
    {'pressure_domain_pa': (F(2000), F(100))},
])
def test_pure_input_types_and_positive_volume_domain(changes):
    with pytest.raises(ValueError):
        pure(**changes)


@pytest.fixture(scope='module')
def dry():
    with pytest.MonkeyPatch.context() as patch:
        storage, previous, calls = setup(patch)
        storage = replace(storage, volume=replace(storage.volume, error_m3=1e-12))
        state = storage.state(0., previous.gas_amounts_mol, 0.)
        before = len(calls)
        point = storage.evaluate(state, 330.)
        state = replace(state, internal_energy_j=point.total_internal_energy_j)
        inverse = storage.invert(state, InversePolicy(1e-6, 1e-6, 100))
        assert len(calls) == before  # Dry caloric inversion never calls the liquid seam.
        assert inverse.temperature_error_bound_k > 0
        yield storage, state, inverse


def changed_mechanical(inverse, **changes):
    return replace(inverse, point=replace(inverse.point, fluid=replace(inverse.point.fluid,
        mechanical=replace(inverse.point.fluid.mechanical, **changes))))


def test_actual_dry_inverse_binding_and_passive_check(dry, monkeypatch):
    storage, state, inverse = dry
    def forbidden(*args, **kwargs):
        pytest.fail('dry pressure check performed a new storage evaluation')
    monkeypatch.setattr(SourceWetStorage, 'evaluate', forbidden)
    monkeypatch.setattr(SourceWetStorage, 'invert', forbidden)
    monkeypatch.setattr(RigidStorage, 'evaluate_at_temperature', forbidden)
    result = enclose_source_dry_pressure(storage, state, inverse)
    continuation = result.continuation
    assert continuation.status == 'conditional_dry_pressure_enclosure'
    ng = sum(map(F, state.gas_amounts_mol), F())
    gas_constant = F(storage.fluid_template.mechanical.gas_constant_j_mol_k)
    for temperature in continuation.temperature_interval_k:
        for volume in continuation.volume_interval_m3:
            assert continuation.interval_pa[0] <= ng*gas_constant*temperature/volume <= continuation.interval_pa[1]
    assert continuation.radius_pa >= F(inverse.point.pressure_error_pa)
    assert result.source_certified is result.event_admitted is result.material_qualified is False
    result.check()
    with pytest.raises(ValueError):
        enclose_source_inverse_pressure(storage, state, inverse)


@pytest.mark.parametrize('field,value', [
    ('liquid_pressure_pa', 1.), ('liquid_inventory_mol', 1e-10),
    ('liquid_volume_m3', 1e-12), ('pressure_solution_path', 'liquid_exact_numerical_endpoint'),
    ('gas_constant_j_mol_k', F(8)), ('pressure_pa', 1.),
    ('pressure_residual_pa', 1.), ('volume_resolution_m3', 0.),
    ('iterations', True), ('partial_pressures_pa', {'O2': 1., 'N2': 1., 'H2O': 1.}),
])
def test_forged_dry_mechanical_evidence_is_rejected(dry, field, value):
    storage, state, inverse = dry
    with pytest.raises(ValueError):
        enclose_source_dry_pressure(storage, state, changed_mechanical(inverse, **{field: value}))


@pytest.mark.parametrize('field', ['pressure_error_pa', 'global_pressure_error_pa',
                                  'extra_pressure_error_pa', 'energy_error_j'])
def test_original_nonzero_source_errors_cannot_be_underreported(dry, field):
    storage, state, inverse = dry
    assert getattr(inverse.point, field) > 0
    with pytest.raises(ValueError):
        enclose_source_dry_pressure(storage, state,
            replace(inverse, point=replace(inverse.point, **{field: 0.})))


def test_source_state_inverse_and_mutable_record_bindings(dry):
    storage, state, inverse = dry
    for changed in (replace(state, liquid_water_mol=1e-12),
                    replace(state, internal_energy_j=state.internal_energy_j+1.),
                    replace(state, gas_amounts_mol=(.1, .2, .001))):
        with pytest.raises(ValueError):
            enclose_source_dry_pressure(storage, changed, inverse)
    with pytest.raises(ValueError):
        enclose_source_dry_pressure(replace(storage, dry_mass_kg=.3), state, inverse)
    for changed in (replace(inverse, temperature_error_bound_k=0.),
                    replace(inverse, energy_residual_j=F(1)),
                    replace(inverse, iterations=True),
                    replace(inverse, final_temperature_bracket_k=(0., 1.)),
                    SimpleNamespace(**vars(inverse))):
        with pytest.raises(ValueError):
            enclose_source_dry_pressure(storage, state, changed)
    result = enclose_source_dry_pressure(storage, state, inverse)
    for changed in (replace(result, event_admitted=True), replace(result, material_qualified=True),
                    replace(result, source_certified=True), replace(result, input_binding='changed'),
                    replace(result, continuation=replace(result.continuation, radius_pa=F()))):
        with pytest.raises(ValueError):
            changed.check()


def test_saved_mapping_representation_keeps_source_identity(dry):
    storage, state, inverse = dry
    assets = dict(inverse.point.fluid.mechanical.source_asset_sha256)
    for mapping in (dict, MappingProxyType):
        result = enclose_source_dry_pressure(storage, state,
            changed_mechanical(inverse, source_asset_sha256=mapping(assets)))
        result.check()
    assets[next(iter(assets))] = '0'*64
    with pytest.raises(ValueError):
        enclose_source_dry_pressure(storage, state, changed_mechanical(inverse, source_asset_sha256=assets))


def test_dry_record_metadata_cannot_gain_material_or_wet_authority(dry):
    storage, state, inverse = dry
    for changes in ({'material_qualified': True}, {'source_ids': ()}, {'fit_error': 0.}):
        with pytest.raises(ValueError):
            enclose_source_dry_pressure(storage, state, replace(inverse, point=replace(inverse.point, **changes)))


@pytest.mark.parametrize('sources', [(), ('fabricated:certified-fluid-eos',)])
def test_fluid_sources_must_match_actual_providers_even_if_aggregate_is_rewritten(dry, sources):
    storage, state, inverse = dry
    # Saved mappings can be reordered; the real provider order remains fixed.
    reordered = dict(reversed(tuple(inverse.point.fluid.mechanical.gas_inventory_mol.items())))
    original = changed_mechanical(inverse, gas_inventory_mol=reordered)
    enclose_source_dry_pressure(storage, state, original).check()
    fluid = replace(original.point.fluid, source_ids=sources)
    point = replace(original.point, fluid=fluid,
                    source_ids=tuple(sorted(set(storage.source_ids+sources))))
    with pytest.raises(ValueError, match='source_dry_fluid_sources_changed'):
        enclose_source_dry_pressure(storage, state, replace(original, point=point))


@pytest.mark.parametrize('which,reason', [
    ('temperature', 'temperature_interval_outside_declared_domain'),
    ('pressure', 'dry_pressure_interval_outside_declared_domain'),
])
def test_source_full_uncertainty_domain_exit_remains_unresolved(dry, which, reason):
    storage, state, inverse = dry
    if which == 'temperature':
        changed = replace(inverse, temperature_error_bound_k=25.)
    else:
        changed = replace(inverse, point=replace(inverse.point, pressure_error_pa=1e8))
    result = enclose_source_dry_pressure(storage, state, changed)
    assert result.continuation.status == 'unresolved' and result.continuation.reason == reason
    assert result.continuation.interval_pa is result.continuation.radius_pa is None
    assert result.source_certified is result.event_admitted is result.material_qualified is False
    result.check()
