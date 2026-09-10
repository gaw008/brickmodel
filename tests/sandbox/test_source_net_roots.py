"""Exact arithmetic root evidence only; no source provider or EOS calls."""
from dataclasses import replace
from fractions import Fraction as F
import math
import pytest
from sludge_sandbox.mass_wet_exact_stage import InventoryPolynomial
from sludge_sandbox.source_net_roots import (
    SourceNetRootError, QuadraticRoot, QuadraticNoRoot,
    isolate_first_root, refine_first_root, same_first_root,
    order_inventory_roots, order_source_panel_roots,
)


def poly(n, r, q=0, *, family='liquid', cell=0, index=0):
    return InventoryPolynomial(family, cell, index, F(n), F(r), F(q))


@pytest.mark.parametrize('p,h,root,kind', [
    (poly(1,-2),F(1),F(1,2),'exact_crossing'),
    (poly(F(1,2),F(-3,4)),F(1),F(2,3),'exact_crossing'),
    (poly(1,1,-2),F(1),F(1),'exact_endpoint'),
    (poly(1,-4,4),F(1),F(1,2),'exact_tangent'),
    (poly(1,-2,1),F(1),F(1),'exact_tangent'),
    (poly(1,-1),F(1),F(1),'exact_endpoint'),
])
def test_exact_route_roots_without_evaporation(p,h,root,kind):
    out=isolate_first_root(p,h)
    assert type(out) is QuadraticRoot
    assert (out.lower,out.upper,out.root_kind)==(root,root,kind)
    out.check()
    assert refine_first_root(out) is out


@pytest.mark.parametrize('h',[F(3,2),F(2)])
def test_convex_first_root_not_second_endpoint_or_recovered_inventory(h):
    out=isolate_first_root(poly(3,-8,4),h)
    assert out.branch_lower==0 and out.branch_upper==1
    assert out.root_kind=='crossing'
    out=refine_first_root(out)
    assert out.lower==F(1,2) and out.upper==1 # legacy-compatible >=0 update
    for _ in range(4):out=refine_first_root(out)
    assert out.lower==F(1,2)<out.upper<F(3,4)


def test_concave_initial_gain_then_descent():
    out=isolate_first_root(poly(1,1,-2),F(2))
    assert (out.branch_lower,out.branch_upper)==(F(1,4),F(2))
    for _ in range(8):out=refine_first_root(out)
    assert out.lower<=1<=out.upper and out.upper-out.lower==F(7,4)/2**8


@pytest.mark.parametrize('p,h,minimum,at',[
    (poly(1,-1,1),F(2),F(3,4),F(1,2)),
    (poly(1,0),F(2),F(1),F()),
    (poly(1,1,1),F(2),F(1),F()),
    (poly(2,1,-1),F(1),F(2),F()),
])
def test_exact_strict_exclusion(p,h,minimum,at):
    out=isolate_first_root(p,h)
    assert type(out) is QuadraticNoRoot and (out.minimum,out.minimum_time)==(minimum,at)
    out.check()


def test_gas_before_multiple_liquid_and_exact_ties():
    liquids=(poly(1,-2,cell=0),poly(2,-4,cell=1))
    gas=poly(1,-4,family='gas',cell=2,index=1)
    out=order_inventory_roots((*liquids,gas),F(1))
    assert out.status=='ordered' and out.earliest_labels==( ('gas',2,1), )
    out.check()
    tie=order_inventory_roots(liquids,F(1))
    assert tie.status=='tied' and len(tie.earliest_labels)==2 and tie.complete
    tie.check()
    cross_tie=order_inventory_roots((liquids[0],replace(liquids[1],family='gas',index=2)),F(1))
    assert cross_tie.status=='tied'


def test_common_later_root_is_not_first_tie():
    left=poly(F(3,16),-1,1)
    right=poly(F(3,8),F(-5,4),1,cell=1)
    a,b=(isolate_first_root(p,F(1)) for p in (left,right))
    assert not same_first_root(a,b)
    out=order_inventory_roots((left,right),F(1))
    assert out.status=='ordered' and out.earliest_labels==( ('liquid',0,0), )
    out.check()


def test_proportional_quadratic_tie_and_tangent_crossing_tie():
    out=order_inventory_roots((poly(1,-3,1),poly(2,-6,2,cell=1)),F(1))
    assert out.status=='tied'
    mixed=order_inventory_roots((poly(1,-4,4),poly(1,-2,cell=1)),F(1))
    assert mixed.status=='tied'


def test_close_roots_and_bounded_unresolved_keep_every_bracket():
    epsilon=F(math.ulp(1.))
    a=poly(1,-3,1)
    b=poly(1+epsilon,-3,1,cell=1)
    unresolved=order_inventory_roots((a,b),F(1),maximum_refinements=1)
    assert unresolved.status=='unresolved' and not unresolved.complete
    assert len(unresolved.roots)==2 and unresolved.refinement_level==1
    unresolved.check()
    resolved=order_inventory_roots((a,b),F(1),maximum_refinements=128)
    assert resolved.status=='ordered' and resolved.earliest_labels==( ('liquid',0,0), )
    assert resolved.refinement_level>1
    resolved.check()


