"""Synchronous ownership of one bounded child, with persisted job observations.

The lock scope is the resolved parent directory of a job. This is not a machine-
wide scheduler. Signals target only this call's Popen handle, never a stored PID.
The inherited flock descriptor keeps that scope locked if the supervisor dies
while its child remains alive. A killed child may leave an unsealed run prefix.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Callable
import uuid

_OPERATIONS = ('run', 'source-run', 'source-execute', 'replay', 'resume')


class SupervisionError(ValueError):
    """An invalid job request or persisted observation."""


@dataclass(frozen=True)
class SupervisionPolicy:
    maximum_wall_seconds: float
    cancel_grace_seconds: float = 5.0
    poll_interval_seconds: float = 0.05

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            try:
                valid = type(value) in (int, float) and math.isfinite(value) and value > 0
            except OverflowError:
                valid = False
            if not valid:
                raise SupervisionError('invalid_supervision_'+name)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps(value, allow_nan=False, ensure_ascii=False, indent=2)+'\n',
                             encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_job(job_directory: str | Path) -> dict[str, Any]:
    """Read a persisted observation; this never proves that a PID is alive."""
    path = Path(job_directory)/'job.json'
    if path.is_symlink():
        raise SupervisionError('invalid_job_record_path')
    try:
        value = json.loads(path.read_bytes())
        if (type(value) is not dict or value.get('schema') != 'sandbox_job_v1' or
                str(uuid.UUID(value['job_id'])) != value['job_id'] or
                value['operation'] not in _OPERATIONS):
            raise SupervisionError('invalid_job_record')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise SupervisionError('invalid_job_record') from exc
    return {**value, 'observation_status': 'persisted_not_live_process_proof'}


def request_cancel(job_directory: str | Path) -> dict[str, Any]:
    """Publish a job-ID-bound request; never signal a persisted PID."""
    directory = Path(job_directory)
    job = read_job(directory)
    request = {'schema': 'sandbox_job_cancel_v1', 'job_id': job['job_id'],
               'requested_at': _timestamp()}
    _write_json(directory/'cancel.json', request)
    return {**request, 'status': 'request_recorded_not_cancellation_confirmation'}


def _cancel_requested(directory: Path, job_id: str) -> bool:
    path = directory/'cancel.json'
    if not path.exists():
        return False
    if path.is_symlink():
        raise SupervisionError('invalid_cancel_request_path')
    try:
        value = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise SupervisionError('invalid_cancel_request') from exc
    if type(value) is not dict or value.get('schema') != 'sandbox_job_cancel_v1':
        raise SupervisionError('invalid_cancel_request')
    return value.get('job_id') == job_id


def _signal_owned(process: subprocess.Popen[bytes], signum: int) -> None:
    # Popen polls before signalling and handles the normal exit race itself.
    try:
        process.send_signal(signum)
    except ProcessLookupError:
        pass


def _publish_source_cancel(directory: Path, job_id: str, cause: str) -> None:
    """Publish only after this supervisor admits a cancellation for its child."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(directory/'source-cancel', flags, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        json.dump({'schema': 'source_worker_cancel_v1', 'job_id': job_id,
                   'cause': cause}, stream)
        stream.write('\n')


def _verify_result(directory: Path, returncode: int) -> dict[str, Any]:
    from .run_service import read_run

    try:
        result, manifest = read_run(directory/'run')
    except (ValueError, OSError) as exc:
        return {'status': 'unverified_result', 'verification_error': str(exc)}
    result_status = result.get('status')
    verified = {'run_status': result_status, 'run_reason': result.get('reason'),
                'result_sha256': manifest['files']['result.json'],
                'case_sha256': result.get('case_sha256'), 'manifest_verified': True}
    if returncode == 0 and result_status == 'completed':
        return {**verified, 'status': 'completed'}
    if result_status == 'completed':
        return {**verified, 'status': 'abnormal_exit'}
    if result_status == 'cancelled':
        return {**verified, 'status': 'cancelled'}
    if result_status in ('numerical_failure', 'domain_exit', 'resource_limit', 'failed'):
        return {**verified, 'status': 'run_failed'}
    return {**verified, 'status': 'unverified_result'}


