"""Public-API constant/linear-flux clock regressions; no thermoelastic/B trajectory."""
from fractions import Fraction as F
import math

import pytest

from sludge_sandbox.integration import ConservedState, IntegrationPolicy, Rates, integrate


def policy(step, maximum_steps):
    return IntegrationPolicy(initial_step_s=step, maximum_step_s=step, minimum_step_s=1e-10,
        relative_tolerance=1e-6, amount_absolute_tolerance_mol=1e-11,
        energy_absolute_tolerance_j=1e-9, amount_scale_mol=1., energy_scale_j=100.,
        maximum_steps=maximum_steps, maximum_rejections=1000, maximum_wall_seconds=20.)


def linear_rates(state, at):
    return Rates([[at], [0.]], [10*at, 0.], [[0.]], [3*at],
                 cell_power_components_w={'mechanical_constraint': [3*at]})


def check_actual_prefixes(result, step):
    assert len(result.steps)+1 == len(result.states) == len(result.times_s)
    amount = heat = work = F()
    start = F(result.times_s[0])
    for index, ledger in enumerate(result.steps):
        assert ledger.start_s == result.times_s[index]
        assert ledger.end_s == result.times_s[index+1]
        assert 0 < ledger.end_s-ledger.start_s <= step+math.ulp(ledger.start_s)+math.ulp(ledger.end_s)
        amount += F(float(ledger.face_species_mol[0, 0]))
        heat += F(float(ledger.face_energy_j[0]))
        work += F(float(ledger.cell_work_components_j['mechanical_constraint'][0]))
        expected = (F(ledger.end_s)**2-start**2)/2
        assert abs(amount-expected) <= F(1e-14)
        assert abs(heat-10*expected) <= F(1e-13)
        assert abs(work-3*expected) <= F(1e-14)
        state = result.states[index+1]
        assert abs(F(float(state.amounts_mol[0, 0]))-expected) <= F(1e-14)
        assert abs(F(float(state.internal_energy_j[0]))-13*expected) <= F(1e-13)


@pytest.mark.parametrize('step', [.005, .0025])
def test_repaired_tail_at_internal_knot_preserves_flux_and_subsequent_segment(step):
    knot = math.nextafter(.3, math.inf)
    result = integrate(ConservedState([[0.]], [0.]), linear_rates,
        start_s=.2, end_s=.305, breakpoints_s=(knot,), policy=policy(step, 45))
    assert result.status == 'completed', (result.status, result.reason)
    assert result.times_s[-1] == .305
    assert result.times_s.count(knot) == 1
    assert all(not ledger.start_s < knot < ledger.end_s for ledger in result.steps)
    check_actual_prefixes(result, step)


@pytest.mark.parametrize('step,cap', [(.005, 20), (.0025, 40)])
def test_repartition_does_not_override_accepted_step_budget(step, cap):
    endpoint = math.nextafter(.3, math.inf)
    result = integrate(ConservedState([[0.]], [0.]), linear_rates,
        start_s=.2, end_s=endpoint, policy=policy(step, cap))
    assert result.status == 'resource_limit'
    assert result.reason == 'accepted_step_limit'
    assert len(result.steps) == cap
    assert result.times_s[-1] < endpoint
    check_actual_prefixes(result, step)
