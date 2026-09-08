import os,subprocess,pathlib,json,hashlib,time
root=pathlib.Path('/Users/wanggaoying/Desktop/brickmodel-github'); out=pathlib.Path('/private/tmp/brick-free-slab-phase-v1')
paths=sorted(list((root/'src/sludge_sandbox').glob('*.py'))+list((root/'tests/sandbox').glob('*.py')))
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(out/'source-before.json').write_text(json.dumps(hashes,indent=2)+'\n')
(out/'PLAN.md').write_text('Real water source-gated opposite liquid/vapor directions in 2 cells; manufactured fixed-solid skeleton and zero mass faces, nonzero shared heat. Horizon 1e-4 s, caps 1e-4/5e-5 s. Original fixed-phase gates retained: per-cell water absolute 1e-11 mol, global E+pe deltaV every prefix 4e-6 J; coarse/fine amounts 1e-11 mol, E 2e-6 J, stretches 2e-7, T 2e-6 K. Integration original tolerances 1e-7 rel, N1e-11 mol, E1e-6 J, stretch1e-9. 60 s each integration based measured fixed-phase 13/25 s; outer 170 s for initial/final decode and instantaneous test. No external material validation claimed.\n')
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'src'),BRICK_FREE_SLAB_PHASE_ARTIFACT=str(out/'trajectory.json'))
cmd=['/private/tmp/brick-water-backend-probe/venv/bin/python','-m','pytest','-q','-s','tests/sandbox/test_free_slab_phase_transfer.py','--junitxml='+str(out/'actual01.xml')]
t=time.monotonic()
with (out/'actual01.log').open('w') as log:
 try: result=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=170);code=result.returncode
 except subprocess.TimeoutExpired: code=124
post={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
status={'exit_code':code,'elapsed_seconds':time.monotonic()-t,'source_unchanged':hashes==post,'command':cmd}
(out/'actual01.status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status));print((out/'actual01.log').read_text()[-6000:]);raise SystemExit(code or (hashes!=post))