def supervise(operation: str, source: str | Path, job_directory: str | Path,
              policy: SupervisionPolicy, *, water_directory: str | Path | None = None,
              evidence_directory: str | Path | None = None,
              assets_root: str | Path | None = None,
              cancel: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Own, supervise, terminate if necessary, and reap a fixed service child.

    The wall limit includes child import, initialization, integration and final
    diagnostics. SIGINT starts a cooperative grace period; SIGKILL follows if
    needed. Maximum wall plus grace plus polling/reaping scheduling is the
    operational bound, not a real-time guarantee against OS scheduling stalls.
    """
    if operation not in _OPERATIONS or not isinstance(policy, SupervisionPolicy):
        raise SupervisionError('invalid_supervision_request')
    if cancel is not None and not callable(cancel):
        raise SupervisionError('invalid_cancel_callback')
    if operation == 'run' and water_directory is None:
        raise SupervisionError('run_requires_water_directory')
    if operation == 'source-run' and assets_root is None:
        raise SupervisionError('source_run_requires_assets_root')
    if operation != 'source-run' and assets_root is not None:
        raise SupervisionError('assets_root_only_for_source_run')
    if operation != 'run' and (water_directory is not None or evidence_directory is not None):
        raise SupervisionError('continuation_uses_frozen_input_directories')
    directory = Path(job_directory).absolute()
    directory.mkdir(parents=True, exist_ok=False)
    directory = directory.resolve()
    begin = time.monotonic()
    job: dict[str, Any] = {
        'schema': 'sandbox_job_v1', 'job_id': str(uuid.uuid4()), 'operation': operation,
        'source': str(Path(source).absolute() if operation == 'source-execute' else Path(source).resolve()),
        'status': 'preparing', 'reason': None,
        'started_at': _timestamp(), 'policy': asdict(policy),
        'lock_scope': str(directory.parent), 'lock_scope_meaning': 'one active child per resolved job parent directory',
        'run_directory': None if operation == 'source-execute' else 'run',
        'pid': None, 'pid_meaning': 'informational only; never used by saved-job cancellation',
        'returncode': None, 'child_reaped': False, 'termination_cause': None,
        'metrics': {'availability': 'unknown_until_clean_child_exit'},
        'wall_bound_scope': 'maximum_wall_seconds + cancel_grace_seconds + polling/reaping scheduling; whole child, not only integrate()'}
    process: subprocess.Popen[bytes] | None = None
    lock_fd: int | None = None
    termination_started: float | None = None
    hard_killed = False
    if operation == 'source-execute':
        job.update(execution_directory='execution', preparation_seconds=None,
                   result_verification_seconds=None)

    def persist() -> None:
        job['elapsed_wall_seconds'] = time.monotonic()-begin
        job['updated_at'] = _timestamp()
        _write_json(directory/'job.json', job)

    persist()
    try:
        flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0)
        lock_fd = os.open(directory.parent/'.sludge-sandbox-native.lock', flags, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            job.update(status='refused', reason='native_child_lock_busy')
            return job
        if operation == 'source-execute':
            from .source_execution_service import prepare_source_execution
            preparation_begin = time.monotonic()
            try:
                binding = prepare_source_execution(Path(job['source']), directory)
            finally:
                job['preparation_seconds'] = time.monotonic()-preparation_begin
            job['input_binding'] = binding
            if binding['operation'] == 'source-run':
                job['run_directory'] = 'execution/run'
            args = [sys.executable, '-I', '-m', 'sludge_sandbox.source_execution_worker',
                    str(directory/'request.json')]
        else:
            args = [sys.executable, '-m', 'sludge_sandbox.job_child', operation,
                    job['source'], '--job-directory', str(directory), '--job-id', job['job_id'],
                    '--lock-fd', str(lock_fd)]
        if water_directory is not None:
            args += ['--water-data', str(Path(water_directory).resolve())]
        if assets_root is not None:
            args += ['--assets-root', str(Path(assets_root).resolve())]
        if evidence_directory is not None:
            args += ['--evidence-data', str(Path(evidence_directory).resolve())]
        job['argv'] = args
        if (cancel is not None and cancel()) or _cancel_requested(directory, job['job_id']):
            job.update(status='cancelled', reason='cancelled_before_launch', termination_cause='user_cancel')
            return job
        if time.monotonic()-begin >= policy.maximum_wall_seconds:
            job.update(status='timed_out', reason='wall_timeout_before_launch', termination_cause='wall_timeout')
            return job
        with (directory/'stdout.log').open('wb') as stdout, (directory/'stderr.log').open('wb') as stderr:
            process = subprocess.Popen(args, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                       pass_fds=(lock_fd,), close_fds=True, start_new_session=True)
            job.update(status='running', pid=process.pid)
            persist()
            while process.poll() is None:
                now = time.monotonic()
                if termination_started is None:
                    cause = None
                    if now-begin >= policy.maximum_wall_seconds:
                        cause = 'wall_timeout'
                    elif (cancel is not None and cancel()) or _cancel_requested(directory, job['job_id']):
                        cause = 'user_cancel'
                    if cause is not None:
                        termination_started = now
                        job.update(status='terminating', termination_cause=cause,
                                   cancellation_sent_at=_timestamp())
                        if operation == 'source-execute':
                            _publish_source_cancel(directory, job['job_id'], cause)
                        _signal_owned(process, signal.SIGINT)
                        persist()
                if termination_started is not None and now-termination_started >= policy.cancel_grace_seconds:
                    if process.poll() is None:
                        _signal_owned(process, signal.SIGKILL)
                        hard_killed = True
                    break
                boundary = (begin+policy.maximum_wall_seconds if termination_started is None else
                            termination_started+policy.cancel_grace_seconds)
                time.sleep(max(0.0, min(policy.poll_interval_seconds, 60.0, boundary-time.monotonic())))
            job['returncode'] = process.wait()
            job['child_reaped'] = True
        if job['termination_cause'] is None and time.monotonic()-begin >= policy.maximum_wall_seconds:
            job['termination_cause'] = 'wall_timeout'
            job['deadline_observation'] = 'Child termination was not observed before the deadline; no claim about an unobserved earlier exit time.'
        if operation == 'source-execute':
            from .source_execution_service import inspect_source_execution
            verification_begin = time.monotonic()
            try:
                verification = inspect_source_execution(directory, returncode=job['returncode'],
                                                        termination_cause=job['termination_cause'])
                _write_json(directory/'RESULT_VERIFICATION.json', verification)
            finally:
                job['result_verification_seconds'] = time.monotonic()-verification_begin
        else:
            verification = _verify_result(directory, job['returncode'])
        job['result_verification'] = verification
        cause = job['termination_cause']
        if cause is not None:
            job.update(status='timed_out' if cause == 'wall_timeout' else 'cancelled', reason=cause)
        elif job['returncode'] < 0:
            job.update(status='abnormal_exit', reason='child_terminated_by_signal')
        else:
            job.update(status=verification['status'], reason=verification.get('run_reason', verification.get('verification_error')))
        metrics_path = directory/'child-metrics.json'
        if not hard_killed and job['returncode'] >= 0 and metrics_path.is_file():
            try:
                metrics = json.loads(metrics_path.read_bytes())
                if metrics.get('job_id') != job['job_id']:
                    raise SupervisionError('child_metrics_binding_mismatch')
                job['metrics'] = metrics
            except (ValueError, AttributeError) as exc:
                job['metrics'] = {'availability': 'unknown', 'reason': str(exc)}
        else:
            job['metrics'] = {'availability': 'unknown', 'reason': 'hard_kill_or_no_clean_child_metrics'}
    except BaseException as exc:
        job.update(status='supervisor_failed', reason=str(exc), error_type=type(exc).__name__)
        if process is not None and process.poll() is None:
            _signal_owned(process, signal.SIGINT)
            try:
                process.wait(timeout=policy.cancel_grace_seconds)
            except subprocess.TimeoutExpired:
                _signal_owned(process, signal.SIGKILL)
                hard_killed = True
                process.wait()
        if process is not None:
            job.update(returncode=process.returncode, child_reaped=process.returncode is not None)
    finally:
        job['hard_killed'] = hard_killed
        # Never explicitly unlock a shared inherited flock while a child lives.
        if lock_fd is not None:
            os.close(lock_fd)
        persist()
    return job
