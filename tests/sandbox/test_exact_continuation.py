from fractions import Fraction as F
from dataclasses import replace
import hashlib
import pytest
from test_exact_depletion_integration import setup
from test_dynamic_solid_storage import forbid_water_eos
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_depletion_integration import integrate_exact_depletion as integrate
from sludge_sandbox.exact_record import encode_exact_run,pack
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
import sludge_sandbox.exact_continuation_admission as admission
import sludge_sandbox.exact_terminal_proof_audit as proof

RUNTIME={'modules':{'test':'b'*64}}

def fixture(monkeypatch):
    s,v,p,e,calls=setup(monkeypatch)
    monkeypatch.setattr(WaterPhaseTransfer,'__post_init__',lambda self:None)
    monkeypatch.setattr(admission,'current_runtime',lambda:RUNTIME)
    # Numerical fixture has explicit partial host shells; all four numerical
    # audits remain real. Geometry/native observation qualification is separate.
    monkeypatch.setattr(proof,'observation_binding',lambda v,o,s:proof.numeric(o.rates))
    monkeypatch.setattr(proof,'geometry_binding',lambda v,s,o:())
    return s,v,p,e,calls

def request(run,v):
    raw=encode_exact_run(run,original_operator=v,start=T(F()),end=T(F(3,100)),case_sha256='a'*64,runtime_identity=RUNTIME)
    return admission.ExactContinuationRequest(raw,hashlib.sha256(raw).hexdigest(),'a'*64,RUNTIME)

def go(s,v,p,e,**kwargs):
    return integrate(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e,**kwargs)

def test_repeated_cancel_resume_preserves_original_prefix(monkeypatch):
    s,v,p,e,calls=fixture(monkeypatch);flag=[False]
    def commit(info):flag[0]=True
    a=go(s,v,p,e,cancel=lambda:flag[0],on_commit=commit)
    assert a.status=='cancelled' and a.steps
    flag[0]=False
    b=go(s,v,p,e,continuation=request(a,v),cancel=lambda:flag[0],on_commit=commit)
    assert b.status=='cancelled',b.reason
    assert len(b.steps)>len(a.steps)
    assert pack(b.steps[:len(a.steps)])==pack(a.steps)
    c=go(s,v,p,e,continuation=request(b,v))
    assert c.status=='completed',c.reason
    assert c.times_s[0]==a.times_s[0] and pack(c.states[:len(b.states)])==pack(b.states)
    assert c.elapsed_seconds>=b.elapsed_seconds>=a.elapsed_seconds
    assert c.costs['evaluations_attempted']>b.costs['evaluations_attempted']>a.costs['evaluations_attempted']
    audit_completed(c,v,s,p,e)

def test_cancel_after_packet_and_resume_aliases(monkeypatch):
    s,v,p,e,calls=fixture(monkeypatch);flag=[False]
    def commit(info):flag[0]=info[1]>=1
    a=go(s,v,p,e,cancel=lambda:flag[0],on_commit=commit)
    assert a.status=='cancelled' and a.packets
    b=go(s,v,p,e,continuation=request(a,v))
    assert b.status=='completed',b.reason
    assert pack(b.steps[:len(a.steps)])==pack(a.steps)
    for packet in b.packets:
        for frame in packet:assert any(frame.terminal.terminal_panel.ledger is x for x in b.steps)
    audit_completed(b,v,s,p,e)

def test_exhausted_preserves_reason_zero_callbacks(monkeypatch):
    s,v,p,e,calls=fixture(monkeypatch);p=replace(p,maximum_steps=1)
    a=go(s,v,p,e)
    assert a.status=='resource_limit' and a.steps
    count=len(calls);b=go(s,v,p,e,continuation=request(a,v))
    assert b.status=='resource_limit' and b.reason==a.reason and len(calls)==count
    assert pack(b.steps)==pack(a.steps) and b.costs==a.costs

def test_hash_and_runtime_rejected_before_callbacks(monkeypatch):
    s,v,p,e,calls=fixture(monkeypatch);flag=[False]
    a=go(s,v,p,e,cancel=lambda:flag[0],on_commit=lambda info:flag.__setitem__(0,True))
    req=request(a,v);count=len(calls)
    with pytest.raises(ValueError,match='hash_mismatch'):go(s,v,p,e,continuation=replace(req,expected_parent_sha256='0'*64))
    monkeypatch.setattr(admission,'current_runtime',lambda:{})
    with pytest.raises(ValueError,match='runtime_mismatch'):go(s,v,p,e,continuation=req)
    assert len(calls)==count

def test_observer_failure_retains_atomic_commit(monkeypatch):
    s,v,p,e,calls=fixture(monkeypatch)
    def fail(info):raise RuntimeError('intentional')
    a=go(s,v,p,e,on_commit=fail)
    assert a.status=='failed' and a.steps and a.reason.startswith('commit_observer_failed:')

