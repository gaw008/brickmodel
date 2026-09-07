"""Event write-back storage rounding, distinct from numerical phase correction."""
from dataclasses import replace
from fractions import Fraction
import math
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState
from sludge_sandbox.depletion_roundoff import (
    DepletionRoundoffError, DepletionRoundoffPolicy, DepletionRoundoffTotals,
    depletion_writeback,
)


def policy(**changes):
    values=dict(correction_absolute_mol=1e-17, correction_fraction_evaporated=1e-8,
        storage_absolute_mol=1e-18, cumulative_storage_absolute_mol=2e-18,
        element_absolute_mol=2e-18, cumulative_element_absolute_mol=4e-18,
        mass_absolute_kg=4e-20, cumulative_mass_absolute_kg=8e-20,
        cumulative_correction_absolute_mol=1e-16, molar_mass_kg_mol=.018)
    values.update(changes)
    return DepletionRoundoffPolicy(**values)


def case(p=None, totals=None, **changes):
    p=p or policy()
    delta=math.ulp(.01)/2
    state=ConservedState([[delta,.1,7.]],[12.])
    args=dict(cell_index=0,liquid_index=0,vapor_index=1,
        panel_liquid_start_mol=.01,panel_liquid_terms_mol=(-.01,delta),
        positive_evaporated_mol=.01,policy=p,
        totals=totals or DepletionRoundoffTotals(p))
    args.update(changes)
    return state,depletion_writeback(state,**args)


def test_unrepresentable_pair_is_budgeted_without_inventing_evaporation():
    old,(new,event,total)=case()
    d=Fraction(float(old.amounts_mol[0,0]))
    assert new.amounts_mol[0,0]==0
    assert new.amounts_mol[0,1]==old.amounts_mol[0,1]
    assert event.ideal_liquid_increment_mol==-d
    assert event.ideal_vapor_increment_mol==d
    assert event.vapor_storage_roundoff_mol==-d
    assert total.signed_storage_roundoff_mol==-d
    assert total.absolute_storage_roundoff_mol==d
    assert total.numerical_phase_correction_mol==d
    assert np.array_equal(new.internal_energy_j,old.internal_energy_j)
    assert new.amounts_mol[0,2]==7
    assert old.amounts_mol[0,0]>0
    with pytest.raises(ValueError):new.amounts_mol[0,0]=1


def test_prefix_absolute_budget_cannot_be_reset_by_small_local_events():
    p=policy()
    _,(_,_,one)=case(p)
    _,(_,_,two)=case(p,one)
    with pytest.raises(DepletionRoundoffError,match='cumulative_storage'):
        case(p,two)


def test_policy_identity_is_preserved_across_prefix():
    _,(_,_,totals)=case()
    with pytest.raises(DepletionRoundoffError,match='policy'):
        case(replace(policy(),cumulative_storage_absolute_mol=1.),totals)


@pytest.mark.parametrize('changes,reason',[
    ({'positive_evaporated_mol':1e-12},'evaporation_fraction'),
    ({'positive_evaporated_mol':0},'evaporation_fraction'),
    ({'panel_liquid_terms_mol':(-.011,)},'negative_panel'),
    ({'panel_liquid_terms_mol':(-.009,)},'panel_state_mismatch'),
    ({'vapor_index':0},'distinct'),
    ({'cell_index':True},'index'),
])
def test_invalid_event_inputs_are_not_clipped(changes,reason):
    with pytest.raises(DepletionRoundoffError,match=reason):case(**changes)


def test_element_and_mass_budgets_are_separate():
    with pytest.raises(DepletionRoundoffError,match='element'):
        case(policy(element_absolute_mol=1e-19))
    with pytest.raises(DepletionRoundoffError,match='mass'):
        case(policy(mass_absolute_kg=1e-22))


