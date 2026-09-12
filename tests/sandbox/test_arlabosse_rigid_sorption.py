"""Manufactured exact-class seams; no water EOS or physical validation runs."""
from dataclasses import replace
from fractions import Fraction as F
import importlib
import math
from types import SimpleNamespace

import pytest

from sludge_sandbox.arlabosse_wet_thermo import ArlabosseWetThermodynamics, _Linear, T_REF
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_mass_caloric import ReactionDisabled
from sludge_sandbox.source_wet_storage import SourceWetStorage, SourceWetPoint


class ManufacturedWater:
    implementation = 'manufactured_not_EOS'
    source_asset_sha256 = {'fixture': '0'*64}
    source_ids = ('manufactured:water',)
    reference = SimpleNamespace(molar_mass_kg_mol=.02)


@pytest.fixture
def fixture(monkeypatch):
    """Keep exact public classes but replace only dependencies inside tests."""
    module = importlib.import_module('sludge_sandbox.arlabosse_rigid_sorption')
    controls = SimpleNamespace(pressure=100000., pressure_error=0., base_error=0.,
                               source_marker='original', source_calls=0, callbacks=0)
    water = ManufacturedWater()
    caloric = SimpleNamespace(component_id='manufactured:dry', reference_temperature_k=F('313.15'),
        specific_internal_energy=lambda t: 2000*(t-F('313.15')),
        binding=lambda: 'manufactured:dry:2000')
    base = object.__new__(SourceWetStorage)
    for name, value in dict(caloric=caloric, dry_mass_kg=.1,
            fluid_template=SimpleNamespace(mechanical=SimpleNamespace(water=water,
                gas_species_ids=('O2', 'N2', 'H2O'), gas_constant_j_mol_k=8.31446261815324)),
            volume=SimpleNamespace(value_m3=.001, error_m3=0.),
            temperature_domain_k=(320., 360.),
            chemistry=ReactionDisabled((caloric.component_id,), ('O2', 'N2', 'H2O'), 'Manufactured seam'),
            water_element_convention=object()).items():
        object.__setattr__(base, name, value)
    monkeypatch.setattr(SourceWetStorage, 'binding', lambda self: _digest((
        self.dry_mass_kg, self.temperature_domain_k, self.caloric.reference_temperature_k)))
    object.__setattr__(base, '_identity', base.binding())
    monkeypatch.setattr(SourceWetStorage, 'source_ids', property(lambda self: ('manufactured:base',)))
    monkeypatch.setattr(SourceWetStorage, 'provenance', lambda self: {'material_qualified': False})

    def evaluate(self, state, t):
        controls.callbacks += 1
        self.check(state)
        # Fixed positive capacity and an independently visible nominal base U.
        u = 300*(F(t)-F(330)) + 40000*F(state.gas_amounts_mol[2])
        solid = F(self.dry_mass_kg)*caloric.specific_internal_energy(F(t))
        fluid = SimpleNamespace(mechanical=SimpleNamespace(temperature_k=t,
            pressure_pa=controls.pressure, gas_volume_m3=.0009), source_ids=('manufactured:runtime',))
        return SourceWetPoint(fluid, float(u), solid, .001, 0., controls.pressure_error,
            0., controls.pressure_error, controls.base_error+float(abs(F(float(u))-u)),
            300., 300., self._identity, self.source_ids+fluid.source_ids)
    monkeypatch.setattr(SourceWetStorage, 'evaluate', evaluate)
    wet = object.__new__(ArlabosseWetThermodynamics)
    chemical = SimpleNamespace(water=water, reference=water.reference,
        source_asset_sha256=dict(water.source_asset_sha256), source_ids=('manufactured:wet-water',),
        gas_constant_j_mol_k=8.31446261815324)
    # q=2.7e6-4e5 W, m=-1e5+1e5 W: nonconstant source-shaped excess.
    for name, value in dict(_chemical=chemical, _mass=.02,
            _rs=chemical.gas_constant_j_mol_k/.02, _latent_reference=2300000.,
            _q=_Linear((.15, .3, .8), (2640000., 2580000., 2380000.)),
            _m=_Linear((.15, .3, .8), (-85000., -70000., -20000.))).items():
        object.__setattr__(wet, name, value)

    def check_sources(self):
        controls.source_calls += 1
    monkeypatch.setattr(ArlabosseWetThermodynamics, '_check_sources', check_sources)
    monkeypatch.setattr(ArlabosseWetThermodynamics, 'definition', lambda self: {
        'fixture': controls.source_marker, 'unknown_fit_error': None,
        'source_point_records': [{'q': None}], 'model_sha256': 'manufactured-only'})
    storage = module.ArlabosseSorptionStorage(base, wet, (90000., 110000.))
    return SimpleNamespace(module=module, storage=storage, base=base, wet=wet, controls=controls)


