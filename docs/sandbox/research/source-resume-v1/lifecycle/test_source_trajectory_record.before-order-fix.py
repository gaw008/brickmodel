"""Local managed resume contracts; native EOS is never used by these tests."""
from fractions import Fraction as F
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from sludge_sandbox.source_trajectory_record import (
    save_source_trajectory, restore_source_trajectory, read_source_trajectory_checkpoint,
)


def test_unknown_session_cannot_issue_a_source_restore_point(tmp_path):
    with pytest.raises(ValueError, match='actual_live_session'):
        save_source_trajectory(object(), tmp_path / 'packet')
    assert not (tmp_path / 'packet').exists()


def manufactured_runtime(monkeypatch):
    """This fixture tests source arithmetic, not a signed/installed runtime."""
    import sludge_sandbox.source_run_service as service
    import sludge_sandbox.source_trajectory as trajectory
    import sludge_sandbox.source_trajectory_record as record
    for module in (service, trajectory, record):
        monkeypatch.setattr(module, 'runtime_identity', lambda: {'manufactured_test_runtime': True})


@pytest.fixture(scope='module')
def parent(tmp_path_factory):
    from test_source_run_service import CASE, liquid_seam
    from test_mass_storage_bridge import REPOSITORY
    from sludge_sandbox.source_run_config import RESUME_PROFILE, required_source_assets
    from sludge_sandbox.source_run_service import run_source_case, RECORD
    from sludge_sandbox.source_study_record import decode_source_study
    if os.environ.get('SOURCE_RESUME_TEST_PACKET'):
        existing = Path(os.environ['SOURCE_RESUME_TEST_PACKET']) / 'parent'
        return existing, json.loads((existing / 'result.json').read_bytes()), decode_source_study((existing / RECORD).read_bytes())
    directory = tmp_path_factory.mktemp('source-restore-parent')
    values = json.loads(CASE.read_bytes())
    values['profile'] = RESUME_PROFILE
    values['assets'] = [dict(path=p, bytes=n, sha256=h) for p, n, h in required_source_assets(RESUME_PROFILE)]
    # Existing manufactured source-trajectory fixture setting; no acceptance
    # tolerance or native input is modified by this persistence test.
    values['pressure_policy']['pressure_tolerance_pa'] = 1e-7
    case = directory / 'case.json'
    case.write_text(json.dumps(values))
    with pytest.MonkeyPatch.context() as patch:
        liquid_seam(patch)
        manufactured_runtime(patch)
        result = run_source_case(case, REPOSITORY, directory / 'parent')
    assert result['status'] == 'completed', result
    record = decode_source_study((directory / 'parent' / RECORD).read_bytes())
    assert record.roots['transition'].numerical_event_accepted
    return directory / 'parent', result, record


def open_test_session(parent, output, monkeypatch):
    from test_source_run_service import liquid_seam
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    from sludge_sandbox.source_trajectory import open_source_trajectory
    liquid_seam(monkeypatch)
    manufactured_runtime(monkeypatch)
    end = parent[2].roots['transition'].candidates[1].end
    horizon = parent[2].metadata['effective_inputs']['horizon']
    return open_source_trajectory(parent[0], output, end=T(end.seconds + 3*horizon))


def test_real_source_pause_save_read_rebuild_continue_preserves_every_callback(parent, tmp_path, monkeypatch):
    from sludge_sandbox.exact_integration_checkpoint import _same
    session = open_test_session(parent, tmp_path / 'original', monkeypatch)
    paused = session.advance(pause_after_steps=1)
    assert paused.status == 'paused', paused.reason
    original_events = {p.name: p.read_bytes() for p in session.recorder.journal.directory.glob('*.json')}
    old_captures = tuple(session.recorder.captures)
    saved = save_source_trajectory(session, tmp_path / 'packet')
    assert saved['disposition'] == 'saved_and_live_session_suspended'
    assert session.closed and session.checkpoint is None
    with pytest.raises(Exception, match='not_resumable'):
        session.advance()
    packet = read_source_trajectory_checkpoint(tmp_path / 'packet')
    assert _same(packet.checkpoint, paused.execution.checkpoint)
    rebuilt = restore_source_trajectory(tmp_path / 'packet', tmp_path / 'restored')
    assert rebuilt.checkpoint is rebuilt.last_result.execution.checkpoint
    assert len(rebuilt.recorder.captures) == len(old_captures)
    assert rebuilt.start == session.start and rebuilt.end == session.end
    assert rebuilt.parent_counts == session.parent_counts
    for name, raw in original_events.items():
        assert (rebuilt.recorder.journal.directory / name).read_bytes() == raw
    final = rebuilt.advance()
    assert final.status == 'completed', final.reason
    assert final.execution.result.evaluations == len(rebuilt.recorder.captures)
    assert _same(final.execution.observations[:len(old_captures)], paused.execution.observations)
    assert final.execution.result.times_s[-1] == session.end
    assert final.cumulative_outer_seconds >= float.fromhex(saved['charged_segment_seconds_hex'])
    from dataclasses import replace
    from sludge_sandbox.source_trajectory import open_source_trajectory
    uninterrupted = open_source_trajectory(parent[0], tmp_path / 'continuous', end=session.end).advance()
    assert uninterrupted.status == 'completed'
    assert _same(replace(final.execution.result, elapsed_seconds=0.),
                 replace(uninterrupted.execution.result, elapsed_seconds=0.))
    assert _same(final.execution.observations, uninterrupted.execution.observations)
    assert final.balances == uninterrupted.balances


