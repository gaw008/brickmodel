"""Passive independent comparison of saved cross-process source outputs.

Only standard-library data readers; no model imports, reconstruction or EOS.
"""
from collections import Counter
from fractions import Fraction as F
import json
import math
from pathlib import Path
import struct

checks = []
def require(ok, label):
    if not ok:
        raise AssertionError(label)
    checks.append(label)

class Node:
    def __init__(self, kind, values):
        self._kind, self._fields = kind, values
    def __getattr__(self, name):
        return self._fields[name]


def decode_graph(graph):
    require(graph['schema'] == 'source_run_raw_projection_v1', 'raw graph schema')
    cache, visiting = {}, set()
    def visit(value):
        if not isinstance(value, dict):
            return value
        if set(value) == {'binary64'}:
            result = float.fromhex(value['binary64'])
            require(math.isfinite(result), 'finite saved float')
            return result
        if set(value) == {'fraction'}:
            n,d = value['fraction']
            require(type(n) is int and type(d) is int and d > 0 and math.gcd(n,d)==1, 'canonical saved fraction')
            return F(n,d)
        require(set(value) == {'ref'}, 'closed raw reference')
        key = value['ref']
        if key in cache:
            return cache[key]
        require(key not in visiting, 'acyclic requested raw data')
        visiting.add(key)
        item = graph['nodes'][key]
        kind = item['type']
        if kind in ('builtins.tuple', 'builtins.list'):
            result = tuple(visit(x) for x in item['values'])
        elif kind in ('builtins.dict', 'builtins.mappingproxy'):
            result = {k:visit(v) for k,v in item['fields'].items()}
        else:
            values = {k:visit(v) for k,v in item.get('fields',{}).items()}
            if 'values' in item:
                values.update(values=tuple(visit(v) for v in item['values']))
            for k,v in item.items():
                if k not in ('type','fields','values'):
                    # Only array shape/dtype, empty-field metadata and passive
                    # live-reference identity/modes are present in requested nodes.
                    values[k] = visit(v) if isinstance(v,dict) else v
            result = Node(kind, values)
        visiting.remove(key)
        cache[key] = result
        return result
    return visit(graph['root'])


def signature(value, *, skip_elapsed=False):
    """Type-sensitive full field projection; no wildcard numeric/identity skip."""
    if isinstance(value, Node):
        fields = value._fields
        if skip_elapsed and value._kind == 'sludge_sandbox.exact_integration.ExactIntegrationResult':
            fields = {k:v for k,v in fields.items() if k != 'elapsed_seconds'}
        return ('node', value._kind, tuple((k,signature(v,skip_elapsed=skip_elapsed)) for k,v in sorted(fields.items())))
    if isinstance(value, dict):
        return ('dict', tuple((k,signature(v,skip_elapsed=skip_elapsed)) for k,v in sorted(value.items())))
    if isinstance(value, (list,tuple)):
        return (type(value).__name__, tuple(signature(v,skip_elapsed=skip_elapsed) for v in value))
    if type(value) is float:
        return ('float',value.hex())
    if type(value) is F:
        return ('fraction',value.numerator,value.denominator)
    return (type(value).__name__,value)


def checkpoint_wire(value):
    """Project the logged checkpoint to its fixed data format, without a codec."""
    if isinstance(value, Node):
        if value._kind=='numpy.ndarray':
            return {'array':{'dtype':'<f8','shape':value.shape,
                'data_hex':b''.join(struct.pack('<d',v) for v in value.values).hex()}}
        name=value._kind.rsplit('.',1)[-1]
        require(name in {'ExactEventTime','ConservedState','Rates','IntegrationPolicy',
            'ExactStepLedger','ExactIntegrationResult','ExactCallbackObservation',
            'ExactIntegrationProblem','ExactIntegrationCheckpoint'},'checkpoint fixed record class')
        require(value._fields.get('uninitialized_fields')==[],'checkpoint complete logged fields')
        return {'record':name,'fields':{k:checkpoint_wire(v) for k,v in value._fields.items()
                                     if k!='uninitialized_fields'}}
    if type(value) is float:
        return {'float_hex':value.hex()}
    if type(value) is F:
        return {'fraction':[value.numerator,value.denominator]}
    if type(value) is tuple:
        return {'tuple':[checkpoint_wire(v) for v in value]}
    if type(value) is dict:
        return {'mapping':[[k,checkpoint_wire(v)] for k,v in value.items()]}
    return value