def state(fixture, liquid=2., gas=(.01, .02, .001), energy=0.):
    return fixture.storage.state(liquid, gas, energy)


def test_excess_energy_entropy_and_fixed_inventory_derivatives(fixture):
    st = state(fixture)
    out = fixture.storage.evaluate(st, 340.)
    base = fixture.base.evaluate(fixture.base.state(2., st.gas_amounts_mol, 0.), 340.)
    w = 2.*.02/.1
    # Independent analytic integral for these manufactured linear coefficients.
    hex_ = -400000.*(w-.8)+200000.*(w*w-.8*.8)
    mi = -100000.*(w-.8)+50000.*(w*w-.8*.8)
    assert out.excess_internal_energy_j == pytest.approx(.1*hex_, abs=1e-9)
    assert out.excess_entropy_j_k == pytest.approx(.1*(hex_-mi)/T_REF, abs=1e-11)
    assert out.excess_helmholtz_energy_j == out.excess_internal_energy_j-F(340)*out.excess_entropy_j_k
    assert abs(F(out.total_internal_energy_j)-F(base.total_internal_energy_j)-
               out.excess_internal_energy_j) <= F(out.energy_error_j)
    other = fixture.storage.evaluate(st, 341.)
    assert other.total_internal_energy_j-out.total_internal_energy_j == pytest.approx(300., abs=1e-9)
    assert other.excess_internal_energy_j == out.excess_internal_energy_j
    assert other.excess_entropy_j_k == out.excess_entropy_j_k
    assert out.closed_heat_capacity_j_k == base.closed_heat_capacity_j_k == 300.
    assert out.minimum_heat_capacity_j_k == base.minimum_heat_capacity_j_k
    assert out.pressure_pa == base.pressure_pa and out.fluid is not None


def test_chemical_potential_is_derivative_of_added_helmholtz(fixture):
    storage = fixture.storage
    n, dn, t = 2., 1e-5, 340.
    out = storage.evaluate(state(fixture, liquid=n), t)
    left = storage.evaluate(state(fixture, liquid=n-dn), t)
    right = storage.evaluate(state(fixture, liquid=n+dn), t)
    df_dn = float(right.excess_helmholtz_energy_j-left.excess_helmholtz_energy_j)/(2*dn)
    assert df_dn == pytest.approx(out.excess_chemical_potential_j_mol, rel=1e-9)
    du_dn = float(right.excess_internal_energy_j-left.excess_internal_energy_j)/(2*dn)
    assert du_dn == pytest.approx(out.excess_partial_water_enthalpy_j_mol, rel=1e-9)
    assert out.activity == pytest.approx(math.exp(out.excess_chemical_potential_j_mol/
                                               (8.31446261815324*t)), rel=2e-15)


def test_gas_water_does_not_enter_moisture_or_excess(fixture):
    a = fixture.storage.evaluate(state(fixture), 340.)
    b = fixture.storage.evaluate(state(fixture, gas=(.01, .02, 100.)), 340.)
    assert a.moisture_kg_water_per_kg_dry == b.moisture_kg_water_per_kg_dry
    assert a.excess_internal_energy_j == b.excess_internal_energy_j
    assert a.excess_chemical_potential_j_mol == b.excess_chemical_potential_j_mol


