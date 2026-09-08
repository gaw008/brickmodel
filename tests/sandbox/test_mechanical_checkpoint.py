"""Mechanical checkpoint continuity and whole-prefix arithmetic; no EOS."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from sludge_sandbox.checkpoint import audit_integration, exact_state_equal, merge_integration
from sludge_sandbox.integration import ConservedState, IntegrationPolicy, IntegrationResult, StepLedger
from sludge_sandbox.verification_case import encode


def policy() -> IntegrationPolicy:
    return IntegrationPolicy(.125, .125, 1e-12, 1e-7, 1e-12, 1e-8,
                             1., 1., 10, 10, 10.,
                             stretch_absolute_tolerance=1/1024, stretch_scale=1.)


def segment(start: float = 0., before: float = 1., after: float = 1.,
            increment: float = 0., roundoff: Fraction = Fraction()) -> dict:
    initial = ConservedState(np.ones((2, 1)), np.ones(2), ('checkpoint_test',))
    ledger = StepLedger(start, start+.125, np.zeros((3, 1)), np.zeros(3),
                        np.zeros((2, 1)), np.zeros(2))
    record = encode(IntegrationResult('cancelled', 'cancel_requested',
                    (start, start+.125), (initial, initial), (ledger,), 7, 0, .1))
    record['states'][0]['mechanical_stretches'] = [before]*3
    record['states'][1]['mechanical_stretches'] = [after]*3
    record['steps'][0]['stretch_increment'] = [increment]*3
    record['steps'][0]['stretch_quadrature_roundoff'] = encode((roundoff,)*3)
    return record


def test_complete_mechanical_prefix_preserves_values_and_binding():
    record = segment(after=1.125, increment=.125)
    audit = audit_integration(record, policy(), start_s=0., end_s=.25)
    assert np.array_equal(audit.states[-1].mechanical_stretches, [1.125]*3)
    assert np.array_equal(audit.ledgers[0].stretch_increment, [.125]*3)
    assert audit.ledgers[0].stretch_quadrature_roundoff == (Fraction(),)*3


def test_legacy_missing_fields_remain_readable():
    record = segment()
    for state in record['states']:
        del state['mechanical_stretches']
    for field in ('stretch_increment', 'stretch_quadrature_roundoff'):
        del record['steps'][0][field]
    plain = replace(policy(), stretch_absolute_tolerance=None, stretch_scale=None)
    audit = audit_integration(record, plain, start_s=0., end_s=.25)
    assert audit.states[0].mechanical_stretches is None


def test_nonmechanical_explicit_null_fields_remain_readable():
    record = segment()
    for state in record['states']:
        state['mechanical_stretches'] = None
    for field in ('stretch_increment', 'stretch_quadrature_roundoff'):
        record['steps'][0][field] = None
    plain = replace(policy(), stretch_absolute_tolerance=None, stretch_scale=None)
    audit_integration(record, plain, start_s=0., end_s=.25)


def test_actual_nonmechanical_run_with_unused_stretch_scales_can_be_audited():
    from sludge_sandbox.integration import Rates,integrate
    initial=ConservedState([[1.]],[1.],('checkpoint_test',))
    result=integrate(initial,lambda s,t:Rates([[0.],[0.]],[0.,0.],[[0.]],[0.]),
                     start_s=0.,end_s=.125,policy=policy())
    assert result.status=='completed'
    audit_integration(encode(result),policy(),start_s=0.,end_s=.125)


def test_actual_cancelled_mechanical_trajectory_resumes_and_audits_original_prefix():
    from sludge_sandbox.integration import Rates,integrate
    initial=ConservedState([[1.]],[1.],('checkpoint_test',),mechanical_stretches=[1.,1.])
    calls=0
    def op(state,time):
        nonlocal calls
        calls+=1
        return Rates([[0.],[0.]],[0.,0.],[[0.]],[.5],mechanical_rates_per_s=[.25,-.125])
    parent=integrate(initial,op,start_s=0.,end_s=.5,policy=policy(),cancel=lambda:calls>=9)
    assert parent.status=='cancelled' and len(parent.steps)==1
    suffix=integrate(parent.states[-1],op,start_s=parent.times_s[-1],end_s=.5,policy=policy())
    assert suffix.status=='completed'
    merged,report=merge_integration(encode(parent),encode(suffix),policy(),start_s=0.,end_s=.5)
    assert report['status']=='passed' and merged['status']=='completed'
    assert merged['states'][:2]==encode(parent.states)
    assert merged['states'][-1]['mechanical_stretches']==[1.125,.9375]


def test_complete_mechanical_suffix_preserves_original_prefix():
    parent = segment(after=1.125, increment=.125)
    suffix = segment(start=.125, before=1.125, after=1.25, increment=.125)
    suffix.update(status='completed', reason=None)
    merged, report = merge_integration(parent, suffix, policy(), start_s=0., end_s=.25)
    assert report['status'] == 'passed'
    assert merged['status'] == 'completed'
    assert merged['states'][:2] == parent['states']
    assert merged['steps'][:1] == parent['steps']
    assert merged['states'][-1]['mechanical_stretches'] == [1.25]*3


@pytest.mark.parametrize('field', ['stretch_increment', 'stretch_quadrature_roundoff'])
def test_partially_omitted_mechanical_keys_are_rejected(field: str):
    record = segment()
    del record['steps'][0][field]
    with pytest.raises(ValueError):
        audit_integration(record, policy(), start_s=0., end_s=.25)


@pytest.mark.parametrize('field,value', [
    ('mechanical_stretches', [1., 1.]),
    ('mechanical_stretches', [1., True, 1.]),
    ('mechanical_stretches', [1., float('nan'), 1.]),
    ('mechanical_stretches', [1., 0., 1.]),
    ('mechanical_stretches', None),
])
def test_mechanical_state_tamper_is_rejected(field: str, value: object):
    record = segment()
    record['states'][1][field] = value
    with pytest.raises(ValueError):
        audit_integration(record, policy(), start_s=0., end_s=.25)


@pytest.mark.parametrize('field,value', [
    ('stretch_increment', None), ('stretch_increment', [0., 0.]),
    ('stretch_increment', [0., True, 0.]),
    ('stretch_quadrature_roundoff', None),
    ('stretch_quadrature_roundoff', [{'numerator': 0, 'denominator': 2}]*3),
    ('stretch_quadrature_roundoff', encode((Fraction(),)*2)),
    ('stretch_quadrature_roundoff', [True]*3),
])
def test_mechanical_ledger_tamper_is_rejected(field: str, value: object):
    record = segment()
    record['steps'][0][field] = value
    with pytest.raises(ValueError):
        audit_integration(record, policy(), start_s=0., end_s=.25)


def test_mechanical_policy_cannot_be_omitted():
    with pytest.raises(ValueError, match='mechanical_policy'):
        audit_integration(segment(), replace(policy(), stretch_absolute_tolerance=None,
                          stretch_scale=None), start_s=0., end_s=.25)


def test_exact_join_includes_stretches():
    record = segment()
    from sludge_sandbox.checkpoint import _state
    a = _state(record['states'][0])
    changed = deepcopy(record['states'][0])
    changed['mechanical_stretches'][0] = 1.125
    assert not exact_state_equal(a, _state(changed))
    assert exact_state_equal(a, _state(record['states'][0]))
    suffix = segment(start=.125, before=1.125, after=1.125)
    with pytest.raises(ValueError, match='suffix_join'):
        merge_integration(record, suffix, policy(), start_s=0., end_s=.25)


def test_resume_cannot_reset_cumulative_stretch_writeback_error():
    parent = segment(after=1+3/4096)
    suffix = segment(start=.125, before=1+3/4096, after=1+6/4096)
    audit_integration(parent, policy(), start_s=0., end_s=.25)
    audit_integration(suffix, policy(), start_s=.125, end_s=.25)
    merged, result = merge_integration(parent, suffix, policy(), start_s=0., end_s=.25)
    assert result['status'] == 'failed'
    assert 'stretch' in result['reason']
    assert merged['states'] == parent['states']


def test_resume_cannot_reset_absolute_quadrature_roundoff_budget():
    parent = segment(roundoff=Fraction(3, 4096))
    suffix = segment(start=.125, roundoff=Fraction(-3, 4096))
    audit_integration(parent, policy(), start_s=0., end_s=.25)
    audit_integration(suffix, policy(), start_s=.125, end_s=.25)
    merged, result = merge_integration(parent, suffix, policy(), start_s=0., end_s=.25)
    assert result['status'] == 'failed'
    assert 'stretch' in result['reason']
    assert merged['states'] == parent['states']


def test_writeback_and_quadrature_errors_cannot_individually_hide_total_error():
    record = segment(after=1+3/4096, roundoff=Fraction(3, 4096))
    with pytest.raises(ValueError, match='stretch'):
        audit_integration(record, policy(), start_s=0., end_s=.25)
