"""Explicit polynomial counterexamples, independent rational roots; no EOS."""
from fractions import Fraction as F
import math
import pytest
from sludge_sandbox.depletion_group_clock import (
    AffineInventory, AffineDomain, RootInterval, GroupClockError,
    positive_panel, isolate_roots, group_roots, outward_absolute_times,
)


def model(i,n,r,a=0):
    return AffineInventory(i,F(n),F(r),F(a))


def domain(*models,duration=4,start=0):
    return AffineDomain(F(start),F(duration),len(models),tuple(models))


def test_equal_tangents_different_acceleration_do_not_prove_common_root():
    d=domain(model(0,1,-1),model(1,1,-1,-2))
    roots=isolate_roots(d,F(1,10000))
    result=group_roots(d,roots,F(1,1000))
    assert roots[0].cell_index==1
    assert result.strict_order_edges==((1,0),)
    assert all(g.status=='ordered' for g in result.groups)
    # Independent root equation t²+t−1 brackets the positive golden root.
    lo,hi=roots[0].lower_s,roots[0].upper_s
    assert lo*lo+lo-1<=0<=hi*hi+hi-1
    assert hi-lo<=F(1,10000)


def test_different_tangents_exact_same_root():
    # N0=1−t; N1=3−t−2t², both first vanish at t=1.
    d=domain(model(0,1,-1),model(1,3,-1,-4),duration=2)
    roots=isolate_roots(d,F(1,100))
    analysis=group_roots(d,roots,F(1,100))
    assert analysis.groups[0].status=='exact_common_root'
    assert analysis.groups[0].lower_s==analysis.groups[0].upper_s==1
    assert d.inventories[0].initial_mol/-d.inventories[0].rate_mol_s != d.inventories[1].initial_mol/-d.inventories[1].rate_mol_s


def test_overlap_chain_keeps_union_not_intersection():
    d=domain(model(0,2,-1),model(1,3,-1),model(2,4,-1),duration=5)
    roots=(RootInterval(0,F(1),F(2)),RootInterval(1,F(2),F(3)),RootInterval(2,F(3),F(4)))
    analysis=group_roots(d,roots,F(1))
    assert analysis.groups[0].members==(0,1,2)
    assert (analysis.groups[0].lower_s,analysis.groups[0].upper_s)==(1,4)
    assert analysis.groups[0].status=='unresolved_wide_cluster'


def test_earlier_nonmember_cannot_be_omitted_and_index_is_not_time_order():
    d=domain(model(0,3,-1),model(1,1,-1),model(2,10,1))
    roots=isolate_roots(d,F(1,100))
    analysis=group_roots(d,roots,F(1,100))
    assert analysis.groups[0].members==(1,)
    assert analysis.no_depletion_cells==(2,)
    with pytest.raises(GroupClockError,match='all_first_roots'):
        group_roots(d,tuple(r for r in roots if r.cell_index==0),F(1,100))


def test_positive_endpoints_negative_interior_reject_panel_and_find_first_root():
    # N=(t−1)(t−3), positive at t=0 and4, negative at vertex2.
    d=domain(model(0,3,-4,2))
    assert d.inventories[0].amount(F(4))>0
    with pytest.raises(GroupClockError,match='not_strictly_positive'):positive_panel(d,F(4))
    roots=isolate_roots(d,F(1,100))
    assert roots==(RootInterval(0,F(1),F(1)),)
    with pytest.raises(GroupClockError,match='first_root_branch'):
        group_roots(d,(RootInterval(0,F(3),F(3)),),F(1,100))


def test_tangent_touch_is_an_event_and_strict_positivity_stops_before_it():
    d=domain(model(0,1,-2,2),duration=2)
    assert positive_panel(d,F(1,2))==(F(1,4),)
    with pytest.raises(GroupClockError):positive_panel(d,F(1))
    assert isolate_roots(d,F(1,100))==(RootInterval(0,F(1),F(1)),)


def test_initial_growth_then_depletion_and_no_event_domain():
    d=domain(model(0,2,1,-2),model(1,1,1,2),duration=2)
    assert isolate_roots(d,F(1,100))==(RootInterval(0,F(2),F(2)),)
    assert group_roots(d,isolate_roots(d,F(1,100)),F(1,100)).no_depletion_cells==(1,)
    short=domain(model(0,2,1,-2),duration=1)
    assert isolate_roots(short,F(1,100))==()
    assert group_roots(short,(),F(1,100)).groups==()


def test_large_clock_outward_enclosure_does_not_fake_represented_exact_time():
    d=domain(model(0,1,-3),start=2**60,duration=1)
    root=RootInterval(0,F(1,3),F(1,3))
    group_roots(d,(root,),F(1,100000000))
    lo,hi=outward_absolute_times(d,root)
    true=F(2**60)+F(1,3)
    assert F(lo)<true<F(hi)
    assert hi==math.nextafter(lo,math.inf)
    assert F(hi)-F(lo)>F(1,100000000)


@pytest.mark.parametrize('bad',[True,1.,float('nan'),float('inf'),'1'])
def test_coefficients_require_explicit_exact_fractions(bad):
    with pytest.raises(GroupClockError):AffineInventory(0,bad,F(-1),F(0))


def test_incomplete_mutable_duplicate_or_nonpositive_models_refused():
    p=model(0,1,-1)
    for items,count in (([p],1),((p,),2),((p,p),2)):
        with pytest.raises(GroupClockError):AffineDomain(F(0),F(1),count,items)
    with pytest.raises(GroupClockError):model(0,0,-1)
    with pytest.raises(GroupClockError):AffineDomain(F(0),F(1),True,(p,))
    with pytest.raises(GroupClockError):RootInterval(True,F(0),F(1))


def test_insufficient_iteration_budget_fails_and_narrow_cluster_not_common():
    d=domain(model(0,1,0,-4)) # irrational root sqrt(1/2)
    with pytest.raises(GroupClockError,match='resolution_budget'):
        isolate_roots(d,F(1,1000000),maximum_bisections=1)
    d=domain(model(0,1,-1),model(1,F(1001,1000),-1),duration=2)
    roots=(RootInterval(0,F(999,1000),F(1)),RootInterval(1,F(1),F(1001,1000)))
    result=group_roots(d,roots,F(1,100))
    assert result.groups[0].status=='unresolved_narrow_cluster'


def test_arbitrary_exact_root_claim_is_rechecked():
    d=domain(model(0,1,-1))
    with pytest.raises(GroupClockError,match='exact_root_proof'):
        group_roots(d,(RootInterval(0,F(1,2),F(1,2)),),F(1,100))
