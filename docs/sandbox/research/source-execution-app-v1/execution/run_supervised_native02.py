"""One frozen input application journey under the existing research supervisor."""
import importlib.util
import json
from pathlib import Path
import sys

root = Path('/Users/wanggaoying/Desktop/brickmodel-github')
scratch = Path('/private/tmp/source-execution-app-v1')
python = Path('/private/tmp/brick-cooling-thermoelastic-v1/installed-venv/bin/python')
installed = python.parent.parent/'lib/python3.12/site-packages/sludge_sandbox'
assets = Path('/private/tmp/brick-source-resume-v1/assets')
supervisor = root/'docs/sandbox/research/research-process-supervisor/supervisor.py'
spec = importlib.util.spec_from_file_location('source_application_research_supervisor', supervisor)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
execution = Path(__file__).parent
inputs = [Path(__file__).resolve(), supervisor, execution/'native_driver02.py',
    execution/'NATIVE_PLAN_V2.md', execution/'NATIVE_PLAN.md', scratch/'install/SOURCE_FREEZE.json',
    root/'docs/sandbox/research/source-resume-v1/execution/verify_native.py',
    root/'data/sandbox/cases/source-nonstationary-heos-resume-v5.json']
inputs.extend(sorted(p for p in (root/'src/sludge_sandbox').rglob('*')
    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'))
inputs.extend(sorted(p for p in installed.rglob('*')
    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'))
inputs.extend(sorted(p for p in assets.rglob('*') if p.is_file()))

# Include the now-complete declared scientific runtimes, without importing EOS.
for package in ('iapws', 'CoolProp'):
    dependency = installed.parent/package
    inputs.extend(sorted(p for p in dependency.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'))
inputs.append(scratch/'install/IAPWS_PASSIVE_VALIDATION.json')
result = module.run_attempt(scratch/'supervised-native02',
    ['/usr/bin/env', '-u', 'PYTHONPATH', str(python), '-I', str(execution/'native_driver02.py')],
    cwd='/private/tmp', input_paths=inputs, timeout_s=570., cleanup_grace_s=10.)
print(json.dumps({k: v for k, v in result.items() if not k.startswith('inputs_')}, indent=2))
sys.exit(0 if result['status'] == 'complete' and result['returncode'] == 0 else 1)
