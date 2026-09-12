"""Analytic manufactured callback tests; no source material or EOS validation."""
from dataclasses import replace
from fractions import Fraction as F
import math
from types import SimpleNamespace as NS

import pytest

import sludge_sandbox.low_moisture_equilibrium as module
from sludge_sandbox.arlabosse_low_moisture_storage import (
    LowMoistureSorptionPoint, LowMoistureSorptionStorage,
)
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential


@pytest.fixture
def analytic(monkeypatch):
    """Actual class identities, explicitly replaced analytic property callbacks.

    No source admission is tested: checks that would validate real files and
    actual water bindings are replaced only inside this manufactured fixture.
    """
    r, v, volume, nt = 8.31446261815324, 1e-5, .001, F(1, 64)
    controls = NS(k=10000., pure=1000., energy_error=0., pressure_error=.01, shift=0.,
        source_ok=True, hole=None, calls=[], pressure_calls=[], budget_clock=0.)
    storage = object.__new__(LowMoistureSorptionStorage)
    chemical = object.__new__(WaterChemicalPotential)
    water = NS(reference=NS(molar_mass_kg_mol=.02))
    base = NS(dry_mass_kg=.01, temperature_domain_k=(325., 338.),
        volume=NS(value_m3=volume, error_m3=0.),
        fluid_template=NS(envelope=NS(liquid_v_error_m3_mol=0.)), water=water,
        gas_ids=('O2', 'N2', 'H2O'))
    object.__setattr__(storage, 'base', base)
    object.__setattr__(storage, 'wet', NS(_mass=.02))
    object.__setattr__(storage, 'pressure_domain_pa', (90000., 110000.))
    object.__setattr__(storage, '_identity', 'a'*64)
    object.__setattr__(chemical, 'water', water)
    object.__setattr__(chemical, 'vapor', NS(gas_constant_j_mol_k=r,
        source_ids=('manufactured:flash-chemical',)))

    def check(self):
        if not controls.source_ok:
            raise ValueError('manufactured_source_changed')
    monkeypatch.setattr(LowMoistureSorptionStorage, '_check', check)
    monkeypatch.setattr(LowMoistureSorptionStorage, 'source_ids',
        property(lambda self: ('manufactured:flash-storage',)))
    monkeypatch.setattr(WaterChemicalPotential, '_check_identity', lambda self: None)
    monkeypatch.setattr(module, 'check_thermal_chemical_sources', lambda *args: None)
    monkeypatch.setattr(module, 'check_low_moisture_point', lambda *args: None)

    def state(self, nc, gas, energy):
        check(self)
        return WetMixedState((.01,), float(nc), tuple(map(float, gas)),
            float(energy), self._identity)
    monkeypatch.setattr(LowMoistureSorptionStorage, 'state', state)

    def evaluate(self, st, t):
        controls.calls.append((t, st))
        check(self)
        if controls.hole is not None and controls.hole(t):
            raise ValueError('manufactured_domain_hole')
        nc, nv = st.liquid_water_mol, st.gas_amounts_mol[2]
        gas_volume = volume-nc*v
        pressure = math.fsum(st.gas_amounts_mol)*r*t/gas_volume
        if not 90000 <= pressure-controls.pressure_error <= pressure+controls.pressure_error <= 110000:
            raise ValueError('manufactured_pressure_domain_exit')
        energy = 300.*(t-330.)+10000.*nv+controls.shift*float(F(nc)+F(nv))
        mechanical = NS(temperature_k=t, pressure_pa=pressure,
            liquid_pressure_pa=pressure if nc else None, liquid_inventory_mol=nc,
            gas_inventory_mol=dict(zip(('O2', 'N2', 'H2O'), st.gas_amounts_mol)),
            gas_volume_m3=gas_volume, liquid_volume_m3=nc*v,
            pressure_bracket_pa=(90000., 110000.),
            final_numerical_pressure_bracket_pa=(pressure-.001, pressure+.001))
        activity = controls.k*nc/1000.
        excess = NS(activity=activity, mu_ex_j_mol=r*t*math.log(activity) if nc else None)
        return LowMoistureSorptionPoint(fluid=NS(mechanical=mechanical),
            total_internal_energy_j=energy, solid_internal_energy_j=F(0),
            available_pore_volume_m3=volume, available_volume_error_m3=0.,
            global_pressure_error_pa=controls.pressure_error, extra_pressure_error_pa=0.,
            pressure_error_pa=controls.pressure_error, energy_error_j=controls.energy_error,
            closed_heat_capacity_j_k=300., minimum_heat_capacity_j_k=300.,
            model_identity=self._identity, source_ids=self.source_ids,
            excess=excess, excess_internal_energy_j=F(0), excess_entropy_j_k=F(0),
            excess_helmholtz_energy_j=F(0))
    monkeypatch.setattr(LowMoistureSorptionStorage, 'evaluate', evaluate)

    def liquid(self, t, p):
        controls.pressure_calls.append((t, p))
        assert 90000 <= p <= 110000
        state = NS(temperature_k=t, pressure_pa=p, molar_mass_kg_mol=.02,
            density_kg_m3=.02/v, phase='liquid')
        return NS(state=state, chemical_potential_j_mol=r*t*math.log(controls.pure/100000.)+controls.shift,
            source_ids=self.source_ids)
    monkeypatch.setattr(WaterChemicalPotential, 'liquid_tp', liquid)
    monkeypatch.setattr(WaterChemicalPotential, 'equilibrium_at_liquid_tp',
        lambda self, t, p: NS(liquid=liquid(self, t, p),
            equilibrium_partial_pressure_pa=controls.pure, source_ids=self.source_ids))
    monkeypatch.setattr(WaterChemicalPotential, 'ideal_vapor', lambda self, t, p:
        NS(chemical_potential_j_mol=r*t*math.log(p/100000.)+controls.shift))

    def root(t):
        # Stable independent solution of k*v*x²-(k*V+RT)*x+Nt*RT=0.
        b = controls.k*volume+r*t
        return 2.*float(nt)*r*t/(b+math.sqrt(b*b-4.*controls.k*v*float(nt)*r*t))

    def target(t):
        return 300.*(t-330.)+10000.*(float(nt)-root(t))+controls.shift*float(nt)

    policy = module.FlashPolicy(inverse_policy=InversePolicy(1e-5, 1e-6, 60),
        temperature_range_k=(325., 338.), pressure_inset_pa=1.,
        composition_tolerance_mol=1e-11, inventory_tolerance_mol=1e-15,
        chemical_tolerance_j_mol=1e-5, equilibrium_pressure_tolerance_pa=1e-6,
        temperature_subdivisions=4, maximum_composition_iterations=70,
        maximum_provider_calls=12000, maximum_elapsed_s=30.)
    return NS(storage=storage, chemical=chemical, controls=controls, total=nt,
        carrier=(.012, .024), root=root, target=target, policy=policy)


