from pathlib import Path
import subprocess,os,json,time,sys
root=Path('/Users/wanggaoying/Desktop/brickmodel-github');out=Path('/private/tmp/brick-free-slab-rates-v1')
names=['free_slab_rates','current_solid_storage','free_solid_slab','free_solid_slab_trajectory','dynamic_solid_storage','free_skeleton_rates','component_work_ledger','depletion_components','mechanical_integration','mechanical_checkpoint','free_solid_cell','mechanical_depletion','depletion_common_endpoint','mechanical_host_guards']
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None)
cmd=[sys.executable,'-m','pytest',*[str(root/'tests/sandbox'/('test_'+n+'.py')) for n in names],'-q','-s','--junitxml='+str(out/'installed-tests.xml')]
start=time.monotonic()
with (out/'installed-tests.log').open('w') as log:
 try:code=subprocess.run(cmd,cwd='/private/tmp',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=80).returncode
 except subprocess.TimeoutExpired:code=124
(out/'installed-tests-status.json').write_text(json.dumps(dict(command=cmd,exit_code=code,elapsed_s=time.monotonic()-start,cwd='/private/tmp',PYTHONPATH=None),indent=2)+'\n')
print((out/'installed-tests.log').read_text());raise SystemExit(code)
