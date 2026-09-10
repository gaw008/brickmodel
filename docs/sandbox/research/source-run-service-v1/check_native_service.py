"""Check the completed owned native job and exercise installed passive CLI.

No physics is run here. The job's original comparison gates remain unchanged.
"""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import time

from sludge_sandbox.cli import main
from sludge_sandbox.run_service import read_run
from sludge_sandbox.source_run_observer import observer_scope

job_directory, output = map(Path, sys.argv[1:3])
begin = time.monotonic()
stream = None
attempts = []
try:
    job = json.loads((job_directory / 'job.json').read_bytes())
    run = job_directory / 'run'
    result = json.loads((run / 'result.json').read_bytes())
    manifest = json.loads((run / 'manifest.json').read_bytes())
    assert job['status'] == 'completed' and job['child_reaped'] and job['returncode'] == 0
    assert result['status'] == result['execution_status'] == 'completed'
    assert result['runtime_before'] == result['runtime_after']
    assert not result['material_qualified'] and not result['full_firing_cycle']
    assert result['numerical_comparison_completed'] is True
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == digest, name
    counts = result['counts']
    assert tuple(counts[k] for k in ('heos_started', 'heos_kernel_returned', 'heos_returned')) == (4, 4, 4)
    assert counts['initial_energy_started'] == counts['initial_energy_returned'] == 3
    assert 0 < counts['rhs_returned'] <= counts['rhs_started'] <= 97
    assert 0 < counts['wet_returned'] <= counts['wet_started'] <= 16
    events = [json.loads(path.read_bytes()) for path in sorted((run / 'events').glob('*.json'))]
    assert len(events) == result['journal_events']
    assert [item['ordinal'] for item in events] == list(range(1, len(events) + 1))
    for key, count in counts.items():
        assert sum(event['event'] == key for event in events) == count, key
    for phase in ('seed', 'proposal', 'approach', 'refinement'):
        assert any(event['event'] == 'stage_returned' and
                   any(node.get('fields', {}).get('stage') == phase
                       for node in event['payload']['nodes'].values()) for event in events), phase
    assert sum(event['event'] == 'candidate_returned' for event in events) == 2
    assert sum(event['event'] == 'transition_returned' for event in events) == 1

    attempts = []
    def forbid_physics(event, **payload):
        if event in ('heos_started', 'rhs_started', 'wet_started'):
            attempts.append(event)
            raise AssertionError('passive_inspection_attempted_physics')

    stream = io.StringIO()
    with observer_scope(forbid_physics), redirect_stdout(stream):
        checked_result, checked_manifest = read_run(run)
        assert checked_result == result and checked_manifest == manifest
        code = main(['source-study-inspect', str(run / 'source-study-record.json'),
            '--capture-index', '16', '--cell', '1', '--path', 'transition/cell_selected_pressure_gates'])
    assert code == 0 and not attempts
    inspection = json.loads(stream.getvalue())
    assert inspection['capture_count'] == counts['rhs_started']
    assert inspection['stages']['transition']['numerical_event_accepted'] == result['numerical_event_accepted']
    assert inspection['stages']['transition']['material_qualified'] is False
    assert inspection['audit']['checks']['completed_reference_replays'] == 3
    assert inspection['physical_run_reexecuted'] is False
    report = dict(status='verified', scope='actual installed source study service, not full firing/material validation',
        job_directory=str(job_directory), case_sha256=result['case_sha256'],
        record_sha256=result['source_record']['sha256'], counts=counts,
        job_status=job['status'], child_reaped=job['child_reaped'],
        numerical_comparison_completed=True, numerical_event_accepted=result['numerical_event_accepted'],
        physical_end_seconds=result['physical_end_seconds'], material_qualified=False, full_firing_cycle=False,
        run_elapsed_wall_seconds=result['elapsed_wall_seconds'],
        passive_elapsed_wall_seconds=time.monotonic() - begin,
        inspection=inspection, forbidden_physical_attempts=attempts)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'inspection'}, ensure_ascii=False))
except Exception as exc:
    failure = dict(status='failed', scope='passive native service acceptance; original run preserved',
        stage='native_service_verification', exception_type=type(exc).__name__, reason=str(exc),
        job_directory=str(job_directory), elapsed_wall_seconds=time.monotonic() - begin,
        cli_stdout=stream.getvalue() if stream is not None else None,
        forbidden_physical_attempts=attempts)
    output.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + '\n')
    raise
