from dataclasses import replace
from fractions import Fraction as F
import pytest
from sludge_sandbox.mass_wet_writeback import *
from sludge_sandbox.exact_affine_depletion import ExactAffineSamples,locate_exact_affine


def policy():
    return DepletionRoundoffPolicy(correction_absolute_mol=1e-15,correction_fraction_evaporated=1e-8,storage_absolute_mol=1e-15,cumulative_storage_absolute_mol=1e-14,element_absolute_mol=2e-15,cumulative_element_absolute_mol=2e-14,mass_absolute_kg=1e-16,cumulative_mass_absolute_kg=1e-15,cumulative_correction_absolute_mol=1e-14,molar_mass_kg_mol=.018015268)


def setup(p=None,zero=False):
    p=p or policy(); sources=('manufactured:local-projection',)
    samples=ExactAffineSamples(ExactEventTime(F()),ExactEventTime(F(1,4) if zero else F(1,10**10)),ExactEventTime(F(1) if zero else F(2,10**9)),.5 if zero else 1e-12,(0.,0.,-1. if zero else -.001),(0.,0.,-1. if zero else -.001),1. if zero else .001,1. if zero else .001,sources)
    clock=locate_exact_affine(samples,time_absolute_s=1e-8,policy=p)
    first=WetMixedState((.01,.002),samples.start_inventory_mol,(.2,.3,1e-6),17.,'a'*64)
    other=WetMixedState((.03,.001),.02,(.1,.4,1e-6),19.,'b'*64)
    panel=MixedCellPanelTerms(((0.,),(0.,)),clock.signed_terms_mol,((0.,),(0.,),tuple(-x for x in clock.signed_terms_mol)),(0.,))
    stationary=MixedCellPanelTerms(((0.,),(0.,)),(0.,),((0.,),(0.,),(0.,)),(0.,))
    raw=replace(first,liquid_water_mol=float(F(first.liquid_water_mol)+sum(map(F,panel.liquid_mol),F())),gas_amounts_mol=first.gas_amounts_mol[:2]+(float(F(first.gas_amounts_mol[2])+sum(map(F,panel.gas_mol[2]),F())),))
    ev=MixedTerminalEvidence(0,(first,other),(raw,other),(panel,stationary),('wet','wet'),'c'*64,sources,clock)
    originals=(replace(first,liquid_water_mol=1.),other)
    ctx=MixedWritebackContext(originals,ExactEventTime(F()),'c'*64,sources,p.molar_mass_kg_mol,p,F('1e-8'))
    return ev,ctx,MixedWritebackTotals.empty(ctx)


def test_fraction_storage_identity_and_only_selected_phase_changes():
    e,c,t=setup();result=project_mixed_depletion(e,context=c,totals=t);r=result.record
    assert r is not None and r.ideal_vapor_increment_mol>0
    a,b=e.raw_states[0],result.states[0]
    assert b.liquid_water_mol==0 and b.solid_mass_kg==a.solid_mass_kg and b.internal_energy_j==a.internal_energy_j
    assert b.gas_amounts_mol[:2]==a.gas_amounts_mol[:2] and result.states[1] is e.raw_states[1]
    assert F(b.gas_amounts_mol[2])-F(a.gas_amounts_mol[2])-F(a.liquid_water_mol)==r.vapor_storage_roundoff_mol
    assert result.totals.aggregate.events==1 and t.aggregate.events==0
    assert result.totals.aggregate.numerical_phase_correction_mol==F(a.liquid_water_mol)


def test_zero_is_noop_but_source_guard_still_runs():
    e,c,t=setup(zero=True);out=project_mixed_depletion(e,context=c,totals=t)
    assert out.record is None and out.totals is t
    with pytest.raises(DepletionRoundoffError,match='source_binding'):
        project_mixed_depletion(replace(e,operator_identity='d'*64),context=c,totals=t)


