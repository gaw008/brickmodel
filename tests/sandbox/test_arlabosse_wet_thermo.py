"""Manufactured provider/source seams test algebra, not actual-source validation.

No water EOS is loaded or executed in this file. The public constructor has no
provider injection; monkeypatches below are explicitly test-only replacements.
"""
from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction
import json
import math
from types import SimpleNamespace

import pytest

import sludge_sandbox.arlabosse_wet_thermo as wet
from sludge_sandbox.arlabosse_desorption95 import DesorptionPoint, SourceReading
from sludge_sandbox.water_properties import WaterReference

T0 = wet.T_REF
M = .01801528
R = 8.31446261815324
RS = R/M
CP_L, CP_V = 4200., 2000.
H_L0, S_L0, S_V0 = -14_000_000., 1000., 8000.
LATENT0 = 2_300_000.


class ManufacturedDry:
    def __init__(self, *args):
        pass

    def _source(self):
        return {}

    def cp(self, t, *, unit):
        assert unit == 'K'
        return SimpleNamespace(value=1434+3.29*(t-273.15))

    def delta_h(self, a, b, *, unit):
        assert unit == 'K'
        return SimpleNamespace(value=(1434-3.29*273.15)*(b-a)+3.29/2*(b*b-a*a))


class ManufacturedDesorption:
    def __init__(self, *args):
        pass

    def _load(self):
        return {}, {}, Fraction(str(R))

    def at_moisture(self, w, *, temperature, unit):
        assert temperature == T0 and unit == 'K'
        aw = Fraction(str(math.exp(-.9*(1-w))))
        q = Fraction(str(2_700_000.-400_000.*w)) if w in wet._Q_NODES else None
        activity = SourceReading(aw, (aw*Fraction(99, 100), aw*Fraction(101, 100)),
                                 '1', 'MANUFACTURED_AW', 'test equation only')
        heat = SourceReading(q, (q-1000, q+1000) if q else None,
                             'J/kg removed water', 'MANUFACTURED_Q', 'test equation only',
                             () if q else ('manufactured_missing_reading',))
        shift = SourceReading(None, None, 'J/mol', 'MANUFACTURED_MU', 'not evaluated')
        return DesorptionPoint(Fraction(str(w)), Fraction(str(T0)), activity, heat, shift)


class ManufacturedChemical:
    reference_pressure_pa = 1e5
    gas_constant_j_mol_k = R
    source_ids = ('MANUFACTURED_WATER_NOT_EVIDENCE',)
    source_asset_sha256 = {}
    method_id = 'manufactured_chemical'
    caloric_method_id = 'manufactured_caloric'

    def __init__(self, directory, *, h_shift=0., s_shift=0.):
        self.h_shift, self.s_shift = h_shift, s_shift
        self.reference = WaterReference(M, RS, R, h_shift*M, T0, 0.)

    def _check_identity(self):
        pass

    def _liquid(self, t):
        h = H_L0+CP_L*(t-T0)+self.h_shift
        s = S_L0+CP_L*math.log(t/T0)+self.s_shift
        return SimpleNamespace(enthalpy_j_mol=h*M, entropy_j_mol_k=s*M,
                               chemical_potential_j_mol=(h-t*s)*M,
                               state=SimpleNamespace(cp_j_kg_k=CP_L))

    def ideal_vapor(self, t, p):
        h = H_L0+LATENT0+CP_V*(t-T0)+self.h_shift
        s = S_V0+CP_V*math.log(t/T0)-RS*math.log(p/1e5)+self.s_shift
        return SimpleNamespace(enthalpy_j_mol=h*M, entropy_j_mol_k=s*M,
                               chemical_potential_j_mol=(h-t*s)*M)

    def equilibrium_at_liquid_tp(self, t, p):
        assert p == 1e5
        liquid = self._liquid(t)
        standard = self.ideal_vapor(t, 1e5)
        pressure = 1e5*math.exp((liquid.chemical_potential_j_mol-
                                standard.chemical_potential_j_mol)/(R*t))
        vapor = self.ideal_vapor(t, pressure)
        return SimpleNamespace(liquid=liquid, vapor=vapor,
                               equilibrium_partial_pressure_pa=pressure)


