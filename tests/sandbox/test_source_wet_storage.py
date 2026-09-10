"""Source Cp coupled to the existing fluid kernel; liquid seam is explicit."""
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction as F
from types import SimpleNamespace

import pytest

from test_mass_wet_storage import setup as old_setup
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.arlabosse_caloric import ArlabosseDryCaloric
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.reaction_reference import ReactionReferenceNetwork
from sludge_sandbox.rigid_storage import RigidStorage
from sludge_sandbox.source_mass_caloric import ArlabosseMassCaloric, ReactionDisabled
from sludge_sandbox.source_wet_storage import SourceWetStorage, ManufacturedFixedFluidVolume


def setup(monkeypatch):
    previous, _, calls = old_setup(monkeypatch)
    raw = ArlabosseDryCaloric(REPOSITORY/'data/sandbox/research/arlabosse2005/source.json', REPOSITORY)
    caloric = ArlabosseMassCaloric(raw, F('313.15'))
    # After constructing the old fluid fixture, no artificial reaction network
    # is available to the new storage constructor or either energy direction.
    def forbidden(*args, **kwargs):
        raise AssertionError('reaction_network_must_not_be_used')
    monkeypatch.setattr(ReactionReferenceNetwork, 'solve', forbidden)
    chemistry = ReactionDisabled((caloric.component_id,), previous.gas_ids,
                                 'Fixed-composition low-temperature numerical coupling')
    volume = ManufacturedFixedFluidVolume(.001, 0., 'Explicit test-only available fluid volume')
    storage = SourceWetStorage(caloric, .2, previous.fluid_template, volume,
                               (310., 350.), chemistry, previous.water_element_convention)
    return storage, storage.state(.2, (.2, .2, .001), 0.), calls


def solid_u(t, anchor=F('313.15')):
    # Independent integration of the printed Cp polynomial, not source calls.
    a = F('1434')-F('3.29')*F('273.15')
    return F(.2)*(a*(F(t)-anchor)+F('3.29')*(F(t)**2-anchor**2)/2)


def test_couples_source_mass_and_actual_shared_fluid_kernel(monkeypatch):
    storage, state, calls = setup(monkeypatch)
    out = storage.evaluate(state, 330.)
    assert calls and out.fluid.mechanical.liquid_inventory_mol == .2
    expected = F(out.fluid.internal_energy_j)+solid_u(330.)
    assert abs(F(out.total_internal_energy_j)-expected) <= F(out.energy_error_j)
    assert out.solid_internal_energy_j == solid_u(330.)
    assert out.gas_volume_m3 < out.available_pore_volume_m3 == .001
    assert out.total_enthalpy_j is None and out.solid_volume_m3 is None
    assert out.fit_error is None and not out.material_qualified
    rates = storage.chemistry.evaluate(state.solid_mass_kg, state.gas_amounts_mol)
    assert rates.solid_kg_s == (0,) and rates.gas_mol_s == (0, 0, 0)
    assert rates.chemical_reference_power_w == 0 and not rates.phase_transfer_included


