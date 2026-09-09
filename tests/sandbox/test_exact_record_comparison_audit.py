import json
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_exact_record import make
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_record import read_exact_run
from sludge_sandbox.exact_record_comparison_audit import audit_exact_comparisons,ComparisonAuditError


def prepared(monkeypatch,cancelled=False):
    raw,op,r=make(monkeypatch,cancelled)
    kw=dict(original_initial=r.states[0],start=T(F()),end=T(F(3,100)),integration_policy=r.initial_policy,event_policy=r.event_policy,case_sha256='a'*64,runtime_identity={'modules':{'test':'b'*64}})
    return raw,op,kw


def test_actual_record_comparisons(monkeypatch):
    raw,op,kw=prepared(monkeypatch)
    result=audit_exact_comparisons(read_exact_run(raw),op,**kw)
    assert result.committed_packets==1 and result.comparisons>=3 and result.pressure_certificates==0
    assert not result.resume_authorized


@pytest.mark.parametrize('mutation',['pressure','grid','safe','status','clock','bool_pressure'])
def test_actual_tampered_comparison_rejected(monkeypatch,mutation):
    raw,op,kw=prepared(monkeypatch);d=json.loads(raw)
    refs=d['result']['fields']['refinements']['sequence']
    independent=next(x['fields'] for x in refs if x['fields']['role']=='independent')
    row=independent['comparison']['sequence'][0]['mapping']
    if mutation=='bool_pressure':row['independent_pressure_bound_pa']=False
    elif mutation=='pressure':row['independent_pressure_bound_pa']={'float_hex':(1.).hex()}
    elif mutation=='grid':independent['path']['fields']['approach_grid']={'sequence':[]}
    elif mutation=='safe':independent['safe_fraction']={'fraction':[1,3]}
    elif mutation=='status':independent['status']='comparison_fail'
    elif mutation=='clock':row['differences']['sequence'][0]={'fraction':[1,1]}
    record=read_exact_run(json.dumps(d).encode())
    with pytest.raises(ComparisonAuditError):audit_exact_comparisons(record,op,**kw)


def test_cancelled_no_packet_stays_partial(monkeypatch):
    raw,op,kw=prepared(monkeypatch,True)
    result=audit_exact_comparisons(read_exact_run(raw),op,**kw)
    assert result.committed_packets==0 and not result.resume_authorized


def test_external_policy_and_replaceable_record_fields(monkeypatch):
    raw,op,kw=prepared(monkeypatch);r=read_exact_run(raw)
    result=audit_exact_comparisons(replace(r,result=None),op,**kw)
    assert result.committed_packets==1
    kw['event_policy']=replace(kw['event_policy'],temperature_absolute_k=1.)
    with pytest.raises(ComparisonAuditError):audit_exact_comparisons(r,op,**kw)


def test_real_pure_pressure_certificate_and_external_observation_binding():
    from copy import deepcopy
    from test_pressure_comparison import fixture
    from sludge_sandbox.exact_record_comparison_audit import _paired_bound
    p,_,binding,record=fixture()
    s=record['states'][0]
    # Stored observation errors represent the actual binary64 host fields.
    from sludge_sandbox.pressure_comparison import _encode
    record['cells'][0]['original_temperature_errors_k']=_encode((F(.01),F(.01)))
    obs={'pressures_pa':[35.],'temperatures_k':[300.],'pressure_errors_pa':[5.],'temperature_errors_k':[.01]}
    assert _paired_bound(record,s,obs,s,obs,policy=p,binding_a=binding,binding_b=binding)==record['bound_pa']
    changed=deepcopy(obs);changed['temperatures_k'][0]=301.
    with pytest.raises(ComparisonAuditError,match='actual_observations'):
        _paired_bound(record,s,changed,s,obs,policy=p,binding_a=binding,binding_b=binding)
    altered=deepcopy(binding);altered['sources']=['d'*64]
    with pytest.raises(ComparisonAuditError,match='actual_bindings'):
        _paired_bound(record,s,obs,s,obs,policy=p,binding_a=altered,binding_b=binding)


def test_invented_coarse_label_cannot_bypass_original_controls(monkeypatch):
    raw,op,kw=prepared(monkeypatch);d=json.loads(raw)
    refs=d['result']['fields']['refinements']['sequence']
    refs[0]['fields']['status']='invented_coarse_status'
    for ref in refs:
        pair=ref['fields']['approach_cap_s']['fraction'];value=F(*pair)*2
        ref['fields']['approach_cap_s']={'fraction':[value.numerator,value.denominator]}
    record=read_exact_run(json.dumps(d).encode())
    with pytest.raises(ComparisonAuditError):audit_exact_comparisons(record,op,**kw)


@pytest.mark.parametrize('mutation',['coarse_comparison','terminal_role','terminal_level'])
def test_committed_refinement_sequence_is_not_only_success_flags(monkeypatch,mutation):
    raw,op,kw=prepared(monkeypatch);d=json.loads(raw)
    refs=d['result']['fields']['refinements']['sequence']
    if mutation=='coarse_comparison':refs[0]['fields']['comparison']={'sequence':[]}
    elif mutation=='terminal_role':refs[1]['fields']['role']='invented_terminal'
    else:refs[0]['fields']['level']=2
    with pytest.raises(ComparisonAuditError):audit_exact_comparisons(read_exact_run(json.dumps(d).encode()),op,**kw)