@pytest.fixture
def factory(monkeypatch, tmp_path):
    monkeypatch.setattr(wet, 'ArlabosseDryCaloric', ManufacturedDry)
    monkeypatch.setattr(wet, 'ArlabosseDesorption95', ManufacturedDesorption)
    monkeypatch.setattr(wet, '_verify_sources', lambda _: None)
    monkeypatch.setattr(wet.ArlabosseWetThermodynamics, '_model_definition',
                        lambda _: {'manufactured_test_only': True})

    def make(h_shift=0., s_shift=0.):
        monkeypatch.setattr(wet, 'WaterChemicalPotential',
                            lambda directory: ManufacturedChemical(directory, h_shift=h_shift, s_shift=s_shift))
        return wet.ArlabosseWetThermodynamics(tmp_path, tmp_path/'water')
    return make


@pytest.fixture
def model(factory):
    return factory()


def test_gibbs_enthalpy_entropy_and_cp_cross_derivatives(model):
    t, w, dt, dw = 342., .355, .01, 1e-5
    x = model.evaluate(t, w)
    tm, tp = model.evaluate(t-dt, w), model.evaluate(t+dt, w)
    wm, wp = model.evaluate(t, w-dw), model.evaluate(t, w+dw)
    assert x.specific_gibbs_j_kg_dry == pytest.approx(
        x.specific_enthalpy_j_kg_dry-t*x.specific_entropy_j_kg_dry_k, abs=1e-8)
    assert (tp.specific_enthalpy_j_kg_dry-tm.specific_enthalpy_j_kg_dry)/(2*dt) == pytest.approx(
        x.heat_capacity_j_kg_dry_k, abs=1e-6)
    assert (tp.specific_gibbs_j_kg_dry-tm.specific_gibbs_j_kg_dry)/(2*dt) == pytest.approx(
        -x.specific_entropy_j_kg_dry_k, abs=2e-6)
    assert (wp.specific_gibbs_j_kg_dry-wm.specific_gibbs_j_kg_dry)/(2*dw) == pytest.approx(
        x.water_chemical_potential_j_kg_water, abs=1e-4)
    assert (wp.specific_enthalpy_j_kg_dry-wm.specific_enthalpy_j_kg_dry)/(2*dw) == pytest.approx(
        x.partial_water_enthalpy_j_kg_water, abs=1e-4)
    # Five-point derivative removes the O(dt**2) caloric-entropy truncation
    # visible in the first retained RED run; the acceptance bound is unchanged.
    step = .1
    mu = lambda delta: model.evaluate(t+delta, w).water_chemical_potential_j_kg_water
    dmu_dt = (-mu(2*step)+8*mu(step)-8*mu(-step)+mu(-2*step))/(12*step)
    assert x.water_chemical_potential_j_kg_water-t*dmu_dt == pytest.approx(
        x.partial_water_enthalpy_j_kg_water, abs=1e-4)
    assert (tp.total_desorption_heat_j_kg_water-tm.total_desorption_heat_j_kg_water)/(2*dt) == pytest.approx(CP_V-CP_L, abs=1e-6)
    assert x.heat_capacity_j_kg_wet_k*(1+w) == x.heat_capacity_j_kg_dry_k


@pytest.mark.parametrize('w', wet._W_NODES)
def test_source_knots_and_missing_readings_remain_separate(model, w):
    x = model.evaluate(T0, w)
    assert x.activity == pytest.approx(math.exp(-.9*(1-w)), rel=2e-15)
    assert x.model_q95_j_kg_water == pytest.approx(2_700_000.-400_000.*w, abs=1e-8)
    assert x.total_desorption_heat_j_kg_water == x.model_q95_j_kg_water
    reading = x.source_readings_at_moisture['total_desorption_heat']
    if w in (.5, .6):
        assert reading['value'] is None
        assert reading['unknown_reasons'] == ['manufactured_missing_reading']
    else:
        assert reading['value'] is not None
    assert x.interpolation_model_error is None
    assert x.experimental_uncertainty is None
    assert not x.material_qualified and not x.training_eligible and not x.full_firing_cycle
    assert x.activity_readout_only_bounds[0] < x.activity < x.activity_readout_only_bounds[1]


def test_log_interpolation_not_linear_activity(model):
    w = .35
    x = model.evaluate(T0, w)
    assert x.activity == pytest.approx(math.exp(-.9*(1-w)), rel=2e-15)
    arithmetic = (math.exp(-.9*.7)+math.exp(-.9*.6))/2
    assert abs(x.activity-arithmetic) > 1e-5
    assert x.source_readings_at_moisture is None


