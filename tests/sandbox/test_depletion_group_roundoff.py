"""Shared-panel accounting tests, explicit affine polynomials; no native EOS."""
from dataclasses import replace
from fractions import Fraction as F
import math
import numpy as np
import pytest
from sludge_sandbox.depletion_group_clock import AffineInventory, AffineDomain, RootInterval
from sludge_sandbox.depletion_group_roundoff import GroupMember, GroupRoundoffError, AffineLiquidTerms, writeback_exact_group
from sludge_sandbox.depletion_roundoff import DepletionRoundoffTotals, DepletionRoundoffError
from sludge_sandbox.integration import ConservedState, StepLedger
from test_depletion_roundoff import policy


def fixture(exact_zero=False):
    amounts=np.array([[.01,.1],[.01,.1],[.02,.1]])
    start=ConservedState(amounts,[12.,13.,14.],mechanical_stretches=[1.,1.,1.,1.])
    delta=F(math.ulp(.01))/4
    face_exact=[delta if exact_zero else 2*delta,delta,F(0),F(0)]
    faces=np.zeros((4,2));faces[:,0]=[float(v) for v in face_exact]
    component_terms=[];reaction=np.zeros((3,2))
    for i in range(3):
        values=(face_exact[i],-face_exact[i+1],-F(.01)-face_exact[i]+face_exact[i+1])
        component_terms.append(AffineLiquidTerms(i,values,(F(0),)*3))
        reaction[i,0]=float(values[2])
    panel=StepLedger(0.,1.,faces,np.zeros(4),reaction,np.array([.25,.5,.75]),
                     stretch_increment=np.array([.125]*4),stretch_quadrature_roundoff=(F(0),)*4)
    raw_n=np.array([[float(F(float(amounts[i,j]))+F(float(faces[i,j]))-F(float(faces[i+1,j]))+F(float(reaction[i,j]))) for j in range(2)] for i in range(3)])
    raw=ConservedState(raw_n,[12.25,13.5,14.75],mechanical_stretches=[1.125]*4)
    models=tuple(AffineInventory(i,F(float(amounts[i,0])),F(-.01),F(0)) for i in range(3))
    domain=AffineDomain(F(0),F(3),3,models)
    p=policy(cumulative_storage_absolute_mol=1e-17,cumulative_element_absolute_mol=2e-17,
             cumulative_mass_absolute_kg=4e-19,storage_absolute_mol=2e-18,
             element_absolute_mol=4e-18,mass_absolute_kg=4e-20)
    args=dict(domain=domain,roots=(RootInterval(0,F(1),F(1)),RootInterval(1,F(1),F(1)),RootInterval(2,F(2),F(2))),
              members=(GroupMember(1,.01),GroupMember(0,.01)),liquid_terms=tuple(component_terms),time_gate_s=F(1,100000000),
              liquid_index=0,vapor_index=1,policy=p,totals=DepletionRoundoffTotals(p))
    return start,raw,panel,args


def test_atomic_shared_writeback_once_only_and_energy_mechanics_preserved():
    initial,raw,panel,args=fixture()
    result=writeback_exact_group(initial,raw,panel,**args)
    delta=F(float(raw.amounts_mol[0,0]))
    assert result.members==(0,1) and result.totals.events==2
    assert result.totals.numerical_phase_correction_mol==2*delta
    assert result.totals.signed_storage_roundoff_mol==-2*delta
    assert np.array_equal(result.state.internal_energy_j,raw.internal_energy_j)
    assert np.array_equal(result.state.mechanical_stretches,raw.mechanical_stretches)
    assert np.array_equal(result.state.amounts_mol[2],raw.amounts_mol[2])
    assert all(result.state.amounts_mol[i,0]==0 for i in (0,1))
    assert args['totals'].events==0 and raw.amounts_mol[0,0]>0
    assert sum((F(float(result.state.amounts_mol[i,j]))-F(float(raw.amounts_mol[i,j])) for i in range(3) for j in range(2)),F())==result.totals.signed_storage_roundoff_mol


def test_exact_zero_member_has_none_and_no_cost_count():
    initial,raw,panel,args=fixture(exact_zero=True)
    result=writeback_exact_group(initial,raw,panel,**args)
    assert result.corrections[0] is None and result.corrections[1] is not None
    assert result.totals.events==1


def test_late_local_fraction_failure_cannot_borrow_or_partially_commit():
    initial,raw,panel,args=fixture();before=raw.amounts_mol.copy();totals=args['totals']
    args['members']=(GroupMember(0,100.),GroupMember(1,0.))
    with pytest.raises(DepletionRoundoffError,match='evaporation_fraction'):
        writeback_exact_group(initial,raw,panel,**args)
    assert np.array_equal(raw.amounts_mol,before) and totals.events==0


