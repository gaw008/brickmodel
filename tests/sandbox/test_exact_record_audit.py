import json
from dataclasses import replace
import pytest
from test_exact_record import make
from sludge_sandbox.exact_record import read_exact_run
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from fractions import Fraction as F
from sludge_sandbox.exact_record_audit import audit_exact_run,ExactAuditError


def setup(monkeypatch,cancelled=False):
    raw,op,run=make(monkeypatch,cancelled)
    kw=dict(original_initial=run.states[0],start=T(F()),end=T(F(3,100)),integration_policy=run.initial_policy,event_policy=run.event_policy,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})
    return raw,op,kw


def test_actual_full_prefix_and_partial_qualification(monkeypatch):
    raw,op,kw=setup(monkeypatch)
    result=audit_exact_run(read_exact_run(raw),op,**kw)
    assert result.accepted_prefixes>0 and result.committed_events==2
    assert not result.resume_authorized and 'partial' in result.scope and len(result.missing_gates)>=4


@pytest.mark.parametrize('field', ['internal_energy_j','amounts_mol','mechanical_stretches'])
def test_wrong_final_quantity_passes_codec_fails_numeric_audit(monkeypatch,field):
    raw,op,kw=setup(monkeypatch);d=json.loads(raw)
    array=d['result']['fields']['states']['sequence'][-1]['fields'][field]['array']['values']
    # Vapor stays nonnegative and does not change the dry-mode liquid constraint.
    index=1 if field=='amounts_mol' else 0
    array[index]={'float_hex':(float.fromhex(array[index]['float_hex'])+.01).hex()}
    record=read_exact_run(json.dumps(d).encode())
    with pytest.raises(ExactAuditError,match='prefix_budget'):audit_exact_run(record,op,**kw)


def test_changed_external_policy_refused(monkeypatch):
    raw,op,kw=setup(monkeypatch);kw['integration_policy']=replace(kw['integration_policy'],energy_absolute_tolerance_j=1.)
    with pytest.raises(ExactAuditError,match='external_original_policies'):audit_exact_run(read_exact_run(raw),op,**kw)


def test_cancelled_prefix_is_audited_and_replaceable_fields_are_not_trusted(monkeypatch):
    raw,op,kw=setup(monkeypatch,True);record=read_exact_run(raw)
    replaced=replace(record,states=(),ledgers=())
    result=audit_exact_run(replaced,op,**kw)
    assert result.accepted_prefixes==len(record.ledgers)>0


def test_nonzero_corrections_recomputed_and_cumulative_tamper_refused(monkeypatch):
    from test_exact_depletion_integration import setup as core_setup
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
    from sludge_sandbox.exact_depletion_integration import integrate_exact_depletion
    from sludge_sandbox.exact_record import encode_exact_run
    s,op,p,e,calls=core_setup(monkeypatch)
    original=WaterPhaseTransfer.evaluate_autonomous
    def thirds(self,state):
        out=original(self,state)
        import numpy as np
        sinks=[3.+100.*state.amounts_mol[i,0] if mode=='existing_liquid' else 0. for i,mode in enumerate(self.interfaces)]
        return replace(out,rates=replace(out.rates,reaction_species_mol_s=np.array([[-v,v] for v in sinks])),
                       cell_transfers=tuple(replace(v,rate_mol_s=sinks[i]) for i,v in enumerate(out.cell_transfers)))
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',thirds)
    monkeypatch.setattr(WaterPhaseTransfer,'__post_init__',lambda self:None)
    run=integrate_exact_depletion(s,op,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e)
    assert run.status=='completed',run.reason
    assert run.roundoff_totals.events>0
    raw=encode_exact_run(run,original_operator=op,start=T(F()),end=T(F(3,100)),case_sha256='a'*64,runtime_identity={})
    kw=dict(original_initial=s,start=T(F()),end=T(F(3,100)),integration_policy=p,event_policy=e,case_sha256='a'*64,runtime_identity={})
    assert audit_exact_run(read_exact_run(raw),op,**kw).committed_events==2
    d=json.loads(raw);totals=d['result']['fields']['roundoff_totals']['fields']
    totals['numerical_phase_correction_mol']={'fraction':[1,10**15]}
    with pytest.raises(ExactAuditError,match='final_roundoff_totals'):
        audit_exact_run(read_exact_run(json.dumps(d).encode()),op,**kw)
