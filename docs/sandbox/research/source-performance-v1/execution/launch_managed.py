"""Single frozen new-implementation worker under the existing process supervisor."""
import json
from pathlib import Path
import runpy
import sys

repo = Path('/Users/wanggaoying/Desktop/brickmodel-github')
scratch = Path('/private/tmp/brick-source-performance-v1')
installed = Path(sys.executable).parent.parent / 'lib/python3.12/site-packages/sludge_sandbox'
inputs = [Path(__file__), scratch/'root/MANAGED_NATIVE_PLAN.md', scratch/'root/managed-request.json',
          scratch/'root/IMPLEMENTATION_FREEZE.json', scratch/'root/INSTALLED_IDENTITY.json',
          repo/'data/sandbox/cases/source-nonstationary-heos-rhs-v3.json']
inputs += sorted((repo/'src/sludge_sandbox').rglob('*.py')) + sorted(installed.rglob('*.py'))
inputs += sorted(p for p in (scratch/'managed-assets').rglob('*') if p.is_file())
run_attempt = runpy.run_path(str(repo/'docs/sandbox/research/research-process-supervisor/supervisor.py'))['run_attempt']
status = run_attempt(scratch/'supervised-rhs02',
    [sys.executable, '-I', '-m', 'sludge_sandbox.source_managed_worker', str(scratch/'root/managed-request.json')],
    cwd='/private/tmp', input_paths=inputs, timeout_s=120., cleanup_grace_s=1.)
print(json.dumps({k: v for k, v in status.items() if k != 'inputs_after'}, indent=2), flush=True)
sys.exit(0 if status['status'] == 'complete' and status.get('returncode') == 0 else 1)