def test_state_model_identity_is_not_silently_relabelled(fixture):
    old = fixture.base.state(2., (.01, .02, .001), 0.)
    new = state(fixture)
    assert new.energy_model_identity != old.energy_model_identity
    with pytest.raises(ValueError, match='identity'):
        fixture.storage.evaluate(old, 340.)
    with pytest.raises(ValueError, match='identity'):
        fixture.base.evaluate(new, 340.)
    with pytest.raises(ValueError, match='fixed_dry_mass'):
        fixture.storage.evaluate(replace(new, solid_mass_kg=(.2,)), 340.)


def test_full_U_inverse_preserves_original_tolerances(fixture):
    point = fixture.storage.evaluate(state(fixture), 342.125)
    target = state(fixture, energy=point.total_internal_energy_j)
    policy = InversePolicy(1e-6, 1e-7, 100)
    inverse = fixture.storage.invert(target, policy)
    residual = F(inverse.point.total_internal_energy_j)-F(target.internal_energy_j)
    assert inverse.energy_residual_j == residual
    assert abs(residual)+F(inverse.point.energy_error_j) <= F(policy.energy_tolerance_j)
    assert abs(inverse.point.temperature_k-342.125) <= inverse.temperature_error_bound_k
    assert inverse.temperature_error_bound_k <= policy.temperature_tolerance_k
    fixture.controls.base_error = 1e-4
    with pytest.raises(ValueError, match='unresolved|unresolvable'):
        fixture.storage.invert(target, policy)


@pytest.mark.parametrize('liquid', [0., .01, 5., -1., True, float('nan')])
def test_moisture_or_invalid_inventory_rejected(fixture, liquid):
    before = fixture.controls.callbacks
    with pytest.raises(ValueError):
        state(fixture, liquid=liquid)
    assert fixture.controls.callbacks == before


@pytest.mark.parametrize('temperature', [308., 319., 361., float('inf'), True])
def test_temperature_domain_before_provider(fixture, temperature):
    before = fixture.controls.callbacks
    with pytest.raises(ValueError):
        fixture.storage.evaluate(state(fixture), temperature)
    assert fixture.controls.callbacks == before


@pytest.mark.parametrize('pressure,error', [(89999., 0.), (110001., 0.), (90000., 1.), (110000., 1.)])
def test_pressure_including_base_bound_must_stay_in_declared_domain(fixture, pressure, error):
    fixture.controls.pressure, fixture.controls.pressure_error = pressure, error
    with pytest.raises(ValueError, match='pressure_domain'):
        fixture.storage.evaluate(state(fixture), 340.)


@pytest.mark.parametrize('domain', [(89999., 110000.), (90000., 110001.), (100001., 100000.),
                                   (100000., 100000.), [90000., 110000.], (True, 110000.)])
def test_constructor_requires_explicit_exploration_pressure_domain(fixture, domain):
    with pytest.raises(ValueError):
        fixture.module.ArlabosseSorptionStorage(fixture.base, fixture.wet, domain)


def test_exact_collaborator_classes_before_callbacks(fixture):
    def forbidden(*args):
        raise AssertionError('untrusted_callback')
    fake = SimpleNamespace(binding=forbidden, _check_sources=forbidden)
    for base, wet in ((fake, fixture.wet), (fixture.base, fake)):
        with pytest.raises(ValueError):
            fixture.module.ArlabosseSorptionStorage(base, wet, (90000., 110000.))


def test_no_implicit_backend_bridge(fixture):
    fixture.wet._chemical.water = SimpleNamespace(reference=fixture.base.water.reference,
        implementation='other', source_asset_sha256=fixture.base.water.source_asset_sha256)
    with pytest.raises(ValueError, match='water_backend'):
        fixture.module.ArlabosseSorptionStorage(fixture.base, fixture.wet, (90000., 110000.))


