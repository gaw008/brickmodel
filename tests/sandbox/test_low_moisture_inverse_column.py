"""Explicit inverse selection, unchanged full-U certificates and shared budgets."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from test_low_moisture_column import setup
from test_controlled_vapor_column import boundary
from sludge_sandbox import low_moisture_fast_inverse as fast
from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage
from sludge_sandbox.source_wet_column import integrate_source_column


def test_default_and_opt_in_select_only_the_declared_inverse(monkeypatch):
    base, states = setup(monkeypatch)
    original = LowMoistureSorptionStorage.invert
    calls = []
    def old(storage, state, policy):
        calls.append((state, policy))
        return original(storage, state, policy)
    monkeypatch.setattr(LowMoistureSorptionStorage, 'invert', old)
    default = replace(base, inverse_strategy='full_U_bisection_v1')
    assert default.model_identity == base.model_identity
    default.evaluate(states)
    assert len(calls) == 2
    selected = replace(base, inverse_strategy=fast.NUMERICAL_POLICY_ID)
    assert selected.model_identity != base.model_identity
    assert selected.storages == base.storages
    assert selected.inverse_policies == base.inverse_policies
    assert selected.provenance()['inverse_strategy'] == fast.strategy_definition()
    result = selected.evaluate(states)
    assert len(calls) == 2  # Opt-in cannot silently return to the old inverse.
    for state, policy, cell in zip(states, base.inverse_policies, result.cells):
        inv = cell.inverse
        assert inv.target_energy_j == state.internal_energy_j
        assert abs(inv.energy_residual_j)+F(inv.point.energy_error_j) <= F(policy.energy_tolerance_j)
        assert inv.temperature_error_bound_k <= policy.temperature_tolerance_k
        assert inv.point.model_identity == state.energy_model_identity


def test_unknown_and_mutated_strategy_fail_before_solving(monkeypatch):
    base, states = setup(monkeypatch)
    for invalid in (None, True, 'fast', ''):
        with pytest.raises(ValueError, match='inverse_strategy'):
            replace(base, inverse_strategy=invalid)
    def forbidden(*args):
        pytest.fail('mutated column reached an inverse')
    monkeypatch.setattr(fast, 'invert_low_moisture_safeguarded', forbidden)
    object.__setattr__(base, 'inverse_strategy', fast.NUMERICAL_POLICY_ID)
    with pytest.raises(ValueError, match='content_changed'):
        base.evaluate(states)


def test_controlled_boundary_retains_shared_water_and_energy_with_fast_inverse(monkeypatch):
    base, states = setup(monkeypatch)
    column = boundary(replace(base, inverse_strategy=fast.NUMERICAL_POLICY_ID))
    assert column.model_identity != boundary(base).model_identity
    run = integrate_source_column(column, states, duration_s=1/128, steps=2)
    assert run.status == 'completed', run.reason
    assert run.states[-1][0].liquid_water_mol > 0
    for old, new, ledger in zip(run.states, run.states[1:], run.ledgers):
        outer = ledger.faces[-1]
        water = lambda row: sum((F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in row), F())
        assert water(new)-water(old) == -outer.gas_mol[2]+sum(ledger.roundoff.liquid_mol)+sum(r[2] for r in ledger.roundoff.gas_mol)
        assert sum(F(n.internal_energy_j)-F(o.internal_energy_j) for o,n in zip(old,new)) == -outer.energy_j+sum(ledger.roundoff.energy_j)
        assert ledger.predictor_rates is not None
    assert not run.material_qualified
