from fractions import Fraction as F
from dataclasses import replace
from decimal import Decimal,localcontext
import numpy as np
import pytest
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.integration import ConservedState,Rates
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy
from sludge_sandbox.exact_root_order import order_exact_affine_roots,verify_exact_root_order,ExactRootOrderError


def inputs(amounts=(.01,.01),initial=(-1.,-1.),acceleration=(0.,-100.),origin=F()):
    cells=len(amounts);mid=F(1,200);upper=F(1,50)
    def rates(t):
        source=np.array([[float(F(r)+F(a)*t),0.] for r,a in zip(initial,acceleration)])
        return Rates(np.zeros((cells+1,2)),np.zeros(cells+1),source,np.zeros(cells))
    p=DepletionRoundoffPolicy(correction_absolute_mol=1e-15,correction_fraction_evaporated=1e-8,storage_absolute_mol=1e-15,cumulative_storage_absolute_mol=1e-14,element_absolute_mol=2e-15,cumulative_element_absolute_mol=2e-14,mass_absolute_kg=1e-16,cumulative_mass_absolute_kg=1e-15,cumulative_correction_absolute_mol=1e-14,molar_mass_kg_mol=.018015268)
    state=ConservedState([[n,0.] for n in amounts],[1.]*cells);first=rates(F());second=rates(mid)
    args=(state,first,second)
    kwargs=dict(start=T(origin),midpoint=T(origin+mid),upper=T(origin+upper),liquid_index=0,wet_cells=tuple(i for i,n in enumerate(amounts) if n>0),evaporation_start_mol_s=tuple(-float(x) for x in first.reaction_species_mol_s[:,0]),evaporation_mid_mol_s=tuple(-float(x) for x in second.reaction_species_mol_s[:,0]),source_binding=('analytic-same-panel',),time_absolute_s=1e-8,policy=p)
    return args,kwargs


def test_tangent_tie_separates_by_actual_affine_acceleration():
    args,kw=inputs();r=order_exact_affine_roots(*args,**kw)
    assert r.selected_cell==1 and len(r.candidates)==2 and not r.exclusions
    with localcontext() as ctx:
        ctx.prec=60
        expected=float((Decimal(3).sqrt()-1)/100)
    bycell={c.cell_index:c.evidence for c in r.candidates}
    assert float(bycell[1].lower.seconds)<=expected<=float(bycell[1].upper.seconds)
    assert bycell[1].upper<bycell[0].lower
    verify_exact_root_order(r,*args,**kw)


def test_strict_gap_below_time_gate_and_all_candidates_retained():
    args,kw=inputs(amounts=(.01,.01+1e-9),acceleration=(0.,0.));r=order_exact_affine_roots(*args,**kw)
    assert r.selected_cell==0
    a,b=[c.evidence for c in r.candidates]
    assert a.upper<b.lower and b.upper.elapsed_since(a.lower)<F(kw['time_absolute_s'])


def test_equal_root_different_tangents_is_explicitly_unsupported():
    # N0=.5-t and N1=.75-t-t² share first root .5, but initial N/-rate differs.
    args,kw=inputs(amounts=(.5,.75),initial=(-1.,-1.),acceleration=(0.,-2.))
    kw.update(midpoint=T(F(1,4)),upper=T(F(1)))
    second=replace(args[2],reaction_species_mol_s=np.array([[-1.,0.],[-1.5,0.]]))
    with pytest.raises(ExactRootOrderError,match='coincident'):
        order_exact_affine_roots(args[0],args[1],second,**kw)


def test_exclusion_is_whole_domain_positive_even_with_interior_vertex():
    args,kw=inputs(amounts=(.01,1.),initial=(-1.,-1.),acceleration=(0.,100.))
    r=order_exact_affine_roots(*args,**kw)
    assert r.selected_cell==0 and len(r.candidates)==1 and len(r.exclusions)==1
    e=r.exclusions[0]
    assert e.minimum_mol==F(1)-F(1,200) and e.cell_index==1


def test_possible_interior_zero_with_nonmonotone_rates_is_not_excluded():
    args,kw=inputs(amounts=(.01,.001),initial=(-1.,-1.),acceleration=(0.,100.))
    with pytest.raises(ExactRootOrderError,match='unsupported_candidate:1:monotone'):
        order_exact_affine_roots(*args,**kw)


def test_missing_or_duplicate_positive_cells_and_source_rebinding_refused():
    args,kw=inputs();r=order_exact_affine_roots(*args,**kw)
    for cells in ((0,),(0,0),(True,1),(1,0)):
        with pytest.raises(ExactRootOrderError):order_exact_affine_roots(*args,**dict(kw,wet_cells=cells))
    with pytest.raises(ExactRootOrderError,match='mismatch'):
        verify_exact_root_order(r,*args,**dict(kw,source_binding=('different',)))
    with pytest.raises(ExactRootOrderError):order_exact_affine_roots(*args,**dict(kw,source_binding=()))
    with pytest.raises(ExactRootOrderError):verify_exact_root_order(replace(r,candidates=r.candidates[:1]),*args,**kw)


