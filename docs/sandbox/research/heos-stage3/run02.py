from pathlib import Path
import sys,json
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
case=Path('/private/tmp/brick-heos-stage3')
sys.path.insert(0,str(root/'docs/sandbox/research/research-process-supervisor'))
from supervisor import run_attempt
inputs=list((root/'src/sludge_sandbox').glob('*.py'))+list((root/'data/sandbox/water').glob('*'))+[case/x for x in ('heos_candidate.py','child02.py','expected.json','PLAN.md','run02.py')]
inputs=[x for x in inputs if x.is_file()]
s=run_attempt(case/'attempt02',['/usr/bin/env',f'PYTHONPATH={case}:{root}/src','PYTHONDONTWRITEBYTECODE=1','COOLPROP_ENABLE_SUPERANCILLARIES=false','/private/tmp/brick-water-backend-probe/venv/bin/python',str(case/'child02.py')],cwd='/private/tmp',input_paths=inputs,timeout_s=30,cleanup_grace_s=.1)
print(json.dumps({k:v for k,v in s.items() if k!='inputs_after'},indent=2))