def solve(a, **changes):
    return module.flash(a.storage, a.chemical, changes.pop('total', a.total),
        changes.pop('carrier', a.carrier), changes.pop('target', a.target(331.25)),
        changes.pop('policy', a.policy), **changes)


def test_analytic_root_full_energy_and_explicit_nominal_qualification(analytic):
    a = analytic
    result = solve(a)
    assert result.point.temperature_k == pytest.approx(331.25, abs=1e-6)
    assert result.state.liquid_water_mol == pytest.approx(a.root(331.25), abs=1e-10)
    assert abs(result.energy_residual_j)+F(result.point.energy_error_j) <= F(1e-5)
    assert result.exact_liquid_mol+result.exact_vapor_mol == a.total
    assert result.water_projection_residual_mol == (
        F(result.state.liquid_water_mol)+F(result.state.gas_amounts_mol[2])-a.total)
    assert abs(result.water_projection_residual_mol) <= F(a.policy.inventory_tolerance_mol)
    assert result.state.gas_amounts_mol[:2] == a.carrier
    assert result.state.internal_energy_j == a.target(331.25)
    assert result.certified_temperature_error_bound_k is None
    assert result.equilibrium_composition_energy_error_j is None
    assert result.qualification == 'nominal_equilibrium_candidate_not_certified_inverse'
    assert not result.material_qualified and not result.training_eligible
    assert result.counts['storage_evaluations'] == len(a.controls.calls)
    assert result.trials


def test_out_of_domain_all_gas_endpoint_is_prefiltered(analytic):
    result = solve(analytic)
    assert all(st.liquid_water_mol > 0 for _, st in analytic.controls.calls)
    assert all(90000 < p < 110000 for _, p in analytic.controls.pressure_calls)
    assert result.composition_bracket_mol[0] <= F(result.state.liquid_water_mol) <= result.composition_bracket_mol[1]


def test_same_invariants_and_repeat_have_same_nominal_root(analytic):
    a = analytic
    n1, n2 = a.total/4, 3*a.total/4
    first = solve(a, total=F(float(n1))+F(float(a.total-n1)))
    second = solve(a, total=F(float(n2))+F(float(a.total-n2)))
    repeated = solve(a, total=first.exact_liquid_mol+first.exact_vapor_mol)
    assert first.state == second.state == repeated.state


def test_common_energy_reference_shift_preserves_root(analytic):
    first = solve(analytic)
    analytic.controls.shift = 123456.
    shifted = solve(analytic)
    assert shifted.point.temperature_k == pytest.approx(first.point.temperature_k, abs=1e-6)
    assert shifted.state.liquid_water_mol == pytest.approx(first.state.liquid_water_mol, abs=1e-11)


def test_exact_dry_total_keeps_target_and_has_named_no_mu(analytic):
    result = solve(analytic, total=F(0), target=300.*1.25)
    assert result.state.liquid_water_mol == result.state.gas_amounts_mol[2] == 0.
    assert result.chemical_potential_residual_j_mol is None
    assert result.chemical_state == 'zero_total_water_no_finite_water_mu'
    assert result.point.temperature_k == pytest.approx(331.25, abs=1e-6)