def test_source_and_coefficient_mutation_stops_public_operations(fixture):
    fixture.controls.source_marker = 'changed'
    with pytest.raises(ValueError, match='changed'):
        fixture.storage.state(2., (.01, .02, .001), 0.)
    fixture.controls.source_marker = 'original'
    object.__setattr__(fixture.wet, '_q', _Linear((.15, .3, .8), (1., 2., 3.)))
    with pytest.raises(ValueError, match='changed'):
        fixture.storage.provenance()


def test_fresh_provenance_reference_offset_and_unknown_physical_errors(fixture):
    trace = fixture.storage.provenance()
    trace['wet_definition']['source_point_records'][0]['q'] = 0.
    fresh = fixture.storage.provenance()
    assert fresh['wet_definition']['source_point_records'][0]['q'] is None
    assert fresh['dry_reference_offset_j'] == pytest.approx(.1*2000*(T_REF-313.15))
    assert fresh['pressure_extension_model_error'] is None
    assert fresh['material_qualified'] is False and fresh['training_eligible'] is False
    point = fixture.storage.evaluate(state(fixture), 340.)
    assert point.pressure_extension_model_error is None and point.interpolation_model_error is None
    assert point.material_qualified is False and point.training_eligible is False
    assert set(fixture.base.source_ids+fixture.wet._source_ids()).issubset(point.source_ids)
    assert 'manufactured:runtime' in point.source_ids


def test_projection_error_is_counted_not_replaced_by_a_fixed_allowance(fixture):
    fixture.controls.base_error = 1e-12
    st = state(fixture, liquid=2.123456789)
    result = fixture.storage.evaluate(st, 343.123456789)
    base = fixture.base.evaluate(fixture.base.state(st.liquid_water_mol, st.gas_amounts_mol, 0.),
                                343.123456789)
    nominal = F(base.total_internal_energy_j)+result.excess_internal_energy_j
    required = F(base.energy_error_j)+abs(F(result.total_internal_energy_j)-nominal)
    assert F(result.energy_error_j) >= required
    assert F(result.energy_error_j) < required+F(math.ulp(result.energy_error_j))*2


def test_large_reference_energy_cannot_fake_a_small_inverse_residual(fixture):
    st = state(fixture, liquid=2.123456789, gas=(.01, .02, 1e12))
    point = fixture.storage.evaluate(st, 340.)
    target = replace(st, internal_energy_j=point.total_internal_energy_j)
    # The printed residual can be exactly zero while projection uncertainty is
    # larger than the original tolerance. No target subtraction may hide it.
    assert point.energy_error_j > 1e-8
    with pytest.raises(ValueError, match='unresolved|unresolvable'):
        fixture.storage.invert(target, InversePolicy(1e-8, 1e-8, 100))


def test_inverse_outside_domain_and_iteration_limit_fail(fixture):
    st = state(fixture)
    low = fixture.storage.evaluate(st, 320.)
    with pytest.raises(ValueError, match='target_outside'):
        fixture.storage.invert(replace(st, internal_energy_j=low.total_internal_energy_j-1.),
                               InversePolicy(1e-5, 1e-5, 100))
    target = fixture.storage.evaluate(st, 347.123456789)
    with pytest.raises(ValueError, match='iteration_limit'):
        fixture.storage.invert(replace(st, internal_energy_j=target.total_internal_energy_j),
                               InversePolicy(1e-6, 1e-6, 1))


def test_source_checks_are_present_at_each_public_operation(fixture):
    storage = fixture.storage
    st = state(fixture)
    target = replace(st, internal_energy_j=storage.evaluate(st, 340.).total_internal_energy_j)
    actions = (storage.binding, storage.provenance, lambda: storage.model_identity,
               lambda: storage.source_ids, lambda: storage.check(st), lambda: state(fixture),
               lambda: storage.evaluate(st, 340.),
               lambda: storage.invert(target, InversePolicy(1e-5, 1e-5, 100)))
    for action in actions:
        before = fixture.controls.source_calls
        action()
        assert fixture.controls.source_calls > before
