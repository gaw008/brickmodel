from dataclasses import replace
from fractions import Fraction as F
import json
import pytest
from test_exact_record import make
from sludge_sandbox.exact_record import read_exact_run
from sludge_sandbox.exact_resource_audit import audit_exact_resources, ResourceAuditError


def test_original_charged_definition_and_remaining(monkeypatch):
    raw, _, run = make(monkeypatch)
    a = audit_exact_resources(raw, original_policy=run.initial_policy)
    expected = run.costs['ordinary_panels'] + run.costs['stage_replans'] + run.costs['terminal_attempts']
    assert a.charged_panels == expected
    assert a.remaining_panels == run.initial_policy.maximum_steps - expected
    assert a.remaining_wall_seconds == F(run.initial_policy.maximum_wall_seconds) - F(run.elapsed_seconds)
    assert not a.resume_authorized
    assert a.terminal_calls == len(run.terminal_attempts)


@pytest.mark.parametrize('attack', ['terminal_reset', 'refinement_reset', 'ordinary_reset'])
def test_discarded_work_cannot_be_reset(monkeypatch, attack):
    raw, _, run = make(monkeypatch)
    d = json.loads(raw); values = d['result']['fields']['costs']['mapping']
    if attack == 'terminal_reset': values['terminal_attempts'] = 0
    elif attack == 'refinement_reset': values['evaluations_attempted'] = values['evaluations_completed'] = 0
    else: values['ordinary_panels'] = 0
    with pytest.raises(ResourceAuditError):
        audit_exact_resources(json.dumps(d).encode(), original_policy=run.initial_policy)


def test_original_policy_and_caller_fields_cannot_grant_credit(monkeypatch):
    raw, _, run = make(monkeypatch)
    record = read_exact_run(raw)
    altered = replace(record, result=None, states=(), ledgers=())
    assert audit_exact_resources(altered, original_policy=run.initial_policy).record_sha256 == record.sha256
    with pytest.raises(ResourceAuditError, match='original_resource_policy'):
        audit_exact_resources(raw, original_policy=replace(run.initial_policy, maximum_steps=run.initial_policy.maximum_steps + 1))


def test_elapsed_overrun_has_zero_credit_and_preserves_telemetry(monkeypatch):
    raw, _, run = make(monkeypatch, True)
    d = json.loads(raw)
    elapsed = float(run.initial_policy.maximum_wall_seconds + 1)
    d['result']['fields']['elapsed_seconds'] = {'float_hex': elapsed.hex()}
    audit = audit_exact_resources(json.dumps(d).encode(), original_policy=run.initial_policy)
    assert audit.remaining_wall_seconds == 0 and audit.cumulative_elapsed_seconds == F(elapsed)
    assert not audit.resume_authorized


def test_disjoint_committed_and_refinement_work_cannot_be_hidden(monkeypatch):
    raw, _, run = make(monkeypatch)
    d = json.loads(raw)
    refined = sum(r.costs['ordinary_panels'] for r in run.refinements)
    committed = len(run.steps) - sum(map(len, run.packets))
    forged = max(refined, committed)
    assert forged < run.costs['ordinary_panels']
    d['result']['fields']['costs']['mapping']['ordinary_panels'] = forged
    with pytest.raises(ResourceAuditError, match='disjoint_ordinary'):
        audit_exact_resources(json.dumps(d).encode(), original_policy=run.initial_policy)


def test_materialized_terminal_panel_cannot_lose_its_charge(monkeypatch):
    raw, _, run = make(monkeypatch)
    data = json.loads(raw)
    result = data['result']['fields']
    attempt = result['terminal_attempts']['sequence'][0]['fields']
    assert attempt['terminal_panel'] is not None
    assert attempt['costs']['fields']['terminal_panels'] == 1
    # The first actual terminal belongs to the first refinement in this fixture.
    ref = result['refinements']['sequence'][0]['fields']
    assert ref['path']['fields']['frames']['sequence'][0]['fields']['terminal']['fields']['terminal_panel'] == attempt['terminal_panel']
    for key in ('terminal_panel_attempts', 'terminal_panels'):
        attempt['costs']['fields'][key] -= 1
    for key in ('terminal_attempts', 'terminal_panels'):
        result['costs']['mapping'][key] -= 1
        ref['costs']['mapping'][key] -= 1
    with pytest.raises(ResourceAuditError):
        audit_exact_resources(json.dumps(data).encode(), original_policy=run.initial_policy)


@pytest.mark.parametrize('field,counter', [('predictor_panel','predictor_panels'), ('root_order','root_order_attempts'), ('corrected_state','writeback_attempts'), ('candidate_operator','mode_transition_attempts')])
def test_materialized_stage_cannot_lose_its_cost(monkeypatch, field, counter):
    raw, _, run = make(monkeypatch)
    data = json.loads(raw)
    attempt = data['result']['fields']['terminal_attempts']['sequence'][0]['fields']
    assert attempt[field] is not None
    attempt['costs']['fields'][counter] = 0
    with pytest.raises(ResourceAuditError, match='materialized_'):
        audit_exact_resources(json.dumps(data).encode(), original_policy=run.initial_policy)


def test_retained_refinement_terminal_requires_recorded_attempt(monkeypatch):
    raw, _, run = make(monkeypatch)
    data = json.loads(raw)
    result = data['result']['fields']
    removed = result['terminal_attempts']['sequence'].pop(0)['fields']
    ref = result['refinements']['sequence'][0]['fields']
    assert ref['path']['fields']['frames']['sequence'][0]['fields']['terminal']['fields'] == removed
    costs = removed['costs']['fields']
    for outer, inner in (('predictor_attempts','predictor_panel_attempts'),
                         ('terminal_attempts','terminal_panel_attempts'),
                         ('terminal_panels','terminal_panels')):
        result['costs']['mapping'][outer] -= costs[inner]
        ref['costs']['mapping'][outer] -= costs[inner]
    with pytest.raises(ResourceAuditError):
        audit_exact_resources(json.dumps(data).encode(), original_policy=run.initial_policy)
