"""Predeclared component tests: exact RK quadrature, not endpoint potentials.

No EOS. Absolute ledger reconstruction allowance is the existing explicit J
policy (1e-9 here); rates use correctly rounded exact represented sums.
"""
from fractions import Fraction as F

import numpy as np
import pytest

from sludge_sandbox.integration import ConservedState, IntegrationError, Rates, integrate
from test_integration import policy


def rates(parts, total=None):
    if total is None:
        total = [float(sum((F(float(v[0])) for v in parts.values()), F()))]
    return Rates([[0], [0]], [0, 0], [[0]], total,
                 cell_power_components_w=parts)


def test_component_snapshot_and_exact_rate_residual():
    original = np.array([0.1])
    parts = {'elastic': original, 'body': [0.2]}
    r = rates(parts)
    original[0] = 4
    parts.clear()
    assert r.cell_power_components_w['elastic'][0] == 0.1
    with pytest.raises(TypeError):
        r.cell_power_components_w['pore'] = [1]
    with pytest.raises(ValueError):
        r.cell_power_components_w['elastic'].setflags(write=True)
    assert r.component_sum_residual_w == (F(float(r.cell_power_w[0]))-F(0.1)-F(0.2),)


@pytest.mark.parametrize('parts,total', [({}, [0]), ({'unknown': [1]}, [1]),
    ({'elastic': [1]}, [2]), ({'body': [1, 2]}, [1]),
    ({'dissipation': [-1]}, [-1]), ({'body': [True]}, [1])])
def test_invalid_component_contract(parts, total):
    with pytest.raises(IntegrationError):
        rates(parts, total)


def test_actual_accepted_quadrature_components_and_prefix():
    def op(state, t):
        return rates({'elastic': [t*t], 'pore': [-2*t*t], 'body': [1+2*t]})
    out = integrate(ConservedState([[1]], [0]), op, start_s=0, end_s=1,
                    policy=policy(initial_step_s=1, maximum_step_s=1,
                                  relative_tolerance=1e-7), breakpoints_s=(0.37,))
    assert out.status == 'completed'
    assert out.rejected_trials > 0
    accum = F()
    for step, state in zip(out.steps, out.states[1:]):
        a, b = step.start_s, step.end_s
        m = a+(b-a)/2
        expected = (m-a)/2*(a*a+m*m)+(b-m)/2*(m*m+b*b)
        assert step.cell_work_components_j['elastic'][0] == pytest.approx(expected, rel=0, abs=2e-16)
        assert step.cell_work_components_j['pore'][0] == pytest.approx(-2*expected, rel=0, abs=4e-16)
        exact = sum((F(float(v[0])) for v in step.cell_work_components_j.values()), F())
        assert exact+step.component_sum_residual_j[0] == F(float(step.cell_work_j[0]))
        accum += exact+step.component_sum_residual_j[0]
        assert abs(F(float(state.internal_energy_j[0]))-accum) <= F(1e-9)
    assert out.states[-1].internal_energy_j[0] == pytest.approx(5/3, rel=0, abs=1e-3)


@pytest.mark.parametrize('later', [None, {'pore': [1]}])
def test_component_identity_change_is_not_a_rejected_physics_trial(later):
    def op(state, t):
        if t == 0:
            return rates({'body': [1]})
        return rates(later, [1])
    out = integrate(ConservedState([[1]], [0]), op, start_s=0, end_s=1, policy=policy())
    assert out.status == 'numerical_failure'
    assert out.reason == 'component_work_schema_changed'
    assert not out.steps


def test_partial_accepted_records_survive_resource_limit():
    out = integrate(ConservedState([[1]], [0]), lambda s,t: rates({'body': [2]}),
                    start_s=0, end_s=1, policy=policy(maximum_steps=1))
    assert out.status == 'resource_limit'
    assert len(out.steps) == 1
    assert out.steps[0].cell_work_components_j['body'][0] == out.steps[0].cell_work_j[0]


def test_legacy_rates_and_ledgers_remain_unspecified():
    out = integrate(ConservedState([[1]], [0]),
                    lambda s,t: Rates([[0],[0]], [0,0], [[0]], [1]),
                    start_s=0, end_s=0.1, policy=policy())
    assert out.status == 'completed'
    assert out.steps[0].cell_work_components_j is None
    assert out.steps[0].component_sum_residual_j is None


def test_cumulative_absolute_decomposition_roundoff_rejects_before_commit():
    # Dyadic total power/state updates are exact; decomposition alone rounds.
    out = integrate(ConservedState([[1]], [0]), lambda s,t: rates({'elastic': [0.1], 'body': [0.4]}),
                    start_s=0, end_s=1,
                    policy=policy(initial_step_s=0.25, maximum_step_s=0.25,
                                  energy_absolute_tolerance_j=1e-17))
    assert out.status == 'numerical_failure'
    assert out.reason == 'cumulative_component_sum_roundoff'
    assert len(out.steps) == 1
    delta = abs(F(0.125)-F(0.025)-F(0.1))
    assert out.cumulative_absolute_component_residual_j == (delta,)
    assert delta <= F(1e-17) < 2*delta
    assert out.times_s[-1] == 0.25


def test_stage_quadrature_rounding_is_exactly_reported_even_when_terms_underflow():
    tiny = float.fromhex('0x0.0000000000001p-1022')
    out = integrate(ConservedState([[1]], [0]),
                    lambda s,t: rates({'elastic': [tiny], 'pore': [-tiny]}),
                    start_s=0, end_s=0.25,
                    policy=policy(initial_step_s=0.25, maximum_step_s=0.25))
    assert out.status == 'completed'
    step = out.steps[0]
    assert step.cell_work_components_j['elastic'][0] == 0
    assert step.component_quadrature_roundoff_j['elastic'] == (-F(tiny)/4,)
    assert step.component_quadrature_roundoff_j['pore'] == (F(tiny)/4,)
    assert step.component_sum_residual_j == (F(),)
    with pytest.raises(TypeError):
        step.component_quadrature_roundoff_j['body'] = (F(),)


def test_none_to_component_schema_change_is_rejected():
    def op(s,t):
        return rates(None if t == 0 else {'body': [1]}, [1])
    out = integrate(ConservedState([[1]], [0]), op, start_s=0, end_s=1, policy=policy())
    assert out.reason == 'component_work_schema_changed'
    assert not out.steps


def test_multicell_signed_components_remain_separate():
    def op(s,t):
        return Rates(np.zeros((3,1)), [0,0,0], [[0],[0]], [3,-1],
                     {'pore': [2,-4], 'body': [1,3]})
    out = integrate(ConservedState([[1],[1]], [0,0]), op, start_s=0, end_s=0.25,
                    policy=policy(initial_step_s=0.25, maximum_step_s=0.25))
    assert out.status == 'completed'
    assert np.array_equal(out.steps[0].cell_work_components_j['pore'], [0.5,-1])
    assert np.array_equal(out.states[-1].internal_energy_j, [0.75,-0.25])
