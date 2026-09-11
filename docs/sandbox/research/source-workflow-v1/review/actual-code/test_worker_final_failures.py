"""Independent pure worker control seams. No model construction or EOS.

Fake branch return records deliberately bypass numerical acceptance. This checks
only the real worker's final cancellation/publication/error and cost handling.
"""
import json
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

import sludge_sandbox._heos_rhs_scope as scope
import sludge_sandbox.run_service as runs
import sludge_sandbox.source_run_service as service
import sludge_sandbox.source_trajectory as trajectory
import sludge_sandbox.exact_integration_checkpoint as checkpoint
import sludge_sandbox.exact_integration_checkpoint_codec as codec
import sludge_sandbox.source_workflow_worker as worker
from sludge_sandbox.exact_event_clock import ExactEventTime as T


ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')


@pytest.mark.parametrize('failure_kind', ['cancel', 'publication', 'clear', 'deadline', 'success'])
def test_final_worker_control(monkeypatch, tmp_path, failure_kind):
    clock = [100.]
    monkeypatch.setattr(worker, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(worker, '_require_isolated_entry', lambda: None)
    configured = [False]
    clear_calls = []
    original_error = OSError('independent final publication or clear seam')

    def configure(deadline):
        assert deadline == 610. and not configured[0]
        configured[0] = True

    def clear():
        clear_calls.append(True)
        if failure_kind == 'clear':
            raise original_error
        configured[0] = False

    monkeypatch.setattr(scope, '_configure_workflow_deadline', configure)
    monkeypatch.setattr(scope, '_clear_workflow_deadline', clear)
    monkeypatch.setattr(worker, '_require_idle_scope', lambda: None)
    monkeypatch.setattr(runs, 'runtime_identity', lambda: {'pure_control_seam': True})
    counts = dict(heos_started=4, heos_kernel_returned=4, heos_returned=4,
        initial_energy_started=3, initial_energy_returned=3,
        rhs_started=32, rhs_returned=32, wet_started=8, wet_returned=8)
    parent = dict(status='completed', numerical_event_accepted=True,
                  counts=counts, elapsed_wall_seconds=1.)
    monkeypatch.setattr(service, 'run_source_case', lambda *a, **kw: parent)
    start = T(Fraction(1, 1000000))
    record = SimpleNamespace(roots={'transition': SimpleNamespace(candidates=[None,
        SimpleNamespace(end=start)])})
    monkeypatch.setattr(runs, 'read_run_with_source_record', lambda path: (parent, None, record))
    sentinel = object()
    monkeypatch.setattr(codec, 'encode_exact_checkpoint', lambda frame: b'pure checkpoint seam')
    monkeypatch.setattr(codec, 'decode_exact_checkpoint', lambda raw: sentinel)
    monkeypatch.setattr(checkpoint, '_same', lambda a, b: a is b)
    sessions = []

    class Session:
        def __init__(self, name):
            self.name, self.call_count = name, 0
            self.recorder = SimpleNamespace(counts=dict(counts,
                heos_started=8, heos_kernel_returned=8, heos_returned=8), stop_status=None)
            self.checkpoint = None

        def advance(self, pause_after_steps=None):
            self.call_count += 1
            is_pause = pause_after_steps is not None
            added = 8 if is_pause else (14 if self.name == 'paused' else 22)
            self.recorder.counts['rhs_started'] += added
            self.recorder.counts['rhs_returned'] += added
            self.checkpoint = sentinel if is_pause else None
            return SimpleNamespace(status='paused' if is_pause else 'completed', reason=None,
                execution=SimpleNamespace(checkpoint=self.checkpoint,
                    result=SimpleNamespace(steps=(1,) if is_pause else (1, 2, 3))))

    def opening(parent_path, output, **kwargs):
        assert kwargs['managed_execution'] is True and configured[0]
        session = Session(output.name)
        sessions.append(session)
        return session

    monkeypatch.setattr(trajectory, 'open_source_trajectory', opening)
    output = tmp_path / 'run'
    cancel_file = tmp_path / 'cancel'

    def verify(*args):
        assert [s.call_count for s in sessions] == [1, 2]
        if failure_kind == 'cancel':
            cancel_file.touch()
        elif failure_kind == 'deadline':
            clock[0] = 610.
        return {'control_seam_only': True}

    monkeypatch.setattr(worker, '_verify_paths', verify)
    publish = worker._publish

    def publication(path, value):
        if path.name == 'ACCEPTANCE.json' and failure_kind == 'publication':
            raise original_error
        return publish(path, value)

    monkeypatch.setattr(worker, '_publish', publication)
    request = dict(schema='source_workflow_request_v1',
        operation='fresh_parent_three_step_comparison',
        case_path=str(ROOT / 'data/sandbox/cases/source-nonstationary-heos-workflow-v4.json'),
        assets_root=str(tmp_path), output=str(output), cancel_file=str(cancel_file),
        material_qualified=False, segment=dict(duration_numerator=3, duration_denominator=64,
        step_numerator=1, step_denominator=64, pause_after_steps=1))
    request_path = tmp_path / 'request.json'
    request_path.write_text(json.dumps(request))
    if failure_kind == 'success':
        result = worker._execute_request(request_path)
        assert result['status'] == 'completed'
        assert not (output / 'FAILURE.json').exists()
        assert clear_calls == [True] and not configured[0]
        return
    with pytest.raises(Exception) as caught:
        worker._execute_request(request_path)
    if failure_kind in ('clear', 'publication'):
        assert caught.value is original_error
    failure = json.loads((output / 'FAILURE.json').read_bytes())
    assert failure['status'] == {'cancel': 'cancelled', 'deadline': 'resource_limit'}.get(failure_kind, 'failed')
    assert failure['total_known_actual_counts'] == dict(counts,
        heos_started=12, heos_kernel_returned=12, heos_returned=12,
        rhs_started=76, rhs_returned=76)
    assert failure['count_completeness'] == 'complete_observed_counts'
    assert failure['material_qualified'] is failure['training_eligible'] is False
    assert not (output / 'ACCEPTANCE.json').exists()
    assert clear_calls == ([True, True] if failure_kind == 'clear' else [True])
    if failure_kind == 'clear':
        assert failure['secondary_errors'][0]['stage'] == 'clear_deadline'
    else:
        assert not configured[0]