def test_inverse_and_constant_inventory_energy_coordinate_shift(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    out = storage.evaluate(state, 331.)
    target = replace(state, internal_energy_j=out.total_internal_energy_j)
    inverse = storage.invert(target, InversePolicy(1e-6, 1e-6, 100))
    assert abs(inverse.point.temperature_k-331.) <= inverse.temperature_error_bound_k
    shifted = replace(storage, caloric=replace(storage.caloric, reference_temperature_k=F('333.15')))
    other = shifted.state(state.liquid_water_mol, state.gas_amounts_mol, 0.)
    point = shifted.evaluate(other, 331.)
    assert out.pressure_pa == point.pressure_pa
    assert out.solid_internal_energy_j-point.solid_internal_energy_j == F(.2)*31970
    with pytest.raises(ValueError, match='identity'):
        shifted.invert(target, InversePolicy(1e-6, 1e-6, 100))
    inverse2 = shifted.invert(replace(other, internal_energy_j=point.total_internal_energy_j),
                              InversePolicy(1e-6, 1e-6, 100))
    assert abs(inverse2.point.temperature_k-331.) <= inverse2.temperature_error_bound_k


def test_point_capacity_and_whole_domain_lower_bound_are_distinct(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    point = storage.evaluate(state, 349.)
    cp = F(.2)*(F('1434')+F('3.29')*(F(349)-F('273.15')))
    cmin = F(.2)*(F('1434')+F('3.29')*(F(310)-F('273.15')))
    assert abs(F(point.closed_heat_capacity_j_k)-F(point.fluid.closed_heat_capacity_j_k)-cp) < F(1e-12)
    assert F(point.minimum_heat_capacity_j_k) <= F(point.fluid.minimum_heat_capacity_j_k)+cmin
    assert abs(F(point.minimum_heat_capacity_j_k)-F(point.fluid.minimum_heat_capacity_j_k)-cmin) < F(1e-12)


def test_phase_redistribution_at_fixed_U_cools_without_extra_latent_source(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    initial = replace(state, internal_energy_j=storage.evaluate(state, 330.).total_internal_energy_j)
    shifted = replace(initial, liquid_water_mol=.199, gas_amounts_mol=(.2, .2, .002))
    out = storage.invert(shifted, InversePolicy(1e-6, 1e-6, 100))
    assert out.point.temperature_k < 330.
    assert out.point.total_internal_energy_j == pytest.approx(initial.internal_energy_j, abs=1e-6)
    assert abs(F(shifted.liquid_water_mol)+F(shifted.gas_amounts_mol[2])-
               F(initial.liquid_water_mol)-F(initial.gas_amounts_mol[2])) < F(1e-16)


def test_available_volume_uncertainty_reaches_pressure_and_energy(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    envelope = replace(storage.fluid_template.envelope, liquid_abs_du_dp_bound_j_mol_pa=1e-6)
    changed = replace(storage, fluid_template=replace(storage.fluid_template, envelope=envelope),
                      volume=replace(storage.volume, error_m3=1e-12))
    st = changed.state(state.liquid_water_mol, state.gas_amounts_mol, 0.)
    point = changed.evaluate(st, 330.)
    added = F(st.liquid_water_mol)*F(envelope.liquid_abs_du_dp_bound_j_mol_pa)*F(point.extra_pressure_error_pa)
    assert added > 0 and F(point.energy_error_j) >= F(point.fluid.energy_error_bound_j)+added
    assert point.pressure_error_pa > storage.evaluate(state, 330.).pressure_error_pa
    with pytest.raises(ValueError):
        replace(changed, volume=replace(changed.volume, error_m3=.001))


@pytest.mark.parametrize('field,value', [('dry_mass_kg', F(1, 5)), ('dry_mass_kg', True),
    ('dry_mass_kg', 0.), ('temperature_domain_k', (308.15, 350.)),
    ('temperature_domain_k', (310., 400.)), ('temperature_domain_k', (340., 320.))])
def test_invalid_or_unrepresented_configuration_rejected(monkeypatch, field, value):
    storage, _, _ = setup(monkeypatch)
    with pytest.raises(ValueError): replace(storage, **{field: value})


def test_fixed_mass_and_no_fabricated_volume_admission(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    with pytest.raises(ValueError, match='fixed_dry_mass'):
        storage.evaluate(replace(state, solid_mass_kg=(.21,)), 330.)
    with pytest.raises(ValueError): replace(storage, volume=None)
    with pytest.raises(ValueError): replace(storage.volume, classification='measured_public_data')
    with pytest.raises(ValueError): replace(storage, chemistry=ReactionDisabled(('A', 'B'), storage.gas_ids, 'Wrong material'))
    with pytest.raises(ValueError): storage.state(Decimal('.2'), state.gas_amounts_mol, 0.)
    with pytest.raises(ValueError): storage.evaluate(state, Decimal('330.1'))


def test_runtime_substitution_rejected_before_callbacks(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    def forbidden(*args, **kwargs): raise AssertionError('untrusted_callback')
    object.__setattr__(storage, 'caloric', SimpleNamespace(binding=forbidden))
    with pytest.raises(ValueError): storage.evaluate(state, 330.)


def test_dry_limit_and_trace_preserve_unknown_material_fields(monkeypatch):
    storage, state, calls = setup(monkeypatch)
    before = len(calls)
    point = storage.evaluate(replace(state, liquid_water_mol=0.), 330.)
    assert len(calls) == before and point.gas_volume_m3 == .001
    trace = storage.provenance()
    assert trace['material_qualified'] is False
    assert trace['available_volume']['classification'] == 'manufactured_test_fixture'
    assert trace['missing_material_evidence']
    assert set(storage.water.source_ids).issubset(storage.source_ids)
    assert set(storage.fluid_template.envelope.source_ids).issubset(storage.source_ids)
    assert set(point.source_ids) == set(storage.source_ids)


def test_actual_fluid_runtime_sources_are_forwarded(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    original = RigidStorage.evaluate_at_temperature
    marker = 'manufactured:source-wet-runtime-metadata-probe'
    assert marker not in storage.source_ids
    def observed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        return replace(result, source_ids=result.source_ids+(marker,))
    monkeypatch.setattr(RigidStorage, 'evaluate_at_temperature', observed)
    assert marker in storage.evaluate(state, 330.).source_ids


def test_outside_energy_and_insufficient_numerical_tolerance_fail(monkeypatch):
    storage, state, _ = setup(monkeypatch)
    low = storage.evaluate(state, 310.)
    with pytest.raises(ValueError, match='energy_target_outside'):
        storage.invert(replace(state, internal_energy_j=low.total_internal_energy_j-1.),
                       InversePolicy(1e-5, 10., 100))
    center = storage.evaluate(state, 330.)
    with pytest.raises(ValueError):
        storage.invert(replace(state, internal_energy_j=center.total_internal_energy_j),
                       InversePolicy(1e-15, 1e-15, 100))
