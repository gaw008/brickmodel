"""Current-state dry point-storage oracles; every water EOS entry is forbidden."""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F

import pytest

import sludge_sandbox.dynamic_solid_storage as m
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.water_properties import WaterProperties
from sludge_sandbox.water_heos import HEOSWaterProperties
from test_rigid_storage import water, R
from test_deforming_solid_storage import build as prescribed_fixture


@pytest.fixture(autouse=True)
def forbid_water_eos(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('dry dynamic storage called water EOS')
    for cls in (WaterProperties, HEOSWaterProperties):
        for name in ('state_tp', 'state_tp_response', 'saturation_pair', 'ideal_vapor'):
            monkeypatch.setattr(cls, name, forbidden)
    monkeypatch.setattr(WaterProperties, '_solve', forbidden)


def build(water):
    old = prescribed_fixture(water)
    skeleton = replace(old.skeleton, viscosity_pa_s=1e6)
    bounds = m.DynamicStorageErrorBounds((.5, 2.), (.5, 2.), 0., 0.,
        ('manufactured:exact-current-inputs',), 'conditional_manufactured_not_material_admission')
    return m.DynamicSolidStorage(template=old.template, skeleton=skeleton, error_bounds=bounds,
        model_id='manufactured:dynamic-point', version='1', allow_manufactured=True)


def args(**changes):
    return dict(normal_stretch=.97, tangential_stretch=.99, liquid_mol=0.,
        gas_mol={'fixture': .01}, solid_mol={'fixture_solid': 2.}, external_pressure_pa=100000.) | changes


def mechanical_oracle(point, normal, tangent):
    with localcontext() as context:
        context.prec = 90
        n, t = D.from_float(normal), D.from_float(tangent)
        logs = (n.ln(), t.ln(), t.ln())
        theta = sum(logs)
        dev = [v-theta/3 for v in logs]
        sk = point.skeleton
        reference = sk.reference
        volume = D.from_float(reference.reference_area_m2)*D.from_float(reference.half_thickness_m)
        elastic = volume*(D.from_float(sk.bulk_modulus_pa)*theta**2/2+
                          D.from_float(sk.shear_modulus_pa)*sum(v*v for v in dev))
        interface = D.from_float(sk.interface_energy_j_m2)*D.from_float(sk.reference_interface_area_m2)*t*t
        return elastic+interface


def test_independent_volume_pressure_and_total_energy(water):
    point = build(water)
    state = point.forward(300., **args())
    ref = point.skeleton.reference
    exact_volume = F(ref.half_thickness_m)*F(ref.reference_area_m2)*F(.97)*F(.99)**2
    available = exact_volume-2*F(2e-5)
    assert abs(F(float(state.deformation.current.volumes_m3[0]))-exact_volume) <= F(state.current_bulk_error_bound_m3)
    expected_p = F(.01)*F(R)*300/available
    assert abs(F(state.thermal_state.mechanical.pressure_pa)-expected_p) <= F(state.thermal_state.pressure_error_bound_pa)
    thermal = 2*(F(-100000)+5*300-F(1e5)*F(2e-5))+F(.01)*(30-F(R))*300
    with localcontext() as context:
        context.prec = 90
        expected = D(thermal.numerator)/D(thermal.denominator)+mechanical_oracle(point, .97, .99)
        assert abs(D.from_float(state.total_energy_j)-expected) <= D.from_float(state.energy_error_bound_j)
    assert state.skeleton_state.normal_rate_per_s == state.skeleton_state.tangential_rate_per_s == 0
    assert any(rate != 0 for rate in state.free_rates.rates)
    assert state.free_rates.pore_pressure_pa == state.thermal_state.mechanical.pressure_pa
    assert state.free_rates.zero_balance_enclosed
    for field in ('elastic_energy_j', 'interface_energy_j'):
        assert getattr(state.skeleton_state, field) == getattr(state.free_rates.state, field)
    assert state.current_storage.bulk_volume_m3 == float(state.deformation.current.volumes_m3[0])


def test_inverse_and_actual_addition_subtraction_bounds(water):
    point = build(water)
    forward = point.forward(300., **args())
    target = point.target(forward.total_energy_j, forward.energy_error_bound_j)
    inverse = point.temperature_from_total_energy(target, temperature_bracket_k=(295., 310.),
        policy=InversePolicy(1e-6, 1e-6, 100), **args())
    assert abs(inverse.state.thermal_state.mechanical.temperature_k-300.) <= inverse.temperature_error_bound_k
    assert inverse.thermal_inverse.state is inverse.state.thermal_state
    exact = F(target.value_j)-F(forward.skeleton_state.elastic_energy_j)-F(forward.skeleton_state.interface_energy_j)
    assert abs(F(inverse.thermal_inverse.target_energy_j)-exact) <= F(inverse.subtraction_roundoff_j)
    exact_add = F(forward.thermal_state.internal_energy_j)+F(forward.skeleton_state.elastic_energy_j)+F(forward.skeleton_state.interface_energy_j)
    assert abs(F(forward.total_energy_j)-exact_add) <= F(forward.total_addition_roundoff_j)
    assert inverse.thermal_inverse.target_energy_error_bound_j >= target.error_bound_j+inverse.state.mechanical_energy_error_bound_j


def test_changed_stretch_at_fixed_energy_changes_temperature_by_independent_cv(water):
    point = build(water)
    initial = point.forward(300., **args(normal_stretch=1., tangential_stretch=1.))
    target = point.target(initial.total_energy_j, initial.energy_error_bound_j)
    inverse = point.temperature_from_total_energy(target, temperature_bracket_k=(295.,310.),
        policy=InversePolicy(1e-6,1e-6,100), **args())
    with localcontext() as context:
        context.prec = 90
        cv = D(10)+D.from_float(.01)*(D(30)-D.from_float(R))
        constant = D(2)*(D(-100000)-D.from_float(1e5)*D.from_float(2e-5))
        expected = (D.from_float(target.value_j)-constant-mechanical_oracle(point,.97,.99))/cv
        actual = D.from_float(inverse.state.thermal_state.mechanical.temperature_k)
        assert abs(actual-expected) <= D.from_float(inverse.temperature_error_bound_k)
    assert inverse.state.thermal_state.mechanical.temperature_k != 300.
    assert inverse.state.model_identity == initial.model_identity == point.identity


def test_pressure_is_decoded_before_free_rate_solver_and_no_second_inverse(water, monkeypatch):
    point = build(water)
    original = m.solve_free_rates
    original_thermal = m.SolidFluidStorage.temperature_from_energy
    events = []
    def inverse(*values, **kwargs):
        result = original_thermal(*values, **kwargs)
        events.append(('decoded', result.state.mechanical.pressure_pa))
        return result
    def free(*values, **kwargs):
        assert events and events[-1] == ('decoded', kwargs['pore_pressure_pa'])
        events.append(('free', kwargs['pore_pressure_pa']))
        return original(*values, **kwargs)
    forward = point.forward(300., **args())
    monkeypatch.setattr(m.SolidFluidStorage, 'temperature_from_energy', inverse)
    monkeypatch.setattr(m, 'solve_free_rates', free)
    point.temperature_from_total_energy(point.target(forward.total_energy_j,forward.energy_error_bound_j),
        temperature_bracket_k=(295.,310.), policy=InversePolicy(1e-6,1e-6,100), **args())
    assert [event[0] for event in events] == ['decoded','free']


def test_prescribed_point_parity_and_uncertainty_preserved(water):
    legacy = prescribed_fixture(water)
    point = build(water)
    old = legacy.forward(300., liquid_mol=0., gas_mol={'fixture':.01}, solid_mol={'fixture_solid':2.}, time_s=.5)
    state = point.forward(300., **args(normal_stretch=float(old.motion.normal_stretches[0]), tangential_stretch=old.motion.tangential_stretch))
    assert state.total_energy_j == old.total_energy_j
    assert state.energy_error_bound_j == old.energy_error_bound_j
    assert state.current_bulk_error_bound_m3 == old.current_bulk_error_bound_m3
    wider = replace(point, template=replace(point.template, bulk_volume_error_m3=1e-12))
    changed = wider.forward(300., **args())
    original = point.forward(300., **args())
    assert changed.current_bulk_error_bound_m3 > original.current_bulk_error_bound_m3
    assert changed.mechanical_energy_error_bound_j > original.mechanical_energy_error_bound_j
    uncertain = replace(point, error_bounds=replace(point.error_bounds,additional_mechanical_energy_error_j=.1))
    with pytest.raises(ValueError):
        uncertain.temperature_from_total_energy(uncertain.target(original.total_energy_j,0.),
            temperature_bracket_k=(295.,310.), policy=InversePolicy(1e-6,1e-6,100), **args())


@pytest.mark.parametrize('changes', [dict(solid_mol={}),dict(solid_mol={'fixture_solid':1.}),
    dict(normal_stretch=.49),dict(tangential_stretch=2.1),dict(external_pressure_pa=-1.),
    dict(normal_stretch=.5,tangential_stretch=.5)])
def test_inventory_pressure_stretch_and_pore_domains_reject(water, changes):
    with pytest.raises(ValueError):
        build(water).forward(300., **args(**changes))


def test_source_model_and_target_guards(water):
    point = build(water)
    with pytest.raises(ValueError):
        replace(point, allow_manufactured=False)
    with pytest.raises(ValueError):
        replace(point, skeleton=replace(point.skeleton, viscosity_pa_s=0.))
    with pytest.raises(ValueError):
        replace(point, skeleton=replace(point.skeleton, solid_provider_identity=('false',)))
    with pytest.raises(ValueError):
        replace(point, template=replace(point.template, bulk_volume_m3=2*point.template.bulk_volume_m3))
    for target in (point.target(-197000.,0.), replace(point.target(-197000.,0.),energy_scope='thermal')):
        wrong = replace(point, version='other')
        with pytest.raises(ValueError):
            wrong.temperature_from_total_energy(target,temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())
    old_phase = point.template.solid_phases['fixture_solid']
    object.__setattr__(point.template, 'solid_phases', {'fixture_solid': replace(old_phase,molar_volume_m3_mol=2.1e-5)})
    with pytest.raises(ValueError, match='runtime_template_identity_changed'):
        point.forward(300.,**args())


def test_immutable_geometry_and_original_rate_limit(water):
    point = build(water)
    state = point.forward(300.,**args())
    for array in state.deformation.current.__dict__.values():
        with pytest.raises(ValueError):
            array.setflags(write=True)
    fast = replace(point, skeleton=replace(point.skeleton,viscosity_pa_s=3.))
    with pytest.raises(ValueError, match='log_rate_out_of_domain'):
        fast.forward(300.,**args())


def test_single_cell_fixed_wrapper_and_explicit_error_domain(water):
    from sludge_sandbox.reacting_skeleton_energy import ManufacturedReactingSkeletonEnergy
    point = build(water)
    multiple = replace(point.skeleton, reference=replace(point.skeleton.reference,cells=2))
    with pytest.raises(ValueError, match='single_cell'):
        replace(point,skeleton=multiple)
    reacting = ManufacturedReactingSkeletonEnergy(
        reference_model=point.skeleton, composition_offset=1.,
        composition_weights_per_mol=(('fixture_solid', 0.),),
        model_id='manufactured-reacting', version='1',
        classification='manufactured_test_fixture', allow_manufactured=True)
    with pytest.raises(ValueError, match='explicit_dynamic_storage'):
        replace(point,skeleton=reacting)
    bounded = replace(point,error_bounds=replace(point.error_bounds,normal_stretch_range=(.98,1.1)))
    with pytest.raises(ValueError, match='outside_error_domain'):
        bounded.forward(300.,**args())
    with pytest.raises(ValueError, match='matching_explicit_total_energy_target'):
        point.temperature_from_total_energy(replace(point.target(-197000.,0.),energy_scope='thermal'),
            temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100),**args())