def test_admission_wall_debited_before_any_physics(monkeypatch):
    import sludge_sandbox.exact_depletion_integration as driver
    from types import SimpleNamespace
    s,v,p,e,calls=fixture(monkeypatch);flag=[False]
    a=go(s,v,p,e,cancel=lambda:flag[0],on_commit=lambda info:flag.__setitem__(0,True))
    req=request(a,v);count=len(calls);clock=[100.]
    monkeypatch.setattr(driver,'time',SimpleNamespace(monotonic=lambda:clock[0]))
    actual=admission.restore_exact_projection
    def timed(*args,**kwargs):
        result=actual(*args,**kwargs);clock[0]+=p.maximum_wall_seconds;return result
    monkeypatch.setattr(admission,'restore_exact_projection',timed)
    b=go(s,v,p,e,continuation=req)
    assert b.status=='resource_limit' and b.reason=='wall_time_limit' and len(calls)==count
    assert b.elapsed_seconds>=a.elapsed_seconds+p.maximum_wall_seconds
    assert pack(b.steps)==pack(a.steps)

def test_each_admission_runs_all_four_audits(monkeypatch):
    s,v,p,e,calls=fixture(monkeypatch);flag=[False]
    a=go(s,v,p,e,cancel=lambda:flag[0],on_commit=lambda info:flag.__setitem__(0,True))
    seen=[]
    for name in ('audit_exact_run','audit_committed_terminal_proofs','audit_exact_comparisons','audit_exact_resources'):
        actual=getattr(admission,name)
        def wrap(*args,_actual=actual,_name=name,**kwargs):seen.append(_name);return _actual(*args,**kwargs)
        monkeypatch.setattr(admission,name,wrap)
    b=go(s,v,p,e,continuation=request(a,v),cancel=lambda:True)
    assert b.status=='cancelled' and len(seen)==4 and len(set(seen))==4
    count=len(calls)
    with pytest.raises(ValueError):go(s,v,replace(p,energy_absolute_tolerance_j=1.),e,continuation=request(a,v))
    assert len(calls)==count

def test_default_none_retains_baseline_numerics(monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path
    import sludge_sandbox.exact_depletion_integration as current
    name='baseline_exact_driver_review';spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name('exact_driver_baseline_v1.py'))
    baseline=importlib.util.module_from_spec(spec);sys.modules[name]=baseline;spec.loader.exec_module(baseline)
    # Identical result dataclass definitions; reuse canonical registered types
    # so pack compares actual numerical values rather than unrelated class IDs.
    for cls in ('ExactPacketFrame','ExactPacketPath','ExactPacketRefinement','ExactDepletionResult'):
        if hasattr(baseline,cls):setattr(baseline,cls,getattr(current,cls))
    s,v,p,e,calls=fixture(monkeypatch)
    a=baseline.integrate_exact_depletion(s,v,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    b=go(s,v,p,e)
    assert a.status==b.status=='completed'
    def without_wall(value):
        if isinstance(value,dict):return {k:without_wall(v) for k,v in value.items() if k!='elapsed_seconds'}
        if isinstance(value,list):return [without_wall(v) for v in value]
        return value
    for field in ('times_s','states','steps','packets','refinements','terminal_attempts','roundoff_totals','costs'):
        assert without_wall(pack(getattr(a,field)))==without_wall(pack(getattr(b,field)))

def audit_completed(run,v,s,p,e):
    req=request(run,v);checked=admission.read_exact_run(req.parent_bytes)
    common=dict(original_initial=s,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e,case_sha256='a'*64,runtime_identity=RUNTIME)
    admission.audit_exact_run(checked,v,**common)
    admission.audit_committed_terminal_proofs(req.parent_bytes,original_operator=v,**common)
    admission.audit_exact_comparisons(checked,v,**common)
    admission.audit_exact_resources(checked,original_policy=p)


def test_cancel_uncommitted_refinement_retains_costs_and_audits(monkeypatch):
    s,v,p,e,calls=fixture(monkeypatch)
    # Trigger on actual speculative mode transition; it is intentionally NOT
    # a commitment signal. The cancelled attempt must remain historical evidence.
    a=go(s,v,p,e,cancel=lambda:any('depleted_no_nucleation' in modes for _,modes in calls))
    assert a.status=='cancelled' and a.steps and a.terminal_attempts and not a.packets,(a.status,a.reason)
    assert a.refinements
    b=go(s,v,p,e,continuation=request(a,v))
    assert b.status=='completed',b.reason
    assert pack(b.refinements[:len(a.refinements)])==pack(a.refinements)
    assert pack(b.terminal_attempts[:len(a.terminal_attempts)])==pack(a.terminal_attempts)
    assert all(b.costs[k]>=a.costs[k] for k in a.costs)
    audit_completed(b,v,s,p,e)
