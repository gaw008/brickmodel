"""Real short process ownership; the substituted workload performs no physics."""
import json
from pathlib import Path
import signal
import subprocess
import sys
import types

import pytest

from sludge_sandbox import job_supervisor as js


def service_fixture(monkeypatch, status='completed'):
    seen = {}

    def prepare(request_path, directory):
        seen['prepare'] = (request_path, directory)
        (directory / 'request.json').write_bytes(Path(request_path).read_bytes())
        return {'operation': 'source-run', 'request_sha256': 'test-only'}

    def inspect(directory, *, returncode=None, termination_cause=None):
        seen['inspect'] = (directory, returncode, termination_cause)
        return {'status': status, 'reported_status': status,
                'validation_scope': 'manufactured_process_test_only',
                'material_qualified': False}

    fake = types.SimpleNamespace(prepare_source_execution=prepare,
                                inspect_source_execution=inspect)
    monkeypatch.setitem(sys.modules, 'sludge_sandbox.source_execution_service', fake)
    return seen


def workload(monkeypatch, mode):
    real = subprocess.Popen
    seen = []
    program = r'''
import signal,sys,time
from pathlib import Path
p=Path(sys.argv[1]); mode=sys.argv[2]
signal.signal(signal.SIGINT,signal.SIG_IGN)
(p/'ready').write_text('fixture')
if mode!='complete':
    end=time.monotonic()+3
    while time.monotonic()<end:
        if mode=='sentinel' and (p/'source-cancel').exists():
            (p/'sentinel-observed').write_text('yes'); break
        if mode=='release' and (p/'release').exists(): break
        time.sleep(.005)
'''

    def launch(args, **kwargs):
        # Validate the real fixed dispatch before substituting a tiny process.
        assert args[:4] == [sys.executable, '-I', '-m',
                           'sludge_sandbox.source_execution_worker']
        assert len(args) == 5 and Path(args[4]).name == 'request.json'
        assert kwargs['pass_fds'] and kwargs['start_new_session']
        process = real([sys.executable, '-I', '-c', program,
                        str(Path(args[4]).parent), mode], **kwargs)
        seen.append(process)
        return process

    monkeypatch.setattr(js.subprocess, 'Popen', launch)
    return seen


def launch(tmp_path, *, cancel=None, policy=None):
    request = tmp_path / 'original.json'
    request.write_bytes(b'{"test_only":true}\n')
    return js.supervise('source-execute', request, tmp_path / 'job',
                        policy or js.SupervisionPolicy(3., .15, .01), cancel=cancel)


@pytest.mark.parametrize('status', ['completed', 'paused', 'unverified_result'])
def test_fixed_isolated_entry_and_result_dispatch(tmp_path, monkeypatch, status):
    seen = service_fixture(monkeypatch, status)
    handles = workload(monkeypatch, 'complete')
    result = launch(tmp_path)
    assert result['status'] == status and result['child_reaped']
    assert handles[0].returncode == 0
    assert result['run_directory'] == 'execution/run'
    assert result['execution_directory'] == 'execution'
    assert result['metrics']['availability'] == 'unknown'
    assert result['preparation_seconds'] >= 0
    assert result['result_verification_seconds'] >= 0
    assert seen['inspect'][1:] == (0, None)
    assert json.loads((tmp_path / 'job/RESULT_VERIFICATION.json').read_bytes())['status'] == status
    assert js.read_job(tmp_path / 'job')['operation'] == 'source-execute'


def test_bound_cancel_publishes_worker_sentinel_and_overrides_late_success(tmp_path, monkeypatch):
    seen = service_fixture(monkeypatch)
    handles = workload(monkeypatch, 'sentinel')
    sent = False

    def cancel():
        nonlocal sent
        if (tmp_path / 'job/ready').exists() and not sent:
            js.request_cancel(tmp_path / 'job')
            sent = True
        return False

    result = launch(tmp_path, cancel=cancel)
    assert sent and result['status'] == 'cancelled' and result['child_reaped']
    assert (tmp_path / 'job/sentinel-observed').read_text() == 'yes'
    sentinel = json.loads((tmp_path / 'job/source-cancel').read_bytes())
    assert sentinel['job_id'] == result['job_id']
    assert handles[0].returncode == 0 and not result['hard_killed']
    assert seen['inspect'][2] == 'user_cancel'


