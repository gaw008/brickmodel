from pathlib import Path
import subprocess,os,json,time,sys
root=Path('/Users/wanggaoying/Desktop/brickmodel-github');out=Path('/private/tmp/brick-free-mechanical-depletion-v1')
names=['mechanical_depletion','mechanical_integration','mechanical_checkpoint','mechanical_host_guards','depletion_integration','depletion_components','depletion_spine','depletion_spine_source_guards','depletion_multicell','depletion_safe_fraction','affine_depletion_integration','affine_depletion_guards','depletion_program_knots','depletion_dry_continuity','depletion_common_endpoint']
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');env.pop('PYTHONPATH',None)
cmd=[sys.executable,'-m','pytest',*[str(root/'tests/sandbox'/('test_'+n+'.py')) for n in names],'-q','--junitxml='+str(out/'installed-tests.xml')]
start=time.monotonic()
with (out/'installed-tests.log').open('w') as log:
 try:code=subprocess.run(cmd,cwd='/private/tmp',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=100).returncode
 except subprocess.TimeoutExpired:code=124
(out/'installed-tests-status.json').write_text(json.dumps(dict(command=cmd,exit_code=code,elapsed_s=time.monotonic()-start,cwd='/private/tmp',PYTHONPATH=None),indent=2)+'\n')
print((out/'installed-tests.log').read_text());raise SystemExit(code)