def test_group_cumulative_budget_applies_after_each_local_success():
    initial,raw,panel,args=fixture();delta=float(raw.amounts_mol[0,0])
    p=replace(args['policy'],cumulative_correction_absolute_mol=delta)
    args.update(policy=p,totals=DepletionRoundoffTotals(p))
    with pytest.raises(DepletionRoundoffError):writeback_exact_group(initial,raw,panel,**args)
    assert args['totals'].events==0


@pytest.mark.parametrize('members',[(GroupMember(0,.01),),(GroupMember(0,.01),GroupMember(0,.01)),
                                     (GroupMember(0,.01),GroupMember(1,.01),GroupMember(2,.01))])
def test_missing_duplicate_extra_members_rejected(members):
    initial,raw,panel,args=fixture();args['members']=members
    with pytest.raises(GroupRoundoffError,match='members'):writeback_exact_group(initial,raw,panel,**args)


def test_omitted_root_and_earlier_nonmember_refused():
    initial,raw,panel,args=fixture();args['roots']=args['roots'][:2]
    with pytest.raises(ValueError,match='all_first_roots'):writeback_exact_group(initial,raw,panel,**args)
    initial,raw,panel,args=fixture()
    models=list(args['domain'].inventories);models[2]=replace(models[2],rate_mol_s=F(-.08))
    args['domain']=replace(args['domain'],inventories=tuple(models))
    args['roots']=args['roots'][:2]+(RootInterval(2,F(1,4),F(1,4)),)
    with pytest.raises(GroupRoundoffError,match='earliest_exact'):writeback_exact_group(initial,raw,panel,**args)


def test_panel_clock_and_raw_binding_checked():
    initial,raw,panel,args=fixture()
    with pytest.raises(GroupRoundoffError,match='clock'):
        writeback_exact_group(initial,raw,replace(panel,end_s=.5),**args)
    changed=ConservedState(raw.amounts_mol,raw.internal_energy_j+1,mechanical_stretches=raw.mechanical_stretches)
    with pytest.raises(GroupRoundoffError,match='raw_energy'):
        writeback_exact_group(initial,changed,panel,**args)


def test_nonrepresentable_shared_absolute_clock_is_explicitly_unsupported():
    initial,raw,panel,args=fixture()
    args['domain']=replace(args['domain'],start_s=F(2**60))
    with pytest.raises(GroupRoundoffError,match='nonrepresentable_shared_clock'):
        writeback_exact_group(initial,raw,panel,**args)


@pytest.mark.parametrize('bad',[True,float('nan'),float('inf'),-.1,'0'])
def test_gross_evaporation_validation(bad):
    with pytest.raises(GroupRoundoffError):GroupMember(0,bad)


def test_existing_prefix_totals_are_retained_without_reset():
    initial,raw,panel,args=fixture()
    previous=F(1,10**20)
    seeded=DepletionRoundoffTotals(args['policy'],-previous,previous,previous,1)
    args['totals']=seeded
    result=writeback_exact_group(initial,raw,panel,**args)
    delta=F(float(raw.amounts_mol[0,0]))
    assert result.totals.events==3
    assert result.totals.numerical_phase_correction_mol==previous+2*delta
    assert result.totals.absolute_storage_roundoff_mol==previous+2*delta
    assert seeded.events==1 and seeded.numerical_phase_correction_mol==previous


def test_unrelated_affine_source_cannot_borrow_exact_zero_root():
    initial,raw,panel,args=fixture(exact_zero=True)
    # Change the asserted affine acceleration without changing the actual panel.
    # Both models still have the same exact first root at t=1.
    models=list(args['domain'].inventories)
    p=models[0]
    models[0]=replace(p,rate_mol_s=F(0),acceleration_mol_s2=-2*p.initial_mol)
    args['domain']=replace(args['domain'],inventories=tuple(models))
    with pytest.raises(GroupRoundoffError,match='affine'):
        writeback_exact_group(initial,raw,panel,**args)


def test_nonmember_affine_evidence_is_checked_before_group_writeback():
    initial,raw,panel,args=fixture()
    models=list(args['domain'].inventories)
    models[2]=replace(models[2],rate_mol_s=F(0),acceleration_mol_s2=-F(.01))
    args['domain']=replace(args['domain'],inventories=tuple(models))
    with pytest.raises(GroupRoundoffError,match='affine_model_component'):
        writeback_exact_group(initial,raw,panel,**args)
    assert args['totals'].events==0


def test_component_integrals_cannot_be_replaced_by_only_equal_net():
    initial,raw,panel,args=fixture(exact_zero=True)
    terms=list(args['liquid_terms']);t=terms[0]
    rates=list(t.start_rates_mol_s);rates[0]+=F(1);rates[2]-=F(1)
    terms[0]=replace(t,start_rates_mol_s=tuple(rates));args['liquid_terms']=tuple(terms)
    with pytest.raises(GroupRoundoffError,match='affine_component_quadrature'):
        writeback_exact_group(initial,raw,panel,**args)


def test_huge_integer_gross_is_structured_error():
    with pytest.raises(GroupRoundoffError,match='unrepresentable_gross'):
        GroupMember(0,10**1000)