def test_wrong_job_cancel_never_becomes_worker_sentinel(tmp_path, monkeypatch):
    service_fixture(monkeypatch)
    workload(monkeypatch, 'release')
    sent = False

    def cancel():
        nonlocal sent
        if (tmp_path / 'job/ready').exists() and not sent:
            (tmp_path / 'job/cancel.json').write_text(json.dumps({
                'schema': 'sandbox_job_cancel_v1', 'job_id': 'another-job'}))
            (tmp_path / 'job/release').write_text('finish fixture')
            sent = True
        return False

    result = launch(tmp_path, cancel=cancel)
    assert sent and result['status'] == 'completed'
    assert not (tmp_path / 'job/source-cancel').exists()


def test_source_request_symlink_reaches_nofollow_admission_without_resolution(tmp_path, monkeypatch):
    target = tmp_path / 'original.json'
    target.write_text('{}')
    link = tmp_path / 'request-link.json'
    link.symlink_to(target)

    def prepare(request_path, directory):
        if request_path.is_symlink():
            raise ValueError('request_symlink_rejected')
        pytest.fail('supervisor erased the request symlink before admission')

    fake = types.SimpleNamespace(prepare_source_execution=prepare)
    monkeypatch.setitem(sys.modules, 'sludge_sandbox.source_execution_service', fake)
    monkeypatch.setattr(js.subprocess, 'Popen', lambda *a, **kw: pytest.fail('unexpected launch'))
    result = js.supervise('source-execute', link, tmp_path/'job', js.SupervisionPolicy(1.))
    assert result['reason'] == 'request_symlink_rejected' and result['pid'] is None
    assert not (tmp_path/'job/execution').exists()


def test_timeout_still_kills_and_reaps_owned_child(tmp_path, monkeypatch):
    service_fixture(monkeypatch)
    handles = workload(monkeypatch, 'ignore')
    result = launch(tmp_path, policy=js.SupervisionPolicy(.2, .1, .01))
    assert result['status'] == 'timed_out' and result['hard_killed']
    assert result['child_reaped'] and handles[0].returncode == -signal.SIGKILL
    assert (tmp_path / 'job/source-cancel').is_file()


@pytest.mark.parametrize('status,code', [('completed', 0), ('paused', 0), ('unverified_result', 1)])
def test_cli_managed_execution_passes_policy_and_status(tmp_path, monkeypatch, capsys, status, code):
    from sludge_sandbox.cli import main
    seen = {}

    def supervise(operation, source, directory, policy, **kwargs):
        seen.update(operation=operation, source=source, directory=directory, policy=policy, **kwargs)
        return {'status': status, 'material_qualified': False}

    monkeypatch.setattr(js, 'supervise', supervise)
    assert main(['source-execute', 'request.json', '--job-directory', str(tmp_path/'job'),
                 '--wall-seconds', '12', '--grace-seconds', '1']) == code
    assert json.loads(capsys.readouterr().out)['status'] == status
    assert seen['operation'] == 'source-execute'
    assert seen['policy'].maximum_wall_seconds == 12 and callable(seen['cancel'])


@pytest.mark.parametrize('command,value,code', [
    ('source-execution-inspect', {'status': 'completed', 'record_valid': True}, 0),
    ('source-execution-inspect', {'status': 'unverified_result', 'record_valid': False}, 1),
    ('source-checkpoint-inspect', {'record_valid': True, 'restore_available': True}, 0),
    ('source-checkpoint-inspect', {'record_valid': True, 'restore_available': False}, 0),
    ('source-checkpoint-inspect', {'record_valid': False, 'restore_available': False}, 1),
])
def test_cli_inspection_keeps_record_validity_separate_from_restore_authority(
        tmp_path, monkeypatch, capsys, command, value, code):
    from sludge_sandbox.cli import main
    seen = []

    def inspect(directory):
        seen.append(directory)
        return value

    fake = types.SimpleNamespace(inspect_source_execution=inspect, inspect_source_checkpoint=inspect)
    monkeypatch.setitem(sys.modules, 'sludge_sandbox.source_execution_service', fake)
    monkeypatch.setattr(js.subprocess, 'Popen', lambda *a, **kw: pytest.fail('inspection launched a child'))
    assert main([command, str(tmp_path)]) == code
    assert json.loads(capsys.readouterr().out) == value and seen == [tmp_path]
