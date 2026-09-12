"""Independent saved-evidence audit. Standard library only; no solver imports.

Three wire formats are decoded into inert local records. No archived class is
imported, instantiated or executed. Ledger arithmetic uses exact Fractions of
saved binary64 inputs; this does not regenerate EOS values or quadrature nodes.
"""
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import time

BASE = Path('/private/tmp/brick-source-resume-v1/native01')
SUPERVISOR = BASE.parent / 'supervised-native01'
OUTPUT = Path(__file__).parent
CHECKS = 0


def check(condition, label):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(label)


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class Record:
    kind: str
    fields: dict

    def __getattr__(self, name):
        return self.fields[name]


@dataclass(frozen=True)
class Array:
    shape: tuple
    values: tuple

    def __getitem__(self, index):
        if isinstance(index, tuple):
            row, column = index
            return self.values[row * self.shape[1] + column]
        return self.values[index]


class Decoder:
    def __init__(self, graph=None):
        self.nodes = {} if graph is None else graph['nodes']
        self.memo = {}
        self.active = set()

    def value(self, item):
        if not isinstance(item, (dict, list)):
            return item
        if isinstance(item, list):
            return tuple(self.value(value) for value in item)
        if set(item) == {'ref'}:
            key = item['ref']
            check(key not in self.active, 'acyclic saved graph')
            if key not in self.memo:
                self.active.add(key)
                self.memo[key] = self.value(self.nodes[key])
                self.active.remove(key)
            return self.memo[key]
        if set(item) == {'value'}:
            return self.value(item['value'])
        if set(item) in ({'binary64'}, {'float_hex'}):
            return float.fromhex(next(iter(item.values())))
        if set(item) == {'fraction'}:
            return F(*item['fraction'])
        if set(item) == {'exact_time'}:
            exact = item['exact_time']
            return Record('ExactEventTime', {'seconds': F(exact['numerator'], exact['denominator'])})
        if 'array' in item:
            array = item['array']
            if 'data_hex' in array:
                check(array['dtype'] == '<f8', 'numeric codec binary64 dtype')
                raw = bytes.fromhex(array['data_hex'])
                values = struct.unpack('<' + 'd' * (len(raw) // 8), raw)
            else:
                values = tuple(self.value(value) for value in array['values'])
            check(math.prod(array['shape']) == len(values), 'array extent')
            return Array(tuple(array['shape']), values)
        if item.get('type') == 'numpy.ndarray':
            check(item['dtype'] == 'float64', 'raw binary64 dtype')
            values = tuple(self.value(value) for value in item['values'])
            check(math.prod(item['shape']) == len(values), 'raw array extent')
            return Array(tuple(item['shape']), values)
        if set(item) == {'tuple'}:
            return tuple(self.value(value) for value in item['tuple'])
        if set(item) == {'mapping'}:
            return {key: self.value(value) for key, value in item['mapping'].items()}
        if item.get('type') in ('builtins.tuple', 'builtins.list'):
            return tuple(self.value(value) for value in item['values'])
        if item.get('type') == 'builtins.dict' or item.get('type', '').rsplit('.', 1)[-1] == 'mappingproxy':
            return {key: self.value(value) for key, value in item['fields'].items()}
        if 'fields' in item and any(key in item for key in ('type', 'class', 'record')):
            label = item.get('type', item.get('class', item.get('record')))
            return Record(label.rsplit('.', 1)[-1],
                          {key: self.value(value) for key, value in item['fields'].items()})
        return {key: self.value(value) for key, value in item.items()}


def graph_value(graph):
    return Decoder(graph).value(graph['root'])


def equal(left, right, *, ignore_elapsed=False):
    """Exact values, including signed binary64 zero; memoized shared subgraphs."""
    visited = set()

    def compare(a, b):
        if type(a) is not type(b):
            return False
        pair = (id(a), id(b))
        if pair in visited:
            return True
        visited.add(pair)
        if isinstance(a, Record):
            if a.kind != b.kind:
                return False
            left_fields = {k: v for k, v in a.fields.items() if not (ignore_elapsed and k == 'elapsed_seconds')}
            right_fields = {k: v for k, v in b.fields.items() if not (ignore_elapsed and k == 'elapsed_seconds')}
            return compare(left_fields, right_fields)
        if isinstance(a, Array):
            return compare(a.shape, b.shape) and compare(a.values, b.values)
        if isinstance(a, dict):
            return a.keys() == b.keys() and all(compare(a[k], b[k]) for k in a)
        if isinstance(a, tuple):
            return len(a) == len(b) and all(compare(x, y) for x, y in zip(a, b))
        if isinstance(a, float):
            return a.hex() == b.hex()
        return a == b

    return compare(left, right)


def journal(directory):
    rows = []
    for ordinal, path in enumerate(sorted((directory / 'events').glob('*.json')), 1):
        row = read(path)
        check(path.name == f'{ordinal:06d}.json' and row['ordinal'] == ordinal, 'journal ordinal')
        rows.append((row['event'], graph_value(row['payload']), path))
    return rows


def named(rows, name):
    return [value for label, value, _ in rows if label == name]


def qarray(array):
    return [F(value) for value in array.values]


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def audit_counts(journals, outcomes):
    counter_names = tuple(outcomes['parent']['counts'])
    unique = dict(journals)
    unique['resumed'] = journals['resumed'][len(journals['paused']):]
    increments = {name: Counter(label for label, _, _ in rows) for name, rows in unique.items()}
    total = {key: sum(increments[name][key] for name in increments) for key in counter_names}
    expected = dict(heos_started=16, heos_kernel_returned=16, heos_returned=16,
                    initial_energy_started=3, initial_energy_returned=3,
                    rhs_started=76, rhs_returned=76, wet_started=8, wet_returned=8)
    check(total == expected, 'actual deduplicated whole-comparison counts')
    manifest = read(BASE/'parent/run/assets/data/sandbox/water/heos-8.0.0-resume-v4-manifest.json')
    native_config_sha = hashlib.sha256(json.dumps(manifest['config'], sort_keys=True).encode()).hexdigest()
    lease_report = []
    for name, rows in unique.items():
        parent_counts = outcomes['parent']['counts'] if name != 'parent' else dict.fromkeys(counter_names, 0)
        actual = Counter(label for label, _, _ in journals[name])
        check(outcomes[name]['counts'] == {key: parent_counts[key]+actual[key] for key in counter_names}, 'cumulative actual lineage counts '+name)
        other = dict.fromkeys(counter_names, 0) if name in ('parent', 'continuous') else {
            key: increments['continuous'][key] for key in counter_names}
        check(outcomes[name]['declared_other_branch_counts'] == other, 'other branch debit independently matches journal '+name)
        check(outcomes[name]['combined_counts'] == {key: outcomes[name]['counts'][key]+other[key] for key in counter_names}, 'shared aggregate arithmetic '+name)
        started, closed = named(rows, 'managed_lease_started'), named(rows, 'managed_lease_closed')
        check(len(started) == len(closed) == 1, 'exactly one new real lease '+name)
        lease = closed[0]
        check(lease['status'] == 'closed' and lease['primary_error'] is None and not lease['secondary_errors'], 'clean lease close '+name)
        audit = lease['audit']
        check(audit['closed'] is True and audit['material_qualified'] is False, 'lease closure scope '+name)
        rhs = audit['rhs']
        check(len(rhs) == increments[name]['rhs_started'] == increments[name]['rhs_returned'], 'lease actual callback count '+name)
        for index, call in enumerate(rhs, 1):
            check(call['ordinal'] == index and call['status'] == 'verified' and call['primary_error'] is None and not call['exit_errors'], 'actual RHS lease audit')
            check(call['native_operations'] > 0 and len(call['checks']) == 8, 'four provider entry/exit checks')
            check(Counter(item['stage'] for item in call['checks']) == {'entry': 4, 'exit': 4}, 'complete entry/exit stages')
            for item in call['checks']:
                check(item['status'] == 'verified' and item['fluid_sha256'] == manifest['fluid_sha256'] and
                      item['config_sha256'] == native_config_sha, 'unchanged actual native fluid/config')
        lease_report.append(dict(phase=name, pid=audit['pid'], supervisor_pid=audit['supervisor_pid'],
            rhs_count=len(rhs), native_operations=sum(call['native_operations'] for call in rhs)))
    check(len({row['pid'] for row in lease_report}) == 4, 'four distinct native worker processes')
    check(len({row['supervisor_pid'] for row in lease_report}) == 1, 'one shared comparison driver')
    check(increments['resumed']['rhs_started'] == 14 and increments['resumed']['heos_started'] == 4 and
          increments['resumed']['initial_energy_started'] == increments['resumed']['wet_started'] == 0,
          'resume only reconstructs providers and computes remaining 14 callbacks')
    return {'actual_total_counts': total, 'new_work': {name: {key: row[key] for key in counter_names} for name, row in increments.items()},
            'leases': lease_report, 'new_unique_events': sum(len(rows) for rows in unique.values())}


def audit_packet(journals, paused, checkpoint):
    directory = BASE/'paused/resume-point'
    manifest = read(directory/'manifest.json')
    actual_files = {path.relative_to(directory).as_posix() for path in directory.rglob('*')
                   if path.is_file() and '.restore-attempt' not in path.relative_to(directory).parts and path != directory/'manifest.json'}
    check(actual_files == set(manifest['files']), 'packet exact files after excluding local claim')
    for name, (sha, length) in manifest['files'].items():
        path = directory/name
        check(path.stat().st_size == length and digest(path) == sha, 'packet file integrity '+name)
    parent = BASE/'parent/run'
    originals = {path.relative_to(parent).as_posix(): digest(path) for path in parent.rglob('*') if path.is_file()}
    copies = {path.relative_to(directory/'parent').as_posix(): digest(path) for path in (directory/'parent').rglob('*') if path.is_file()}
    check(originals == copies, 'complete original parent tree byte preservation')
    for name in ('FINALIZING.json', 'SAVE_FAILURE.json', 'WORKER_FAILURE.json'):
        check(not (directory/name).exists(), 'clean suspended packet '+name)
    source = graph_value(read(directory/'source-observations.json'))
    captures = source['captures']
    check(len(captures) == len(checkpoint.observations) == 8, 'complete captured source prefix')
    event_paths = {path.name: (label, value, path) for label, value, path in journals['paused']}
    for index, (capture, original) in enumerate(zip(captures, checkpoint.observations), 1):
        check(capture['ordinal'] == index and equal(capture['packed_input'], original.state) and
              equal(capture['time'], original.time), 'capture binds original numeric input')
        check(equal(capture['evaluation'].rates, original.rates), 'capture binds original numeric rates')
        for key, kind in (('started_event', 'rhs_started'), ('returned_event', 'rhs_returned')):
            ref = capture[key]
            label, value, path = event_paths[Path(ref['path']).name]
            check(label == kind and digest(path) == ref['sha256'], 'capture original raw event hash')
            check(equal(value['state'], original.state) and equal(value['time'], original.time), 'raw source input binding')
            if kind == 'rhs_returned':
                check(equal(value['evaluation'], capture['evaluation']), 'complete saved/source raw evaluation binding')
    meta = source['metadata']
    check(meta['parent_study_sha256'] == paused.parent_study_sha256 == digest(parent/'source-study-record.json'),
          'actual original parent source-record identity')
    check(equal(meta['balances'], paused.balances) and dict(paused.counts) == meta['counts'], 'packet ledger and count binding')
    check(meta['journal_count'] == len(journals['paused']) and meta['journal_bytes'] ==
          sum(path.stat().st_size for _, _, path in journals['paused']), 'saved journal byte and event budget')
    envelope = read(directory/'packet.json')
    check(envelope['source_resume_authorized'] is True and envelope['historical_study_resume_authorized'] is False and
          envelope['material_qualified'] is False and envelope['full_firing_cycle'] is False, 'packet qualification boundaries')
    claim = directory/'.restore-attempt'
    check({path.name for path in claim.iterdir()} == {'started.json', 'restored.json'}, 'one successful local restore claim')
    return {'packet_files': len(manifest['files']), 'original_parent_files': len(originals),
            'checkpoint_sha256': digest(directory/'ordinary-checkpoint.json'),
            'source_observations_sha256': digest(directory/'source-observations.json')}


def audit_time(outcomes, results):
    parent = read(BASE/'parent/run/result.json')['elapsed_wall_seconds']
    envelope = read(BASE/'paused/resume-point/packet.json')
    saved = float.fromhex(envelope['charged_segment_seconds_hex'])
    allowance = float.fromhex(envelope['finalization_allowance_seconds_hex'])
    claim_started = read(BASE/'paused/resume-point/.restore-attempt/started.json')
    restored = read(BASE/'paused/resume-point/.restore-attempt/restored.json')
    restoration_debit = restored['charged_segment_seconds']
    final_debit = results['resumed'].cumulative_outer_seconds-parent
    solved_elapsed = results['resumed'].execution.result.elapsed_seconds
    prior_solve = results['paused'].execution.result.elapsed_seconds
    check(allowance == 1. and saved >= results['paused'].cumulative_outer_seconds-parent >= prior_solve,
          'S retains previous active solve/publication cost plus explicit allowance')
    check(saved <= restoration_debit < final_debit < 180., 'S plus new active read/reconstruction/solve remains charged')
    check(final_debit >= solved_elapsed >= prior_solve and parent+final_debit < 510., 'ordinary and lifetime original limits')
    check(0 <= final_debit-saved <= outcomes['resumed']['process_elapsed_seconds'], 'new active debit fits actual resume worker interval')
    check(restored['counts']['rhs_started'] == outcomes['paused']['counts']['rhs_started'] and
          restored['counts']['heos_started'] == outcomes['paused']['counts']['heos_started']+4,
          'actual restored checkpoint charged four constructors before any new RHS')
    offline_anchor = (claim_started['started_wall_time_ns']-envelope['suspended_wall_time_ns'])/1e9
    # The anchor precedes the tail of save finalization. This interval is not
    # represented as a precisely measured duration after process termination.
    return dict(parent_active_seconds=parent, saved_charged_S_seconds=saved,
        explicit_finalization_allowance_seconds=allowance, restored_before_advance_charged_seconds=restoration_debit,
        final_ordinary_charged_seconds=final_debit, new_active_charge_to_result_seconds=final_debit-saved,
        worker_resume_elapsed_seconds=outcomes['resumed']['process_elapsed_seconds'],
        resume_entry_and_final_publication_outside_result_seconds=outcomes['resumed']['process_elapsed_seconds']-(final_debit-saved),
        wall_anchor_to_claim_seconds=offline_anchor,
        scope='saved samples establish retained S and positive bounded new A; monotonic intermediate timestamps and completed-session offline_history are not independently persisted')


def audit_supervision(outcomes):
    metadata, status = read(SUPERVISOR/'metadata.json'), read(SUPERVISOR/'status.json')
    check(status['status'] == 'complete' and status['returncode'] == 0 and status['inputs_unchanged'] is True,
          'successful supervisor completion')
    check(metadata['timeout_s'] == 570. and metadata['cleanup_grace_s'] == 1., 'original supervisor limits')
    check({path: info['sha256'] for path, info in metadata['inputs_before'].items()} == status['inputs_after'],
          'supervised before/after input identity')
    for path, sha in status['inputs_after'].items():
        check(digest(path) == sha and Path(path).stat().st_size == metadata['inputs_before'][path]['bytes'],
              'supervised input still unchanged '+path)
    check(status['cleanup']['leader_reaped'] is True and not status['cleanup']['signal_errors'], 'process-group cleanup')
    check(status['elapsed_s'] < metadata['timeout_s'], 'supervisor deadline')
    case_sha, config_sha = digest(BASE/'parent/run/case.json'), digest(BASE/'parent/run/config.json')
    remaining = []
    for name, outcome in outcomes.items():
        request_path = BASE/(name+'-request.json')
        request = read(request_path)
        check((BASE/name/'request.json').read_bytes() == request_path.read_bytes(), 'exact worker request bytes')
        check(outcome['request_sha256'] == digest(request_path), 'actual request hash')
        check(outcome['raw_case_sha256'] == case_sha and outcome['canonical_config_sha256'] == config_sha,
              'raw and canonical case hashes separately correct')
        check(outcome['runtime_before'] == outcome['runtime_after'] == outcomes['parent']['runtime_before'], 'same installed execution identity')
        budget = request['shared_budget']
        check(budget['total_callback_cap'] == 97 and budget['wet_pressure_request_cap'] == 16, 'original common count limits')
        check(outcome['process_elapsed_seconds'] < budget['outer_remaining_seconds'], 'individual actual time within remaining comparison budget')
        remaining.append(budget['outer_remaining_seconds'])
        check(not (BASE/name/'FAILURE.json').exists(), 'no worker failure publication')
    check(510. >= remaining[0] > remaining[1] > remaining[2] > remaining[3] > 0., 'whole comparison wall budget progresses')
    check(not (BASE/'DRIVER_FAILURE.json').exists(), 'no driver failure publication')
    return dict(checked_inputs=len(status['inputs_after']), supervisor_elapsed_seconds=status['elapsed_s'],
                cleanup=status['cleanup'], raw_case_sha256=case_sha, canonical_config_sha256=config_sha,
                shared_remaining_seconds=remaining)


def audit_chain(parent, ordinary, saved_rows):
    """Independently accumulate every saved segment from the original wet state."""
    selected = parent.candidates[1]
    initial_trial = parent.refinement.approach.trial
    initial = initial_trial.initial
    terminal = selected.terminal
    initial_n, initial_u = qarray(initial.amounts_mol), qarray(initial.internal_energy_j)
    cells = initial.amounts_mol.shape[0]
    summed_n = [F()] * (4 * cells)
    summed_u = [F()] * cells
    full_n, full_u = summed_n.copy(), summed_u.copy()
    corrected_n = summed_n.copy()
    correction_water = summed_u.copy()
    masses = [cell.molar_masses_kg_mol for cell in selected.captures[0].evaluation.source_evaluation.gas_states]
    amount_gate = F(selected.seed.policy.amount_absolute_tolerance_mol)
    energy_gate = F(selected.seed.policy.energy_absolute_tolerance_j)
    previous_time = initial_trial.start
    previous_state = initial
    expected = iter(saved_rows)
    results = []

    def record(state, when, phase):
        saved = next(expected)
        check(saved.phase == phase and equal(saved.time, when), 'whole-chain phase/time')
        n = qarray(state.amounts_mol)
        u = qarray(state.internal_energy_j)
        rows = []
        for i in range(cells):
            residual = tuple(n[4*i+j] - initial_n[4*i+j] - summed_n[4*i+j] - corrected_n[4*i+j] for j in range(4))
            exact_residual = tuple(n[4*i+j] - initial_n[4*i+j] - full_n[4*i+j] - corrected_n[4*i+j] for j in range(4))
            energy = u[i] - initial_u[i] - summed_u[i]
            exact_energy = u[i] - initial_u[i] - full_u[i]
            water = residual[0] + residual[3] + correction_water[i]
            elements = (('H', 2*water), ('O', water+2*residual[1]), ('N', 2*residual[2]))
            mass = F(masses[i]['H2O'])*water + F(masses[i]['O2'])*residual[1] + F(masses[i]['N2'])*residual[2]
            fields = dict(cell_index=i, inventory_residual_mol=residual, energy_residual_j=energy,
                full_inventory_residual_mol=exact_residual, full_energy_residual_j=exact_energy,
                water_balance_residual_mol=water, event_water_storage_roundoff_mol=correction_water[i],
                fluid_element_residuals_mol=elements, fluid_mass_residual_kg=mass)
            check(equal(fields, saved.cell_balances[i].fields), 'recomputed full per-cell ledger')
            check(all(abs(x) <= amount_gate for x in residual + exact_residual) and
                  max(abs(energy), abs(exact_energy)) <= energy_gate, 'original per-cell tolerances')
            rows.append(fields)
        for name in ('inventory_residual_mol', 'full_inventory_residual_mol'):
            check(tuple(sum((row[name][j] for row in rows), F()) for j in range(4)) == getattr(saved, name), 'global species ledger')
            check(all(abs(v) <= amount_gate for v in getattr(saved, name)), 'original global species tolerance')
        for name in ('energy_residual_j', 'full_energy_residual_j', 'water_balance_residual_mol',
                     'event_water_storage_roundoff_mol', 'fluid_mass_residual_kg'):
            check(sum((row[name] for row in rows), F()) == getattr(saved, name), 'global scalar ledger')
        check(max(abs(saved.energy_residual_j), abs(saved.full_energy_residual_j)) <= energy_gate,
              'original global energy tolerance')
        elements = tuple((symbol, sum((dict(row['fluid_element_residuals_mol'])[symbol] for row in rows), F()))
                         for symbol in ('H', 'O', 'N'))
        check(elements == saved.fluid_element_residuals_mol, 'global elemental ledger')
        results.append(dict(phase=phase, time_fraction=str(when.seconds), cells=cells,
            maximum_cell_energy_residual_j=max(float(abs(row['energy_residual_j'])) for row in rows),
            global_energy_residual_j=float(saved.energy_residual_j)))

    def accumulate(state, ledger, phase, exact=None):
        nonlocal previous_time, previous_state
        check(equal(ledger.start_s, previous_time), 'whole-chain connected ledger times')
        faces_n = qarray(ledger.face_species_mol)
        reaction = qarray(ledger.reaction_species_mol)
        faces_u = qarray(ledger.face_energy_j)
        work = qarray(ledger.cell_work_j)
        dn = [faces_n[4*i+j]-faces_n[4*(i+1)+j]+reaction[4*i+j] for i in range(cells) for j in range(4)]
        du = [faces_u[i]-faces_u[i+1]+work[i] for i in range(cells)]
        fn, fu = (dn, du) if exact is None else exact
        for target, increment in ((summed_n, dn), (summed_u, du), (full_n, fn), (full_u, fu)):
            for index, value in enumerate(increment):
                target[index] += value
        record(state, ledger.end_s, phase)
        previous_time, previous_state = ledger.end_s, state

    for state, ledger in zip(initial_trial.reference.states[1:], initial_trial.reference.steps):
        accumulate(state, ledger, 'wet_reference')
    pieces = {name: values for name, values, _ in terminal.prefix.integrals}
    face_n, reaction_n = pieces['face_species_mol_s'], pieces['reaction_species_mol_s']
    face_u, power_u = pieces['face_energy_w'], pieces['cell_power_w']
    full_delta_n = [face_n[4*i+j]-face_n[4*(i+1)+j]+reaction_n[4*i+j] for i in range(cells) for j in range(4)]
    full_delta_u = [face_u[i]-face_u[i+1]+power_u[i] for i in range(cells)]
    accumulate(terminal.prefix.raw_state, terminal.prefix.ledger, 'wet_terminal', (full_delta_n, full_delta_u))
    corrected_n[:] = [a-b for a, b in zip(qarray(terminal.corrected_state.amounts_mol), qarray(previous_state.amounts_mol))]
    correction_water[terminal.selected_cell_index] = terminal.totals.signed_storage_roundoff_mol
    check(equal(previous_state.internal_energy_j, terminal.corrected_state.internal_energy_j), 'writeback preserves U')
    for i in range(cells):
        changes = corrected_n[4*i:4*i+4]
        check(sum(changes, F()) == correction_water[i], 'writeback water storage')
        check(changes[1] == changes[2] == 0 and
              (i == terminal.selected_cell_index or all(value == 0 for value in changes)), 'writeback species/cell locality')
    record(terminal.corrected_state, previous_time, 'writeback')
    check(equal(selected.reference.states[0], terminal.corrected_state), 'dry starts from actual corrected state')
    for state, ledger in zip(selected.reference.states[1:], selected.reference.steps):
        accumulate(state, ledger, 'dry_reference')
    check(equal(ordinary.states[0], previous_state) and equal(ordinary.times_s[0], previous_time), 'ordinary starts at original candidate 1')
    for state, ledger in zip(ordinary.states[1:], ordinary.steps):
        accumulate(state, ledger, 'post_dry_reference')
    check(next(expected, None) is None, 'all whole-chain ledger rows recomputed')
    return results


def main():
    started = time.monotonic()
    outcomes = {name: read(BASE/name/'OUTCOME.json') for name in ('parent', 'continuous', 'paused', 'resumed')}
    dirs = {name: BASE/name/('run' if name == 'parent' else 'trajectory') for name in outcomes}
    journals = {name: journal(directory) for name, directory in dirs.items()}
    results = {name: named(journals[name], 'ordinary_segment_returned')[-1]
               for name in ('continuous', 'paused', 'resumed')}
    transition = named(journals['parent'], 'transition_returned')[0]['result']
    parent_saved = graph_value(read(dirs['parent']/'source-study-record.json'))['roots']['transition']
    check(equal(parent_saved.candidates[1].reference, transition.candidates[1].reference),
          'candidate 1 entire parent source-record reference matches actual return')
    check(equal(parent_saved.candidates[1].terminal.corrected_state, transition.candidates[1].terminal.corrected_state),
          'candidate 1 source-record corrected state matches actual return')
    check(transition.numerical_event_accepted is True and transition.material_qualified is False, 'parent numerical gate and material boundary')
    continuous, paused, resumed = (results[name] for name in ('continuous', 'paused', 'resumed'))
    check(equal(continuous.execution.result, resumed.execution.result, ignore_elapsed=True), 'complete numeric trajectory except elapsed')
    check(equal(continuous.execution.observations, resumed.execution.observations), 'all 22 numerical observations')
    check(equal(continuous.balances, resumed.balances), 'all whole-chain balances identical')
    check(equal(paused.execution.observations, resumed.execution.observations[:8]), 'original eight numerical observations')
    for result in (continuous, resumed):
        check(result.selected_candidate_index == 1 and result.status == 'completed', 'actual selected candidate and complete result')
        check(len(result.execution.result.steps) == 3 and result.execution.result.rejected_trials == 0 and
              len(result.execution.observations) == 22 and result.execution.result.evaluations == 22,
              'original three-step zero-rejection gate')
    checkpoint_file = BASE/'paused/resume-point/ordinary-checkpoint.json'
    wire = read(checkpoint_file)
    check(canonical_digest(wire['checkpoint']) == wire['payload_sha256'], 'numeric checkpoint payload digest')
    checkpoint = Decoder().value(wire['checkpoint'])
    check(equal(checkpoint, paused.execution.checkpoint), 'entire serialized original checkpoint')
    check(checkpoint.initial_probe_done is True and checkpoint.next_step_s == F(1, 64), 'original controller continuation')
    for name in ('continuous', 'paused', 'resumed'):
        request = named(journals[name], 'source_trajectory_reconstructed')[-1]
        check(equal(request['start'], transition.candidates[1].end), 'candidate 1 exact start')
        check(request['end'].seconds-request['start'].seconds == F(3, 64), 'original exact duration')
        check(equal(request['ordinary_policy'], checkpoint.problem.policy), 'identical original policy')
    original_files = {path.name: path.read_bytes() for _, _, path in journals['paused']}
    for name, raw in original_files.items():
        check((dirs['resumed']/'events'/name).read_bytes() == raw, 'resumed old event bytes unchanged')
        check((BASE/'paused/resume-point/events'/name).read_bytes() == raw, 'packet original event bytes unchanged')
    check(len(original_files) == 32, 'entire original event prefix')
    raw_returns = {name: named(journals[name], 'rhs_returned') for name in ('continuous', 'paused', 'resumed')}
    for a, b in zip(raw_returns['continuous'], raw_returns['resumed']):
        for key in ('state', 'time', 'evaluation'):
            check(equal(a[key], b[key]), 'complete actual source callback '+key)
    check(len(raw_returns['continuous']) == len(raw_returns['resumed']) == 22, 'source callback lengths')
    for a, b in zip(raw_returns['paused'], raw_returns['resumed'][:8]):
        for key in ('state', 'time', 'evaluation'):
            check(equal(a[key], b[key]), 'saved actual callback prefix '+key)
    chain = audit_chain(transition, resumed.execution.result, resumed.balances)
    first = raw_returns['resumed'][0]['evaluation'].source_evaluation.cells
    last = raw_returns['resumed'][-1]['evaluation'].source_evaluation.cells
    def temperature(cell):
        point = cell.inverse.point
        return point.fluid.mechanical.temperature_k if 'fluid' in point.fields else point.temperature_k
    changes = [temperature(b)-temperature(a) for a, b in zip(first, last)]
    bounds = [a.inverse.temperature_error_bound_k+b.inverse.temperature_error_bound_k for a, b in zip(first, last)]
    check(any(abs(change) > bound for change, bound in zip(changes, bounds)), 'original resolvable nonzero temperature gate')
    check(any(face.conduction_w != 0. for result in raw_returns['resumed']
              for face in result['evaluation'].source_evaluation.faces), 'nonzero actual internal conduction')
    deltas = []
    numeric = resumed.execution.result
    for previous, state in zip(numeric.states, numeric.states[1:]):
        check(equal(previous.amounts_mol, state.amounts_mol), 'ordinary source inventories unchanged')
        residual = sum(qarray(state.internal_energy_j), F())-sum(qarray(previous.internal_energy_j), F())
        check(abs(residual) <= F(checkpoint.problem.policy.energy_absolute_tolerance_j), 'original ordinary global energy gate')
        deltas.append(float(residual))
    report = {'status': 'passed', 'whole_chain_rows': chain, 'temperature_change_k': changes,
              'paired_inverse_temperature_bounds_k': bounds, 'ordinary_global_energy_changes_j': deltas,
              'counts_and_leases': audit_counts(journals, outcomes),
              'packet_integrity': audit_packet(journals, paused, checkpoint),
              'time_accounting': audit_time(outcomes, results),
              'supervision': audit_supervision(outcomes)}
    report.update(assertions=CHECKS, elapsed_seconds=time.monotonic()-started,
                  application_imports=0, eos_calls=0)
    (OUTPUT/'AUDIT.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
