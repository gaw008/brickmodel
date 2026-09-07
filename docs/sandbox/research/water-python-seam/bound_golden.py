"""Execute golden with stdin, validating the actual source tree before evaluation."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
case=Path('/private/tmp/brick-water-python-seam')
script=(case/'golden.py').read_text()
results=[]
for label,tree in [('old',case/'baseline-package'),('new',root/'src')]:
    expected=(tree/'sludge_sandbox/water_properties.py').resolve()
    check=f'''import sludge_sandbox.water_properties as module\nfrom pathlib import Path\nimport hashlib, json, sys\nactual=Path(module.__file__).resolve()\nassert actual==Path({str(expected)!r}), (actual, {str(expected)!r})\nprint(json.dumps({{"module_path":str(actual),"sha256":hashlib.sha256(actual.read_bytes()).hexdigest()}}), file=sys.stderr)\n'''
    env={**os.environ,'PYTHONPATH':str(tree),'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run([str(root/'.venv/bin/python'),'-'],input=check+script,cwd='/private/tmp',env=env,text=True,capture_output=True,timeout=15)
    (case/f'bound-{label}.json').write_text(result.stdout)
    (case/f'bound-{label}.stderr').write_text(result.stderr)
    assert result.returncode==0, result.stderr
    results.append(json.loads(result.stdout))
assert results[0]==results[1] and len(results[0]['cases'])==34
assert (case/'bound-old.json').read_bytes()==(case/'bound-new.json').read_bytes()
old=json.loads((case/'bound-old.stderr').read_text());new=json.loads((case/'bound-new.stderr').read_text())
assert old['sha256']!=new['sha256']
print(json.dumps({'status':'passed','cases':34,'old':old,'new':new,'output_sha256':hashlib.sha256((case/'bound-old.json').read_bytes()).hexdigest()},indent=2))