def test_large_origin_preserves_semantic_root_order_and_offsets():
    args,kw=inputs();r=order_exact_affine_roots(*args,**kw)
    _,shifted=inputs(origin=F(10**12));s=order_exact_affine_roots(*args,**shifted)
    assert r.selected_cell==s.selected_cell
    assert [c.evidence.lower.elapsed_since(kw['start']) for c in r.candidates]==[c.evidence.lower.elapsed_since(shifted['start']) for c in s.candidates]
    assert r.input_sha256!=s.input_sha256


def test_zero_inventory_not_in_wet_set_but_all_input_arrays_still_bound():
    args,kw=inputs(amounts=(.01,0.),initial=(-1.,0.),acceleration=(0.,0.))
    r=order_exact_affine_roots(*args,**kw);assert r.wet_cells==(0,)
    changed=replace(args[2],cell_power_w=np.array([0.,1.]))
    with pytest.raises(ExactRootOrderError,match='mismatch'):verify_exact_root_order(r,args[0],args[1],changed,**kw)


def test_no_roots_and_finite_refinement_limit_explicit():
    args,kw=inputs(amounts=(1.,1.),initial=(-1.,-1.),acceleration=(0.,0.))
    with pytest.raises(ExactRootOrderError,match='no_roots'):order_exact_affine_roots(*args,**kw)
    args,kw=inputs()
    with pytest.raises(ExactRootOrderError,match='refinement_budget'):order_exact_affine_roots(*args,**dict(kw,maximum_refinements=1))


def test_three_equal_first_roots_preserve_full_failed_candidate_set():
    args,kw=inputs(amounts=(.01,.01,.01),initial=(-1.,-1.,-1.),acceleration=(0.,0.,0.))
    with pytest.raises(ExactRootOrderError,match='coincident') as failure:order_exact_affine_roots(*args,**kw)
    diagnostic=failure.value.diagnostic
    assert diagnostic[1]==(0,1,2) and tuple(row[0] for row in diagnostic[3])==(0,1,2)


def test_later_equal_roots_do_not_block_strictly_earlier_event():
    args,kw=inputs(amounts=(.005,.01,.01),initial=(-1.,-1.,-1.),acceleration=(0.,0.,0.))
    r=order_exact_affine_roots(*args,**kw)
    assert r.selected_cell==0 and len(r.candidates)==3


@pytest.mark.parametrize('mutation',[
    lambda r:replace(r,selected_cell=True),
    lambda r:replace(r,wet_cells=(False,True)),
    lambda r:replace(r,candidates=(replace(r.candidates[0],cell_index=False),*r.candidates[1:])),
    lambda r:replace(r,candidates=list(r.candidates)),
])
def test_verifier_rejects_equal_values_with_wrong_exact_types(mutation):
    args,kw=inputs();r=order_exact_affine_roots(*args,**kw)
    with pytest.raises(ExactRootOrderError):verify_exact_root_order(mutation(r),*args,**kw)


def test_nested_evidence_time_and_policy_types_cannot_be_forged():
    from copy import copy
    args,kw=inputs();r=order_exact_affine_roots(*args,**kw)
    e=r.candidates[0].evidence
    for slot,value in (('time_absolute_s',F(e.time_absolute_s)),('iterations',float(e.iterations))):
        forged=copy(e);object.__setattr__(forged,slot,value)
        candidate=replace(r.candidates[0],evidence=forged)
        with pytest.raises(ExactRootOrderError):verify_exact_root_order(replace(r,candidates=(candidate,*r.candidates[1:])),*args,**kw)
    forged_time=copy(e.samples.start);object.__setattr__(forged_time,'seconds',False)
    forged_samples=copy(e.samples);object.__setattr__(forged_samples,'start',forged_time)
    forged_e=copy(e);object.__setattr__(forged_e,'samples',forged_samples)
    candidate=replace(r.candidates[0],evidence=forged_e)
    with pytest.raises(ExactRootOrderError):verify_exact_root_order(replace(r,candidates=(candidate,*r.candidates[1:])),*args,**kw)


def test_exclusion_fraction_cannot_be_replaced_with_equal_float():
    args,kw=inputs(amounts=(.01,1.),initial=(-1.,0.),acceleration=(0.,0.))
    r=order_exact_affine_roots(*args,**kw)
    forged=replace(r.exclusions[0],minimum_mol=1.)
    with pytest.raises(ExactRootOrderError):verify_exact_root_order(replace(r,exclusions=(forged,)),*args,**kw)
