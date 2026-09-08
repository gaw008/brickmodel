from pathlib import Path
import subprocess,os,json,time,sys,hashlib
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
out=Path('/private/tmp/brick-free-mechanical-depletion-v1')
files=sorted(list((root/'src/sludge_sandbox').glob('*.py'))+list((root/'tests/sandbox').glob('*.py')))
before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'src'),BRICK_FREE_DEPLETION_ARTIFACT=str(out/'attempt03.json'))
cmd=[sys.executable,'-m','pytest','tests/sandbox/test_free_mechanical_depletion.py','-q','-s','--junitxml='+str(out/'attempt03.xml')]
start=time.monotonic()
with (out/'attempt03.log').open('w') as log:
    try:
        run=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=210)
        code=run.returncode
    except subprocess.TimeoutExpired:
        code=124
same=all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in before.items())
(out/'attempt03-status.json').write_text(json.dumps(dict(command=cmd,exit_code=code,elapsed_s=time.monotonic()-start,source_unchanged=same,source_hashes=before),indent=2)+'\n')
print((out/'attempt03.log').read_text())
raise SystemExit(code if code else (0 if same else 2))