@pytest.mark.parametrize('r,q',[(0,0),(-1,0),(1,0),(1,-1)])
def test_zero_initial_is_explicit_incomplete_not_excluded(r,q):
    zero=poly(0,r,q,family='gas',index=1)
    with pytest.raises(SourceNetRootError):isolate_first_root(zero,F(1))
    out=order_inventory_roots((poly(1,-2),zero),F(1))
    assert out.status=='unsupported_zero_initial' and not out.complete
    assert out.zero_initial_labels==( ('gas',0,1), ) and out.earliest_labels==()
    assert len(out.roots)==1 and not out.exclusions
    out.check()


@pytest.mark.parametrize('bad',[
    poly(-1,0),poly(1,0,family='energy'),poly(1,0,cell=-1),
    replace(poly(1,0),initial=1.),replace(poly(1,0),linear=False),
    replace(poly(1,0),cell=True),
])
def test_invalid_polynomial_contract(bad):
    with pytest.raises(SourceNetRootError):isolate_first_root(bad,F(1))


@pytest.mark.parametrize('duration',[1.,F(),F(-1),True])
def test_invalid_duration(duration):
    with pytest.raises(SourceNetRootError):isolate_first_root(poly(1,-1),duration)


def test_forged_branch_enclosure_and_no_root_record():
    root=isolate_first_root(poly(1,-3,1),F(1))
    for change in ({'branch_lower':F(1,4)}, {'lower':F(1,8)}, {'root_kind':'exact_tangent'},
                   {'refinements':True}, {'upper':1.}):
        with pytest.raises(SourceNetRootError):replace(root,**change)
    fake=replace(root)
    object.__setattr__(fake,'branch_upper',F(1,8))
    with pytest.raises(SourceNetRootError):same_first_root(root,fake)
    exclusion=isolate_first_root(poly(1,-1,1),F(2))
    with pytest.raises(SourceNetRootError):replace(exclusion,minimum=F(1))
    object.__setattr__(exclusion,'minimum_time',F(1))
    with pytest.raises(SourceNetRootError):exclusion.check()


def test_forged_order_and_missing_competitor_rejected_by_saved_result_check():
    result=order_inventory_roots((poly(1,-2),poly(1,-4,cell=1)),F(1))
    for change in ({'earliest_labels':(('liquid',0,0),)}, {'roots':result.roots[:1]},
                   {'complete':1}, {'duration':F(2)}, {'zero_initial_labels':(('gas',0,1),)}):
        with pytest.raises(SourceNetRootError):replace(result,**change).check()
    with pytest.raises(SourceNetRootError):order_inventory_roots((poly(1,0),poly(1,0)),F(1))


def test_no_roots_result():
    result=order_inventory_roots((poly(1,0),poly(1,-1,1,cell=1)),F(1))
    assert result.status=='no_roots' and result.complete and len(result.exclusions)==2
    result.check()


def test_panel_root_origin_binding_and_no_extra_physics(monkeypatch):
    from test_source_net_panel import panel, sample
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    from sludge_sandbox.water_properties import WaterProperties
    def forbidden(*args,**kwargs):pytest.fail('pure roots called physics')
    for owner,name in ((ExactSourceColumn,'evaluate'),(SourceWetStorage,'invert'),(WaterProperties,'state_tp')):
        monkeypatch.setattr(owner,name,forbidden)
    origin=F(2**80)+F(1,3)
    base=panel(sample(F(),liquid=.25),sample(F(1,2),liquid=.25,role='interior'))
    shifted=panel(sample(origin,liquid=.25),sample(origin+F(1,2),liquid=.25,role='interior'),origin=origin)
    a,b=(order_source_panel_roots(p) for p in (base,shifted))
    assert a.order.status=='ordered' and a.order.earliest_labels==( ('liquid',0,0), )
    assert a.order==b.order and b.start.seconds-a.start.seconds==origin
    assert b.upper.seconds-a.upper.seconds==origin
    a.check();b.check()
    for changed in (replace(b,start=T(origin+1)),replace(b,sample_bindings=()),replace(b,order=object()),
                    replace(b,order=replace(b.order,polynomials=b.order.polynomials[:1]))):
        with pytest.raises(SourceNetRootError):changed.check()
    # All raw sample provenance is revalidated through the original panel.
    object.__setattr__(base.first.evaluation.source_evaluation,'source_ids',('changed',))
    with pytest.raises(ValueError):a.check()


def test_source_panel_cannot_hide_zero_gas_inventory():
    from test_source_net_panel import panel, sample
    from sludge_sandbox.integration import ConservedState
    import numpy as np
    def zero_gas(at,role):
        s=sample(at,role=role)
        originals=tuple(replace(row,gas_amounts_mol=(0.,*row.gas_amounts_mol[1:]))
                        for row in s.evaluation.source_states)
        amounts=np.array(s.state.amounts_mol);amounts[:,1]=0.
        packed=ConservedState(amounts,s.state.internal_energy_j,s.state.energy_model_identity)
        return replace(s,state=packed,evaluation=replace(s.evaluation,source_states=originals))
    p=panel(zero_gas(F(),'first'),zero_gas(F(1,2),'interior'))
    out=order_source_panel_roots(p)
    assert out.order.status=='unsupported_zero_initial' and not out.order.complete
    assert out.order.zero_initial_labels==tuple(('gas',i,1) for i in range(3))
    out.check()
