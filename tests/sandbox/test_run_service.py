"""Application boundary checks; no manufactured result is a material validation."""
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from sludge_sandbox.run_service import RunError, read_run, runtime_identity, trace_run

CASE = Path(__file__).resolve().parents[2]/'data/sandbox/cases/reacting-wet-slab-v1.json'


def test_runtime_identity_is_content_bound():
    identity = runtime_identity()
    assert len(identity['modules']['integration.py']) == 64
    assert 'python' in identity


def test_missing_run_is_explicit(tmp_path):
    with pytest.raises(RunError, match='invalid_run'):
        read_run(tmp_path)


@pytest.mark.parametrize('name', ['../outside', '/tmp/outside', 'water/../../outside'])
def test_manifest_rejects_escape_before_open(tmp_path, name):
    (tmp_path/'manifest.json').write_text(json.dumps({
        'schema': 'sandbox_run_manifest_v1', 'files': {name: 'a'*64}}))
    with pytest.raises(RunError, match='invalid_artifact_path'):
        read_run(tmp_path)


def test_trace_unknown_quantity_fails_without_loading_run(tmp_path):
    with pytest.raises(RunError, match='unsupported_quantity'):
        trace_run(tmp_path, 'compressive_strength_mpa')


def save_manifest(tmp_path):
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in tmp_path.iterdir() if p.name != 'manifest.json'}
    (tmp_path/'manifest.json').write_text(json.dumps({
        'schema': 'sandbox_run_manifest_v1', 'files': files}))


def test_modified_result_is_not_read_as_original(tmp_path):
    (tmp_path/'case.json').write_text('{}')
    (tmp_path/'result.json').write_text(json.dumps({'case_sha256': hashlib.sha256(b'{}').hexdigest()}))
    save_manifest(tmp_path)
    read_run(tmp_path)
    (tmp_path/'result.json').write_text('{}')
    with pytest.raises(RunError, match='artifact_hash_mismatch'):
        read_run(tmp_path)


def test_case_binding_checked_even_when_each_file_hash_is_valid(tmp_path):
    (tmp_path/'case.json').write_text('{}')
    (tmp_path/'result.json').write_text(json.dumps({'case_sha256': 'a'*64}))
    save_manifest(tmp_path)
    with pytest.raises(RunError, match='case_binding_mismatch'):
        read_run(tmp_path)


def test_added_input_is_not_silently_used_for_replay(tmp_path):
    (tmp_path/'case.json').write_text('{}')
    (tmp_path/'result.json').write_text(json.dumps({'case_sha256': hashlib.sha256(b'{}').hexdigest()}))
    save_manifest(tmp_path)
    (tmp_path/'water').mkdir()
    (tmp_path/'water'/'new.json').write_text('{}')
    with pytest.raises(RunError, match='unrecorded_run_artifacts'):
        read_run(tmp_path)


