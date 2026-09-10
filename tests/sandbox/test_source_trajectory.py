"""Real source-column continuation with an explicitly manufactured liquid seam."""
from dataclasses import replace
from fractions import Fraction as F
import json
from pathlib import Path

import numpy as np
import pytest

from test_source_run_service import CASE, liquid_seam
from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_integration import ExactIntegrationResult, ExactStepLedger
from sludge_sandbox.integration import IntegrationError, DomainExit
from sludge_sandbox.run_service import RunError, _seal, read_run_with_source_record
from sludge_sandbox.source_run_service import run_source_case, RECORD
from sludge_sandbox.source_study_record import decode_source_study
from sludge_sandbox.source_study_schema import reify
from sludge_sandbox.source_net_prefix import _same
from sludge_sandbox.source_trajectory import open_source_trajectory


@pytest.fixture(scope='module')
def source_run(tmp_path_factory):
    output = tmp_path_factory.mktemp('source-trajectory-parent') / 'run'
    # The seam's rigid-fluid root error, amplified by its global compliance
    # bound, exhausted the double-endpoint pressure budget. Tighten that root
    # solve by 100x; keep the original acceptance gate and real HEOS case.
    values = json.loads(CASE.read_bytes())
    values['pressure_policy']['pressure_tolerance_pa'] = 1e-7
    case = output.parent / 'manufactured-seam-case.json'
    case.write_text(json.dumps(values))
    with pytest.MonkeyPatch.context() as patch:
        liquid_seam(patch)
        result = run_source_case(case, REPOSITORY, output)
    assert result['status'] == 'completed', result
    record = decode_source_study((output / RECORD).read_bytes())
    assert record.roots['transition'].numerical_event_accepted
    return output, result, record


def new_session(source_run, tmp_path, monkeypatch, **kwargs):
    directory, _, record = source_run
    liquid_seam(monkeypatch)
    end = record.roots['transition'].candidates[1].end
    horizon = record.metadata['effective_inputs']['horizon']
    return open_source_trajectory(directory, tmp_path / 'events',
        end=T(end.seconds + 3*horizon), **kwargs)


def test_reconstruction_uses_original_endpoint_and_new_actual_storage(source_run, tmp_path, monkeypatch):
    session = new_session(source_run, tmp_path, monkeypatch)
    candidate = source_run[2].roots['transition'].candidates[1]
    assert session.start == candidate.reference.times_s[-1]
    assert np.array_equal(session.initial.amounts_mol, reify(candidate.reference.states[-1]).amounts_mol)
    assert session.adapter.interfaces == ('existing_liquid', 'depleted_no_nucleation', 'existing_liquid')
    assert session.adapter is not session.built.adapter
    assert all(a is b for a, b in zip(session.adapter.column.storages, session.built.storages))
    assert session.initial.amounts_mol[1, 0] == 0
    assert session.recorder.counts['rhs_started'] == source_run[1]['counts']['rhs_started']
    assert not session.record.resume_authorized


def test_pause_resume_preserves_callbacks_and_original_full_chain(source_run, tmp_path, monkeypatch):
    session = new_session(source_run, tmp_path, monkeypatch)
    first = session.advance(pause_after_steps=1)
    assert first.status == 'paused', (first.status, first.reason)
    assert len(first.execution.result.steps) == 1
    first_count = first.execution.result.evaluations
    initial_count = source_run[1]['counts']['rhs_started']
    assert dict(first.counts)['rhs_started'] == initial_count + first_count
    assert first.balances[-1].phase == 'post_dry_reference'
    assert len(first.balances) == len(source_run[2].roots['transition'].balance_paths[1]) + 1
    second = session.advance()
    assert second.status == 'completed', (second.status, second.reason)
    assert second.execution.result.times_s[0] == session.start
    assert second.execution.result.times_s[-1] == session.end
    assert dict(second.counts)['rhs_started'] == initial_count + second.execution.result.evaluations
    assert second.execution.result.evaluations == 1 + 7*len(second.execution.result.steps)
    assert _same(second.execution.result.steps[:1], first.execution.result.steps)
    assert not second.material_qualified and not second.full_firing_cycle and not second.archived_resume_authorized
    with pytest.raises(IntegrationError, match='not_resumable'):
        session.advance()


def test_old_runtime_is_rejected_before_new_construction(source_run, tmp_path, monkeypatch):
    import shutil
    import sludge_sandbox.source_trajectory as module
    parent = tmp_path / 'old'
    shutil.copytree(source_run[0], parent)
    result = dict(source_run[1], runtime_before={'old': True}, runtime_after={'old': True})
    (parent / 'result.json').write_text(json.dumps(result))
    _seal(parent)
    monkeypatch.setattr(module, 'build_source_run', lambda *a: pytest.fail('constructed before identity admission'))
    with pytest.raises(RunError, match='runtime_changed'):
        open_source_trajectory(parent, tmp_path / 'no-output', end=T(F(1)))
    assert not (tmp_path / 'no-output').exists()


def test_original_outer_wall_cannot_be_reset(source_run, tmp_path, monkeypatch):
    import shutil
    import sludge_sandbox.source_trajectory as module
    parent = tmp_path / 'spent'
    shutil.copytree(source_run[0], parent)
    result = dict(source_run[1], elapsed_wall_seconds=1e6)
    (parent / 'result.json').write_text(json.dumps(result))
    _seal(parent)
    monkeypatch.setattr(module, 'build_source_run', lambda *a: pytest.fail('constructed after original deadline'))
    with pytest.raises(IntegrationError, match='original_outer_limit'):
        open_source_trajectory(parent, tmp_path / 'events', end=T(F(1)))
    files = tuple((tmp_path / 'events').rglob('*.json'))
    assert files  # Actual failed admission and retained parent cost.


