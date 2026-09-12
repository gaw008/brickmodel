"""One bounded child process; preserve its actual terminal status and logs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(exist_ok=False)
    script = Path(__file__).resolve().parent/'probe.py'
    d1 = script.parent.parents[1]/'wang2021-drying-holdout-v1'/'reproduce'
    inputs = [Path(args.csv).resolve(), script.parent.parent/'PREREGISTRATION.md']
    inputs += list(sorted(script.parent.glob('*.py')))
    inputs += [d1/'wang_d1.py', d1/'study_io.py']

    def hashes():
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}

    command = [sys.executable, '-I', str(script), '--csv', str(Path(args.csv).resolve()),
               '--output', str(output/'training')]
    record = dict(started_utc=datetime.now(timezone.utc).isoformat(), command=command,
                  hard_timeout_s=630, inputs_before=hashes())
    (output/'supervisor-start.json').write_text(json.dumps(record, indent=2)+'\n')
    began = time.monotonic()
    try:
        with (output/'stdout.log').open('x') as stdout, (output/'stderr.log').open('x') as stderr:
            child = subprocess.run(command, cwd=output, stdout=stdout, stderr=stderr,
                                   timeout=630, check=False)
        record.update(returncode=child.returncode, timed_out=False, child_reaped=True)
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits for this single Python child on timeout.
        record.update(returncode=None, timed_out=True, child_reaped=True)
    except Exception as exc:
        record.update(returncode=None, timed_out=False, error=type(exc).__name__+': '+str(exc))
    record['elapsed_seconds'] = time.monotonic()-began
    record['inputs_after'] = hashes()
    record['inputs_unchanged'] = record['inputs_before'] == record['inputs_after']
    (output/'supervisor-end.json').write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
    print(json.dumps(record), flush=True)
    return 0 if record.get('returncode') == 0 and record['inputs_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
