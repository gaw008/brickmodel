from decimal import Decimal as D
from sludge_sandbox.water_density_tube import *
I=eos.I

def args(fn,**changes):
    a=dict(derivative=fn,binding=lambda:('source','impl'),reducing_density=D(1),reducing_temperature=D(10),maximum_boxes=31,maximum_wall_seconds=1.)
    a.update(changes)
    return prove_generic(eos.Interval(D(2),D(3)),eos.Interval(D(2),D(4)),**a)


def test_whole_temperature_and_exact_leaf_coverage():
    seen=[]
    def d(t,r):
        seen.append((t,r))
        return eos.Interval(D(-1),D(2)) if r.hi-r.lo>D('.5') else I(1)
    r=args(d)
    assert r.proved and len(r.leaves)==4 and r.evaluations_attempted==7
    assert all(t==r.temperature for t,b in seen)
    assert r.leaves[0].lo==D(2) and r.leaves[-1].hi==D(4)
    assert all(a.hi==b.lo for a,b in zip(r.leaves,r.leaves[1:]))
    assert all(v.derivative.lo>0 for v in r.visits if v.decision=='positive')


def test_negative_interior_not_hidden_by_positive_endpoints():
    # q(rho)=(rho-3)^2-.1 is positive at rho=2,4, negative internally.
    def d(t,r):
        values=[(r.lo-D(3))**2,(r.hi-D(3))**2]
        lo=D(0) if r.lo<=D(3)<=r.hi else min(values)
        return eos.Interval(lo-D('.1'),max(values)-D('.1'))
    r=args(d)
    assert not r.proved and r.pending
    assert r.reason=='nonpositive_derivative'


def test_box_budget_and_callback_failure_retained():
    r=args(lambda t,r:eos.Interval(D(-1),D(1)),maximum_boxes=2)
    assert not r.proved and r.evaluations_attempted==2 and 'box_budget' in r.reason
    assert len(r.visits)==2 and len(r.pending)==3
    def broken(t,r):raise ValueError('synthetic_callback_failure')
    r=args(broken)
    assert not r.proved and r.evaluations_attempted==1 and r.evaluations_completed==0
    assert r.visits[0].decision=='callback_failed'


def test_source_changed_after_evaluation_not_accepted():
    source=['a']
    def d(t,r):source[0]='b';return I(1)
    r=args(d,binding=lambda:tuple(source))
    assert not r.proved and not r.leaves and r.evaluations_completed==1
    assert r.visits[0].derivative==I(1) and 'source_changed' in r.reason


def test_wall_limit_preserves_actual_cost():
    ticks=[0.]
    def clock():return ticks[0]
    def d(t,r):ticks[0]=2.;return I(1)
    r=args(d,clock=clock)
    assert not r.proved and not r.leaves and r.evaluations_completed==1 and 'wall_budget' in r.reason


def test_pinned_wrapper_refuses_source_without_eos_call(tmp_path):
    import pytest
    p=tmp_path/'source';p.write_text('{}')
    with pytest.raises(ValueError,match='source_or_implementation_mismatch'):
        prove_density_tube(p,'0'*64,eos.Interval(D(2),D(3)),eos.Interval(D(2),D(4)))


def test_input_values_unchanged_and_exact_midpoint_under_low_precision():
    from decimal import localcontext
    t=eos.Interval(D(2),D(3));r=eos.Interval(D('2.0000000000000000000000000001'),D('2.0000000000000000000000000003'))
    original=(t.lo,t.hi,r.lo,r.hi)
    with localcontext() as ctx:
        ctx.prec=8
        def derivative(t,b):return eos.Interval(D(-1),D(2)) if b==r else I(1)
        out=prove_generic(t,r,derivative=derivative,binding=lambda:('x',),reducing_density=D(1),reducing_temperature=D(10),maximum_boxes=3,maximum_wall_seconds=1.)
    assert out.proved and out.leaves[0].hi==D('2.0000000000000000000000000002')
    assert (t.lo,t.hi,r.lo,r.hi)==original


def test_mutable_binding_snapshot_cannot_be_rewritten():
    import pytest
    identity=['source','implementation'];calls=[]
    def derivative(t,r):identity[0]='changed';calls.append(1);return I(1)
    with pytest.raises(ValueError,match='immutable_nonempty_string_binding_required'):
        args(derivative,binding=lambda:identity)
    assert calls==[] and identity==['source','implementation']


def test_later_binding_must_still_be_immutable():
    identity=[('source','implementation')]
    def derivative(t,r):identity[0]=['source','implementation'];return I(1)
    r=args(derivative,binding=lambda:identity[0])
    assert not r.proved and r.source_before==('source','implementation')
    assert r.evaluations_completed==1 and not r.leaves
    assert 'immutable_nonempty_string_binding_required' in r.reason


def test_empty_nested_or_nonstr_binding_rejected():
    import pytest
    for identity in ((),('',),(' ',),(('nested',),),(1,),('source',[])):
        with pytest.raises(ValueError,match='immutable_nonempty_string_binding_required'):
            args(lambda t,r:I(1),binding=lambda:identity)
