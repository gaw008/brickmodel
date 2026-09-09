from dataclasses import replace
from fractions import Fraction as F
import json,math
from pathlib import Path
import numpy as np
import pytest
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_affine_depletion import ExactAffineSamples,ExactAffineEvidence,locate_exact_affine,exact_depletion_writeback
from sludge_sandbox.depletion_roundoff import DepletionRoundoffPolicy,DepletionRoundoffTotals,DepletionRoundoffError,depletion_writeback
from sludge_sandbox.affine_depletion_clock import AffineDepletionClockEvidence
from sludge_sandbox.integration import ConservedState


def saved():return json.loads((Path(__file__).parent / 'fixtures' / 'exact-affine-depletion-v1' / 'saved-cell2.json').read_text())
def policy():return DepletionRoundoffPolicy(**saved()['roundoff_policy'])
def fixture():
    d=saved();c=d['clock']
    return ExactAffineSamples(T.from_float(c['start_s']),T.from_float(c['midpoint_s']),T.from_float(math.nextafter(c['end_s'],math.inf)),
        c['start_inventory_mol'],tuple(c['liquid_rates_start_mol_s']),tuple(c['liquid_rates_mid_mol_s']),d['evaporation_start'],d['evaporation_mid'],('saved-input:'+d['source_sha256'],))


def raw_for(evidence):
    n=float(F(evidence.samples.start_inventory_mol)+sum(map(F,evidence.signed_terms_mol),F()))
    return ConservedState([[n,.000001,7.],[2.,3.,4.]],[10.,20.],mechanical_stretches=[.9,.95,.99])


def write(e,p=None,totals=None,**changes):
    p=p or policy();args=dict(cell_index=0,liquid_index=0,vapor_index=1,panel_liquid_start_mol=e.samples.start_inventory_mol,
        panel_liquid_terms_mol=e.signed_terms_mol,positive_evaporated_mol=e.positive_evaporated_mol,policy=p,totals=totals or DepletionRoundoffTotals(p),clock_evidence=e)
    args.update(changes);return exact_depletion_writeback(raw_for(e),**args)


def test_actual_saved_float_clock_refuses_but_exact_clock_meets_same_local_gates():
    d=saved();c=d['clock'];p=policy();raw=ConservedState([[d['raw_liquid_mol'],1e-6]],[10.])
    old=AffineDepletionClockEvidence(**c)
    with pytest.raises(DepletionRoundoffError,match='correction_exceeds_evaporation_fraction'):
        depletion_writeback(raw,cell_index=0,liquid_index=0,vapor_index=1,panel_liquid_start_mol=c['start_inventory_mol'],panel_liquid_terms_mol=d['old_terms'],positive_evaporated_mol=d['old_gross'],policy=p,totals=DepletionRoundoffTotals(p),clock_evidence=old)
    e=locate_exact_affine(fixture(),time_absolute_s=1e-8,policy=p)
    out,record,total=write(e)
    assert out.amounts_mol[0,0]==0 and total.events==1
    assert record.ideal_vapor_increment_mol<=F(e.positive_evaporated_mol)*F(p.correction_fraction_evaporated)
    assert e.upper.elapsed_since(e.lower)<=F(1e-8)
    assert e.samples.inventory(e.lower.elapsed_since(e.samples.start))>=0
    assert e.samples.inventory(e.upper.elapsed_since(e.samples.start))<=0
    assert type(e.lower) is T
    np.testing.assert_array_equal(out.internal_energy_j,raw_for(e).internal_energy_j)
    np.testing.assert_array_equal(out.mechanical_stretches,raw_for(e).mechanical_stretches)
    np.testing.assert_array_equal(out.amounts_mol[1],raw_for(e).amounts_mol[1])
    assert out.amounts_mol[0,2]==7.


def test_origin_translation_invariance_including_zero_and_large_origin():
    base=fixture();dur=base.upper.elapsed_since(base.start);mid=base.midpoint.elapsed_since(base.start);outputs=[]
    for origin in (F(),base.start.seconds,F(10**12)):
        s=replace(base,start=T(origin),midpoint=T(origin+mid),upper=T(origin+dur))
        e=locate_exact_affine(s,time_absolute_s=1e-8,policy=policy());outputs.append(e)
    assert len({e.lower.elapsed_since(e.samples.start) for e in outputs})==1
    assert len({e.signed_terms_mol for e in outputs})==1
    assert outputs[-1].lower.display().seconds_binary64==outputs[-1].samples.start.display().seconds_binary64