@pytest.mark.parametrize('w', wet._W_NODES[1:-1])
def test_knot_continuity_and_one_sided_composition_derivatives(model, w):
    # Unequal neighbouring slopes force the implementation to retain both sides.
    values = tuple(y+500*(i*i) for i, y in enumerate(model._m.y))
    object.__setattr__(model, '_m', wet._Linear(wet._W_NODES, values))
    t, eps = 335., 1e-8
    x, a, b = model.evaluate(t, w), model.evaluate(t, w-eps), model.evaluate(t, w+eps)
    assert abs(a.specific_enthalpy_j_kg_dry-b.specific_enthalpy_j_kg_dry) < 1.
    assert (x.water_chemical_potential_j_kg_water-a.water_chemical_potential_j_kg_water)/eps == pytest.approx(
        x.composition_derivative_left_j_kg_water, rel=2e-6, abs=.3)
    assert (b.water_chemical_potential_j_kg_water-x.water_chemical_potential_j_kg_water)/eps == pytest.approx(
        x.composition_derivative_right_j_kg_water, rel=2e-6, abs=.3)


def test_reference_moisture_is_only_integral_anchor(model):
    x = model.evaluate(T0, .8)
    assert x.specific_enthalpy_j_kg_dry == pytest.approx(.8*H_L0, abs=1e-8)
    assert x.specific_entropy_j_kg_dry_k == pytest.approx(.8*S_L0, abs=1e-8)
    assert x.activity < 1
    assert x.partial_water_enthalpy_j_kg_water != x.liquid_enthalpy_j_kg_water
    assert x.composition_derivative_right_j_kg_water is None
    assert model.evaluate(T0, .15).composition_derivative_left_j_kg_water is None


def test_common_water_h_s_reference_shifts_leave_heat_and_activity_unchanged(factory):
    original, shifted = factory(), factory(h_shift=4_000_000., s_shift=1500.)
    for t, w in [(320., .25), (T0, .75)]:
        a, b = original.evaluate(t, w), shifted.evaluate(t, w)
        assert b.specific_enthalpy_j_kg_dry-a.specific_enthalpy_j_kg_dry == pytest.approx(w*4e6, abs=1e-8)
        assert b.specific_entropy_j_kg_dry_k-a.specific_entropy_j_kg_dry_k == pytest.approx(w*1500, abs=1e-8)
        assert b.water_chemical_potential_j_kg_water-a.water_chemical_potential_j_kg_water == pytest.approx(4e6-t*1500, abs=1e-8)
        assert b.activity == pytest.approx(a.activity, rel=2e-14)
        assert b.model_equilibrium_vapor_pressure_pa == pytest.approx(a.model_equilibrium_vapor_pressure_pa, rel=2e-14)
        assert b.total_desorption_heat_j_kg_water == pytest.approx(a.total_desorption_heat_j_kg_water, abs=1e-8)
    a, b = original.isothermal_drying_heat(340., .75, .25), shifted.isothermal_drying_heat(340., .75, .25)
    assert a.heat_j == pytest.approx(b.heat_j, abs=1e-8)
    assert abs(a.energy_identity_residual_j) < 1e-8
    assert abs(b.energy_identity_residual_j) < 1e-8


def test_isothermal_heat_analytic_oracle_and_latent_double_count_negative_control(model):
    t, a, b, md = 339., .75, .25, .1
    result = model.isothermal_drying_heat(t, a, b, md)
    expected = md*((CP_V-CP_L)*(t-T0)*(a-b)+2_700_000.*(a-b)-200_000.*(a*a-b*b))
    assert result.heat_j == pytest.approx(expected, abs=1e-8)
    assert abs(result.energy_identity_residual_j) < 1e-8
    assert result.removed_water_kg == pytest.approx(.05)
    assert result.vapor_carried_enthalpy_j < 0  # Shared formation reference; never abs().
    extra_latent = result.removed_water_kg*(LATENT0+(CP_V-CP_L)*(t-T0))
    assert abs((result.heat_j+extra_latent)-result.material_enthalpy_change_j-result.vapor_carried_enthalpy_j) > 100_000
    assert result.heat_readout_only_bounds_j[0] <= result.heat_j <= result.heat_readout_only_bounds_j[1]
    assert 'not_total_uncertainty' in result.bounds_scope


def test_piecewise_q_integral_respects_breaks(model):
    y = (2.7e6, 2.6e6, 2.5e6, 2.45e6, 2.4e6, 2.35e6)
    object.__setattr__(model, '_q', wet._Linear(wet._Q_NODES, y))
    result = model.isothermal_drying_heat(T0, .75, .25)
    expected = .05*(2.55e6+2.5e6)/2 + .1*(2.5e6+2.45e6)/2 + .3*(2.45e6+2.4e6)/2 + .05*(2.4e6+2.375e6)/2
    assert result.heat_j == pytest.approx(expected, abs=1e-8)
    assert abs(result.energy_identity_residual_j) < 1e-8


