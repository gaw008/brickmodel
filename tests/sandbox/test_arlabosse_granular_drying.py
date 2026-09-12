"""Manufactured thermal seam; no publication images or water EOS required."""
from decimal import Decimal, localcontext
import json
import math
from types import SimpleNamespace

import pytest

from sludge_sandbox import arlabosse_granular_drying as model


class Point:
    def __init__(self, t, w):
        self.temperature_k = t
        self.specific_enthalpy_j_kg_dry = (1000*(t-300) + w*(2000*(t-300)-1e6)
                                          + .5e5*(w-.8)**2)
        self.total_desorption_heat_j_kg_water = 2e5-1e5*(w-.8)
        self.model_equilibrium_vapor_pressure_pa = 10000*w

    def to_record(self):
        return vars(self).copy()


class Thermal:
    def __init__(self, *args):
        self.calls = 0

    def definition(self):
        return {'classification': 'manufactured_test_fixture'}

    def evaluate(self, t, w):
        return Point(t, w)

    def isothermal_drying_heat(self, t, wi, wf, dry_mass_kg):
        mass = dry_mass_kg*(wi-wf)
        q = dry_mass_kg*(2.8e5*(wi-wf)-.5e5*(wi**2-wf**2))
        return SimpleNamespace(heat_j=q, removed_water_kg=mass,
                               vapor_carried_enthalpy_j=mass*(2000*(t-300)-8e5))

    def inverse_enthalpy(self, target_j, *, dry_mass_kg, moisture, **kwargs):
        w = moisture
        t = 300+(target_j/dry_mass_kg+1e6*w-.5e5*(w-.8)**2)/(1000+2000*w)
        state = Point(t, w)
        return SimpleNamespace(state=state, residual_j=dry_mass_kg*state.specific_enthalpy_j_kg_dry-target_j,
                               to_record=lambda: {'state': state.to_record()})


@pytest.fixture
def setup(monkeypatch):
    source = {'parameters': {'a': {'value': '34.38'}, 'b': {'value': '4.58'}},
              'classification': 'manufactured_test_fixture'}
    monkeypatch.setattr(model, '_load_source', lambda root: json.loads(json.dumps(source)))
    monkeypatch.setattr(model, 'ArlabosseWetThermodynamics', Thermal)
    return dict(dry_mass_kg=.1, contact_area_m2=.02, temperature_k=358.15,
                ambient_vapor_pressure_pa=500., initial_moisture=.32,
                final_moisture=.15, intervals=8, wall_seconds=10.)


def run(args, **overrides):
    return model.run_isothermal_drying('manufactured-root', 'manufactured-water',
                                       **(args | overrides))


def test_time_mass_and_heat_have_independent_oracles(setup):
    result = run(setup)
    assert result['status'] == 'completed'
    rows = result['observations']
    assert len(rows) == 9
    with localcontext() as ctx:
        ctx.prec = 60
        a, b = Decimal('34.38'), Decimal('4.58')
        for row in rows:
            w = Decimal(str(row['moisture_kg_water_kg_dry']))
            time = Decimal(3600)*Decimal('.1')/(Decimal('.02')*a)*(
                (a*Decimal('.32')+b)/(a*w+b)).ln()
            assert row['time_s'] == pytest.approx(float(time), abs=1e-12)
            analytic_w = (Decimal('.32')+b/a)*(-a*Decimal('.02')*Decimal(str(row['time_s']))/
                                               (Decimal(3600)*Decimal('.1'))).exp()-b/a
            assert float(analytic_w) == pytest.approx(float(w), abs=1e-15)
            dw = .32-float(w)
            assert row['cumulative_water_out_kg'] == pytest.approx(.1*dw, abs=1e-17)
            independent_q = .1*(2.8e5*dw-.5e5*(.32**2-float(w)**2))
            assert row['cumulative_net_heat_j'] == pytest.approx(independent_q, abs=1e-10)
            assert row['inverse']['state']['temperature_k'] == pytest.approx(358.15, abs=2e-12)
            assert abs(row['open_energy_residual_j']) < 1e-9
            assert abs(row['water_balance_residual_kg']) < 1e-16
    assert rows[-1]['cumulative_vapor_enthalpy_j'] < 0
    assert all(b['time_s'] > a['time_s'] for a, b in zip(rows, rows[1:]))
    assert result['full_firing_cycle'] is False
    assert result['rate_condition_transfer_model_error'] is None


def test_area_and_mass_scaling_do_not_change_required_specific_heat(setup):
    original = run(setup)['observations'][-1]
    larger_area = run(setup, contact_area_m2=.04)['observations'][-1]
    larger_mass = run(setup, dry_mass_kg=.2)['observations'][-1]
    assert larger_area['time_s'] == original['time_s']/2
    assert larger_area['cumulative_net_heat_j'] == original['cumulative_net_heat_j']
    assert larger_mass['time_s'] == original['time_s']*2
    assert larger_mass['cumulative_net_heat_j'] == original['cumulative_net_heat_j']*2


