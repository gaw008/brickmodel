"""Actual short child processes exercise ownership; fixtures make no EOS claims."""
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from sludge_sandbox import job_supervisor as js

# Replaces only fixed service child's workload, retaining the real Popen handle,
# pipes, session and inherited lock descriptor. No fake poll/wait/kill methods.
FIXTURE = r'''
import hashlib,json,os,signal,sys,time
from pathlib import Path
folder=Path(sys.argv[1]); mode=sys.argv[2]
if mode in ('hang','orphan'):
    signal.signal(signal.SIGINT,signal.SIG_IGN)
elif mode=='cancel':
    signal.signal(signal.SIGINT,lambda *_: None)
(folder/'ready').write_text('ready')
if mode=='signal':
    os.kill(os.getpid(),signal.SIGKILL)
if mode in ('hang','cancel','orphan'):
    while not (folder/'release').exists():
        if mode=='cancel' and (folder/'cancel.json').exists(): break
        time.sleep(.01)
run=folder/'run'; run.mkdir()
case=b'{}'; (run/'case.json').write_bytes(case)
status='cancelled' if mode=='cancel' else ('numerical_failure' if mode=='failed' else 'completed')
(run/'result.json').write_text(json.dumps({'status':status,'reason':'fixture',
    'case_sha256':hashlib.sha256(case).hexdigest()}))
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}
(run/'manifest.json').write_text(json.dumps({'schema':'sandbox_run_manifest_v1','files':files}))
if mode=='tamper': (run/'result.json').write_text('{}')
job=json.loads((folder/'job.json').read_bytes())
(folder/'child-metrics.json').write_text(json.dumps({'job_id':job['job_id'],'availability':'test_fixture'}))
sys.exit(1 if mode in ('nonzero','failed','cancel') else 0)
'''


def workload(monkeypatch, mode):
    real_popen = subprocess.Popen
    handles = []

    def launch(args, **kwargs):
        folder = args[args.index('--job-directory')+1]
        process = real_popen([sys.executable, '-c', FIXTURE, folder, mode], **kwargs)
        handles.append(process)
        return process

    monkeypatch.setattr(js.subprocess, 'Popen', launch)
    return handles


def run(tmp_path, policy=None, **kwargs):
    return js.supervise('run', tmp_path/'case', tmp_path/'job',
                        policy or js.SupervisionPolicy(5., .1, .01),
                        water_directory=tmp_path/'water', **kwargs)


@pytest.mark.parametrize('field', ['maximum_wall_seconds','cancel_grace_seconds','poll_interval_seconds'])
@pytest.mark.parametrize('value', [True, 0., -1., float('inf'), float('nan')])
def test_invalid_policy(field, value):
    fields = dict(maximum_wall_seconds=1., cancel_grace_seconds=.1, poll_interval_seconds=.01)
    fields[field] = value
    with pytest.raises(js.SupervisionError): js.SupervisionPolicy(**fields)


@pytest.mark.parametrize('mode,status', [('complete','completed'), ('tamper','unverified_result'),
                                        ('nonzero','abnormal_exit'), ('failed','run_failed'),
                                        ('signal','abnormal_exit')])
def test_actual_exit_and_artifact_verification(tmp_path, monkeypatch, mode, status):
    handles = workload(monkeypatch, mode)
    value = run(tmp_path)
    assert value['status'] == status
    assert value['child_reaped'] and handles[0].returncode is not None
    assert js.read_job(tmp_path/'job')['status'] == status
    assert js.read_job(tmp_path/'job')['observation_status'] == 'persisted_not_live_process_proof'
    if mode == 'signal': assert value['metrics']['availability'] == 'unknown'


def test_deadline_kills_reaps_and_releases_scope(tmp_path, monkeypatch):
    handles = workload(monkeypatch, 'hang')
    started = time.monotonic()
    value = run(tmp_path, js.SupervisionPolicy(.2, .1, .01))
    assert value['status'] == 'timed_out' and value['hard_killed']
    assert handles[0].returncode == -signal.SIGKILL and value['child_reaped']
    assert value['metrics']['availability'] == 'unknown'
    # Generous OS scheduling guard, not an assertion of hard real-time accuracy.
    assert time.monotonic()-started < 5.
    again = js.supervise('replay', tmp_path/'missing', tmp_path/'second',
                         js.SupervisionPolicy(.2, .1, .01))
    assert again['status'] == 'timed_out'  # launched, not lock-refused
    assert len(handles) == 2 and all(p.returncode is not None for p in handles)


def test_cancel_request_is_bound_and_cooperative_child_is_reaped(tmp_path, monkeypatch):
    handles = workload(monkeypatch, 'cancel')
    requested = False

    def callback():
        nonlocal requested
        if (tmp_path/'job'/'ready').exists() and not requested:
            response = js.request_cancel(tmp_path/'job')
            assert response['status'] == 'request_recorded_not_cancellation_confirmation'
            requested = True
        return False

    value = run(tmp_path, cancel=callback)
    assert requested and value['status'] == 'cancelled' and not value['hard_killed']
    assert value['child_reaped'] and handles[0].returncode == 1
    assert value['result_verification']['run_status'] == 'cancelled'


