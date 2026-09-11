"""Isolated exact arithmetic controls; no model imports or original data edits."""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).parent
checker = (ROOT / 'original-check_basis.py').read_bytes()
facts = json.loads((ROOT / 'original-facts.json').read_bytes())
results = []
started = time.perf_counter()
for name in ('control', 'changed_charge', 'changed_actual_moisture', 'changed_product',
             'invalid_actual_moisture', 'material_label_upgrade'):
    value = deepcopy(facts)
    if name == 'changed_charge':
        value['actual_run']['feed_mass_g'] = '35.32'
    elif name == 'changed_actual_moisture':
        value['actual_run']['initial_moisture_percent'] = '9.9'
    elif name == 'changed_product':
        value['printed_mass_percent']['gas'][1] = '8.12'
    elif name == 'invalid_actual_moisture':
        value['actual_run']['initial_moisture_percent'] = '120'
    elif name == 'material_label_upgrade':
        value['material_qualified'] = True
    case = ROOT / name
    case.mkdir(exist_ok=False)
    (case / 'check_basis.py').write_bytes(checker)
    (case / 'facts.json').write_text(json.dumps(value, indent=2)+'\n')
    run = subprocess.run([sys.executable, str(case / 'check_basis.py')], capture_output=True,
                         text=True, timeout=10, check=False)
    (case / 'stdout.txt').write_text(run.stdout)
    (case / 'stderr.txt').write_text(run.stderr)
    result = {'case': name, 'exit_code': run.returncode}
    if run.returncode == 0:
        output = json.loads(run.stdout)
        result.update(actual_dry_mass=output['actual_run_dry_mass_g_from_printed_inputs'],
            initial_water=output['actual_run_initial_water_g_from_printed_inputs'],
            output_material_qualified=output['material_qualified'])
        if name == 'control':
            assert output == json.loads(Path('docs/sandbox/research/gnest2021-retort-basis-v1/ARITHMETIC01.json').read_bytes())
            assert F(result['actual_dry_mass']) == F('34.32') * F('0.972')
        if name == 'changed_charge':
            assert F(result['actual_dry_mass']) == F('35.32') * F('0.972')
        if name == 'changed_actual_moisture':
            assert F(result['actual_dry_mass']) == F('34.32') * F('0.901')
    if name == 'changed_product':
        assert run.returncode != 0
    results.append(result)
report = {'source_sha256': hashlib.sha256(checker).hexdigest(), 'elapsed_seconds':time.perf_counter()-started,
          'cases':results, 'eos_calls':0}
(ROOT/'PROBE_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
