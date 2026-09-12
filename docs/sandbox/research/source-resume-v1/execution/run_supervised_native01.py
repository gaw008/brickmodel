"""One preregistered cross-process attempt; preserve all inputs and failures."""
import importlib.util
import json
from pathlib import Path
import sys

root = Path('/Users/wanggaoying/Desktop/brickmodel-github')
scratch = Path('/private/tmp/brick-source-resume-v1')
python = Path('/private/tmp/brick-water-backend-probe/venv/bin/python')
installed = python.parent.parent / 'lib/python3.12/site-packages/sludge_sandbox'
supervisor = root/'docs/sandbox/research/research-process-supervisor/supervisor.py'
spec = importlib.util.spec_from_file_location('source_resume_supervisor',supervisor)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
execution = Path(__file__).parent
inputs = [Path(__file__).resolve(), supervisor, execution/'native_driver.py', execution/'verify_native.py',
    execution.parent/'NATIVE_PLAN.md', root/'data/sandbox/cases/source-nonstationary-heos-resume-v5.json']
inputs.extend(sorted((root/'src/sludge_sandbox').glob('*.py')))
inputs.extend(sorted(installed.glob('*.py')))
inputs.extend(sorted(p for p in (scratch/'assets').rglob('*') if p.is_file()))
result = module.run_attempt(scratch/'supervised-native01',
    ['/usr/bin/env','-u','PYTHONPATH',str(python),'-I',str(execution/'native_driver.py')],
    cwd='/private/tmp',input_paths=inputs,timeout_s=570.,cleanup_grace_s=1.)
print(json.dumps({k:v for k,v in result.items() if not k.startswith('inputs_')},indent=2))
sys.exit(0 if result['status']=='complete' and result['returncode']==0 else 1)
