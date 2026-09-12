"""One 130-second deadline for import, BOTH native paths, comparison and recording."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

DEADLINE_S = 130.


def load_driver():
    path = Path(__file__).resolve().with_name('run_validation.py')
    spec = importlib.util.spec_from_file_location('cooling_energy_validation_driver', path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    return driver


def supervise(freeze_path, output, *, runner=None, clock=None):
    """Injectable process boundary for short fake tests; never retry a worker."""
    runner = subprocess.run if runner is None else runner
    clock = time.monotonic if clock is None else clock
    started = clock()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = dict(passed=False, timeout_s=DEADLINE_S, child_reaped=None,
        timed_out=False, real_native_integration=False,
        unreturned_accepted_prefix='unknown', terminal_status='preflight_failed')
    driver = load_driver()
    before = None
    try:
        freeze = driver.read_freeze(freeze_path)
        before = driver.verify_freeze(freeze, freeze_path)
        command = [freeze['python_executable'], '-I', str(Path(driver.__file__).resolve()),
                   '--freeze', str(Path(freeze_path).resolve()),
                   '--output', str(output.resolve()/'worker')]
        record.update(command=command, cwd='/private/tmp', input_sha256_before=before)
        driver.write_new(output/'START.json', record)
        remaining = DEADLINE_S-(clock()-started)
        if remaining <= 0:
            record.update(timed_out=True, terminal_status='deadline_before_launch')
        else:
            with (output/'stdout.log').open('x') as stdout, (output/'stderr.log').open('x') as stderr:
                try:
                    process = runner(command, cwd='/private/tmp', stdout=stdout, stderr=stderr,
                                     timeout=remaining, check=False)
                    record.update(returncode=process.returncode, child_reaped=True,
                                  terminal_status='worker_returned')
                except subprocess.TimeoutExpired:
                    # subprocess.run kills and waits for the child before raising.
                    record.update(returncode=None, timed_out=True, child_reaped=True,
                                  terminal_status='external_deadline')
                except OSError as exc:
                    record.update(returncode=None, launch_error=str(exc), terminal_status='launch_failed')
                except Exception as exc:
                    record.update(returncode=None, process_error=f'{type(exc).__name__}:{exc}',
                                  child_reaped=None, terminal_status='process_outcome_unknown')
    except Exception as exc:
        record.update(preflight_error=f'{type(exc).__name__}:{exc}')
    try:
        after = driver.verify_freeze(freeze, freeze_path) if before is not None else None
        record.update(input_sha256_after=after, inputs_unchanged=before is not None and after == before)
    except Exception as exc:
        record.update(inputs_unchanged=False, post_verification_error=f'{type(exc).__name__}:{exc}')
    # Even after a hard kill, enumerate only files that actually reached disk.
    worker = output/'worker'
    record['preserved_worker_files'] = sorted(p.name for p in worker.iterdir()) if worker.is_dir() else []
    try:
        child = json.loads((worker/'RESULT.json').read_text())
        record['worker_result'] = child
        record['real_native_integration'] = child.get('real_native_integration') is True
        required = {'INPUTS.json', 'coarse.json', 'fine.json', 'coarse-audit.json', 'fine-audit.json', 'RESULT.json'}
        evidence_complete = required <= set(record['preserved_worker_files'])
        record['complete_worker_artifacts_present'] = evidence_complete
        record['passed'] = (record.get('returncode') == 0 and not record['timed_out']
            and record['child_reaped'] is True and record.get('inputs_unchanged') is True
            and child.get('passed') is True and child.get('inputs_unchanged') is True
            and child.get('real_native_integration') is True and evidence_complete)
        if record['terminal_status'] == 'worker_returned':
            record['terminal_status'] = 'completed' if record['passed'] else 'worker_failed'
    except Exception as exc:
        record.update(passed=False, worker_result_read_error=f'{type(exc).__name__}:{exc}')
        if record['terminal_status'] == 'worker_returned':
            record['terminal_status'] = 'worker_evidence_unreadable'
    record['elapsed_s'] = clock()-started
    if record['elapsed_s'] >= DEADLINE_S:
        record.update(passed=False, end_to_end_deadline_exceeded=True)
        if record['terminal_status'] == 'completed':
            record['terminal_status'] = 'deadline_during_verification'
    driver.write_new(output/'EXECUTION.json', record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    record = supervise(args.freeze, args.output)
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
