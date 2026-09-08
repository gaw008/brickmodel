"""Resume application tests use an independent constant-source verification ODE."""
import json
from pathlib import Path

import numpy as np
import pytest

from sludge_sandbox import run_service, verification_case
from sludge_sandbox.integration import ConservedState, IntegrationPolicy, IntegrationResult, Rates, StepLedger

CASE = Path(__file__).resolve().parents[2]/'data/sandbox/cases/reacting-wet-slab-v1.json'


class ConstantOperator:
    def __init__(self):
        self.calls = 0

    def __call__(self, state, at):
        self.calls += 1
        source = np.zeros((2, 5))
        source[:, 0] = -.125
        source[:, 1] = .125
        return Rates(np.zeros((3, 5)), np.zeros(3), source, np.full(2, 2.))

    def breakpoints_s(self, start, end):
        return ()


def prepare(tmp_path, monkeypatch):
    operators = []

    def build(case, water_dir):
        p = case.payload
        operator = ConstantOperator()
        operators.append(operator)
        state = ConservedState(p['initial']['parent_amounts_mol'], [-199999., -199998.],
                               ('test_total_energy', ('fixed',)))
        policy_values = dict(p['numerics']['integration'])
        for key in ('initial_step_s', 'maximum_step_s'):
            policy_values[key] /= 2**p['refinement']
        return verification_case.BuiltCase(case, operator, state,
            p['numerics']['start_s'], p['numerics']['end_s'],
            IntegrationPolicy(**policy_values),
            {'conservative_state': verification_case.encode(state)})

    monkeypatch.setattr(verification_case, 'build_case', build)
    monkeypatch.setattr(verification_case, 'snapshot', lambda b, s, t: {
        'state': verification_case.encode(s), 'time_s': t})
    water = tmp_path/'water'
    water.mkdir()
    return operators, water


def cancelled_parent(tmp_path, monkeypatch):
    operators, water = prepare(tmp_path, monkeypatch)
    output = tmp_path/'parent'
    result = run_service.run_case(CASE, water, output,
        # Initial evaluation + six RK stages + accepted-state validation = 8.
        # Cancel during the next trial, after that first panel was committed.
        cancel=lambda: bool(operators) and operators[-1].calls >= 9)
    assert result['status'] == result['integration']['status'] == 'cancelled'
    assert len(result['integration']['steps']) == 1
    return output, result, operators


def test_resume_preserves_prefix_and_solves_remaining_interval(tmp_path, monkeypatch):
    parent, original, operators = cancelled_parent(tmp_path, monkeypatch)
    before = (parent/'result.json').read_bytes()
    result = run_service.resume_run(parent, tmp_path/'resumed')
    assert result['status'] == 'completed', result.get('reason')
    run = result['integration']
    assert run['states'][:2] == original['integration']['states']
    assert run['steps'][:1] == original['integration']['steps']
    assert len(run['steps']) == 2
    duration = run['times_s'][-1]-run['times_s'][0]
    initial, final = run['states'][0], run['states'][-1]
    for i in range(2):
        assert final['amounts_mol'][i][0] == initial['amounts_mol'][i][0]-.125*duration
        assert final['amounts_mol'][i][1] == .125*duration
        assert final['internal_energy_j'][i] == initial['internal_energy_j'][i]+2*duration
    assert (parent/'result.json').read_bytes() == before
    run_service.read_run(tmp_path/'resumed')


def test_resume_rejects_tampered_parent_before_build(tmp_path, monkeypatch):
    parent, _, operators = cancelled_parent(tmp_path, monkeypatch)
    (parent/'result.json').write_text('{}')
    count = len(operators)
    with pytest.raises(ValueError):
        run_service.resume_run(parent, tmp_path/'resumed')
    assert len(operators) == count


def test_resume_rejects_changed_implementation_before_build(tmp_path, monkeypatch):
    parent, _, operators = cancelled_parent(tmp_path, monkeypatch)
    actual = run_service.runtime_identity()
    monkeypatch.setattr(run_service, 'runtime_identity', lambda: {**actual, 'python': 'different'})
    count = len(operators)
    with pytest.raises(ValueError):
        run_service.resume_run(parent, tmp_path/'resumed')
    assert len(operators) == count


def test_completed_run_is_not_a_resumable_checkpoint(tmp_path, monkeypatch):
    _, water = prepare(tmp_path, monkeypatch)
    run_service.run_case(CASE, water, tmp_path/'parent')
    with pytest.raises(ValueError):
        run_service.resume_run(tmp_path/'parent', tmp_path/'resumed')


