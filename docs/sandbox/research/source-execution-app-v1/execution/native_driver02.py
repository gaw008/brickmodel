"""One installed CLI journey; original numerical/material gates stay unchanged."""
from contextlib import redirect_stdout
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
SCRATCH = Path('/private/tmp/source-execution-app-v1')
ASSETS = Path('/private/tmp/brick-source-resume-v1/assets')
TOTAL_SECONDS = 510.
_stopping = False


def stop(signum, frame):
    global _stopping
    _stopping = True
    raise KeyboardInterrupt('outer_driver_termination')


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    from sludge_sandbox.cli import main as cli
    from sludge_sandbox.run_service import read_run_with_source_record
    from sludge_sandbox.source_execution_service import inspect_source_checkpoint
    from sludge_sandbox.source_trajectory_record import read_source_trajectory_checkpoint

    # Reuse the previous research-only passive comparison projection. It never
    # imports a saved class or performs physical reconstruction.
    projection_path = ROOT/'docs/sandbox/research/source-resume-v1/execution/verify_native.py'
    spec = importlib.util.spec_from_file_location('saved_source_research_projection', projection_path)
    projection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(projection)
    output = SCRATCH/'native02'
    output.mkdir(exist_ok=False)
    begin = time.monotonic()
    signal.signal(signal.SIGTERM, stop)
    jobs = []

    def execute(name, operation, source, *, refusal=False, **extra):
        remaining = TOTAL_SECONDS-(time.monotonic()-begin)
        if _stopping or remaining <= 5.:
            raise RuntimeError('journey_original_total_budget_exhausted')
        job_directory = output/name
        request = dict(schema='source_execution_request_v1', operation=operation,
            source=str(source), output=str(job_directory/'execution'),
            cancel_file=str(job_directory/'source-cancel'), shared_budget=None, **extra)
        request_path = output/(name+'-request.json')
        write(request_path, request)
        with (output/(name+'-cli.json')).open('x', encoding='utf-8') as stream:
            with redirect_stdout(stream):
                code = cli(['source-execute', str(request_path), '--job-directory', str(job_directory),
                            '--wall-seconds', str(min(180., remaining-5.)), '--grace-seconds', '5'])
        job = json.loads((job_directory/'job.json').read_bytes())
        if _stopping:
            raise RuntimeError('journey_cancelled_by_outer_supervisor')
        if refusal:
            assert code != 0 and job['pid'] is None and not job['child_reaped']
            assert not (job_directory/'execution').exists()
            assert job['reason'] == 'source_execution_service_restore_already_claimed'
            return job
        jobs.append(job)
        assert code == 0 and job['status'] in ('completed', 'paused')
        assert job['child_reaped'] is True and job['returncode'] == 0
        checked = job['result_verification']
        assert checked['record_valid'] is True and checked['status'] == job['status']
        result = json.loads((job_directory/'execution/OUTCOME.json').read_bytes())
        assert all(result[key] is False for key in (
            'material_qualified', 'training_eligible', 'full_firing_cycle',
            'historical_study_resume_authorized'))
        assert result['combined_counts'] == result['counts']
        assert all(n == 0 for n in result['declared_other_branch_counts'].values())
        print(json.dumps(dict(phase=name, status=job['status'], pid=job['pid'],
            counts=result['counts'], elapsed_seconds=time.monotonic()-begin)), flush=True)
        return result

    try:
        case = ROOT/'data/sandbox/cases/source-nonstationary-heos-resume-v5.json'
        assert hashlib.sha256(case.read_bytes()).hexdigest() == 'f416547debfc42e45e26894a81bad00ac8d5c0c5b2dd006423d9fc1761741028'
        parent = execute('parent', 'source-run', case, assets_root=str(ASSETS))
        assert parent['status'] == 'completed' and parent['details']['numerical_event_accepted'] is True
        parent_directory = output/'parent/execution/run'
        _, _, saved = read_run_with_source_record(parent_directory)
        start = saved.roots['transition'].candidates[1].reference.times_s[-1].seconds
        end = start+Fraction(3, 64)
        paused = execute('paused', 'source-advance', parent_directory, pause_after_steps=1,
            end=dict(numerator=end.numerator, denominator=end.denominator),
            step_sizes=dict(initial_step_s=1/64, maximum_step_s=1/64,
                            rationale='Original three-step conduction gate; application journey only.'))
        packet_directory = output/'paused/execution/resume-point'
        available = inspect_source_checkpoint(packet_directory)
        write(output/'CHECKPOINT_BEFORE.json', available)
        assert paused['status'] == 'paused' and available['record_valid'] and available['restore_available']
        packet = read_source_trajectory_checkpoint(packet_directory)
        assert len(packet.last_result.execution.result.steps) == 1
        assert len(packet.last_result.execution.observations) == 8
        prefix = {p.name: p.read_bytes() for p in (packet_directory/'events').glob('*.json')}
        resumed = execute('resumed', 'source-resume', packet_directory, pause_after_steps=0)
        assert resumed['status'] == 'completed'
        assert resumed['details']['accepted_steps'] == 3 and resumed['details']['observations'] == 22
        assert resumed['counts']['rhs_started'] == resumed['counts']['rhs_returned'] == 54
        assert resumed['counts']['heos_started'] == resumed['counts']['heos_returned'] == 12
        assert resumed['counts']['initial_energy_started'] == resumed['counts']['initial_energy_returned'] == 3
        assert resumed['counts']['wet_started'] == resumed['counts']['wet_returned'] == 8
        assert resumed['counts']['rhs_started']-paused['counts']['rhs_started'] == 14
        trajectory = output/'resumed/execution/trajectory'
        assert all((trajectory/'events'/name).read_bytes() == raw for name, raw in prefix.items())
        paused_events = projection.load_events(output/'paused/execution/trajectory')
        resumed_events = projection.load_events(trajectory)
        old = projection.decode_graph(next(e for e in reversed(paused_events)
            if e['event'] == 'ordinary_segment_returned')['payload'])
        final = projection.decode_graph(next(e for e in reversed(resumed_events)
            if e['event'] == 'ordinary_segment_returned')['payload'])
        assert projection.signature(old.execution.result.steps) == projection.signature(final.execution.result.steps[:1])
        assert projection.signature(old.execution.observations) == projection.signature(final.execution.observations[:8])
        assert final.execution.result.times_s[0].seconds == start
        assert final.execution.result.times_s[-1].seconds == end
        assert final.execution.result.evaluations == 22 and final.execution.result.rejected_trials == 0
        assert all(b.seconds-a.seconds == Fraction(1, 64) for a, b in
                   zip(final.execution.result.times_s, final.execution.result.times_s[1:]))
        after = inspect_source_checkpoint(packet_directory)
        write(output/'CHECKPOINT_AFTER.json', after)
        assert after['record_valid'] and not after['restore_available']
        refusal = execute('repeated-resume', 'source-resume', packet_directory,
                          pause_after_steps=0, refusal=True)
        elapsed = time.monotonic()-begin
        assert elapsed < TOTAL_SECONDS and len({job['pid'] for job in jobs}) == 3
        write(output/'ACCEPTANCE.json', dict(status='completed', elapsed_seconds=elapsed,
            separate_physical_worker_processes=3, workers_reaped=True,
            counts=resumed['counts'], accepted_steps=3, observations=22,
            exact_duration=dict(numerator=3, denominator=64),
            saved_event_prefix_preserved=True, first_step_and_observations_preserved=True,
            repeated_restore_refused_before_launch=True, repeated_restore_status=refusal['status'],
            original_budgets_preserved=True, controller_arithmetic_replay=False,
            material_qualified=False, training_eligible=False, full_firing_cycle=False))
    except BaseException as exc:
        write(output/'DRIVER_FAILURE.json', dict(status='failed', exception_type=type(exc).__name__,
            reason=str(exc), elapsed_seconds=time.monotonic()-begin, external_termination=_stopping))
        raise


if __name__ == '__main__':
    main()