def test_multiple_signed_terms_each_once_rounded_and_mismatch_rejected():
    s=ExactAffineSamples(T(F()),T(F(1,10**10)),T(F(1,10**8)),1e-12,(.001,-.002,-.001),(.001,-.002,-.001),.001,.001,('analytic',))
    e=locate_exact_affine(s,time_absolute_s=1e-8,policy=policy());h=e.lower.elapsed_since(s.start)
    assert e.signed_terms_mol==tuple(float(F(x)*h) for x in s.liquid_rates_start_mol_s)
    write(e)
    bad=list(e.signed_terms_mol);bad[0]=math.nextafter(bad[0],math.inf);bad[2]-=bad[0]-e.signed_terms_mol[0]
    with pytest.raises(DepletionRoundoffError):write(e,panel_liquid_terms_mol=bad)


def test_positive_part_evaporation_integral_is_not_signed_or_net_removal():
    # Signed evaporation -1+4t crosses zero at 1/4; root inventory at 1/2.
    p=policy();s=ExactAffineSamples(T(F()),T(F(1,4)),T(F(1)),.5,(0.,0.,-1.),(0.,0.,-1.),-1.,0.,('analytic',))
    e=locate_exact_affine(s,time_absolute_s=1e-8,policy=p)
    h=e.lower.elapsed_since(s.start)
    assert e.exact_positive_evaporated_mol==2*(h-F(1,4))**2
    assert e.exact_positive_evaporated_mol!=h
    out,record,total=write(e)
    assert out.amounts_mol[0,0]==0 and record is None and total.events==0


def test_budget_bound_and_original_gross_binding_cannot_be_bypassed():
    s=fixture()
    with pytest.raises(DepletionRoundoffError,match='refinement_budget'):
        locate_exact_affine(s,time_absolute_s=1e-8,policy=policy(),maximum_refinements=1)
    e=locate_exact_affine(s,time_absolute_s=1e-8,policy=policy())
    with pytest.raises(DepletionRoundoffError,match='evaporation_mismatch'):write(e,positive_evaporated_mol=e.positive_evaporated_mol*2)
    with pytest.raises(DepletionRoundoffError):replace(e,lower=e.samples.start)
    with pytest.raises(DepletionRoundoffError):replace(e,iterations=True)


def test_atomic_cumulative_gate_failure_retains_original_state_and_totals():
    p=replace(policy(),cumulative_correction_absolute_mol=1e-30)
    e=locate_exact_affine(fixture(),time_absolute_s=1e-8,policy=p)
    initial_totals=DepletionRoundoffTotals(p)
    with pytest.raises(DepletionRoundoffError,match='cumulative_phase_correction_budget'):write(e,p,initial_totals)
    assert initial_totals.events==0 and initial_totals.numerical_phase_correction_mol==0


@pytest.mark.parametrize('change',[{'start_inventory_mol':True},{'evaporation_start_mol_s':float('nan')},{'liquid_rates_start_mol_s':(0.,0.,True)},{'source_ids':()},{'start':.5}])
def test_invalid_sample_inputs(change):
    with pytest.raises(DepletionRoundoffError):replace(fixture(),**change)


def test_exact_zero_writeback_still_checks_every_component_before_bypass():
    s=ExactAffineSamples(T(F()),T(F(1,4)),T(F(1)),.5,(.5,-.5,-1.),(.5,-.5,-1.),1.,1.,('analytic',))
    e=locate_exact_affine(s,time_absolute_s=1e-8,policy=policy())
    assert raw_for(e).amounts_mol[0,0]==0
    bad=list(e.signed_terms_mol);bad[0]+=.125;bad[1]-=.125
    with pytest.raises(DepletionRoundoffError,match='signed_panel_binding_mismatch'):write(e,panel_liquid_terms_mol=bad)


def test_signed_gross_crossing_from_positive_to_negative():
    s=ExactAffineSamples(T(F()),T(F(1,4)),T(F(1)),.5,(0.,0.,-1.),(0.,0.,-1.),1.,0.,('analytic',))
    e=locate_exact_affine(s,time_absolute_s=1e-8,policy=policy())
    assert e.exact_positive_evaporated_mol==F(1,8)
    assert e.positive_evaporated_mol==.125


def test_hand_constructed_evidence_cannot_use_wide_or_shifted_dyadic_bin():
    e=locate_exact_affine(fixture(),time_absolute_s=1e-8,policy=policy())
    width=e.upper.elapsed_since(e.lower)
    with pytest.raises(DepletionRoundoffError):replace(e,lower=e.lower.shifted(-width),upper=e.upper.shifted(-width))
    with pytest.raises(DepletionRoundoffError):replace(e,time_absolute_s=0.)
    with pytest.raises(DepletionRoundoffError):replace(e,iterations=e.iterations+1)
