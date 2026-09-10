"""One bounded attempt using the existing process supervisor, no shell child."""
from pathlib import Path
import json
import os
import runpy
import sys

root = Path('/Users/wanggaoying/Desktop/brickmodel-github')
scratch = Path('/private/tmp/brick-source-dynamic-continuation-v1')
stage = root/'docs/sandbox/research/source-dynamic-continuation-v1'
assert 'PYTHONPATH' not in os.environ
installed = Path(sys.executable).parent.parent/'lib/python3.12/site-packages/sludge_sandbox'
inputs = [stage/'run_native_v2.py', stage/'NATIVE_PLAN_V2.md',
          root/'data/sandbox/cases/source-nonstationary-heos-v2.json',
          root/'data/sandbox/cases/source-nonstationary-heos-v1.json',
          root/'data/sandbox/cases/source-multicell-heos-v1.json', Path(__file__)]
inputs += sorted((root/'src/sludge_sandbox').rglob('*.py')) + sorted(installed.rglob('*.py'))
assert len(list(installed.rglob('*.py'))) == 146
run_attempt = runpy.run_path(str(root/'docs/sandbox/research/research-process-supervisor/supervisor.py'))['run_attempt']
status = run_attempt(scratch/'supervised-native02',
                     [sys.executable, str(stage/'run_native_v2.py'), str(root),
                      '/private/tmp/brick-source-run-service-v1/native-job01/run/assets', str(scratch/'native02')],
                     cwd='/private/tmp', input_paths=inputs, timeout_s=570., cleanup_grace_s=1.)
print(json.dumps({k:v for k,v in status.items() if k != 'inputs_after'}, indent=2), flush=True)
sys.exit(0 if status['status'] == 'complete' and status.get('returncode') == 0 else 1)
