"""Bounded POSIX research subprocess supervision; no kernel-level deadline claim."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from typing import Sequence


def _atomic_json(path: Path, data: dict) -> None:
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _duration(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive')
    return float(value)


def _signal_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


def _cleanup(process: subprocess.Popen, grace: float) -> dict:
    # Also stop descendants when the group leader has already exited. A child
    # can inherit stdout/stderr; direct file output avoids pipe-drain deadlocks.
    errors = []
    def send(sig):
        try:
            _signal_group(process.pid, sig)
        except OSError as exc:
            errors.append(f'{signal.Signals(sig).name}: {type(exc).__name__}')
    send(signal.SIGTERM)
    started = time.monotonic()
    # Reap promptly: probing an unreaped group leader can fail with EPERM in
    # restricted hosts. Escalate the original group even if its leader exited.
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    remaining = grace - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)
    send(signal.SIGKILL)
    try:
        process.wait(timeout=grace)
        reaped = True
    except subprocess.TimeoutExpired:
        reaped = False
    return {'term_sent': True, 'kill_attempted': True, 'leader_reaped': reaped,
            'signal_errors': errors,
            'scope': 'original_process_group_only; escaped_sessions_not_contained'}


class SupervisorTerminated(BaseException):
    """SIGTERM interrupted supervision; child cleanup still runs."""


def run_attempt(attempt_dir: str | Path, command: Sequence[str], *, cwd: str | Path,
                input_paths: Sequence[str | Path] = (), timeout_s: float = 1,
                cleanup_grace_s: float = .1) -> dict:
    """Main-thread POSIX supervisor; preserves the caller's SIGTERM handler.

    Arguments and child logs are retained verbatim: callers must exclude secrets.
    Repeated TERM during cleanup is ignored; SIGKILL cannot be handled.
    """
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('supervision requires the main thread for signal cleanup')
    previous = signal.getsignal(signal.SIGTERM)
    termination = {'spawning': False, 'pending': False}

    def terminate(signum, frame):
        termination['pending'] = True
        if not termination['spawning']:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            raise SupervisorTerminated('supervisor received SIGTERM')

    signal.signal(signal.SIGTERM, terminate)
    try:
        return _run_attempt(attempt_dir, command, cwd=cwd, input_paths=input_paths,
                            timeout_s=timeout_s, cleanup_grace_s=cleanup_grace_s,
                            termination=termination)
    finally:
        signal.signal(signal.SIGTERM, previous)


def _run_attempt(attempt_dir: str | Path, command: Sequence[str], *, cwd: str | Path,
                input_paths: Sequence[str | Path] = (), timeout_s: float = 1,
                cleanup_grace_s: float = .1, termination: dict) -> dict:
    """Create one exclusive attempt; never overwrite/reuse a prior result.

    Command runs without a shell, in a new session/process group. Timeout limits
    parent waiting, followed by bounded cleanup. OS scheduling, uninterruptible
    native calls and deliberately escaped process groups preclude a hard guarantee.
    Inputs are hash observations, not a sandbox or immutable filesystem snapshot.
    """
    timeout = _duration(timeout_s, 'timeout_s')
    grace = _duration(cleanup_grace_s, 'cleanup_grace_s')
    if isinstance(command, (str, bytes)) or not command or any(not isinstance(x, str) or not x or '\0' in x for x in command):
        raise ValueError('command must be a nonempty argument sequence')
    directory = Path(cwd).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError('cwd must be a directory')
    inputs = {}
    for item in input_paths:
        path = Path(item)
        path = (directory / path).resolve(strict=True) if not path.is_absolute() else path.resolve(strict=True)
        if not path.is_file():
            raise ValueError('input must be a regular file')
        inputs[str(path)] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
    attempt = Path(attempt_dir).absolute()
    attempt.mkdir(parents=False, exist_ok=False)
    metadata = {'attempt_id': attempt.name, 'attempt_dir': str(attempt), 'command': list(command),
                'cwd': str(directory), 'inputs_before': inputs, 'timeout_s': timeout,
                'cleanup_grace_s': grace, 'supervisor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'started_unix_s': time.time()}
    _atomic_json(attempt / 'metadata.json', metadata)
    status = {'attempt_id': attempt.name, 'status': 'running', 'returncode': None}
    _atomic_json(attempt / 'status.json', status)
    started = time.monotonic()
    process = None
    try:
        with (attempt / 'stdout.log').open('xb') as stdout, (attempt / 'stderr.log').open('xb') as stderr:
            try:
                # Defer TERM until the new child has an owned cleanup handle.
                termination['spawning'] = True
                try:
                    process = subprocess.Popen(list(command), cwd=directory, stdout=stdout, stderr=stderr,
                                               shell=False, start_new_session=True, close_fds=True)
                finally:
                    termination['spawning'] = False
                    if termination['pending']:
                        raise SupervisorTerminated('supervisor received SIGTERM during launch')
                code = process.wait(timeout=timeout)
                status.update(status='complete' if code == 0 else 'failed', returncode=code)
            except subprocess.TimeoutExpired:
                status.update(status='timed_out')
            finally:
                if process is not None:
                    # A first TERM during cleanup must not interrupt escalation.
                    termination['spawning'] = True
                    try:
                        status['cleanup'] = _cleanup(process, grace)
                        status['returncode'] = process.returncode
                        if status['status'] == 'complete':
                            if not status['cleanup']['leader_reaped']:
                                status.update(status='failed', error='leader_not_reaped')
                            elif status['cleanup']['signal_errors']:
                                status.update(status='failed', error='group_cleanup_unverified')
                    finally:
                        termination['spawning'] = False
                    if termination['pending']:
                        raise SupervisorTerminated('supervisor received SIGTERM')
    except BaseException as exc:
        status.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        if not isinstance(exc, Exception):
            raise
    finally:
        status['elapsed_s'] = time.monotonic() - started
        status['inputs_after'] = {}
        for path in inputs:
            try:
                status['inputs_after'][path] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            except OSError as exc:
                status['inputs_after'][path] = {'error': type(exc).__name__}
        status['inputs_unchanged'] = all(status['inputs_after'][path] == data['sha256'] for path, data in inputs.items())
        if status['status'] == 'complete' and not status['inputs_unchanged']:
            status.update(status='failed', error='declared_inputs_changed')
        _atomic_json(attempt / 'status.json', status)
    return status
