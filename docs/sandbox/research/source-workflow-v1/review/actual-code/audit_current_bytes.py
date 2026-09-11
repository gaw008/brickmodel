"""Read-only source/config manifest review. Standard library; zero EOS."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
OUT = Path(__file__).parent
checks = []
def require(ok, name):
    assert ok, name
    checks.append(name)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
files = [
    'src/sludge_sandbox/source_workflow_worker.py',
    'src/sludge_sandbox/source_run_service.py',
    'src/sludge_sandbox/source_trajectory.py',
    'src/sludge_sandbox/_heos_rhs_scope.py',
    'src/sludge_sandbox/heos_runtime_registry.py',
    'src/sludge_sandbox/source_run_config.py',
    'src/sludge_sandbox/water_heos.py',
    'tests/sandbox/test_source_managed_lifecycle.py',
    'tests/sandbox/test_source_workflow_worker.py',
    'tests/sandbox/test_source_rhs_runtime_selection.py',
    'data/sandbox/cases/source-nonstationary-heos-workflow-v4.json',
    'data/sandbox/water/heos-8.0.0-workflow-v3-manifest.json',
    'docs/sandbox/research/source-workflow-v1/NATIVE_PLAN.md',
]
hashes = {name: sha((ROOT/name).read_bytes()) for name in files}
for name in files:
    if name.endswith('.py'):
        ast.parse((ROOT/name).read_bytes())
        checks.append('AST:' + name)
expected = {
    'src/sludge_sandbox/source_run_service.py': '3d73ba98ee8582aaa95a2c03e7beab4b80121ad246ffbc3d9a263d0adadfc093',
    'src/sludge_sandbox/source_trajectory.py': 'd4b86d0f902e14ce26265fc8bafb13af40b60f5c7bc5e8a7aab5e7af85d423be',
    'tests/sandbox/test_source_managed_lifecycle.py': '755d2b8dd6249d74480e2c5586aaac04f5c78da652bf47ece3ac93a635792bd3',
}
for name, value in expected.items():
    require(hashes[name] == value, 'author frozen bytes:' + name)
manifest = json.loads((ROOT/files[11]).read_bytes())
old_manifest = json.loads((ROOT/'data/sandbox/water/heos-8.0.0-rhs-v2-manifest.json').read_bytes())
for name, digest in manifest['execution_sources'].items():
    require(sha((ROOT/'src/sludge_sandbox'/name).read_bytes()) == digest, 'execution source:' + name)
require(manifest['adapter_sha256'] == sha((ROOT/'src/sludge_sandbox/_heos_kernel.py').read_bytes()), 'kernel binding')
for key in ('execution_sources', 'execution_contract'):
    manifest.pop(key)
    old_manifest.pop(key)
require(canonical(manifest) == canonical(old_manifest), 'all native metadata/constants unchanged')
for node in ast.parse((ROOT/'src/sludge_sandbox/heos_runtime_registry.py').read_bytes()).body:
    if isinstance(node, ast.Assign) and node.targets[0].id == 'WORKFLOW_MANIFEST_ASSET':
        path, size, digest = ast.literal_eval(node.value)
        raw = (ROOT/path).read_bytes()
        require((len(raw), sha(raw)) == (size, digest), 'registry exact bytes')
        break
else:
    raise AssertionError('registry missing')
new = json.loads((ROOT/files[10]).read_bytes())
old = json.loads((ROOT/'data/sandbox/cases/source-nonstationary-heos-v2.json').read_bytes())
require([i for i, (a,b) in enumerate(zip(old['assets'], new['assets'])) if canonical(a) != canonical(b)] == [10]
        and len(old['assets']) == len(new['assets']) == 17, 'single changed asset row')
require(new['assets'][10] == {'path': path, 'bytes': size, 'sha256': digest}, 'case new registry row')
new['assets'], new['profile'] = old['assets'], old['profile']
require(canonical(new) == canonical(old), 'all physical values gates and resources unchanged')
for name in ('src/sludge_sandbox/_heos_kernel.py', 'src/sludge_sandbox/_heos_kernel_v1.py',
             'data/sandbox/water/heos-8.0.0-approved-manifest.json',
             'data/sandbox/water/heos-8.0.0-rhs-v2-manifest.json',
             'data/sandbox/cases/source-nonstationary-heos-v2.json'):
    old = subprocess.check_output(['git', 'show', '9544ec9:' + name], cwd=ROOT)
    require((ROOT/name).read_bytes() == old, 'historical baseline preserved:' + name)
prior = json.loads((ROOT/'data/sandbox/water/heos-8.0.0-rhs-v2-manifest.json').read_bytes())
for name, digest in prior['execution_sources'].items():
    raw = (ROOT/'docs/sandbox/research/source-workflow-v1/historical-v2'/name).read_bytes()
    require(sha(raw) == digest and raw == subprocess.check_output(['git','show','9544ec9:src/sludge_sandbox/' + name], cwd=ROOT),
            'prior execution archive:' + name)
scratch = Path('/private/tmp/brick-source-workflow-v1/root')
for name in ('run_supervised_native01.py', 'request-native01.json'):
    hashes[str(scratch/name)] = sha((scratch/name).read_bytes())
ast.parse((scratch/'run_supervised_native01.py').read_bytes())
checks.append('supervisor launcher AST')
result = dict(status='passed', checks=checks, check_count=len(checks), hashes=hashes,
              scope='source/config/manifest static identity; not installed/native validation',
              eos_calls=0)
(OUT/'CURRENT_BYTES.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'check_count': len(checks), 'eos_calls': 0}))
