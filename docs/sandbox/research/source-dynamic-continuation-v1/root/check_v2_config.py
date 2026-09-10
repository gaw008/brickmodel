"""Passive installed schema check for the separately registered numeric profile."""
from pathlib import Path
import hashlib
import json
import time

from sludge_sandbox.source_run_config import load_source_run_config

root = Path('/Users/wanggaoying/Desktop/brickmodel-github')
stage = root/'docs/sandbox/research/source-dynamic-continuation-v1'
p1 = root/'data/sandbox/cases/source-nonstationary-heos-v1.json'
p2 = root/'data/sandbox/cases/source-nonstationary-heos-v2.json'
a, b = load_source_run_config(p1.read_bytes()), load_source_run_config(p2.read_bytes())
expected = json.loads(p1.read_bytes())
expected['pressure_policy']['pressure_tolerance_pa'] = 1e-7
expected['inverse_policy']['energy_tolerance_j'] = 1e-6
assert json.loads(p2.read_bytes()) == expected
# Config values freeze JSON arrays as tuples; compare the same representation.
assert b.values == load_source_run_config(json.dumps(expected).encode()).values
assert a.values['classification'] == b.values['classification'] == 'manufactured_test_fixture'
assert a.values['event_policy'] == b.values['event_policy']
assert a.values['resources'] == b.values['resources']
files = [p1, p2, stage/'run_native.py', stage/'run_native_v2.py', stage/'NATIVE_PLAN_V2.md']
record = dict(status='passed', time_unix_s=time.time(), eos_calls=0, source_study_decodes=0,
              changed_fields_only=['pressure_policy.pressure_tolerance_pa', 'inverse_policy.energy_tolerance_j'],
              physical_case_unchanged=True, event_gates_unchanged=True, resources_unchanged=True,
              files={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(stage/'V2_CONFIG_CHECK.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record, indent=2))