@pytest.mark.parametrize('temperature', [325.00001, 337.99999])
def test_near_temperature_domain_edges(analytic, temperature):
    out = solve(analytic, target=analytic.target(temperature))
    assert out.point.temperature_k == pytest.approx(temperature, abs=1e-6)


def test_energy_target_outside_range_retains_trials(analytic):
    with pytest.raises(module.FlashFailure, match='temperature_bracket_not_found') as failure:
        solve(analytic, target=1e8)
    assert failure.value.trials
    assert failure.value.counts['storage_evaluations'] > 0


def test_composition_root_outside_pressure_domain_is_not_called_equilibrium(analytic):
    analytic.controls.pure = 1e9
    with pytest.raises(module.FlashFailure, match='temperature_bracket_not_found') as failure:
        solve(analytic, target=0.)
    assert any('composition_no_sign_bracket' in t.reason for t in failure.value.trials if t.reason)


def test_internal_temperature_domain_hole_is_named_and_preserved(analytic):
    analytic.controls.hole = lambda t: 331.0 < t < 331.5
    policy = replace(analytic.policy, temperature_subdivisions=1)
    with pytest.raises(module.FlashFailure, match='domain_hole') as failure:
        solve(analytic, policy=policy)
    assert failure.value.trials and failure.value.__cause__ is not None


def test_large_conditional_energy_error_does_not_receive_acceptance(analytic):
    analytic.controls.energy_error = 10000.
    with pytest.raises(module.FlashFailure, match='energy_sign_unresolved'):
        solve(analytic)


def test_provider_budget_and_iteration_limit_fail_with_ledger(analytic):
    with pytest.raises(module.FlashFailure, match='provider_call_budget') as failure:
        solve(analytic, policy=replace(analytic.policy, maximum_provider_calls=5))
    assert failure.value.counts['provider_calls'] == 5
    assert failure.value.trials
    with pytest.raises(module.FlashFailure, match='composition_iteration_limit'):
        solve(analytic, policy=replace(analytic.policy, maximum_composition_iterations=1))


def test_mutated_source_rejected_before_any_property_call(analytic):
    analytic.controls.source_ok = False
    with pytest.raises(module.FlashFailure, match='provider_validation'):
        solve(analytic)
    assert not analytic.controls.calls and not analytic.controls.pressure_calls


@pytest.mark.parametrize('total', [-1., True, float('nan'), float('inf')])
def test_invalid_total_rejected(analytic, total):
    with pytest.raises(module.FlashFailure, match='input'):
        solve(analytic, total=total)
    assert not analytic.controls.calls


def test_unrepresentable_target_and_invalid_policy_rejected(analytic):
    with pytest.raises(module.FlashFailure, match='input'):
        solve(analytic, target=F(1, 3))
    with pytest.raises(ValueError):
        replace(analytic.policy, pressure_inset_pa=0.)
    with pytest.raises(ValueError):
        replace(analytic.policy, maximum_provider_calls=True)


def test_fraction_total_is_not_silently_replaced_by_float_sum(analytic):
    total = analytic.total+F(1, 10**20)
    out = solve(analytic, total=total)
    assert out.exact_liquid_mol+out.exact_vapor_mol == total
    assert out.water_projection_residual_mol != 0
    assert out.liquid_projection_error_mol+out.vapor_projection_error_mol == out.water_projection_residual_mol


def test_full_pressure_error_still_rejects_nominal_boundary_point(analytic):
    analytic.controls.pressure_error = 2.
    with pytest.raises(module.FlashFailure, match='pressure_domain_exit'):
        solve(analytic)


def test_nonbinary_water_sum_must_fit_explicit_projection_budget(analytic):
    total = analytic.total+F(1, 10**20)
    with pytest.raises(module.FlashFailure, match='inventory_projection_budget'):
        solve(analytic, total=total,
              policy=replace(analytic.policy, inventory_tolerance_mol=1e-25))


def test_empty_pressure_feasible_set_performs_no_storage_calls(analytic):
    with pytest.raises(module.FlashFailure, match='temperature_bracket_not_found') as failure:
        solve(analytic, carrier=(.12, .24))
    assert not analytic.controls.calls
    assert all(t.kind == 'excluded_temperature' for t in failure.value.trials)


def test_sources_changed_during_last_probe_fail_before_return(analytic, monkeypatch):
    original = module._Engine.finish
    def finish(self, *args):
        analytic.controls.source_ok = False
        return original(self, *args)
    monkeypatch.setattr(module._Engine, 'finish', finish)
    with pytest.raises(module.FlashFailure, match='provider_failure'):
        solve(analytic)


def test_unexpected_provider_exception_keeps_named_failure_and_cause(analytic, monkeypatch):
    def unavailable(*args):
        raise RuntimeError('manufactured_unavailable_provider')
    monkeypatch.setattr(WaterChemicalPotential, 'liquid_tp', unavailable)
    with pytest.raises(module.FlashFailure, match='provider_failure') as failure:
        solve(analytic)
    assert isinstance(failure.value.__cause__, RuntimeError)
    assert failure.value.counts['provider_calls'] == 1
