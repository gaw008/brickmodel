"""Independent manufactured event checks; no native water or material claims."""
from dataclasses import replace
from fractions import Fraction
import math
import numpy as np

import pytest

from sludge_sandbox.depletion_integration import integrate_depletion
from sludge_sandbox.integration import Rates
from test_depletion_spine import configured, oracle, initial, exact_event, audit, check_costs


def run_affine(b, *, method='affine_midpoint', callback=None, strict_water=False):
    p, e = configured()
    p = replace(p, relative_tolerance=1e-11)
    if strict_water:
        p = replace(p, relative_tolerance=1e-13, amount_absolute_tolerance_mol=1e-14)
    e = replace(e, terminal_method=method, amount_absolute_mol=1e-10)
    op, counts = oracle(b)
    if callback is not None:
        op = replace(op, evaluate_callback=callback(op.evaluate_callback))
    result = integrate_depletion(initial(), op, start_s=0., end_s=.2,
        integration_policy=p, event_policy=e)
    return result, counts


@pytest.mark.parametrize('b', [0., .002])
def test_affine_event_matches_independent_root_reaction_and_energy(b):
    out, counts = run_affine(b)
    audit(out, b)
    check_costs(out)
    event = out.events[0]
    assert abs(event.time_s-exact_event(b)) < 1e-10
    assert counts['calls'] == out.evaluations
    assert event.terminal_evidence is not None
    certificate = event.terminal_evidence.clock
    assert certificate.start_s < certificate.midpoint_s < certificate.end_s
    assert certificate.end_s == event.time_s
    row = out.states[out.times_s.index(event.time_s)].amounts_mol[0]
    assert abs(row[2]-2*math.exp(-.1*event.time_s)) < 1e-10
    assert any(r.status == 'independent_approach_pass' for r in out.refinements)


def test_affine_total_work_reduces_at_same_acceptance_gates():
    affine, _ = run_affine(.002)
    euler, _ = run_affine(.002, method='euler')
    assert affine.status == euler.status == 'completed'
    assert affine.evaluations < euler.evaluations
    assert affine.phase_costs['approach']['evaluations'] < euler.phase_costs['approach']['evaluations']


def test_affine_midpoint_failure_does_not_commit_event():
    # The midpoint callback is an actual evaluation: fail there, not a cached lookup.
    def injected(original):
        def evaluate(state, t, modes):
            import inspect
            if any(f.function == 'affine_terminal' for f in inspect.stack()):
                raise ValueError('manufactured_midpoint_failure')
            return original(state, t, modes)
        return evaluate
    out, _ = run_affine(.002, callback=injected)
    assert out.status != 'completed'
    assert 'manufactured_midpoint_failure' in out.reason
    assert not out.events and not out.corrections
    assert out.operator.interfaces == ('existing_liquid',)
    assert all(s.amounts_mol[0, 0] > 0 for s in out.states)


def test_unknown_terminal_method_rejected():
    _, event = configured()
    with pytest.raises(ValueError, match='terminal_method'):
        replace(event, terminal_method='uncertified')


def test_nonlinear_sink_and_time_dependent_work_have_independent_integrals():
    def nonlinear(original):
        def evaluate(state, t, modes):
            out = original(state, t, modes)
            sink = .001*(1+t)**2 if modes[0] == 'existing_liquid' else 0.
            reaction = out.rates.reaction_species_mol_s.copy()
            reaction[0, :2] = [-sink, sink]
            power = .3+.5*t if modes[0] == 'existing_liquid' else 2.
            rates = Rates(out.rates.face_species_mol_s, out.rates.face_energy_w,
                reaction, np.array([power]), cell_power_components_w={
                    'elastic': [.1], 'pore': [-.1], 'body': [power]})
            return replace(out, rates=rates, evaporation_mol_s=(sink,))
        return evaluate
    out, _ = run_affine(.002, callback=nonlinear, strict_water=True)
    assert out.status == 'completed', out.reason
    exact = 1.3**(1/3)-1
    assert abs(out.events[0].time_s-exact) < 1e-9
    assert abs(out.states[-1].internal_energy_j[0]-(600+.3*exact+.25*exact**2+2*(.2-exact))) < 1e-8
    check_costs(out)
    for step in out.steps:
        pieces = sum((Fraction(float(v[0])) for v in step.cell_work_components_j.values()), Fraction())
        assert pieces+step.component_sum_residual_j[0] == Fraction(float(step.cell_work_j[0]))


@pytest.mark.parametrize('n,a,b,h,expected', [
    (1,-4,4,1,0),       # (2t-1)^2 touches zero internally.
    (1,-6,6,1,Fraction(-1,2)),  # Both endpoints positive; interior negative.
    (1,2,-1,1,1),      # Concave: minimum is at an endpoint.
    (1,-1,0,1,0),
])
def test_full_inventory_interval_includes_interior_minimum(n,a,b,h,expected):
    from sludge_sandbox.depletion_integration import _quadratic_inventory_minimum
    assert _quadratic_inventory_minimum(*map(Fraction,(n,a,b,h))) == expected


@pytest.mark.parametrize('a,b,h,expected', [
    (1,-2,1,Fraction(1,4)),  # Triangle before zero, despite zero signed integral.
    (-1,2,1,Fraction(1,4)),  # Triangle after zero.
    (-1,-1,1,0),
    (2,0,3,6),
])
def test_gross_phase_transfer_is_positive_area_not_clamped_net(a,b,h,expected):
    from sludge_sandbox.depletion_integration import _positive_affine_integral
    assert _positive_affine_integral(*map(Fraction,(a,b,h))) == expected