def load_events(directory):
    paths = sorted((directory / 'events').glob('*.json'))
    events = [json.loads(p.read_bytes()) for p in paths]
    require(events and [x['ordinal'] for x in events] == list(range(1, len(events)+1)), 'contiguous journal')
    return events


def verify(directory):
    checks.clear()
    parent_dir = directory / 'parent/run'
    continuous_dir = directory / 'continuous/trajectory'
    paused_dir = directory / 'paused/trajectory'
    resumed_dir = directory / 'resumed/trajectory'
    parent, continuous, paused, resumed = map(load_events, (parent_dir, continuous_dir, paused_dir, resumed_dir))
    old_files = sorted((paused_dir / 'events').glob('*.json'))
    require(all(p.read_bytes() == (resumed_dir / 'events' / p.name).read_bytes() for p in old_files),
            'saved prefix journal original bytes')
    extract = lambda events, name: [decode_graph(e['payload']) for e in events if e['event'] == name]
    baseline = extract(continuous, 'ordinary_segment_returned')[-1]
    prefix = extract(paused, 'ordinary_segment_returned')[-1]
    finished = extract(resumed, 'ordinary_segment_returned')[-1]
    require(baseline.status == finished.status == 'completed' and prefix.status == 'paused', 'actual statuses')
    require(signature(baseline.execution.result, skip_elapsed=True) ==
            signature(finished.execution.result, skip_elapsed=True), 'full numerical results except elapsed')
    require(signature(baseline.execution.observations) == signature(finished.execution.observations),
            'all original controller observations')
    require(signature(baseline.balances) == signature(finished.balances), 'all cumulative balance rows')
    require(signature(prefix.execution.result.steps) == signature(finished.execution.result.steps[:1]),
            'original first step preserved')
    require(signature(prefix.execution.observations) == signature(finished.execution.observations[:8]),
            'original eight observations preserved')
    rhs = extract(resumed, 'rhs_returned')
    continuous_rhs = extract(continuous, 'rhs_returned')
    require(signature(tuple(x['evaluation'] for x in rhs)) ==
            signature(tuple(x['evaluation'] for x in continuous_rhs)), 'all actual source returns')
    numerical = finished.execution.result
    require(len(numerical.steps) == 3 and numerical.evaluations == 22 and numerical.rejected_trials == 0,
            'original three-step gate')
    require(len(prefix.execution.result.steps) == 1 and len(rhs) == 22, 'pause then fourteen new callbacks')
    require(numerical.times_s[-1].seconds - numerical.times_s[0].seconds == F(3,64), 'original duration')
    require(all(b.seconds-a.seconds == F(1,64) for a,b in zip(numerical.times_s,numerical.times_s[1:])),
            'original step sizes')
    transition = extract(parent, 'transition_returned')[0]['result']
    require(transition.numerical_event_accepted is True and
            numerical.times_s[0].seconds == transition.candidates[1].end.seconds, 'parent original event')
    config = json.loads((parent_dir / 'case.json').read_bytes())
    u_tol = F(config['integration_policy']['energy_absolute_tolerance_j'])
    n_tol = F(config['integration_policy']['amount_absolute_tolerance_mol'])
    global_changes = []
    for old, new, step in zip(numerical.states, numerical.states[1:], numerical.steps):
        require(signature(old.amounts_mol) == signature(new.amounts_mol), 'all inventories constant')
        face, work = list(map(F, step.face_energy_j.values)), list(map(F, step.cell_work_j.values))
        require(face[0] == face[-1] == 0 and all(x == 0 for x in work), 'closed energy boundary')
        require(any(x != 0 for x in face[1:-1]), 'nonzero integrated conduction')
        for i, (a,b) in enumerate(zip(old.internal_energy_j.values, new.internal_energy_j.values)):
            require(abs(F(b)-F(a)-(face[i]-face[i+1]+work[i])) <= u_tol, 'independent per-cell step energy')
        delta = sum(map(F,new.internal_energy_j.values)) - sum(map(F,old.internal_energy_j.values))
        require(abs(delta) <= u_tol, 'independent whole-step energy')
        global_changes.append(float(delta))
    require(len(finished.balances) == 7, 'seven original full-history balance rows')
    for row in finished.balances:
        require(abs(row.full_energy_residual_j) <= u_tol and
                all(abs(v) <= n_tol for v in row.full_inventory_residual_mol), 'saved full-chain residual gates')
        for cell in row.cell_balances:
            require(abs(cell.full_energy_residual_j) <= u_tol and
                    all(abs(v) <= n_tol for v in cell.full_inventory_residual_mol), 'saved full-chain per-cell gates')
    dt, bounds = [], []
    for a,b in zip(rhs[0]['evaluation'].source_evaluation.cells, rhs[-1]['evaluation'].source_evaluation.cells):
        dt.append(F(b.inverse.point.fluid.mechanical.temperature_k)-F(a.inverse.point.fluid.mechanical.temperature_k))
        bounds.append(F(a.inverse.temperature_error_bound_k)+F(b.inverse.temperature_error_bound_k))
    require(any(abs(a)>b for a,b in zip(dt,bounds)), 'temperature change exceeds saved inverse bounds')
    counts = Counter(e['event'] for events in (parent,continuous,resumed) for e in events)
    expected = dict(rhs_started=76, rhs_returned=76, heos_started=16, heos_kernel_returned=16,
        heos_returned=16, initial_energy_started=3, initial_energy_returned=3, wet_started=8, wet_returned=8)
    require(all(counts[k] == n for k,n in expected.items()), 'actual cumulative work including reconstruction')
    for branch, events, sizes in (('parent',parent,[32]),('continuous',continuous,[22]),('resumed',resumed,[8,14])):
        leases = extract(events, 'managed_lease_closed')
        require(len(leases) == len(sizes), branch+' lease count')
        for entry, n in zip(leases,sizes):
            require(entry['status']=='closed' and entry['primary_error'] is None and not entry['secondary_errors'],
                    branch+' clean scope close')
            audit = entry['audit']
            require(audit['closed'] is True and len(audit['rhs']) == n, branch+' actual scoped requests')
            require(all(r['status']=='verified' and not r['exit_errors'] and r['primary_error'] is None
                and [c['stage'] for c in r['checks']] == ['entry']*4+['exit']*4
                and all(c['status']=='verified' for c in r['checks']) for r in audit['rhs']), branch+' scope checks')
    for result in (baseline,prefix,finished):
        require(result.material_qualified is result.full_firing_cycle is result.archived_resume_authorized is False,
                'material and historical qualification unchanged')
        require(result.execution.result.elapsed_seconds < 180 and result.cumulative_outer_seconds < 510,
                'original cumulative wall budgets')
    packet = json.loads((directory/'paused/resume-point/packet.json').read_bytes())
    cp = json.loads((directory/'paused/resume-point/ordinary-checkpoint.json').read_bytes())
    require(cp['checkpoint'] == checkpoint_wire(prefix.execution.checkpoint), 'complete original numeric checkpoint')
    require(packet['source_resume_authorized'] is True and packet['historical_study_resume_authorized'] is False,
            'separate ordinary resume permission')
    require((directory/'paused/resume-point/.restore-attempt/restored.json').is_file(), 'actual exclusive restore claim')
    return dict(status='passed', semantic_checks=len(checks), expected_actual_counts=expected,
        temperature_change_k=list(map(float,dt)), paired_inverse_temperature_bounds_k=list(map(float,bounds)),
        global_energy_changes_j=global_changes, new_rhs_after_resume=14,
        application_imports=0, new_eos_in_verifier=0, material_qualified=False, full_firing_cycle=False)

