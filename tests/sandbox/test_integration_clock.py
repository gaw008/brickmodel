"""Absolute clock rounding must not create a spurious RK tail panel."""
from fractions import Fraction
import math

import pytest

from sludge_sandbox.integration import ConservedState, Rates, integrate
from test_integration import policy


@pytest.mark.parametrize('start,end',[(.5,.51),(-.51,-.5),(1e6,1e6+.01)])
@pytest.mark.parametrize('panels',[2,4,8])
def test_nominal_clock_panels_integrate_all_boundary_flux(start,end,panels):
    step=.01/panels
    seen=[]
    def feed(state,t):
        seen.append(t)
        return Rates([[1.],[0.]],[10.,0.],[[0.]],[0.])
    run=integrate(ConservedState([[0.]],[0.]),feed,start_s=start,end_s=end,
        policy=policy(initial_step_s=step,maximum_step_s=step,maximum_steps=panels))
    assert run.status=='completed', (run.reason,run.times_s)
    assert len(run.steps)==panels and run.times_s[-1]==end and end in seen
    amount=Fraction();energy=Fraction()
    for a,b,ledger,state in zip(run.times_s,run.times_s[1:],run.steps,run.states[1:]):
        assert 0<b-a<=step+math.ulp(a)+math.ulp(b)
        assert ledger.start_s==a and ledger.end_s==b
        amount+=Fraction(float(ledger.face_species_mol[0,0]))
        energy+=Fraction(float(ledger.face_energy_j[0]))
        assert abs(Fraction(float(state.amounts_mol[0,0]))-amount)<=Fraction(1e-14)
        assert abs(Fraction(float(state.internal_energy_j[0]))-energy)<=Fraction(1e-13)
    exact=Fraction(end)-Fraction(start)
    assert abs(amount-exact)<=Fraction(1e-14)
    assert abs(energy-10*exact)<=Fraction(1e-13)


def test_clock_reanchors_at_forcing_breakpoint():
    def feed(state,t):return Rates([[1.],[0.]],[10.,0.],[[0.]],[0.])
    r=integrate(ConservedState([[0.]],[0.]),feed,start_s=.5,end_s=.51,
        breakpoints_s=(.505,),policy=policy(initial_step_s=.00125,maximum_step_s=.00125,maximum_steps=8))
    assert r.status=='completed' and len(r.steps)==8
    assert .505 in r.times_s
    assert all(not a<.505<b for a,b in zip(r.times_s,r.times_s[1:]))
    assert r.states[-1].amounts_mol[0,0]==pytest.approx(.51-.5,abs=1e-14,rel=0)


def test_full_remaining_interval_includes_mechanical_work():
    def work(state,t):return Rates([[0.],[0.]],[0.,0.],[[0.]],[3.])
    r=integrate(ConservedState([[1.]],[0.]),work,start_s=.5,end_s=.51,
        policy=policy(initial_step_s=.00125,maximum_step_s=.00125,maximum_steps=8))
    assert r.status=='completed' and len(r.steps)==8 and r.evaluations==57
    total=sum((Fraction(float(s.cell_work_j[0])) for s in r.steps),Fraction())
    exact=3*(Fraction(.51)-Fraction(.5))
    assert abs(total-exact)<=Fraction(1e-15)
    assert abs(Fraction(float(r.states[-1].internal_energy_j[0]))-total)<=Fraction(1e-15)


def test_binary_interval_remainder_is_fully_integrated():
    def work(s,t):return Rates([[0.],[0.]],[0.,0.],[[0.]],[3.])
    r=integrate(ConservedState([[1.]],[0.]),work,start_s=.15,end_s=.2,
        policy=policy(initial_step_s=.01,maximum_step_s=.01,maximum_steps=5))
    assert r.status=='completed',(r.reason,r.times_s)
    assert r.times_s[-1]==.2 and len(r.steps)==5
    total=sum((Fraction(float(s.cell_work_j[0])) for s in r.steps),Fraction())
    assert abs(total-3*(Fraction(.2)-Fraction(.15)))<=Fraction(1e-15)


@pytest.mark.parametrize('step,panels',[(.005,20),(.0025,40)])
def test_separately_rounded_knot_receives_full_time_dependent_heat_and_work(step,panels):
    start,end=.2,math.nextafter(.3,math.inf)
    def feed(state,t):
        return Rates([[t],[0.]],[10*t,0.],[[0.]],[3*t],
            cell_power_components_w={'mechanical_constraint':[3*t]})
    r=integrate(ConservedState([[0.]],[0.]),feed,start_s=start,end_s=end,
        policy=policy(initial_step_s=step,maximum_step_s=step,maximum_steps=panels+1))
    assert r.status=='completed',(r.reason,r.times_s)
    assert r.times_s[-1]==end and len(r.steps)<=panels+1
    amount,heat,work=Fraction(),Fraction(),Fraction()
    for ledger,state in zip(r.steps,r.states[1:]):
        assert ledger.start_s<ledger.end_s
        assert ledger.end_s-ledger.start_s<=step+math.ulp(ledger.start_s)+math.ulp(ledger.end_s)
        amount+=Fraction(float(ledger.face_species_mol[0,0]))
        heat+=Fraction(float(ledger.face_energy_j[0]))
        work+=Fraction(float(ledger.cell_work_components_j['mechanical_constraint'][0]))
        expected=(Fraction(ledger.end_s)**2-Fraction(start)**2)/2
        assert abs(amount-expected)<=Fraction(1e-14)
        assert abs(heat-10*expected)<=Fraction(1e-13)
        assert abs(work-3*expected)<=Fraction(1e-14)
        assert abs(Fraction(float(state.internal_energy_j[0]))-heat-work)<=Fraction(1e-13)
        assert abs(Fraction(float(state.amounts_mol[0,0]))-amount)<=Fraction(1e-14)


def test_intentionally_adjacent_forcing_knots_are_not_merged():
    first=.3
    second=math.nextafter(first,math.inf)
    seen=[]
    def feed(state,t):
        seen.append(t)
        return Rates([[1.],[0.]],[10.,0.],[[0.]],[0.])
    r=integrate(ConservedState([[0.]],[0.]),feed,start_s=.29,end_s=.31,
        breakpoints_s=(first,second),
        policy=policy(initial_step_s=.005,maximum_step_s=.005,maximum_steps=10))
    assert r.status=='numerical_failure' and r.reason=='unresolvable_stage_time'
    assert r.times_s[-1]==first
    assert all(t<=first for t in seen)
    assert all(ledger.end_s<=first for ledger in r.steps)
