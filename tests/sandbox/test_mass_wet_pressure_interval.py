from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
import pytest
from sludge_sandbox.water_interval_eos import Interval
from sludge_sandbox.mass_wet_pressure_interval import (
    PressureProofError,LiquidBranchModelPolicy,ProofBudget,QueryBoxes,
    BoundLiquidPressureRequest,connected_tube_density,pressure_radius_checked,
    encoded,ProofOperation,COEFFICIENT_SHA,
)


def iv(a,b):return Interval(D(a),D(b))


def proposals():
    return QueryBoxes(iv('55000','56000'),iv('54000','56001'),(iv('10','11'),iv('-4','-3')),
                      (D('10.5'),D('-3.5')),((D(1),D(0)),(D(0),D(1))),(D(1),D(1)))


def test_tube_must_include_full_native_box_even_if_mechanical_narrower():
    box=connected_tube_density(iv(50000,51000),iv(55000,56000),iv(54000,56001),iv(55500,55500))
    assert box==iv(50000,56001)
    # The function constructs only a proposal. Positivity must be proved on
    # this entire interval by the actual pinned tube routine at evaluation.
    with pytest.raises(PressureProofError,match='actual_native_density'):
        connected_tube_density(iv(50000,51000),iv(55000,56000),iv(54000,56001),iv(56002,56002))
    with pytest.raises(PressureProofError,match='coexistence_below'):
        connected_tube_density(iv(55000,55100),iv(55000,56000),iv(54000,56001),iv(55500,55500))


def test_original_ambiguity_strict_and_radius_exact_at_low_decimal_precision():
    with localcontext() as ctx:
        ctx.prec=6
        got=pressure_radius_checked(100000.,iv('99999.123456789','100001.987654321'),.125,
                                    iv(10000,1000000),(F(10000),F(1000000)),iv(3000,3001))
    assert got==F('1.987654321')+F(.125)
    boundary=F(10000)+F(.01)
    # Finite exact Decimal construction avoids silently testing a rounded face.
    with localcontext() as ctx:
        ctx.prec=100
        edge=D(boundary.numerator)/D(boundary.denominator)
    with pytest.raises(PressureProofError,match='ambiguity'):
        pressure_radius_checked(11000.,Interval(edge,D(12000)),0.,iv(10000,1000000),
                                (F(10000),F(1000000)),iv(10000,10000))


def test_full_pressure_interval_cannot_be_clipped_to_nominal_domain():
    with pytest.raises(PressureProofError,match='full_pressure_interval'):
        pressure_radius_checked(100000.,iv(9999,100001),.1,iv(10000,1000000),
                                (F(10000),F(1000000)),iv(3000,3001))


@pytest.mark.parametrize('changes',[{'maximum_proof_operations':True},{'maximum_boxes_per_primitive':3},
    {'maximum_wall_seconds':float('nan')},{'precision':True}])
def test_invalid_resources(changes):
    args=dict(maximum_proof_operations=4,maximum_boxes_per_primitive=256,maximum_wall_seconds=15.,precision=60)
    args.update(changes)
    with pytest.raises(PressureProofError):ProofBudget(**args)


def test_mutable_or_boolean_proposals_rejected():
    q=proposals()
    with pytest.raises(PressureProofError):replace(q,weights=[D(1),D(1)])
    with pytest.raises(PressureProofError):replace(q,preconditioner=((True,D(0)),(D(0),D(1))))
    with pytest.raises(PressureProofError):replace(q,center=(D('NaN'),D(0)))


def test_exact_evidence_bytes_and_unknown_cost_are_preserved():
    raw=encoded(ProofOperation('attempt','failed',.1,b'raw before failure','no root'))
    assert b'bytes_hex' in raw and b'726177206265666f7265206661696c757265' in raw


