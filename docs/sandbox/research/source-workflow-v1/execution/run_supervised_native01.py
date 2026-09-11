"""One pre-registered installed workflow attempt. Does not retry a failure."""
import importlib.util
import json
from pathlib import Path
import sys

root = Path('/Users/wanggaoying/Desktop/brickmodel-github')
scratch = Path('/private/tmp/brick-source-workflow-v1')
python = Path('/private/tmp/brick-water-backend-probe/venv/bin/python')
installed = python.parent.parent / 'lib/python3.12/site-packages/sludge_sandbox'
supervisor = root / 'docs/sandbox/research/research-process-supervisor/supervisor.py'
spec = importlib.util.spec_from_file_location('registered_workflow_supervisor', supervisor)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
request = scratch / 'root/request-native01.json'
inputs = [request, Path(__file__).resolve(), supervisor,
    root / 'docs/sandbox/research/source-workflow-v1/NATIVE_PLAN.md',
    root / 'data/sandbox/cases/source-nonstationary-heos-workflow-v4.json']
inputs.extend(sorted((root / 'src/sludge_sandbox').glob('*.py')))
inputs.extend(sorted(installed.glob('*.py')))
inputs.extend(sorted(p for p in (scratch / 'assets').rglob('*') if p.is_file()))
result = module.run_attempt(scratch / 'supervised-native01',
    ['/usr/bin/env', '-u', 'PYTHONPATH', str(python), '-I', '-m',
     'sludge_sandbox.source_workflow_worker', str(request)],
    cwd='/private/tmp', input_paths=inputs, timeout_s=570., cleanup_grace_s=1.)
print(json.dumps({key: value for key, value in result.items() if not key.startswith('inputs_')}, indent=2))
sys.exit(0 if result['status'] == 'complete' and result['returncode'] == 0 else 1)