def test_concurrent_same_parent_is_refused_without_launch(tmp_path, monkeypatch):
    handles = workload(monkeypatch, 'hang')
    nested = []

    def callback():
        if (tmp_path/'job'/'ready').exists() and not nested:
            nested.append(js.supervise('replay', 'missing', tmp_path/'second', js.SupervisionPolicy(1.)))
            return True
        return False

    value = run(tmp_path, cancel=callback)
    assert value['status'] == 'cancelled'
    assert nested[0]['status'] == 'refused' and nested[0]['pid'] is None
    assert len(handles) == 1 and handles[0].returncode == -signal.SIGKILL


def test_callback_exception_still_reaps(tmp_path, monkeypatch):
    handles = workload(monkeypatch, 'hang')

    def callback():
        if (tmp_path/'job'/'ready').exists(): raise RuntimeError('controller_failure')
        return False

    value = run(tmp_path, cancel=callback)
    assert value['status'] == 'supervisor_failed' and value['reason'] == 'controller_failure'
    assert value['child_reaped'] and handles[0].returncode == -signal.SIGKILL


def test_cancel_before_launch_and_wrong_request_id(tmp_path, monkeypatch):
    monkeypatch.setattr(js.subprocess, 'Popen', lambda *a, **k: pytest.fail('unexpected launch'))
    value = run(tmp_path, cancel=lambda: True)
    assert value['reason'] == 'cancelled_before_launch' and value['pid'] is None
    request = js.request_cancel(tmp_path/'job')
    assert js._cancel_requested(tmp_path/'job', request['job_id'])
    assert not js._cancel_requested(tmp_path/'job', 'different-id')
    with pytest.raises(FileExistsError): run(tmp_path)


def test_real_service_child_error_and_metrics(tmp_path):
    # Actual installed/source entrypoint, invalid input stops before build/EOS.
    value = run(tmp_path)
    assert value['status'] == 'unverified_result'
    assert value['child_reaped'] and value['returncode'] == 1
    assert value['metrics']['availability'] == 'observed_at_wrapper_exit'
    assert value['metrics']['cpu_user_seconds'] >= 0
    assert value['metrics']['peak_rss_native'] > 0


def test_cli_passes_options_and_exit_status(tmp_path, monkeypatch, capsys):
    from sludge_sandbox.cli import main
    seen = {}

    def fake(operation, source, directory, policy, **kwargs):
        seen.update(operation=operation, source=source, directory=directory, policy=policy, **kwargs)
        return {'status':'timed_out'}

    monkeypatch.setattr(js, 'supervise', fake)
    assert main(['supervise','run','case','--job-directory',str(tmp_path/'job'),
                 '--water-data','water','--wall-seconds','10','--grace-seconds','2']) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'timed_out'
    assert seen['operation'] == 'run' and seen['policy'].maximum_wall_seconds == 10
    assert seen['policy'].cancel_grace_seconds == 2 and callable(seen['cancel'])


def test_launch_failure_has_terminal_observation(tmp_path, monkeypatch):
    def fail(*args, **kwargs): raise OSError('launch_failed')
    monkeypatch.setattr(js.subprocess, 'Popen', fail)
    value = run(tmp_path)
    assert value['status'] == 'supervisor_failed' and value['pid'] is None
    assert js.read_job(tmp_path/'job')['reason'] == 'launch_failed'


def test_inherited_lock_survives_supervisor_death(tmp_path):
    import fcntl
    import os
    # Only the independent owner is killed using its live handle. Its fixture
    # child self-terminates after 2 seconds and accepts a release file; no stored
    # PID is signalled and no indefinite orphan workload is created.
    owner_script = r'''
import subprocess,sys
from sludge_sandbox import job_supervisor as js
real=subprocess.Popen
code="import time,sys; from pathlib import Path; p=Path(sys.argv[1]); (p/'ready').write_text('ready'); end=time.monotonic()+2;\nwhile time.monotonic()<end and not (p/'release').exists(): time.sleep(.01)"
def launch(args,**kwargs):
    folder=args[args.index('--job-directory')+1]
    return real([sys.executable,'-c',code,folder],**kwargs)
js.subprocess.Popen=launch
js.supervise('replay','unused',sys.argv[1],js.SupervisionPolicy(5.))
'''
    folder = tmp_path/'job'
    owner = subprocess.Popen([sys.executable, '-c', owner_script, str(folder)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    lock_fd = None
    try:
        deadline = time.monotonic()+5.
        while not (folder/'ready').exists():
            assert owner.poll() is None
            assert time.monotonic() < deadline
            time.sleep(.01)
        owner.kill()
        owner.wait(timeout=3.)
        lock_fd = os.open(tmp_path/'.sludge-sandbox-native.lock', os.O_RDWR)
        with pytest.raises(BlockingIOError):
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert js.read_job(folder)['observation_status'] == 'persisted_not_live_process_proof'
        (folder/'release').write_text('release')
        deadline = time.monotonic()+5.
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                assert time.monotonic() < deadline
                time.sleep(.01)
    finally:
        if folder.exists(): (folder/'release').write_text('release')
        if owner.poll() is None: owner.kill()
        owner.wait(timeout=3.)
        if owner.stderr is not None: owner.stderr.close()
        if lock_fd is not None: os.close(lock_fd)
