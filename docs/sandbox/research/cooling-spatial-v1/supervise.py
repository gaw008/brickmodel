"""Thirty seconds total for one registered grid's two time-accuracy runs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time


LIMIT_SECONDS = 30.


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, allow_nan=False, separators=(',', ':'))
        stream.write('\n')


def hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def confirmed_prefix(path, state_size=None):
    """Read only intact newline-terminated accepted records; never repair a file."""
    count, last, trailing_error = 0, None, None
    if not path.exists():
        return dict(count=0, last=None, trailing_error=None)
    with path.open() as stream:
        for line in stream:
            if not line.endswith('\n'):
                trailing_error = 'unterminated_final_record'
                break
            try:
                row = json.loads(line)
                t = row['time_s']
                state = row['state']
                if (type(t) not in (int, float) or not math.isfinite(t)
                        or t < 0 or t > 10 or (last is not None and t <= last['time_s'])
                        or (last is None and t != 0.)
                        or not isinstance(state, list) or not state
                        or (state_size is not None and len(state) != state_size)
                        or any(type(x) not in (int,float) or not math.isfinite(x) for x in state)):
                    raise ValueError('invalid accepted record')
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                trailing_error = str(exc)
                break
            count += 1
            last = dict(time_s=t, state=state)
    return dict(count=count, last=last, trailing_error=trailing_error)


def supervise(python, cells, output, *, run_child=subprocess.run, clock=time.monotonic):
    if type(cells) is not int or cells not in (16,32,64):
        raise ValueError('registered_grid_required')
    started = clock()
    deadline = started+LIMIT_SECONDS
    root = Path(__file__).resolve().parent
    inputs = [root/'run_spatial.py', root/'NEXT.md', Path(__file__).resolve()]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    before = hashes(inputs)
    command = [str(python), '-I', str(root/'run_spatial.py'), '--cells', str(cells),
               '--output', str(output.resolve()/'worker'), '--protocol', str(root/'NEXT.md'),
               '--deadline-monotonic', repr(deadline)]
    record = dict(cells=cells, command=command, cwd='/private/tmp', timeout_s=LIMIT_SECONDS,
                  input_sha256_before=before, started_monotonic=started,
                  deadline_monotonic=deadline)
    write_new(output/'START.json', record)
    with (output/'stdout.log').open('x') as stdout, (output/'stderr.log').open('x') as stderr:
        try:
            remaining = deadline-clock()
            if remaining <= 0.:
                raise TimeoutError('deadline_before_child_launch')
            child = run_child(command, cwd='/private/tmp', stdout=stdout, stderr=stderr,
                              timeout=remaining, check=False)
            record.update(returncode=child.returncode, timed_out=False, child_reaped=True)
        except subprocess.TimeoutExpired:
            # subprocess.run kills and waits for its direct child before raising.
            record.update(returncode=None, timed_out=True, child_reaped=True)
        except TimeoutError as exc:
            record.update(returncode=None, timed_out=True, child_reaped=None, launch_error=str(exc))
        except OSError as exc:
            record.update(returncode=None, timed_out=False, child_reaped=None, launch_error=str(exc))
    record['child_finished_elapsed_s'] = clock()-started
    evidence_errors = {}
    try:
        record['input_sha256_after'] = hashes(inputs)
        record['inputs_unchanged'] = record['input_sha256_after'] == before
    except OSError as exc:
        record['input_sha256_after'] = None
        record['inputs_unchanged'] = False
        evidence_errors['post_input_hashes'] = dict(type=type(exc).__name__,message=str(exc))
    record['accepted_prefixes'] = {}
    for name in ('coarse','fine'):
        try:
            prefix = confirmed_prefix(output/'worker'/name/'accepted.jsonl',3*cells+1)
            record['accepted_prefixes'][name] = prefix
            if prefix['trailing_error'] is not None:
                evidence_errors[f'{name}_accepted_prefix'] = dict(
                    type='IncompleteOrInvalidRecord',message=prefix['trailing_error'])
        except (OSError, UnicodeDecodeError) as exc:
            error = dict(type=type(exc).__name__,message=str(exc))
            record['accepted_prefixes'][name] = dict(count=None,last=None,read_error=error)
            evidence_errors[f'{name}_accepted_prefix'] = error
    result_path = output/'worker'/'result.json'
    try:
        worker = json.loads(result_path.read_text())
        if not isinstance(worker,dict):
            raise ValueError('worker_result_must_be_json_object')
        record['worker_status'] = worker.get('status')
        record['worker_real_time_integration'] = worker.get('real_time_integration')
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        record['worker_status'] = None
        record['worker_result_error'] = str(exc)
        evidence_errors['worker_result'] = dict(type=type(exc).__name__,message=str(exc))
    record['evidence_errors'] = evidence_errors
    record['elapsed_s'] = clock()-started
    record['within_wall_limit'] = record['elapsed_s'] <= LIMIT_SECONDS
    record['passed'] = bool(record.get('returncode') == 0 and record['inputs_unchanged']
                            and not record['timed_out'] and record['within_wall_limit']
                            and not evidence_errors
                            and record['worker_status'] == 'completed'
                            and record.get('worker_real_time_integration') is True)
    write_new(output/'EXECUTION.json', record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True)
    parser.add_argument('--cells', type=int, choices=(16,32,64), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = supervise(args.python, args.cells, args.output)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
