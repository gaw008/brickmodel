"""One predeclared physical validation path, including its references, in ten seconds."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True)
    parser.add_argument('--case', choices=('relaxation', 'cooling'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    inputs = [root/'run_validation.py', root/'PREREGISTRATION.md', Path(__file__).resolve()]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    args.output.mkdir(parents=True, exist_ok=False)
    command = [args.python, '-I', str(root/'run_validation.py'), '--case', args.case,
               '--output', str(args.output.resolve()/'worker'),
               '--preregistration', str(root/'PREREGISTRATION.md')]
    record = dict(command=command, cwd='/private/tmp', timeout_s=10,
                  input_sha256_before=hashes)
    with (args.output/'START.json').open('x') as stream:
        json.dump(record, stream, indent=2)
    started = time.monotonic()
    with (args.output/'stdout.log').open('x') as stdout, (args.output/'stderr.log').open('x') as stderr:
        try:
            result = subprocess.run(command, cwd='/private/tmp', stdout=stdout,
                                    stderr=stderr, timeout=10, check=False)
            record.update(returncode=result.returncode, timed_out=False, child_reaped=True)
        except subprocess.TimeoutExpired:
            # run() kills and waits for its child before raising this exception.
            record.update(returncode=None, timed_out=True, child_reaped=True)
        except OSError as exc:
            record.update(returncode=None, timed_out=False, launch_error=str(exc), child_reaped=None)
    record['elapsed_s'] = time.monotonic()-started
    record['input_sha256_after'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    record['inputs_unchanged'] = record['input_sha256_after'] == hashes
    with (args.output/'EXECUTION.json').open('x') as stream:
        json.dump(record, stream, indent=2)
    return 0 if record.get('returncode') == 0 and record['inputs_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
