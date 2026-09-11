"""One original-implementation diagnostic sample under an existing supervisor."""
import json
from pathlib import Path
import runpy
import sys

repo = Path('/Users/wanggaoying/Desktop/brickmodel-github')
scratch = Path('/private/tmp/brick-source-performance-v1')
installed = Path(sys.executable).parent.parent/'lib/python3.12/site-packages/sludge_sandbox'
inputs = [scratch/'root/profile_rhs.py', scratch/'root/PROFILE_PLAN.md', Path(__file__),
          repo/'data/sandbox/cases/source-nonstationary-heos-v2.json']
inputs += sorted((repo/'src/sludge_sandbox').rglob('*.py')) + sorted(installed.rglob('*.py'))
run_attempt = runpy.run_path(str(repo/'docs/sandbox/research/research-process-supervisor/supervisor.py'))['run_attempt']
status = run_attempt(scratch/'supervised-rhs01', [sys.executable, str(scratch/'root/profile_rhs.py')],
                     cwd='/private/tmp', input_paths=inputs, timeout_s=120., cleanup_grace_s=1.)
print(json.dumps({k:v for k,v in status.items() if k != 'inputs_after'}, indent=2), flush=True)
sys.exit(0 if status['status'] == 'complete' and status.get('returncode') == 0 else 1)