def test_cancellation_does_not_restart_or_grant_checkpoint(source_run, tmp_path, monkeypatch):
    requested = [False]
    session = new_session(source_run, tmp_path, monkeypatch, cancel=lambda: requested[0])
    original = session.recorder.counts['rhs_started']
    requested[0] = True
    stopped = session.advance()
    assert stopped.status == 'cancelled'
    assert stopped.execution.checkpoint is None and dict(stopped.counts)['rhs_started'] == original
    with pytest.raises(IntegrationError, match='not_resumable'):
        session.advance()


def test_original_transition_budget_includes_new_segment_residual(source_run, tmp_path, monkeypatch):
    session = new_session(source_run, tmp_path, monkeypatch)
    state = session.initial
    end = T(session.start.seconds + F(1, 1_000_000))
    n, species = state.amounts_mol.shape
    # A changed endpoint with no matching exchange is rejected against the
    # original wet initial condition, including the prior event writeback.
    changed = state.internal_energy_j.copy()
    changed[0] += 2*session.policy.energy_absolute_tolerance_j
    final = replace(state, internal_energy_j=changed)
    ledger = ExactStepLedger(session.start, end, np.zeros((n+1, species)), np.zeros(n+1),
                            np.zeros((n, species)), np.zeros(n))
    reference = ExactIntegrationResult('completed', None, (session.start, end), (state, final),
                                      (ledger,), 8, 0, 0., 1)
    with pytest.raises(IntegrationError, match='cumulative_original_balance_budget'):
        session._audit(reference)


def test_policy_mutation_is_rejected_before_new_rhs(source_run, tmp_path, monkeypatch):
    session = new_session(source_run, tmp_path, monkeypatch)
    original = session.recorder.counts['rhs_started']
    session.policy = replace(session.policy, maximum_steps=session.policy.maximum_steps+1)
    with pytest.raises(IntegrationError, match='definition_changed'):
        session.advance()
    assert session.recorder.counts['rhs_started'] == original


def test_single_validation_pass_returns_same_source_record(source_run, monkeypatch):
    import sludge_sandbox.source_run_service as module
    calls = []
    original = module.decode_source_study
    def decode(raw):
        calls.append(raw)
        return original(raw)
    monkeypatch.setattr(module, 'decode_source_study', decode)
    result, manifest, record = read_run_with_source_record(source_run[0])
    assert len(calls) == 1
    assert record.sha256 == manifest['files'][RECORD] == result['source_record']['sha256']


def test_source_record_change_after_manifest_check_is_rejected(source_run, monkeypatch):
    import sludge_sandbox.source_run_service as module
    original = module._read
    monkeypatch.setattr(module, '_read', lambda path, *args: original(path, *args) + b' ')
    with pytest.raises(RunError, match='record_changed_after_validation'):
        read_run_with_source_record(source_run[0])


def test_summary_change_after_manifest_check_is_rejected(source_run, monkeypatch):
    target = source_run[0] / 'result.json'
    original = Path.read_bytes
    reads = []
    def read(path):
        raw = original(path)
        if path == target:
            reads.append(path)
            if len(reads) == 2:
                return raw + b' '
        return raw
    monkeypatch.setattr(Path, 'read_bytes', read)
    with pytest.raises(RunError, match='result_changed_after_validation'):
        read_run_with_source_record(source_run[0])


def test_publication_failure_retains_actual_result_but_closes_session(source_run, tmp_path, monkeypatch):
    session = new_session(source_run, tmp_path, monkeypatch)
    original = session.recorder.journal.append
    def append(event, value):
        if event == 'ordinary_segment_returned':
            raise OSError('result disk failure')
        return original(event, value)
    monkeypatch.setattr(session.recorder.journal, 'append', append)
    with pytest.raises(OSError, match='result disk failure'):
        session.advance(pause_after_steps=1)
    assert session.last_result.execution.result.steps
    assert session.checkpoint is None and session.closed
    with pytest.raises(IntegrationError, match='not_resumable'):
        session.advance()


def test_admission_journal_failure_preserves_primary_error(source_run, tmp_path, monkeypatch):
    import sludge_sandbox.source_trajectory as module
    from sludge_sandbox.source_run_journal import SourceRunJournal
    primary = DomainExit('original construction domain failure')
    def build(*args):
        raise primary
    def append(*args):
        raise OSError('secondary disk failure')
    monkeypatch.setattr(module, 'build_source_run', build)
    monkeypatch.setattr(SourceRunJournal, 'append', append)
    with pytest.raises(DomainExit) as caught:
        open_source_trajectory(source_run[0], tmp_path / 'failure', end=T(F(1)))
    assert caught.value is primary and 'OSError' in primary.__notes__[0]


@pytest.mark.parametrize('counter', ['rhs_started', 'rhs_returned'])
def test_pause_cannot_reset_source_callback_costs(source_run, tmp_path, monkeypatch, counter):
    session = new_session(source_run, tmp_path, monkeypatch)
    stopped = session.advance(pause_after_steps=1)
    assert stopped.status == 'paused'
    session.recorder.counts[counter] = dict(session.parent_counts)[counter]
    with pytest.raises(IntegrationError, match='costs_changed'):
        session.advance()


def test_pause_checkpoint_cannot_be_cleared_to_restart(source_run, tmp_path, monkeypatch):
    session = new_session(source_run, tmp_path, monkeypatch)
    paused = session.advance(pause_after_steps=1)
    assert paused.status == 'paused'
    original = dict(session.recorder.counts)
    session.checkpoint = None
    with pytest.raises(IntegrationError, match='continuation_state_changed'):
        session.advance()
    assert session.recorder.counts == original