@pytest.mark.parametrize('t', [308.15, 319.7, 341.32, T0])
def test_inverse_independent_analytic_enthalpy_oracle(model, t):
    w, md = .35, .2
    # Manufactured m0 does not enter H. Integrate b0=-400000+400000W.
    excess = -400000*(w-.8)+200000*(w*w-.8*.8)
    dry = (1434-3.29*273.15)*(t-T0)+3.29/2*(t*t-T0*T0)
    target = md*(dry+w*(H_L0+CP_L*(t-T0))+excess)
    out = model.inverse_enthalpy(target, dry_mass_kg=md, moisture=w)
    assert out.state.temperature_k == pytest.approx(t, abs=1e-7)
    assert abs(out.residual_j) <= out.residual_tolerance_j
    assert out.bracket_width_k <= out.temperature_tolerance_k
    assert 0 <= out.iterations <= out.maximum_iterations


@pytest.mark.parametrize('endpoint,direction', [(wet.T_MIN, -math.inf), (T0, math.inf)])
def test_inverse_endpoint_slack_is_explicit_and_bounded(model, endpoint, direction):
    target = model.evaluate(endpoint, .3).specific_enthalpy_j_kg_dry
    adjacent = math.nextafter(target, direction)
    out = model.inverse_enthalpy(adjacent, dry_mass_kg=1., moisture=.3)
    assert out.convergence == 'binary64_endpoint_roundoff'
    assert out.target_outside_nominal_endpoint_range
    assert out.residual_j == target-adjacent != 0
    assert abs(out.residual_j) <= out.endpoint_roundoff_allowance_j
    far = target + (100*math.ulp(target) if direction > 0 else -100*math.ulp(target))
    with pytest.raises(wet.WetThermodynamicError, match='outside_declared_temperature_domain'):
        model.inverse_enthalpy(far, dry_mass_kg=1., moisture=.3)


def test_inverse_exhaustion_refuses_and_preserves_diagnostics(model):
    target = model.evaluate(314.3, .3).specific_enthalpy_j_kg_dry
    with pytest.raises(wet.WetThermodynamicError, match='budget_exhausted.*residual_j=.*bracket_k='):
        model.inverse_enthalpy(target, dry_mass_kg=1., moisture=.3, maximum_iterations=1)


@pytest.mark.parametrize('kwargs', [
    {'maximum_iterations': True}, {'maximum_iterations': 0}, {'maximum_iterations': 513},
    {'maximum_iterations': 2.}, {'temperature_tolerance_k': 0},
    {'temperature_tolerance_k': 1e-14}, {'temperature_tolerance_k': math.nan},
    {'dry_mass_kg': 0}, {'dry_mass_kg': math.inf}, {'dry_mass_kg': True},
])
def test_inverse_invalid_controls(model, kwargs):
    options = {'dry_mass_kg': 1., 'moisture': .3, **kwargs}
    with pytest.raises(wet.WetThermodynamicError):
        model.inverse_enthalpy(-4e6, **options)


@pytest.mark.parametrize('t,w', [
    (True, .3), ('340', .3), (math.nan, .3), (math.inf, .3), (308.14, .3),
    (368.16, .3), (340., .14999), (340., .8001), (340., False), (340., math.nan),
    (Decimal('308.149999999999999999999999999'), .3),
    (340., Decimal('0.8000000000000000000000000001')),
])
def test_inputs_reject_without_clipping(model, t, w):
    with pytest.raises(wet.WetThermodynamicError):
        model.evaluate(t, w)


def test_decimal_fraction_and_zero_path(model):
    x = model.evaluate(Decimal('340'), Fraction(3, 10))
    assert x.temperature_k == 340 and x.moisture_kg_water_per_kg_dry == .3
    path = model.isothermal_drying_heat(340., .3, .3)
    assert path.heat_j == path.removed_water_kg == path.energy_identity_residual_j == 0
    with pytest.raises(wet.WetThermodynamicError, match='nonincreasing'):
        model.isothermal_drying_heat(340., .3, .4)