@pytest.mark.parametrize('status', ['resource_limit', 'numerical_failure', 'domain_exit', 'cancelled', 'failed'])
def test_cli_noncompletion_is_nonzero(monkeypatch, capsys, tmp_path, status):
    from sludge_sandbox import run_service
    from sludge_sandbox.cli import main
    monkeypatch.setattr(run_service, 'run_case', lambda *a, **k: {'status': status})
    assert main(['run', 'case', '--water-data', 'water', '--output', str(tmp_path/'out')]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == status


def test_prebuild_cancel_is_saved_and_output_cannot_be_overwritten(tmp_path, monkeypatch):
    from sludge_sandbox.run_service import run_case
    from sludge_sandbox import verification_case
    water = tmp_path/'water'
    water.mkdir()
    # A nested manifest must be covered too.
    (water/'manifest.json').write_text('{}')
    monkeypatch.setattr(verification_case, 'build_case', lambda *a: pytest.fail('cancelled build called'))
    output = tmp_path/'run'
    result = run_case(CASE, water, output, cancel=lambda: True)
    assert result['status'] == 'cancelled'
    saved, manifest = read_run(output)
    assert saved == result
    assert 'water/manifest.json' in manifest['files']
    with pytest.raises(FileExistsError):
        run_case(CASE, water, output)


def test_diagnostic_failure_retains_accepted_solver_states(tmp_path, monkeypatch):
    import numpy as np
    from sludge_sandbox import verification_case
    from sludge_sandbox.integration import ConservedState, IntegrationPolicy, Rates
    from sludge_sandbox.run_service import run_case

    class ZeroOperator:
        def __call__(self, state, time):
            return Rates(np.zeros((3, 5)), np.zeros(3), np.zeros((2, 5)), np.zeros(2))

        def breakpoints_s(self, start, end):
            return ()

    built = SimpleNamespace(initial=ConservedState(np.ones((2, 5)), np.ones(2)),
        operator=ZeroOperator(), start_s=0., end_s=.125, initialization={},
        policy=IntegrationPolicy(.125, .125, 1e-12, 1e-7, 1e-12, 1e-8, 1., 1., 10, 10, 10.))
    monkeypatch.setattr(verification_case, 'build_case', lambda *a: built)

    def fail_snapshot(*a):
        if a[-1] == 0.:
            return {'status': 'initial_checked'}
        raise ValueError('diagnostic_failure')

    monkeypatch.setattr(verification_case, 'snapshot', fail_snapshot)
    water = tmp_path/'water'
    water.mkdir()
    result = run_case(CASE, water, tmp_path/'run')
    assert result['status'] == 'failed'
    assert result['integration']['status'] == 'completed'
    assert result['integration']['times_s'][-1] == .125
    assert result['integration']['steps']
    read_run(tmp_path/'run')
    assert trace_run(tmp_path/'run', 'amounts_mol')['value'] == [[1.]*5]*2


@pytest.mark.parametrize('mutation,code', [
    (lambda p: p.update(material_qualified=True), 'evidence_incomplete'),
    (lambda p: p.update(model_id='real_sludge'), 'unsupported_model'),
    (lambda p: p['solid'].update(classification='measured_public_data'), 'evidence_incomplete'),
    (lambda p: p['transport'].update(typo=1), 'invalid_case'),
    (lambda p: p['initial']['parent_amounts_mol'][0].__setitem__(0, True), 'invalid_case'),
])
def test_case_rejects_false_admission_and_unknown_parameters(tmp_path, mutation, code):
    from sludge_sandbox.verification_case import CaseError, read_case
    payload = json.loads(CASE.read_bytes())
    mutation(payload)
    path = tmp_path/'case.json'
    path.write_text(json.dumps(payload))
    with pytest.raises(CaseError) as caught:
        read_case(path)
    assert caught.value.code == code


def test_case_parser_has_no_eos_import_dependency():
    import subprocess
    import sys
    code = '''import sys
from sludge_sandbox.verification_case import read_case
read_case(sys.argv[1])
assert not any(n in sys.modules for n in ('numpy','CoolProp','iapws'))
'''
    subprocess.run([sys.executable, '-c', code, str(CASE)], check=True)


def test_cli_sigint_requests_cooperative_cancel_and_restores_handler(monkeypatch, capsys, tmp_path):
    import signal
    from sludge_sandbox import run_service
    from sludge_sandbox.cli import main
    previous = signal.getsignal(signal.SIGINT)

    def fake_run(*args, cancel, evidence_directory):
        assert not cancel()
        signal.raise_signal(signal.SIGINT)
        assert cancel()
        return {'status': 'cancelled'}

    monkeypatch.setattr(run_service, 'run_case', fake_run)
    assert main(['run', 'case', '--water-data', 'water', '--output', str(tmp_path/'out')]) == 1
    assert signal.getsignal(signal.SIGINT) is previous
    assert json.loads(capsys.readouterr().out)['status'] == 'cancelled'


@pytest.mark.parametrize('files', [['case.json'], 'case.json'])
def test_malformed_manifest_container_is_structured_error(tmp_path, files):
    (tmp_path/'manifest.json').write_text(json.dumps({'schema': 'sandbox_run_manifest_v1', 'files': files}))
    with pytest.raises(RunError, match='invalid_run_manifest'):
        read_run(tmp_path)
