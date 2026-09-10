"""Installed-style source CLI and the actual fixed child dispatch, no EOS."""
import json
from pathlib import Path

from test_mass_storage_bridge import REPOSITORY
from sludge_sandbox.cli import main
from sludge_sandbox.job_supervisor import supervise, SupervisionPolicy
from sludge_sandbox.run_service import read_run


def test_source_validate_and_error_cli(tmp_path, capsys):
    case = REPOSITORY / 'data/sandbox/cases/source-multicell-heos-v1.json'
    assert main(['source-validate', str(case), '--assets-root', str(REPOSITORY)]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value['source_assets_checked'] is True and value['material_qualified'] is False
    output = tmp_path / 'missing-run'
    assert main(['source-run', str(tmp_path / 'missing'), '--assets-root', str(REPOSITORY),
                 '--output', str(output)]) == 1
    value = json.loads(capsys.readouterr().out)
    assert value['status'] == 'failed' and value['counts']['heos_started'] == 0
    assert read_run(output)[0]['original_case_available'] is False


def test_supervisor_runs_real_source_child_and_reaps_it(tmp_path, monkeypatch):
    # Resolve the test invocation's source imports before the supervisor changes
    # child cwd. In installed acceptance, this points to the installed package.
    import sludge_sandbox
    monkeypatch.setenv('PYTHONPATH', str(Path(sludge_sandbox.__file__).resolve().parents[1]))
    job = tmp_path / 'job'
    value = supervise('source-run', tmp_path / 'absent', job,
        SupervisionPolicy(20., 1., .05), assets_root=REPOSITORY)
    assert value['status'] == 'run_failed'
    assert value['child_reaped'] is True and value['returncode'] == 1
    result, _ = read_run(job / 'run')
    assert result['integration_kind'] == 'source_wet_to_dry_study_v1'
    assert result['counts']['heos_started'] == 0
