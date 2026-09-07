from pathlib import Path
import sys,json
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage4')
sys.path.insert(0,str(repo/'docs/sandbox/research/research-process-supervisor'))
from supervisor import run_attempt
inputs=list((repo/'src/sludge_sandbox').glob('*.py'))+list((repo/'data/sandbox/water').glob('*'))+list(case.glob('*.py'))+[case/'PLAN.md',case/'expected.json']
s=run_attempt(case/'grid-attempt01',['/usr/bin/env',f'PYTHONPATH={case}:{repo}/src','PYTHONDONTWRITEBYTECODE=1','/private/tmp/brick-water-backend-probe/venv/bin/python',str(case/'grid.py')],cwd='/private/tmp',input_paths=[p for p in inputs if p.is_file()],timeout_s=30,cleanup_grace_s=.1)
print(json.dumps({k:v for k,v in s.items() if k!='inputs_after'},indent=2))
