import os,subprocess,pathlib,json,hashlib,time
root=pathlib.Path('/Users/wanggaoying/Desktop/brickmodel-github'); out=pathlib.Path('/private/tmp/brick-free-slab-depletion-v1')
paths=sorted(list((root/'src/sludge_sandbox').glob('*.py'))+list((root/'tests/sandbox').glob('*.py')))
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(out/'source-before.json').write_text(json.dumps(hashes,indent=2)+'\n')
with (out/'PLAN.md').open('a') as f:f.write('\nPre-run review addition: cumulative absolute represented sum of mechanical_constraint per step <= original 1e-6 J at every prefix; cumulative local absolute C each >1e-10 J to distinguish disabled constraint exchange, numerical detection threshold only, not material bound. Initial/final Csum within returned numerical bound. Final snapshot saved before new assertions.\n')
env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'src'),BRICK_FREE_SLAB_DEPLETION_ARTIFACT=str(out/'attempt01.json'))
cmd=['/private/tmp/brick-water-backend-probe/venv/bin/python','-m','pytest','-q','-s','tests/sandbox/test_free_slab_depletion.py','--junitxml='+str(out/'attempt01.xml')]
t=time.monotonic()
with (out/'attempt01.log').open('w') as log:
 try: result=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=660);code=result.returncode
 except subprocess.TimeoutExpired: code=124
post={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
status={'exit_code':code,'elapsed_seconds':time.monotonic()-t,'source_unchanged':hashes==post,'command':cmd}
(out/'attempt01.status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status));print((out/'attempt01.log').read_text()[-6000:]);raise SystemExit(code or (hashes!=post))