def test_instability_and_activity_above_one_refuse_without_clipping(model):
    object.__setattr__(model, '_m', wet._Linear(wet._W_NODES, tuple(-1000-i*100 for i in range(8))))
    with pytest.raises(wet.WetThermodynamicError, match='composition_instability'):
        model.evaluate(T0, .3)
    object.__setattr__(model, '_m', wet._Linear(wet._W_NODES, tuple(1000+i*100 for i in range(8))))
    with pytest.raises(wet.WetThermodynamicError, match='activity_above_one'):
        model.evaluate(T0, .3)


def test_equilibrium_molar_units_and_negative_control(model):
    x = model.evaluate(335., .35)
    vapor = model._chemical.ideal_vapor(x.temperature_k, x.model_equilibrium_vapor_pressure_pa)
    assert x.water_chemical_potential_j_mol == pytest.approx(vapor.chemical_potential_j_mol, abs=1e-8)
    assert x.water_chemical_potential_j_kg_water*M == x.water_chemical_potential_j_mol
    assert abs(x.water_chemical_potential_j_kg_water-vapor.chemical_potential_j_mol) > 1e6
    assert x.model_equilibrium_vapor_pressure_pa == x.pure_model_equilibrium_vapor_pressure_pa*x.activity


def test_source_failure_rechecked_and_no_mutable_definition_leak(model, monkeypatch):
    d = model.definition()
    d['source_point_records'][0]['activity']['value'] = None
    assert model.definition()['source_point_records'][0]['activity']['value'] is not None
    x = model.evaluate(340., .3)
    with pytest.raises(FrozenInstanceError):
        x.activity = 1.
    json.dumps(x.to_record(), allow_nan=False)
    json.dumps(model.definition(), allow_nan=False)
    def fail(_):
        raise wet.WetThermodynamicError('changed_source')
    monkeypatch.setattr(wet, '_verify_sources', fail)
    for operation in (lambda: model.evaluate(340., .3), model.definition,
                      lambda: model.inverse_enthalpy(-4e6, dry_mass_kg=1., moisture=.3),
                      lambda: model.isothermal_drying_heat(340., .4, .3)):
        with pytest.raises(wet.WetThermodynamicError, match='changed_source'):
            operation()


def test_constructor_rejects_missing_metadata_without_loading_water(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('water constructor reached before model source admission')
    monkeypatch.setattr(wet, 'WaterChemicalPotential', forbidden)
    with pytest.raises(wet.WetThermodynamicError, match='asset_unavailable'):
        wet.ArlabosseWetThermodynamics(tmp_path, tmp_path)
    target = tmp_path/wet.MODEL_PATH
    target.parent.mkdir(parents=True)
    target.write_text('{}')
    with pytest.raises(wet.WetThermodynamicError, match='metadata_changed'):
        wet.ArlabosseWetThermodynamics(tmp_path, tmp_path)
    with pytest.raises(TypeError):
        wet.ArlabosseWetThermodynamics(tmp_path, tmp_path, water_provider=object())


def test_source_assets_metadata_digest_checked_before_water(tmp_path, monkeypatch):
    # Only byte identity failure is tested; this is not a valid source load.
    repository = __import__('pathlib').Path(__file__).resolve().parents[2]
    target = tmp_path/wet.MODEL_PATH
    target.parent.mkdir(parents=True)
    raw = (repository/wet.MODEL_PATH).read_bytes()
    target.write_bytes(raw)
    definition = json.loads(raw)
    first = tmp_path/definition['upstream'][0]['path']
    first.parent.mkdir(parents=True)
    first.write_bytes(b'changed reviewed source')
    def forbidden(*args, **kwargs):
        pytest.fail('water reached before upstream metadata hash check')
    monkeypatch.setattr(wet, 'WaterChemicalPotential', forbidden)
    with pytest.raises(wet.WetThermodynamicError, match='wet_model_asset_changed'):
        wet.ArlabosseWetThermodynamics(tmp_path, tmp_path)


def test_dry_mass_scaling_and_json_records(model):
    a = model.isothermal_drying_heat(340., .7, .2, .1)
    b = model.isothermal_drying_heat(340., .7, .2, .4)
    assert b.heat_j == 4*a.heat_j
    assert b.vapor_carried_enthalpy_j == 4*a.vapor_carried_enthalpy_j
    assert b.material_enthalpy_change_j == 4*a.material_enthalpy_change_j
    target = .1*model.evaluate(337., .4).specific_enthalpy_j_kg_dry
    inverse = model.inverse_enthalpy(target, dry_mass_kg=.1, moisture=.4)
    json.dumps(inverse.to_record(), allow_nan=False)
    json.dumps(a.to_record(), allow_nan=False)