def test_two_locally_small_errors_cannot_reset_global_allowance():
    from sludge_sandbox.checkpoint import audit_integration, merge_integration
    policy = IntegrationPolicy(.125, .125, 1e-12, 1e-7, 1e-12, 1/1024, 1., 1., 10, 10, 10.)
    initial = ConservedState(np.ones((2, 5)), np.ones(2), ('test_energy',))
    middle = ConservedState(initial.amounts_mol, np.full(2, 1+3/4096), initial.energy_model_identity)
    final = ConservedState(initial.amounts_mol, np.full(2, 1+6/4096), initial.energy_model_identity)

    def segment(start, end, before, after, status):
        ledger = StepLedger(start, end, np.zeros((3, 5)), np.zeros(3), np.zeros((2, 5)), np.zeros(2))
        return verification_case.encode(IntegrationResult(status, None, (start, end), (before, after),
                                                          (ledger,), 7, 0, .1))

    parent = segment(0., .125, initial, middle, 'cancelled')
    suffix = segment(.125, .25, middle, final, 'completed')
    audit_integration(parent, policy, start_s=0., end_s=.25)
    audit_integration(suffix, policy, start_s=.125, end_s=.25)
    merged, audit = merge_integration(parent, suffix, policy, start_s=0., end_s=.25)
    assert audit['status'] == 'failed'
    assert merged['status'] == 'numerical_failure'
    assert merged['states'] == parent['states']


def test_remaining_budget_debits_original_history():
    from sludge_sandbox.checkpoint import remaining_policy, CheckpointError
    policy = IntegrationPolicy(.125, .125, 1e-12, 1e-7, 1e-12, 1e-8, 1., 1., 10, 8, 12.)
    record = {'steps': [None]*3, 'rejected_trials': 2, 'elapsed_seconds': 4.}
    remaining = remaining_policy(record, policy)
    assert (remaining.maximum_steps, remaining.maximum_rejections, remaining.maximum_wall_seconds) == (7, 6, 8.)
    record['elapsed_seconds'] = 12.
    with pytest.raises(CheckpointError, match='budget_exhausted'):
        remaining_policy(record, policy)


def test_repeated_resume_keeps_whole_history_and_budget(tmp_path, monkeypatch):
    operators, water = prepare(tmp_path, monkeypatch)
    payload = json.loads(CASE.read_bytes())
    payload['refinement'] = 1
    case = tmp_path/'case.json'
    case.write_text(json.dumps(payload))
    parent = run_service.run_case(case, water, tmp_path/'first',
        cancel=lambda: bool(operators) and operators[-1].calls >= 9)
    assert len(parent['integration']['steps']) == 1
    middle = run_service.resume_run(tmp_path/'first', tmp_path/'second',
        cancel=lambda: len(operators) >= 2 and operators[-1].calls >= 9)
    assert middle['status'] == 'cancelled'
    assert len(middle['integration']['steps']) == 2
    final = run_service.resume_run(tmp_path/'second', tmp_path/'third')
    assert final['status'] == 'completed', final.get('reason')
    assert len(final['integration']['steps']) == 4
    assert final['integration']['steps'][:2] == middle['integration']['steps']
    assert final['suffix_policy']['maximum_steps'] == payload['numerics']['integration']['maximum_steps']-2
    assert final['suffix_policy']['maximum_wall_seconds'] <= payload['numerics']['integration']['maximum_wall_seconds']-middle['integration']['elapsed_seconds']


@pytest.mark.parametrize('integration', [None, []])
def test_malformed_cancelled_record_is_structured_error(integration):
    from sludge_sandbox.checkpoint import validate_cancelled, CheckpointError
    policy = IntegrationPolicy(.125, .125, 1e-12, 1e-7, 1e-12, 1e-8, 1., 1., 10, 8, 12.)
    with pytest.raises(CheckpointError):
        validate_cancelled({'status': 'cancelled', 'integration': integration}, policy, start_s=0., end_s=1.)


def test_component_roundoff_budget_is_not_reset_between_segments():
    from fractions import Fraction
    from sludge_sandbox.checkpoint import merge_integration
    policy = IntegrationPolicy(.125, .125, 1e-12, 1e-7, 1e-12, 1/1024, 1., 1., 10, 10, 10.)
    state = ConservedState(np.ones((2, 5)), np.ones(2), ('test_energy',))

    def segment(start, end, status):
        ledger = StepLedger(start, end, np.zeros((3, 5)), np.zeros(3), np.zeros((2, 5)), np.zeros(2),
                            {'elastic_deformation': np.full(2, 3/4096)})
        return verification_case.encode(IntegrationResult(status, None, (start, end), (state, state),
                                                          (ledger,), 7, 0, .1, (Fraction(3, 4096),)*2))

    parent, suffix = segment(0., .125, 'cancelled'), segment(.125, .25, 'completed')
    merged, audit = merge_integration(parent, suffix, policy, start_s=0., end_s=.25)
    assert audit['status'] == 'failed'
    assert 'component_roundoff' in audit['reason']
    assert merged['steps'] == parent['steps']