def test_original_fraction_is_additional_and_per_cell_cumulative():
    e,c,t=setup();delta=F(e.raw_states[0].liquid_water_mol)
    small=replace(c,original_liquid_fraction_limit=delta/2)
    with pytest.raises(DepletionRoundoffError,match='original_cell_liquid_fraction_budget'):
        project_mixed_depletion(e,context=small,totals=MixedWritebackTotals.empty(small))
    c=replace(c,original_liquid_fraction_limit=delta*F(3,2))
    prior=DepletionRoundoffTotals(c.policy,F(),F(),delta,1)
    t=MixedWritebackTotals(c,(prior,DepletionRoundoffTotals(c.policy)))
    with pytest.raises(DepletionRoundoffError,match='original_cell_liquid_fraction_budget'):project_mixed_depletion(e,context=c,totals=t)
    assert t.per_cell[0] is prior and e.raw_states[0].liquid_water_mol>0


def test_global_cumulative_original_gate_fails_atomically():
    e,c,t=setup(replace(policy(),cumulative_correction_absolute_mol=1e-30))
    with pytest.raises(DepletionRoundoffError,match='cumulative_phase_correction_budget'):project_mixed_depletion(e,context=c,totals=t)
    assert t.aggregate.events==0 and e.raw_states[0].liquid_water_mol>0


@pytest.mark.parametrize('change',[{'cell_index':True},{'modes':('dry','wet')},{'source_ids':('wrong',)},{'raw_states':()},{'panel_terms':()}])
def test_forged_or_incomplete_evidence_rejected(change):
    e,c,t=setup()
    with pytest.raises(DepletionRoundoffError):replace(e,**change)


@pytest.mark.parametrize('field,value',[('internal_energy_j',18.),('solid_mass_kg',(.02,.002)),('gas_amounts_mol',(.3,.3,1e-6))])
def test_whole_raw_state_cannot_be_substituted(field,value):
    e,c,t=setup()
    with pytest.raises(DepletionRoundoffError,match='whole_raw_panel_state_mismatch'):replace(e,raw_states=(replace(e.raw_states[0],**{field:value}),e.raw_states[1]))


@pytest.mark.parametrize('limit',[True,1e-8,F('1e-7'),F(0)])
def test_explicit_fraction_limit_is_strict(limit):
    e,c,t=setup()
    with pytest.raises(DepletionRoundoffError):replace(c,original_liquid_fraction_limit=limit)


@pytest.mark.parametrize('field', ['storage_absolute_mol','element_absolute_mol','mass_absolute_kg','cumulative_storage_absolute_mol','cumulative_element_absolute_mol','cumulative_mass_absolute_kg'])
def test_every_original_storage_budget_remains_active(field):
    e,c,t=setup();normal=project_mixed_depletion(e,context=c,totals=t)
    assert normal.record.vapor_storage_roundoff_mol!=0
    e,c,t=setup(replace(policy(),**{field:1e-40}))
    with pytest.raises(DepletionRoundoffError):project_mixed_depletion(e,context=c,totals=t)
    assert t.aggregate.events==0 and e.raw_states[0].liquid_water_mol>0


def test_original_water_mass_policy_and_whole_original_context_bound():
    e,c,t=setup()
    with pytest.raises(DepletionRoundoffError,match='same_water_molar_mass'):replace(c,water_molar_mass_kg_mol=.019)
    other=replace(c,original_states=(replace(c.original_states[0],internal_energy_j=2.),c.original_states[1]))
    with pytest.raises(DepletionRoundoffError,match='original_context_changed'):project_mixed_depletion(e,context=other,totals=t)


def test_frozen_instance_tampering_revalidated_at_use():
    e,c,t=setup();object.__setattr__(e,'cell_index',True)
    with pytest.raises(DepletionRoundoffError,match='selected_cell_index'):project_mixed_depletion(e,context=c,totals=t)


def test_gross_cannot_come_from_unrelated_phase_rate():
    e,c,t=setup()
    altered=replace(e.clock.samples,evaporation_start_mol_s=.002,evaporation_mid_mol_s=.002)
    wrong=replace(e.clock,samples=altered)
    with pytest.raises(DepletionRoundoffError,match='phase_only_liquid_sample_required'):replace(e,clock=wrong)
