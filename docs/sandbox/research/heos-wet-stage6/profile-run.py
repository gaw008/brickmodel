from pathlib import Path
import sys,json
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
case=Path('/private/tmp/brick-heos-wet-stage6')
sys.path.insert(0,str(root/'docs/sandbox/research/research-process-supervisor'))
from supervisor import run_attempt
inputs=list((root/'src/sludge_sandbox').glob('*.py'))+list((root/'tests/sandbox').glob('*.py'))+list((root/'data/sandbox/water').rglob('*'))+list(case.glob('*.py'))+list(case.glob('*.json'))
inputs=[p for p in inputs if p.is_file()]+[root/'docs/sandbox/research/research-process-supervisor/supervisor.py']
command=['/usr/bin/env','PYTHONDONTWRITEBYTECODE=1','PYTHONPATH='+str(root/'src')+':'+str(root/'tests/sandbox'),'/private/tmp/brick-water-backend-probe/venv/bin/python',str(case/'profile-child.py')]
r=run_attempt(case/'profile-attempt01',command,cwd=case,input_paths=inputs,timeout_s=30)
print(json.dumps({k:r[k] for k in ('status','returncode','elapsed_s','cleanup')},indent=2))
