import os,pathlib,subprocess,time,json
root=pathlib.Path('/Users/wanggaoying/Desktop/brickmodel-github');out=pathlib.Path('/private/tmp/brick-free-slab-phase-v1')
names=['test_free_slab_phase_transfer','test_free_slab_gas_transport','test_free_water_phase_transfer','test_free_solid_slab','test_free_slab_rates','test_current_solid_storage','test_mechanical_integration','test_mechanical_checkpoint','test_mechanical_depletion','test_mechanical_host_guards']
cmd=['/private/tmp/brick-water-backend-probe/venv/bin/python','-m','pytest','-q','-s']+[str(root/'tests/sandbox'/f'{n}.py') for n in names]+['--junitxml='+str(out/'installed.xml')]
env=os.environ.copy();env.pop('PYTHONPATH',None);env.update(PYTHONDONTWRITEBYTECODE='1',BRICK_FREE_SLAB_PHASE_ARTIFACT=str(out/'installed-trajectory.json'))
t=time.monotonic()
with (out/'installed.log').open('w') as f:
 try:r=subprocess.run(cmd,cwd='/private/tmp',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=150);code=r.returncode
 except subprocess.TimeoutExpired:code=124
status={'exit_code':code,'elapsed_seconds':time.monotonic()-t,'command':cmd}
(out/'installed.status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status));print((out/'installed.log').read_text()[-4000:]);raise SystemExit(code)