def test_generic_analytic_liquid_not_mislabelled_HEOS_query(monkeypatch):
    from test_mass_wet_exact_stage import setup
    pair,states=setup(monkeypatch)
    rate=pair.evaluate(states).cells[0]
    with pytest.raises(PressureProofError,match='explicit_HEOS'):
        BoundLiquidPressureRequest.capture(pair,states,rate,0)
    with pytest.raises(PressureProofError,match='cell_index'):
        BoundLiquidPressureRequest.capture(pair,states,rate,False)


def test_policy_source_bytes_checked_before_mathematics(tmp_path):
    pdf=tmp_path/'official.pdf';pdf.write_bytes(b'wrong')
    source=tmp_path/'water.json';source.write_bytes(b'wrong')
    with pytest.raises(PressureProofError,match='pinned_sources'):
        LiquidBranchModelPolicy(str(pdf),str(source),'a'*64)
    with pytest.raises(PressureProofError,match='limited_ordinary'):
        LiquidBranchModelPolicy(str(pdf),str(source),'a'*64,temperature_domain_k=(F(270),F(310)))


def test_original_inverse_epsilon_and_full_domain_not_nominal_only():
    from sludge_sandbox.mass_wet_pressure_interval import inverse_temperature_interval
    args=dict(returned_temperature=300.,total_energy=1.,target_energy=0.,energy_error=.5,
              minimum_cp=10.,epsilon=.2,energy_tolerance=2.,temperature_tolerance=.3,
              domains=((295.,310.),(299.,301.)),precision=60)
    actual,required=inverse_temperature_interval(**args)
    assert required==F(3,20)
    assert F(actual.lo)<=F(300)-F(.2) and F(actual.hi)>=F(300)+F(.2)
    for changed in ({'epsilon':.1},{'domains':((299.9,300.1),)}, {'minimum_cp':False}, {'energy_error':-.1}):
        with pytest.raises(PressureProofError):inverse_temperature_interval(**(args|changed))


def test_inverse_exact_residual_cannot_round_oversized_error_to_gate():
    from sludge_sandbox.mass_wet_pressure_interval import inverse_temperature_interval
    with pytest.raises(PressureProofError,match='original_inverse_energy'):
        inverse_temperature_interval(returned_temperature=300.,total_energy=1.,target_energy=-2.**-54,
            energy_error=0.,minimum_cp=1.,epsilon=2.,energy_tolerance=1.,temperature_tolerance=3.,
            domains=((295.,310.),),precision=60)


@pytest.fixture
def control_flow_only(monkeypatch):
    """Synthetic guards/parameters only; every math attempt fails, no proof PASS."""
    import types
    from sludge_sandbox import mass_wet_pressure_interval as mod
    stamp=['unchanged'];clock=[0.]
    monkeypatch.setattr(mod.LiquidBranchModelPolicy,'check_sources',lambda self:(stamp[0],))
    monkeypatch.setattr(mod.BoundLiquidPressureRequest,'check',lambda self:None)
    monkeypatch.setattr(mod,'time',types.SimpleNamespace(monotonic=lambda:clock[0]))
    policy=mod.LiquidBranchModelPolicy('not-a-source','not-a-source','a'*64)
    request=mod.BoundLiquidPressureRequest(None,(),None,0,'b'*64,'c'*64)
    parameters=mod.QueryParameters(iv(300,301),iv('0.1','0.2'),1.,iv(1,1),8.,iv(1,1),
         100000.,.1,iv(10000,1000000),(300.,100000.,1000.,.018,.018,1.,.000018,1e-16),F(0),F(0),b'isolated-control-flow')
    monkeypatch.setattr(mod,'parameters',lambda *args:parameters)
    def fail(*args,**kwargs):raise RuntimeError('mathematical_operation_sentinel')
    monkeypatch.setattr(mod.coex,'enclose_coexistence',fail)
    return mod,policy,request,stamp,clock


