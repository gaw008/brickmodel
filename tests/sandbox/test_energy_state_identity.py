"""Model energy identity is a binding, never a material evidence certificate."""
import math

import numpy as np
import pytest

from sludge_sandbox.integration import ConservedState, IntegrationError, Rates, integrate
from test_integration import policy

IDENTITY = ('manufactured:total-energy', '1', ('thermal', 'elastic', 'interface'))


@pytest.mark.parametrize('identity', ['', 'total', (), ('',), ('bad ',), ('x', []), ('x', True), ('x', 1)])
def test_malformed_or_mutable_identity_rejected(identity):
    with pytest.raises(IntegrationError, match='energy_model_identity'):
        ConservedState([[1]], [0], energy_model_identity=identity)


def test_all_rk_stages_and_accepted_states_preserve_identity():
    seen = []
    def operator(state, t):
        seen.append(state.energy_model_identity)
        return Rates([[0], [0]], [0, 0], [[0]], [state.internal_energy_j[0]+1])
    start = ConservedState([[1]], [0], energy_model_identity=IDENTITY)
    result = integrate(start, operator, start_s=0, end_s=1,
        policy=policy(initial_step_s=1, maximum_step_s=1, relative_tolerance=1e-7),
        breakpoints_s=(.375,))
    assert result.status == 'completed'
    assert result.rejected_trials > 0
    assert seen and all(v == IDENTITY for v in seen)
    assert all(s.energy_model_identity == IDENTITY for s in result.states)
    assert result.states[-1].internal_energy_j[0] == pytest.approx(math.e-1, abs=1e-3)


def test_legacy_default_remains_none():
    result = integrate(ConservedState([[1]], [0]),
        lambda s,t: Rates([[0], [0]], [0, 0], [[0]], [1]),
        start_s=0, end_s=.125, policy=policy())
    assert result.status == 'completed'
    assert all(s.energy_model_identity is None for s in result.states)


def test_gas_host_refuses_tagged_energy_before_thermo_decode():
    from test_gas_heat_model import model
    host = model()
    state = ConservedState([[1, 0], [1, 0]], [0, 0], energy_model_identity=IDENTITY)
    with pytest.raises(IntegrationError, match='energy_model_identity'):
        host.evaluate(state, 0)


def test_actual_rigid_and_solid_hosts_refuse_tagged_energy_without_eos(monkeypatch):
    from test_solid_fluid_heat import solid_host
    from test_water_phase_transfer import DATA, transfer
    from sludge_sandbox.water_properties import load_water_properties
    from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    ingredients = load_water_properties(DATA), IdealWaterVapor(DATA), WaterChemicalPotential(DATA)
    def forbidden(*args, **kwargs):
        raise AssertionError('tagged energy reached liquid EOS')
    monkeypatch.setattr(type(ingredients[0]), 'state_tp', forbidden)
    for host in (transfer(ingredients).base_model, solid_host(ingredients)):
        state = ConservedState(np.zeros((1, len(host.species_order))), [0], energy_model_identity=IDENTITY)
        with pytest.raises(IntegrationError, match='energy_model_identity'):
            host.evaluate(state, 0)


def test_event_writeback_preserves_energy_binding():
    from sludge_sandbox.depletion_roundoff import depletion_writeback, DepletionRoundoffTotals
    from test_depletion_roundoff import policy as writeback_policy
    p = writeback_policy()
    delta = math.ulp(.01)/2
    old = ConservedState([[delta, .1, 7]], [12], energy_model_identity=IDENTITY)
    state, record, totals = depletion_writeback(old, cell_index=0, liquid_index=0,
        vapor_index=1, panel_liquid_start_mol=.01, panel_liquid_terms_mol=(-.01, delta),
        positive_evaporated_mol=.01, policy=p, totals=DepletionRoundoffTotals(p))
    assert state.energy_model_identity == IDENTITY
    assert np.array_equal(state.internal_energy_j, old.internal_energy_j)
    assert totals.events == 1