def test_exactly_representable_pair_has_zero_storage_residual():
    d=2.**-60
    state=ConservedState([[d,d]],[0.])
    p=policy()
    new,e,total=depletion_writeback(state,cell_index=0,liquid_index=0,vapor_index=1,
        panel_liquid_start_mol=.01,panel_liquid_terms_mol=(-.01,d),positive_evaporated_mol=.01,
        policy=p,totals=DepletionRoundoffTotals(p))
    assert new.amounts_mol[0,1]==2*d
    assert e.vapor_storage_roundoff_mol==0
    assert total.absolute_storage_roundoff_mol==0


def test_large_vapor_does_not_enlarge_phase_correction_limit():
    d=1e-10
    state=ConservedState([[d,1e20]],[0.])
    p=policy(correction_absolute_mol=1.)
    with pytest.raises(DepletionRoundoffError,match='local_ulp'):
        depletion_writeback(state,cell_index=0,liquid_index=0,vapor_index=1,
            panel_liquid_start_mol=.01,panel_liquid_terms_mol=(-.01,d),positive_evaporated_mol=1.,
            policy=p,totals=DepletionRoundoffTotals(p))


def test_power_of_two_upward_rounding_and_absolute_prefix_do_not_cancel():
    d=math.ulp(1.)/4
    p=policy(correction_absolute_mol=1e-15,storage_absolute_mol=1e-15,
        cumulative_storage_absolute_mol=1.5*d,element_absolute_mol=1e-14,
        cumulative_element_absolute_mol=1e-14,mass_absolute_kg=1e-14,
        cumulative_mass_absolute_kg=1e-14,cumulative_correction_absolute_mol=1e-14)
    state=ConservedState([[d,math.nextafter(1.,0.)]],[0.])
    args=dict(cell_index=0,liquid_index=0,vapor_index=1,panel_liquid_start_mol=1.,
        panel_liquid_terms_mol=(-1.,d),positive_evaporated_mol=1.,policy=p)
    _,first,totals=depletion_writeback(state,totals=DepletionRoundoffTotals(p),**args)
    assert first.vapor_after_mol==1.
    assert first.vapor_storage_roundoff_mol==Fraction(d)
    assert first.half_neighbor_spacing_mol==Fraction(d)
    state=ConservedState([[d,1.]],[0.])
    # This event would have the opposite signed residual, but its absolute
    # cumulative loss-of-resolution budget must still fail.
    with pytest.raises(DepletionRoundoffError,match='cumulative_storage'):
        depletion_writeback(state,totals=totals,**args)


def test_minimum_subnormal_increment_is_preserved_when_representable():
    d=math.ulp(0.)
    p=policy()
    state=ConservedState([[d,0.]],[0.])
    new,record,_=depletion_writeback(state,cell_index=0,liquid_index=0,vapor_index=1,
        panel_liquid_start_mol=.01,panel_liquid_terms_mol=(-.01,d),positive_evaporated_mol=.01,
        policy=p,totals=DepletionRoundoffTotals(p))
    assert new.amounts_mol[0,1]==d
    assert record.vapor_storage_roundoff_mol==0
    assert record.half_neighbor_spacing_mol==Fraction(d)/2


def test_prefix_json_roundtrip_retains_fraction_budgets():
    import json
    p=policy()
    _,(_,_,first)=case(p)
    restored=DepletionRoundoffTotals.from_record(json.loads(json.dumps(first.to_record())))
    assert restored==first
    _,(_,_,second)=case(p,restored)
    with pytest.raises(DepletionRoundoffError,match='cumulative_storage'):case(p,second)
    bad=first.to_record()
    bad['events']=0
    with pytest.raises(DepletionRoundoffError,match='empty_prefix'):
        DepletionRoundoffTotals.from_record(bad)


def test_nonzero_exact_panel_term_cannot_silently_underflow():
    with pytest.raises(DepletionRoundoffError,match='underflow'):
        case(panel_liquid_terms_mol=(-.01,math.ulp(.01)/2,Fraction(1,10**400)))