def test_operation_failure_retains_attempt_without_completion(control_flow_only):
    mod,policy,request,_,_=control_flow_only
    result=mod.IAPWS95LiquidPressureProvider().evaluate(request,branch_policy=policy,boxes=proposals(),
        budget=ProofBudget(4,8,5.))
    assert result.status=='unresolved' and result.pressure_radius_pa is None
    assert result.attempted_proof_operations==1 and result.completed_proof_operations==0
    assert result.operations[0].status=='failed' and 'sentinel' in result.operations[0].reason
    assert result.bottom_level_residual_evaluation_count is None and result.native_calls==0


@pytest.mark.parametrize('cancelled', [True,False])
def test_budget_and_cancel_do_not_enter_mathematics(control_flow_only,cancelled):
    mod,policy,request,_,_=control_flow_only
    result=mod.IAPWS95LiquidPressureProvider().evaluate(request,branch_policy=policy,boxes=proposals(),
        budget=ProofBudget(0,8,5.),cancel=lambda:cancelled)
    assert result.status=='unresolved' and not result.operations
    assert result.attempted_proof_operations==result.completed_proof_operations==0
    assert ('cancelled' if cancelled else 'proof_operation_budget') in result.reason


@pytest.mark.parametrize('change',['source','wall'])
def test_post_operation_guard_retains_completed_cost_and_evidence(control_flow_only,monkeypatch,change):
    mod,policy,request,stamp,clock=control_flow_only
    def completed(*args,**kwargs):
        if change=='source':stamp[0]='changed'
        else:clock[0]=6.
        return None  # Pure control-flow return; never a coexistence proof.
    monkeypatch.setattr(mod.coex,'enclose_coexistence',completed)
    result=mod.IAPWS95LiquidPressureProvider().evaluate(request,branch_policy=policy,boxes=proposals(),
        budget=ProofBudget(4,8,5.))
    assert result.status=='unresolved' and result.pressure_radius_pa is None
    assert result.attempted_proof_operations==result.completed_proof_operations==1
    assert result.operations[0].evidence_json==b'null'
    if change=='source':assert result.source_after!=result.source_before
    else:assert result.elapsed_seconds==6.>result.budget.maximum_wall_seconds


def test_additional_fixed_T_error_must_remain_in_original_pressure_domain():
    with pytest.raises(PressureProofError,match='full_pressure_interval'):
        pressure_radius_checked(10000.5,iv(10000,10001),.1,iv(10000,1000000),
                                (F(10000),F(1000000)),iv(3000,3001))


def test_changed_proposal_or_budget_cannot_hide_post_call(control_flow_only,monkeypatch):
    mod,policy,request,_,_=control_flow_only
    budget=ProofBudget(4,8,5.)
    def changed(*args,**kwargs):
        object.__setattr__(budget,'maximum_proof_operations',1000)
        return None
    monkeypatch.setattr(mod.coex,'enclose_coexistence',changed)
    result=mod.IAPWS95LiquidPressureProvider().evaluate(request,branch_policy=policy,boxes=proposals(),budget=budget)
    assert result.status=='unresolved' and result.source_before!=result.source_after
    assert result.budget.maximum_proof_operations==4
    assert result.completed_proof_operations==1


def test_request_mutation_preserves_original_failure_snapshot(control_flow_only,monkeypatch):
    mod,policy,request,_,_=control_flow_only
    object.__setattr__(request,'captured_query_json',b'original query')
    object.__setattr__(request,'captured_source_json',b'original source')
    original_id=request.numeric_identity
    def change(*args,**kwargs):
        object.__setattr__(request,'captured_query_json',b'changed query')
        object.__setattr__(request,'captured_source_json',b'changed source')
        object.__setattr__(request,'numeric_identity','d'*64)
        return None
    monkeypatch.setattr(mod.coex,'enclose_coexistence',change)
    result=mod.IAPWS95LiquidPressureProvider().evaluate(request,branch_policy=policy,boxes=proposals(),budget=ProofBudget(4,8,5.))
    assert result.status=='unresolved' and result.pressure_radius_pa is None
    assert result.request_sha256==original_id
    assert result.original_query_json==b'original query'
    assert result.original_source_json==b'original source'
    assert result.attempted_proof_operations==result.completed_proof_operations==1