@pytest.fixture(scope='module')
def saved_packet(request, tmp_path_factory):
    existing = os.environ.get('SOURCE_RESUME_TEST_PACKET')
    if existing:
        return Path(existing)
    parent = request.getfixturevalue('parent')
    root = tmp_path_factory.mktemp('source-record-template')
    with pytest.MonkeyPatch.context() as patch:
        session = open_test_session(parent, root / 'run', patch)
        assert session.advance(pause_after_steps=1).status == 'paused'
        save_source_trajectory(session, root / 'packet')
    return root / 'packet'


@pytest.fixture
def packet(saved_packet, tmp_path, monkeypatch):
    manufactured_runtime(monkeypatch)
    path = tmp_path / 'packet'
    shutil.copytree(saved_packet, path, ignore=shutil.ignore_patterns('.restore-attempt'))
    return path


def reseal_file(packet, name):
    import hashlib
    manifest = json.loads((packet / 'manifest.json').read_bytes())
    raw = (packet / name).read_bytes()
    manifest['files'][name] = [hashlib.sha256(raw).hexdigest(), len(raw)]
    (packet / 'manifest.json').write_text(json.dumps(manifest))


def mutate_observations(packet, change):
    from sludge_sandbox.source_study_record import decode_source_study, encode_source_study
    from sludge_sandbox.source_study_schema import reify
    path = packet / 'source-observations.json'
    record = decode_source_study(path.read_bytes())
    captures = [dict(reify(c)) for c in record.captures]
    metadata = dict(reify(record.metadata))
    metadata['counts'] = dict(metadata['counts'])
    change(captures, metadata)
    path.write_bytes(encode_source_study({}, contexts=record.contexts,
        captures=tuple(captures), metadata=metadata))
    reseal_file(packet, path.name)


@pytest.mark.parametrize('mutation', ['counter', 'capture_order', 'balance'])
def test_rehashed_derived_evidence_is_rejected_before_provider(packet, tmp_path, monkeypatch, mutation):
    import sludge_sandbox.source_trajectory as trajectory
    def change(captures, metadata):
        if mutation == 'counter':
            metadata['counts']['rhs_started'] -= 1
        elif mutation == 'capture_order':
            captures[0], captures[1] = captures[1], captures[0]
            for i, capture in enumerate(captures, 1):
                capture['ordinal'] = i
        else:
            metadata['balances'] = ()
    mutate_observations(packet, change)
    monkeypatch.setattr(trajectory, 'build_source_run', lambda *a: pytest.fail('new provider before passive rejection'))
    with pytest.raises(ValueError):
        restore_source_trajectory(packet, tmp_path / 'failed')
    assert (packet / '.restore-attempt/failed.json').exists()
    with pytest.raises(ValueError, match='already_claimed'):
        restore_source_trajectory(packet, tmp_path / 'retry')


def test_unfinished_finalizer_is_rejected_even_with_valid_manifest(packet):
    (packet / 'FINALIZING.json').write_text('{"status":"unfinished_finalization"}')
    with pytest.raises(ValueError, match='unfinished_finalization'):
        read_source_trajectory_checkpoint(packet)


def test_missing_source_asset_cannot_be_replaced_by_numeric_checkpoint(packet, tmp_path, monkeypatch):
    import sludge_sandbox.source_trajectory as trajectory
    asset = next((packet / 'parent/assets').rglob('*.json'))
    asset.unlink()
    monkeypatch.setattr(trajectory, 'build_source_run', lambda *a: pytest.fail('new provider with missing asset'))
    with pytest.raises(ValueError, match='manifest_files'):
        restore_source_trajectory(packet, tmp_path / 'failed')


@pytest.mark.parametrize('offset', [86400 * 10**9, -86400 * 10**9])
def test_offline_wall_only_changes_diagnostic_not_charged_debit(packet, tmp_path, monkeypatch, offset):
    import sludge_sandbox.source_trajectory_record as module
    real_clock = module.time.monotonic
    anchor = json.loads((packet / 'packet.json').read_bytes())['suspended_wall_time_ns']
    debit = float.fromhex(json.loads((packet / 'packet.json').read_bytes())['charged_segment_seconds_hex'])
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=real_clock, time_ns=lambda: anchor + offset))
    def rebuild(directory, output, **kwargs):
        resume = kwargs['resume']
        assert debit <= real_clock() - resume.begin < debit + 30.
        assert resume.offline_history[-1]['status'] == (
            'diagnostic_only_not_charged' if offset > 0 else 'clock_discontinuity')
        return SimpleNamespace(recorder=SimpleNamespace(counts=dict(resume.observations.metadata['counts'])),
                               begin=resume.begin)
    monkeypatch.setattr(module, '_open_source_trajectory', rebuild)
    restored = restore_source_trajectory(packet, tmp_path / 'restored')
    assert real_clock() - restored.begin < debit + 30.


def test_exhausted_original_time_is_not_reset_by_restore(packet, tmp_path, monkeypatch):
    import sludge_sandbox.source_trajectory as trajectory
    path = packet / 'packet.json'
    raw = json.loads(path.read_bytes())
    raw['charged_segment_seconds_hex'] = float(1000).hex()
    path.write_text(json.dumps(raw)); reseal_file(packet, path.name)
    monkeypatch.setattr(trajectory, 'build_source_run', lambda *a: pytest.fail('new provider after spent budget'))
    with pytest.raises(ValueError, match='original_wall_budget_exhausted'):
        restore_source_trajectory(packet, tmp_path / 'failed')
