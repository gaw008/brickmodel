"""Fixed service entrypoint for the owning job supervisor; never executes saved code."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
from typing import Any

from .job_supervisor import _cancel_requested, _write_json, read_job


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Owned sandbox service child')
    parser.add_argument('operation', choices=('run', 'replay', 'resume'))
    parser.add_argument('source', type=Path)
    parser.add_argument('--job-directory', required=True, type=Path)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--lock-fd', required=True, type=int)
    parser.add_argument('--water-data', type=Path)
    parser.add_argument('--evidence-data', type=Path)
    args = parser.parse_args(argv)
    started = time.monotonic()
    requested = False
    returncode = 1
    result_status: str | None = None
    error: dict[str, str] | None = None

    def request(signum: int, frame: Any) -> None:
        nonlocal requested
        requested = True

    def cancelled() -> bool:
        return requested or _cancel_requested(args.job_directory, args.job_id)

    previous = signal.signal(signal.SIGINT, request)
    try:
        # Keep this inherited descriptor open for the complete child lifetime.
        # Do not LOCK_UN it: parent and child share the same open description.
        os.fstat(args.lock_fd)
        job = read_job(args.job_directory)
        if (job['job_id'] != args.job_id or job['operation'] != args.operation or
                job['source'] != str(args.source.resolve())):
            raise ValueError('child_job_binding_mismatch')
        from .run_service import run_case, replay_run, resume_run

        output = args.job_directory/'run'
        if args.operation == 'run':
            if args.water_data is None:
                raise ValueError('run_requires_water_directory')
            result = run_case(args.source, args.water_data, output, cancel=cancelled,
                              evidence_directory=args.evidence_data)
        elif args.operation == 'replay':
            if args.water_data is not None or args.evidence_data is not None:
                raise ValueError('continuation_uses_frozen_input_directories')
            result = replay_run(args.source, output, cancel=cancelled)
        else:
            if args.water_data is not None or args.evidence_data is not None:
                raise ValueError('continuation_uses_frozen_input_directories')
            result = resume_run(args.source, output, cancel=cancelled)
        result_status = result['status']
        returncode = 0 if result_status == 'completed' else 1
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'reason': str(exc)}
        traceback.print_exc()
    finally:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        metrics = {
            'schema': 'sandbox_job_child_metrics_v1', 'job_id': args.job_id,
            'availability': 'observed_at_wrapper_exit', 'pid': os.getpid(),
            'returncode': returncode, 'run_status': result_status, 'error': error,
            'wrapper_elapsed_wall_seconds': time.monotonic()-started,
            'cpu_user_seconds': usage.ru_utime, 'cpu_system_seconds': usage.ru_stime,
            'peak_rss_native': usage.ru_maxrss,
            'peak_rss_unit': 'platform_native_ru_maxrss_unit_not_normalized',
            'platform': sys.platform,
            'scope': 'RUSAGE_SELF reports this child process including imports before wrapper timer; peak RSS native units are deliberately not interpreted as bytes or KiB. No descendant-process aggregate is claimed.'}
        _write_json(args.job_directory/'child-metrics.json', metrics)
        signal.signal(signal.SIGINT, previous)
    return returncode


if __name__ == '__main__':
    raise SystemExit(main())
