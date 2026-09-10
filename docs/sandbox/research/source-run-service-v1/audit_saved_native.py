"""Independent stdlib audit of saved service events; no record decoder or EOS."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

ROOT = Path('/Users/wanggaoying/Desktop/brickmodel-github')
BASE = Path('/private/tmp/brick-source-run-service-v1')
OUT = BASE / 'code-review'
RUN = BASE / 'native-job01/run'
checks = 0
begin = time.monotonic()
def require(ok, reason):
    global checks
    checks += 1
    if not ok:
        raise AssertionError(reason)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_bytes())
def node(graph, value):
    return graph['nodes'][value['ref']]
def fields(graph, value):
    return node(graph, value)['fields']
def top(event):
    graph = event['payload']
    return graph, fields(graph, graph['root'])
def small(graph, value):
    if not isinstance(value, dict) or 'ref' not in value:
        return value
    item = node(graph, value)
    return [small(graph, child) for child in item['values']]
def signature(graph, value):
    memo = {}
    def visit(item):
        if isinstance(item, dict):
            if set(item) == {'ref'}:
                ident = item['ref']
                if ident not in memo:
                    memo[ident] = hashlib.sha256(json.dumps(visit(graph['nodes'][ident]),
                        sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                return {'subgraph_sha256': memo[ident]}
            return {key: visit(child) for key, child in item.items()}
        if isinstance(item, list):
            return [visit(child) for child in item]
        return item
    return visit(value)

job, result, manifest = (read(BASE / 'native-job01/job.json'), read(RUN / 'result.json'), read(RUN / 'manifest.json'))
freeze = read(OUT / 'CODE_REVIEW_FINAL.json')
for name, digest in freeze['files_sha256'].items():
    require(sha(ROOT / name) == digest, 'review_freeze:' + name)
require(job['status'] == 'completed' and job['returncode'] == 0 and job['child_reaped'] is True, 'job terminal')
require(job['hard_killed'] is False and job['termination_cause'] is None, 'no termination')
require(result['status'] == result['execution_status'] == 'completed', 'result terminal')
require(result['runtime_before'] == result['runtime_after'], 'runtime stable')
require(job['result_verification']['result_sha256'] == sha(RUN / 'result.json'), 'job result binding')
actual = {p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file() and p != RUN / 'manifest.json'}
require(actual == set(manifest['files']), 'complete file inventory')
for name, digest in manifest['files'].items():
    path = RUN / name
    require(path.resolve().is_relative_to(RUN.resolve()) and not path.is_symlink(), 'contained file:' + name)
    require(sha(path) == digest, 'manifest hash:' + name)
case = read(RUN / 'case.json')
require(result['case_sha256'] == sha(RUN / 'case.json') == freeze['files_sha256']['data/sandbox/cases/source-multicell-heos-v1.json'], 'fixed case')
asset_names = {'assets/' + item['path'] for item in case['assets']}
require(len(asset_names) == 17 and asset_names == {name for name in actual if name.startswith('assets/')}, 'exact private asset inventory')
for item in case['assets']:
    path = RUN / 'assets' / item['path']
    require(path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], 'private asset binding')
modules = result['runtime_before']['modules']
require(len(modules) == 143, 'module count')
for name, digest in modules.items():
    require(manifest['files']['implementation/' + name] == digest, 'frozen implementation:' + name)
installed = read(BASE / 'installed-identity01.json')
require(installed['status'] == 'matched' and installed['module_count'] == 143 and installed['package_file_count'] == 150, 'installed identity report')
for item in installed['files']:
    require(sha(Path(installed['installed']) / item['path']) == item['sha256'] == sha(Path(installed['source']) / item['path']), 'installed bytes:' + item['path'])
suites = ET.parse(BASE / 'installed-tests01.xml').getroot().findall('testsuite')
require(len(suites) == 1 and suites[0].get('tests') == '286' and all(suites[0].get(k) == '0' for k in ('errors', 'failures', 'skipped')), 'installed tests')

events = [read(path) for path in sorted((RUN / 'events').glob('*.json'))]
require(len(events) == result['journal_events'] == 111, '111 events')
require(sum(path.stat().st_size for path in (RUN / 'events').glob('*.json')) == result['journal_bytes'] == 9742925, 'journal bytes')
require([event['ordinal'] for event in events] == list(range(1, 112)), 'event ordering')
counts = Counter(event['event'] for event in events)
for name, count in result['counts'].items():
    require(counts[name] == count, 'event counter:' + name)
require(result['counts'] == dict(heos_started=4, heos_kernel_returned=4, heos_returned=4,
    initial_energy_started=3, initial_energy_returned=3, rhs_started=32, rhs_returned=32, wet_started=8, wet_returned=8), 'actual call totals')
require(not any(name.endswith('_failed') or name == 'request_blocked' for name in counts), 'no failed actual callbacks')
require(counts['candidate_returned'] == 2 and counts['transition_returned'] == 1, 'returned candidates')
pending = {}
modes, initial_cells, stages, material_flags = Counter(), [], [], 0
for event in events:
    typ = event['event']
    graph, value = top(event)
    for item in graph['nodes'].values():
        if 'material_qualified' in item.get('fields', {}):
            require(item['fields']['material_qualified'] is False, 'raw material flag remains false')
            material_flags += 1
    if typ == 'initial_energy_started':
        initial_cells.append(value['cell_index'])
    if typ == 'stage_returned':
        stages.append(value['stage'])
    if typ in ('rhs_started', 'wet_started'):
        family = typ.split('_')[0]
        require(family not in pending, 'no overlapped unreturned request')
        keys = ('adapter', 'state', 'time', 'phase') if family == 'rhs' else ('storage', 'request', 'phase')
        pending[family] = {key: signature(graph, value[key]) for key in keys}
    elif typ in ('rhs_returned', 'wet_returned'):
        family = typ.split('_')[0]
        require(family in pending, 'return has original start')
        require(all(signature(graph, value[key]) == saved for key, saved in pending.pop(family).items()), 'original request-return association')
        if family == 'rhs':
            state = fields(graph, value['state'])
            require(node(graph, state['amounts_mol'])['shape'] == [3, 4] and node(graph, state['internal_energy_j'])['shape'] == [3], 'N3 state shape')
            adapter = node(graph, value['adapter'])
            mode = tuple(small(graph, adapter['modes']))
            modes[mode] += 1
            evaluation = fields(graph, value['evaluation'])
            require(signature(graph, evaluation['operator_identity']) == signature(graph, adapter['identity']), 'returned operator binding')
            require(signature(graph, evaluation['time']) == signature(graph, value['time']), 'exact return time')
            source = fields(graph, evaluation['source_evaluation'])
            require(len(node(graph, source['cells'])['values']) == 3, 'three actual cell observations')
        else:
            request = small(graph, value['request'])
            water = fields(graph, value['state'])
            require([water['temperature_k'], water['pressure_pa'], water['phase']] == request, 'wet WaterState request binding')
    elif typ == 'heos_returned':
        water = node(graph, value['water'])
        require(water['type'] == 'sludge_sandbox.water_heos.HEOSWaterProperties' and not water['uninitialized_fields'], 'complete HEOS wrapper')
        implementation = fields(graph, water['fields']['implementation'])
        descriptor = json.loads(implementation['canonical_descriptor'])
        require(descriptor['wrapper_sha256'] == modules['water_heos.py'], 'observed HEOS implementation')
require(not pending, 'all source/wet requests returned')
require(initial_cells == [0, 1, 2], 'three initialization cells')
require(stages == ['seed', 'proposal', 'approach', 'refinement'], 'ordered returned stages')
require(set(modes) == {('existing_liquid',) * 3, ('existing_liquid', 'depleted_no_nucleation', 'existing_liquid')}, 'actual wet and mixed dry modes')
graph, value = top(events[-1])
transition = fields(graph, value['result'])
gates = {key: small(graph, transition[key]) for key in ('endpoint_gates', 'conditional_pressure_gates', 'selected_pressure_gates', 'cell_conditional_pressure_gates', 'cell_selected_pressure_gates')}
require(gates['endpoint_gates'] == [[True, True, True, False]] * 2, 'original NUT/P gates preserved')
require(gates['conditional_pressure_gates'] == [False, False] and gates['cell_conditional_pressure_gates'] == [[False] * 3] * 2, 'old conditional P failures retained')
require(gates['cell_selected_pressure_gates'] == [[True] * 3] * 2, 'joint selected gates')
require(transition['numerical_event_accepted'] is True and transition['material_qualified'] is False and result['transition_status'] == transition['status'] == 'conditional_numerical_event_accepted', 'conditional numerical event only')
require(all(result[key] is False for key in ('material_qualified', 'training_eligible', 'resume_authorized', 'full_firing_cycle')), 'result scope flags')

acceptance = read(BASE / 'NATIVE_ACCEPTANCE01.json')
inspection = acceptance['inspection']
require(acceptance['status'] == 'verified' and acceptance['forbidden_physical_attempts'] == [], 'saved passive acceptance')
require(acceptance['record_sha256'] == result['source_record']['sha256'] == sha(RUN / 'source-study-record.json'), 'passive record binding')
require(inspection['capture_count'] == inspection['complete_observation_count'] == 32 and not inspection['failed_capture_indices'] and not inspection['unreturned_capture_indices'], 'complete formal observations')
require(inspection['audit']['checks']['complete_transition_balance_rows'] == 7 and inspection['audit']['checks']['completed_reference_replays'] == 3, 'saved original passive audit scope')
require(inspection['source_assets_verified'] is False and inspection['resume_authorized'] is False and inspection['physical_run_reexecuted'] is False, 'passive codec boundaries')
report = dict(status='verified', checks=checks, elapsed_seconds=time.monotonic()-begin,
    reviewer_EOS_calls=0, formal_record_redecoded_by_reviewer=False,
    job_status=job['status'], job_elapsed_seconds=job['elapsed_wall_seconds'], run_elapsed_seconds=result['elapsed_wall_seconds'],
    passive_checker_elapsed_seconds=acceptance['passive_elapsed_wall_seconds'], installed_test_xml_seconds=float(suites[0].get('time')),
    counts=result['counts'], event_kinds=dict(counts), journal_events=111, journal_bytes=9742925,
    rhs_modes=[{'modes':list(mode),'count':count} for mode,count in modes.items()], raw_material_flags_checked=material_flags,
    original_and_selected_gates=gates, conditional_numerical_event_accepted=True, material_qualified=False,
    original_case_sha256=result['case_sha256'], record_sha256=result['source_record']['sha256'],
    source_and_test_freeze_count=len(freeze['files_sha256']), private_assets=17,
    source_module_count=143, installed_package_files=150,
    input_artifact_sha256={name:sha(BASE/name) for name in ('native-job01/job.json','native-job01/run/result.json','native-job01/run/manifest.json','NATIVE_ACCEPTANCE01.json','installed-identity01.json','installed-tests01.xml')},
    scientific_limits=inspection['audit']['not_verified'])
(OUT / 'NATIVE_SAVED_AUDIT.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
