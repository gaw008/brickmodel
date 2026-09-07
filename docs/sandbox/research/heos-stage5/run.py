from pathlib import Path
import json,sys
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage5')
sys.path.insert(0,str(repo/'docs/sandbox/research/research-process-supervisor'))
from supervisor import run_attempt
inputs=list((case/'sludge_sandbox').glob('*.py'))+list((repo/'data/sandbox/water').glob('*'))+[case/'PLAN.md',case/'expected.json',case/'smoke.py',case/'run.py',repo/'docs/sandbox/research/water-python-seam/bound-old.json']
s=run_attempt(case/'smoke-attempt01',['/usr/bin/env',f'PYTHONPATH={case}','PYTHONDONTWRITEBYTECODE=1','/private/tmp/brick-water-backend-probe/venv/bin/python',str(case/'smoke.py')],cwd='/private/tmp',input_paths=[p for p in inputs if p.is_file()],timeout_s=30,cleanup_grace_s=.1)
print(json.dumps({k:v for k,v in s.items() if k!='inputs_after'},indent=2))