def test_observation_sampling_is_not_a_time_solver_policy(setup):
    coarse = run(setup, intervals=2)['observations'][-1]
    fine = run(setup, intervals=13)['observations'][-1]
    assert coarse['time_s'] == fine['time_s']
    assert coarse['cumulative_net_heat_j'] == pytest.approx(fine['cumulative_net_heat_j'], abs=1e-10)


@pytest.mark.parametrize('key,value', [('dry_mass_kg', 0), ('contact_area_m2', -1),
    ('temperature_k', 400), ('initial_moisture', .33), ('final_moisture', .1),
    ('initial_moisture', .15), ('intervals', True), ('intervals', 129),
    ('wall_seconds', float('inf')), ('ambient_vapor_pressure_pa', -1),
    ('contact_area_m2', float('nan')), ('dry_mass_kg', '0.1')])
def test_invalid_inputs_rejected_before_source_or_eos(setup, monkeypatch, key, value):
    monkeypatch.setattr(model, '_load_source', lambda root: pytest.fail('source read before validation'))
    with pytest.raises(ValueError):
        run(setup, **{key: value})


def test_saturated_environment_cannot_generate_unqualified_evaporation(setup):
    result = run(setup, ambient_vapor_pressure_pa=1500.)
    assert result['status'] == 'failed'
    assert 'vapor_boundary' in result['reason']
    assert result['observations'] == []


def test_cancellation_retains_accepted_prefix(setup):
    calls = iter([False, False, False, True])
    result = run(setup, cancel=lambda: next(calls))
    assert result['status'] == 'cancelled'
    assert 0 < len(result['observations']) < 9
    assert result['observations'][0]['time_s'] == 0


def test_source_failure_is_not_a_completed_run(setup, monkeypatch):
    def fail(root):
        raise ValueError('source_asset_changed')
    monkeypatch.setattr(model, '_load_source', fail)
    result = run(setup)
    assert result['status'] == 'failed' and result['reason'] == 'source_asset_changed'
    assert result['observations'] == []


def test_inverse_failure_keeps_prefix_and_pending_energy(setup, monkeypatch):
    original = Thermal.inverse_enthalpy
    def fail_second(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 2:
            raise ValueError('manufactured_inverse_failure')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Thermal, 'inverse_enthalpy', fail_second)
    result = run(setup)
    assert result['status'] == 'failed'
    assert len(result['observations']) == 1
    pending = result['pending_observation']
    assert pending['index'] == 1 and pending['step_heat_j'] > 0
    assert pending['step_vapor_enthalpy_j'] < 0
    assert 'inverse' not in pending


def test_deadline_retains_computed_prefix(setup, monkeypatch):
    values = iter([0., 0., 0., .5, 11., 11.])
    monkeypatch.setattr(model.time, 'monotonic', lambda: next(values))
    result = run(setup)
    assert result['status'] == 'time_budget_exceeded'
    assert len(result['observations']) == 2
    assert result['elapsed_seconds'] == 11.


def test_law_uses_intercept_and_source_domain(setup):
    law = model.ArlabosseGranularFlux('manufactured-root')
    assert law.flux_kg_water_m2_h(.2) == pytest.approx(11.456)
    t = law.elapsed_seconds(.32, .2, dry_mass_kg=.1, contact_area_m2=.02)
    omitted_b = 3600*.1/(.02*34.38)*math.log(.32/.2)
    assert abs(t-omitted_b) > 1
    with pytest.raises(ValueError):
        law.flux_kg_water_m2_h(.4)


def test_clock_avoids_representable_ratio_intermediate_overflow(setup):
    law = model.ArlabosseGranularFlux('manufactured-root')
    normal = law.elapsed_seconds(.32, .15, dry_mass_kg=1., contact_area_m2=1.)
    extreme = law.elapsed_seconds(.32, .15, dry_mass_kg=1e308, contact_area_m2=1e308)
    assert extreme == normal


@pytest.mark.parametrize('mass,area', [(1e-323, 1e-323), (.1, 1e-323)])
def test_unrepresentable_positive_flows_or_inventory_cannot_complete(setup, mass, area):
    result = run(setup, dry_mass_kg=mass, contact_area_m2=area, intervals=1)
    assert result['status'] == 'failed'
    assert not any(row['water_out_kg_s'] == 0 for row in result['observations'])


def test_positive_subnormal_inventory_cannot_hide_temperature_error(setup):
    result = run(setup, dry_mass_kg=1e-320, intervals=1)
    assert result['status'] == 'failed'
    assert result['reason'] == 'numerical_gate_isothermal_temperature'
    candidate = result['pending_observation']
    assert abs(candidate['recovered_temperature_difference_k']) > result['numerical_policy']['temperature_tolerance_k']


def test_acceptance_policy_is_explicit_and_cannot_be_nonfinite(setup):
    result = run(setup, temperature_tolerance_k=2e-6, energy_tolerance_j=1e-6,
                 water_tolerance_kg=1e-13)
    assert result['status'] == 'completed'
    assert result['numerical_policy']['temperature_tolerance_k'] == 2e-6
    with pytest.raises(ValueError):
        run(setup, temperature_tolerance_k=float('inf'))
