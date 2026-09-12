"""Bounded passive reading of the existing ordinary source terminal journal.

This is an association/balance reader, not a checkpoint codec, a numerical
controller replay, an EOS authentication service, or authority to resume.
Only explicitly registered passive records can be materialized. Native handles
and source providers stay labelled raw data and are never constructed.
"""
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction as F
import hashlib
import math
import os
import stat
from pathlib import Path
from types import MappingProxyType

import numpy as np

from .exact_event_clock import ExactEventTime as T
from .exact_integration import ExactIntegrationResult
from .exact_integration_checkpoint import ExactCallbackObservation, _digest
from .exact_integration_checkpoint_codec import (
    _FIELD_NAMES, _record_fields, _Budget, _encode, MAX_BYTES as MAX_EXPANDED_BYTES,
)
from .integration import IntegrationPolicy
from .run_service import read_run_with_source_record
from .source_execution_worker import COUNTERS
from .source_net_panel import SavedSourceSample
from .source_observation_record import SourceObservationContext, _check_sample
from .source_observation_schema import strict_json
from .source_run_config import load_source_run_config
from .source_run_journal import MAX_EVENT_BYTES, MAX_JOURNAL_BYTES
from .source_study_schema import REGISTRY, SourceStudyNode, reify
from .source_trajectory import SourceOrdinaryStepSizes, SourceTrajectoryResult, _audit_trajectory_balance
from .source_trajectory_record import read_source_trajectory_checkpoint

MAX_EVENTS = 10_000
MAX_VALUES = 300_000
MAX_ARRAY_VALUES = 250_000
MAX_STEPS = 256
MAX_OBSERVATIONS = 4096
SCOPE = 'source_terminal_schema_observation_balance_and_lineage_checked'


def _require(ok, reason):
    if not ok:
        raise ValueError('source_terminal_' + reason)


def _shape(value, names, reason):
    _require(type(value) is dict and set(value) == set(names.split()), reason)


def _same(left, right):
    """Bound each distinct shared pair; saved DAGs must not expand exponentially."""
    seen = set()
    def visit(a, b, depth):
        _require(depth <= 96 and len(seen) <= MAX_VALUES, 'comparison_limit')
        if type(a) is not type(b):
            return False
        key = (id(a), id(b))
        if key in seen:
            return True
        seen.add(key)
        if type(a) is np.ndarray:
            return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()
        if is_dataclass(a):
            return all(visit(getattr(a, f.name), getattr(b, f.name), depth + 1) for f in fields(a))
        if isinstance(a, Mapping):
            return a.keys() == b.keys() and all(visit(a[k], b[k], depth + 1) for k in a)
        if type(a) in (tuple, list):
            return len(a) == len(b) and all(visit(x, y, depth + 1) for x, y in zip(a, b))
        if type(a) is float:
            return a.hex() == b.hex()
        return a == b
    return visit(left, right, 0)


def _nonnegative(value):
    return type(value) is float and math.isfinite(value) and value >= 0.


def _integer(value):
    return type(value) is int and 0 <= value <= 1_000_000_000


def _read(path, limit=MAX_EVENT_BYTES):
    # The shared reader rejects FIFOs but follows symlinks. This result boundary
    # additionally refuses links atomically at open, including broken links.
    _require(not Path(path).is_symlink(), 'regular_file')
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        status = os.fstat(descriptor)
        _require(stat.S_ISREG(status.st_mode), 'regular_file')
        _require(status.st_size <= limit, 'file_limit')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        _require(len(raw) <= limit, 'file_limit')
        return raw
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class _Passive:
    kind: str
    values: dict


# Additional shapes are data labels only. These classes are never imported or
# called based on the archive. The existing source registry owns source types.
_EXTRA = {
    'sludge_sandbox.source_trajectory.SourceTrajectoryResult':
        'execution balances counts cumulative_outer_seconds parent_study_sha256 selected_candidate_index '
        'journal_events status reason material_qualified full_firing_cycle archived_resume_authorized '
        'qualification managed_execution managed_audits',
    'sludge_sandbox.source_trajectory.SourceOrdinaryStepSizes':
        'initial_step_s maximum_step_s rationale classification',
    'sludge_sandbox.exact_integration_checkpoint.ExactCheckpointRun':
        'result checkpoint observations committed_checkpoint failure',
    'sludge_sandbox.water_heos.HEOSWaterProperties':
        'reference source_asset_sha256 numerical_limits implementation _kernel _ideal',
    'sludge_sandbox.water_properties.WaterProperties':
        'reference source_asset_sha256 numerical_limits _backend _model _saturation_cache',
    'sludge_sandbox.water_properties.NumericalLimits':
        'energy_identity_absolute_j_kg eos_caloric_absolute_j_kg gibbs_absolute_j_kg '
        'heat_capacity_absolute_j_kg_k pressure_absolute_pa pressure_relative temperature_absolute_k',
}
_NUMERIC = {cls.__module__ + '.' + cls.__qualname__: cls for cls in _FIELD_NAMES}
_EXTRA.update({kind: _FIELD_NAMES[cls] for kind, cls in _NUMERIC.items() if kind not in REGISTRY})
_OPAQUE = {'sludge_sandbox._heos_kernel.HEOSCandidate', 'builtins.module', 'iapws.iapws95.IAPWS95'}


class _Graph:
    """One fixed journal projection; references are resolved once, without calls."""
    def __init__(self, graph):
        _shape(graph, 'schema root nodes numeric_validation_performed resume_authorized', 'graph_schema')
        _require(graph['schema'] == 'source_run_raw_projection_v1' and
                 graph['numeric_validation_performed'] is False and graph['resume_authorized'] is False,
                 'graph_authority')
        nodes = graph['nodes']
        _require(type(nodes) is dict and 0 < len(nodes) <= MAX_VALUES and
                 set(nodes) == {str(i) for i in range(len(nodes))}, 'graph_nodes')
        self.graph, self.memo, self.active = graph, {}, set()
        self.visits, self.arrays = 0, 0
        self.root = self._visit(graph['root'], 0)
        _require(len(self.memo) == len(nodes), 'unreachable_graph_nodes')

    def _visit(self, value, depth):
        self.visits += 1
        _require(self.visits <= MAX_VALUES and depth <= 96, 'graph_work_limit')
        if value is None or type(value) is bool:
            return value
        if type(value) is str:
            _require(len(value.encode('utf8')) <= 65536, 'graph_string_limit')
            return value
        if type(value) is int:
            _require(value.bit_length() <= 4096, 'graph_integer_limit')
            return value
        _require(type(value) is dict, 'tagged_value')
        if set(value) == {'binary64'}:
            raw = value['binary64']
            _require(type(raw) is str and len(raw) <= 32, 'float_hex')
            result = float.fromhex(raw)
            _require(math.isfinite(result) and result.hex() == raw, 'canonical_float')
            return result
        if set(value) == {'fraction'}:
            pair = value['fraction']
            _require(type(pair) is list and len(pair) == 2 and
                     all(type(n) is int and n.bit_length() <= 4096 for n in pair) and
                     pair[1] > 0 and math.gcd(*pair) == 1, 'canonical_fraction')
            return F(*pair)
        _require(set(value) == {'ref'} and type(value['ref']) is str, 'raw_reference')
        key = value['ref']
        _require(key not in self.active, 'graph_cycle')
        _require(key in self.graph['nodes'], 'raw_reference')
        if key in self.memo:
            return self.memo[key]
        self.active.add(key)
        node = self.graph['nodes'][key]
        _require(type(node) is dict and type(node.get('type')) is str and
                 len(node['type']) <= 512, 'node_type')
        kind = node['type']
        child = lambda item: self._visit(item, depth + 1)
        if kind in ('builtins.tuple', 'builtins.list'):
            _shape(node, 'type values', 'sequence_fields')
            _require(type(node['values']) is list and len(node['values']) <= MAX_VALUES, 'sequence_limit')
            values = [child(x) for x in node['values']]
            result = tuple(values) if kind == 'builtins.tuple' else values
        elif kind in ('builtins.dict', 'builtins.mappingproxy'):
            _shape(node, 'type fields', 'mapping_fields')
            _require(type(node['fields']) is dict, 'mapping_fields')
            result = {self._visit(k, depth + 1): child(v) for k, v in node['fields'].items()}
            for flag in ('material_qualified', 'full_firing_cycle', 'training_eligible'):
                _require(flag not in result or result[flag] is False, 'saved_qualification_upgrade')
        elif kind == 'numpy.ndarray':
            _shape(node, 'type dtype shape values', 'array_fields')
            shape, values = node['shape'], node['values']
            _require(node['dtype'] == 'float64' and type(shape) is list and len(shape) in (1, 2) and
                     all(type(n) is int and 0 < n <= MAX_ARRAY_VALUES for n in shape), 'array_shape')
            count = math.prod(shape)
            self.arrays += count
            _require(self.arrays <= MAX_ARRAY_VALUES and type(values) is list and len(values) == count,
                     'array_limit')
            numbers = [child(v) for v in values]
            _require(all(type(v) is float for v in numbers), 'array_binary64')
            result = np.frombuffer(np.asarray(numbers, dtype=np.float64).tobytes(), dtype=np.float64).reshape(shape)
        elif kind == 'pathlib.PosixPath':
            _shape(node, 'type path', 'path_fields')
            result = _Passive(kind, {'path': child(node['path'])})
        elif kind in _OPAQUE:
            _shape(node, 'type unavailable reason', 'opaque_fields')
            _require(node['unavailable'] is True and node['reason'] == 'opaque_runtime_object_not_serializable',
                     'opaque_contract')
            result = _Passive(kind, {'unavailable': True, 'reason': node['reason']})
        elif kind == 'sludge_sandbox.exact_source_column.ExactSourceColumn':
            _shape(node, 'type live_reference_only identity modes', 'live_reference_fields')
            _require(node['live_reference_only'] is True, 'live_reference_contract')
            result = _Passive(kind, dict(identity=child(node['identity']), modes=child(node['modes'])))
        else:
            _require(kind in REGISTRY or kind in _EXTRA, 'unsupported_record:' + kind)
            _shape(node, 'type fields uninitialized_fields', 'record_shape')
            _require(node['uninitialized_fields'] == [], 'incomplete_record')
            names = ({f.name for f in fields(REGISTRY[kind])} if kind in REGISTRY
                     else set(_EXTRA[kind].split()))
            _require(type(node['fields']) is dict and set(node['fields']) == names, 'record_fields:' + kind)
            body = {k: child(v) for k, v in node['fields'].items()}
            if kind == 'sludge_sandbox.exact_event_clock.ExactEventTime':
                _require(type(body['seconds']) is F, 'exact_time_fraction')
                result = T(body['seconds'])
            else:
                result = SourceStudyNode(kind, MappingProxyType(body)) if kind in REGISTRY else _Passive(kind, body)
        self.active.remove(key)
        self.memo[key] = result
        return result


def _materialize(value, memo=None):
    """Materialize only original passive source/numeric whitelist, no replay."""
    if memo is None:
        _expansion_limit(value)
        memo = {}
    if id(value) in memo:
        return memo[id(value)]
    if type(value) is SourceStudyNode:
        result = reify(value)
    elif type(value) is _Passive:
        _require(value.kind in _NUMERIC, 'unsupported_materialization:' + value.kind)
        cls = _NUMERIC[value.kind]
        body = {k: _materialize(v, memo) for k, v in value.values.items()}
        _record_fields(cls, body)
        result = cls(**{f.name: body[f.name] for f in fields(cls) if f.init})
        _require(all(_same(getattr(result, k), v) for k, v in body.items()), 'constructor_changed_fields')
    elif type(value) is tuple:
        result = tuple(_materialize(v, memo) for v in value)
    elif type(value) is list:
        result = [_materialize(v, memo) for v in value]
    elif isinstance(value, Mapping):
        result = {k: _materialize(v, memo) for k, v in value.items()}
    else:
        result = value
    memo[id(value)] = result
    return result


def _expansion_limit(value):
    """Bound duplicated numeric data before constructors or digest serialization.

    A memo stores full expanded cost, not just distinct-node cost. Every repeat
    edge charges that cost again, without actually expanding the shared object.
    The checkpoint codec supplies the existing 32 MiB representation ceiling.
    This is a conservative data/work bound, not a process-RSS prediction.
    """
    memo, active, visits = {}, set(), 0

    def cost(item, depth=0):
        nonlocal visits
        visits += 1
        _require(depth <= 96 and visits <= MAX_VALUES, 'numeric_expansion_work_limit')
        total = 128  # Typed wrappers, delimiters and scalar spellings.
        cls = type(item)
        if item is None or cls in (bool, float):
            return total
        if cls is str:
            total += 6 * len(item.encode('utf8'))
        elif cls is int:
            total += item.bit_length()
        elif cls is F:
            total += item.numerator.bit_length() + item.denominator.bit_length()
        else:
            key = id(item)
            _require(key not in active, 'numeric_expansion_cycle')
            if key in memo:
                return memo[key]
            active.add(key)
            if cls is np.ndarray:
                total += 16 * item.size
            elif cls is T:
                total += cost(item.seconds, depth + 1)
            else:
                if cls in (_Passive, SourceStudyNode):
                    children = item.values.items()
                    total += 6 * len(item.kind.encode('utf8'))
                elif isinstance(item, Mapping):
                    children = item.items()
                elif cls in (tuple, list):
                    children = ((None, child) for child in item)
                else:
                    raise ValueError('source_terminal_unsupported_numeric_expansion')
                for name, child in children:
                    total += cost(child, depth + 1)
                    if name is not None:
                        total += cost(name, depth + 1)
                    _require(total <= MAX_EXPANDED_BYTES, 'numeric_expansion_size_limit')
            active.remove(key)
            memo[key] = total
        _require(total <= MAX_EXPANDED_BYTES, 'numeric_expansion_size_limit')
        return total

    return cost(value)


_EVENT_FIELDS = {
    'heos_started': 'phase source_directory manifest',
    'heos_kernel_returned': 'phase source_directory manifest kernel',
    'heos_returned': 'phase source_directory manifest water',
    'source_trajectory_reconstructed': 'parent_study_sha256 runtime original_counts original_elapsed_wall_seconds '
        'selected_candidate_index start end adapter_provenance original_reference_policy ordinary_policy step_sizes scope',
    'managed_lease_started': 'ordinal phase status audit primary_error secondary_errors',
    'managed_lease_closed': 'ordinal phase status audit primary_error secondary_errors elapsed_seconds',
    'rhs_started': 'phase adapter state time',
    'rhs_returned': 'phase adapter state time evaluation',
}


def _read_events(directory):
    directory = Path(directory)
    _require(directory.is_dir() and not directory.is_symlink(), 'regular_trajectory_directory')
    _require({p.name for p in directory.iterdir()} == {'events'}, 'trajectory_members')
    event_dir = directory / 'events'
    _require(event_dir.is_dir() and not event_dir.is_symlink(), 'regular_events_directory')
    paths = []
    for path in event_dir.iterdir():
        paths.append(path)
        _require(len(paths) <= MAX_EVENTS, 'event_count_limit')
    _require(bool(paths), 'empty_journal')
    total, work, result = 0, 0, []
    for index, path in enumerate(sorted(paths), 1):
        _require(path.name == f'{index:06d}.json', 'event_order')
        raw = _read(path)
        total += len(raw)
        _require(total <= MAX_JOURNAL_BYTES, 'journal_byte_limit')
        event = strict_json(raw)
        _shape(event, 'event ordinal payload', 'event_fields')
        _require(type(event['ordinal']) is int and event['ordinal'] == index, 'event_ordinal')
        kind = event['event']
        _require(type(kind) is str and kind in (*_EVENT_FIELDS, 'ordinary_segment_returned'), 'unsupported_event')
        graph = _Graph(event['payload'])
        work += graph.visits
        _require(work <= 2_000_000, 'journal_work_limit')
        if kind == 'ordinary_segment_returned':
            _require(type(graph.root) is _Passive and graph.root.kind ==
                     'sludge_sandbox.source_trajectory.SourceTrajectoryResult', 'terminal_type')
        else:
            _shape(graph.root, _EVENT_FIELDS[kind], 'event_payload:' + kind)
        result.append((kind, graph, hashlib.sha256(raw).hexdigest(), len(raw)))
    _require(result[-1][0] == 'ordinary_segment_returned', 'missing_terminal_event')
    _require(sum(e[0] == 'source_trajectory_reconstructed' for e in result) ==
             sum(e[0] == 'ordinary_segment_returned' for e in result) ==
             sum(e[0] == 'managed_lease_closed' for e in result), 'operation_journal_boundaries')
    return result


def _count_events(events, baseline):
    _require(type(baseline) is dict and set(baseline) == set(COUNTERS) and
             all(_integer(v) for v in baseline.values()), 'baseline_counts')
    actual = Counter(e[0] for e in events)
    return {key: baseline[key] + actual[key] for key in COUNTERS}


def _numerical(execution, initial, start, end, policy):
    _require(type(execution) is _Passive and execution.kind ==
             'sludge_sandbox.exact_integration_checkpoint.ExactCheckpointRun', 'execution_type')
    body = execution.values
    _require(body['checkpoint'] is None and body['failure'] is None, 'completed_execution_only')
    _expansion_limit(body)
    result = _materialize(body['result'])
    observations = _materialize(body['observations'])
    _require(type(result) is ExactIntegrationResult and result.status == 'completed' and result.reason is None,
             'numerical_completed')
    _require(type(result.times_s) is tuple and type(result.states) is tuple and type(result.steps) is tuple and
             0 < len(result.steps) <= MAX_STEPS and len(result.states) == len(result.times_s) == len(result.steps) + 1,
             'accepted_history_shape')
    _require(type(observations) is tuple and len(observations) <= MAX_OBSERVATIONS and
             all(_integer(x) for x in (result.evaluations, result.rejected_trials, result.attempted_trials)) and
             result.evaluations == len(observations) and
             result.attempted_trials == len(result.steps) + result.rejected_trials and
             1 + 7 * len(result.steps) + result.rejected_trials <= result.evaluations <= 1 + 7 * result.attempted_trials,
             'numerical_counters')
    _require(result.times_s[0] == start and result.times_s[-1] == end and _same(result.states[0], initial)
             and all(a < b for a, b in zip(result.times_s, result.times_s[1:])), 'exact_terminal_clock')
    _require(_nonnegative(result.elapsed_seconds) and result.elapsed_seconds < policy.maximum_wall_seconds and
             len(result.steps) <= policy.maximum_steps and result.rejected_trials <= policy.maximum_rejections,
             'original_segment_limits')
    for before, after, step in zip(result.states, result.states[1:], result.steps):
        _require(before.amounts_mol.shape == after.amounts_mol.shape == initial.amounts_mol.shape and
                 before.internal_energy_j.shape == after.internal_energy_j.shape == initial.internal_energy_j.shape and
                 before.energy_model_identity == after.energy_model_identity == initial.energy_model_identity and
                 before.mechanical_stretches is after.mechanical_stretches is None, 'state_domain')
        _require(step.face_species_mol.shape == (initial.amounts_mol.shape[0] + 1, 4) and
                 step.reaction_species_mol.shape == initial.amounts_mol.shape and
                 step.face_energy_j.shape == (initial.amounts_mol.shape[0] + 1,) and
                 step.cell_work_j.shape == initial.internal_energy_j.shape, 'ledger_shapes')
        local_n, local_u = [], []
        for i in range(initial.amounts_mol.shape[0]):
            row = tuple(F(float(after.amounts_mol[i,j])) - F(float(before.amounts_mol[i,j]))
                - F(float(step.face_species_mol[i,j])) + F(float(step.face_species_mol[i+1,j]))
                - F(float(step.reaction_species_mol[i,j])) for j in range(4))
            energy = F(float(after.internal_energy_j[i])) - F(float(before.internal_energy_j[i])) \
                - F(float(step.face_energy_j[i])) + F(float(step.face_energy_j[i+1])) - F(float(step.cell_work_j[i]))
            _require(all(abs(v) <= F(policy.amount_absolute_tolerance_mol) for v in row) and
                     abs(energy) <= F(policy.energy_absolute_tolerance_j), 'local_step_balance')
            local_n.append(row)
            local_u.append(energy)
        _require(all(abs(sum((row[j] for row in local_n), F())) <= F(policy.amount_absolute_tolerance_mol)
                     for j in range(4)) and abs(sum(local_u,F())) <= F(policy.energy_absolute_tolerance_j),
                 'whole_step_balance')
        _require(all(getattr(step, key) is None for key in
                     ('cell_work_components_j', 'component_quadrature_roundoff_j', 'component_sum_residual_j',
                      'stretch_increment', 'stretch_quadrature_roundoff')), 'unsupported_ledger_component')
    _require(all(step.start_s == a and step.end_s == b for step, a, b in
                 zip(result.steps, result.times_s, result.times_s[1:])), 'ledger_clock')
    _require(result.cumulative_absolute_component_residual_j is None, 'unsupported_component_history')
    for i, observation in enumerate(observations, 1):
        _require(type(observation) is ExactCallbackObservation and type(observation.ordinal) is int and
                 observation.ordinal == i and _integer(observation.attempt_index) and
                 observation.attempt_index <= result.attempted_trials and type(observation.role) is str and
                 observation.validated is True and observation.failure_kind is None and observation.failure_message is None
                 and observation.returned_type == 'sludge_sandbox.integration.Rates', 'observation_schema')
        _require(start <= observation.time <= end and observation.state.energy_model_identity == initial.energy_model_identity,
                 'observation_domain')
        observation.rates.derivatives(observation.state)
    roles = ('full_first', 'full_second', 'left_first', 'left_second',
             'right_first', 'right_second', 'accepted')
    _require(observations and observations[0].attempt_index == 0 and observations[0].role == 'initial'
             and observations[0].time == start and _same(observations[0].state, initial), 'initial_observation')
    attempts = [[] for _ in range(result.attempted_trials)]
    for observation in observations[1:]:
        _require(1 <= observation.attempt_index <= len(attempts), 'observation_attempt')
        attempts[observation.attempt_index-1].append(observation)
    _require(_same(tuple(o for attempt in attempts for o in attempt), observations[1:]), 'attempt_order')
    accepted_index = 0
    for attempt in attempts:
        _require(tuple(o.role for o in attempt) in (roles[:6], roles), 'unsupported_attempt_roles')
        # Saved successful error-rejected trials have six stages. A successful
        # accepted observation must bind the next committed state, never a trial.
        _require(attempt[0].time == result.times_s[accepted_index] and
                 _same(attempt[0].state, result.states[accepted_index]), 'attempt_initial_state')
        if len(attempt) == 7:
            accepted_index += 1
            _require(accepted_index < len(result.states) and attempt[-1].time == result.times_s[accepted_index]
                     and _same(attempt[-1].state, result.states[accepted_index]), 'accepted_observation_state')
    _require(accepted_index == len(result.steps), 'accepted_observation_count')
    # This is the actually saved last committed frame, including its original
    # completed status. No interior checkpoint is fabricated or admitted.
    committed = _materialize(body['committed_checkpoint'])
    _require(committed is not None and type(committed.observations) is tuple and
             len(committed.observations) == len(observations), 'committed_observations_limit')
    _require(_same(committed.problem.initial, initial) and committed.problem.start_s == start and
             committed.problem.end_s == end and _same(committed.problem.policy, policy) and
             committed.problem.breakpoints_s == () and committed.result.status == 'completed' and
             committed.result.reason is None and committed.phase == 'accepted_boundary' and
             committed.initial_probe_done is True, 'committed_problem')
    for field in fields(ExactIntegrationResult):
        if field.name not in ('status', 'reason', 'elapsed_seconds'):
            _require(_same(getattr(committed.result, field.name), getattr(result, field.name)), 'committed_history')
    _require(_nonnegative(committed.result.elapsed_seconds) and
             committed.result.elapsed_seconds <= result.elapsed_seconds and
             _same(committed.observations, observations), 'committed_observations')
    _require(type(committed.next_step_s) is F and F(policy.minimum_step_s) <= committed.next_step_s <=
             F(policy.maximum_step_s) and committed.knot_index == 0 and committed.component_schema is None,
             'committed_controller_fields')
    cumulative_n = [F()] * initial.amounts_mol.size
    cumulative_u = [F()] * initial.internal_energy_j.size
    for step in result.steps:
        for i in range(initial.amounts_mol.shape[0]):
            for j in range(4):
                cumulative_n[i*4+j] += F(float(step.face_species_mol[i,j])) - F(float(step.face_species_mol[i+1,j])) + F(float(step.reaction_species_mol[i,j]))
            cumulative_u[i] += F(float(step.face_energy_j[i])) - F(float(step.face_energy_j[i+1])) + F(float(step.cell_work_j[i]))
    _require(committed.cumulative_n == tuple(cumulative_n) and committed.cumulative_u == tuple(cumulative_u) and
             committed.cumulative_components == (F(),) * initial.internal_energy_j.size and
             committed.cumulative_stretch is committed.cumulative_stretch_exact is committed.cumulative_stretch_roundoff is None,
             'committed_cumulative_ledger')
    # Use only the existing bounded field encoder, not checkpoint admission or
    # replay. It charges every repeated array/node before the legacy digest can
    # duplicate data. All historical correspondence checks already passed above.
    _encode(committed, _Budget())
    _require(committed.binding_sha256 == _digest(committed), 'committed_binding')
    return result, observations


def _audit_events(events, observations, context, baseline):
    """Bind every original callback and native-scope close to its saved value."""
    ordinal, active, lease, leases, source_pair = 0, None, None, [], None
    constructors, active_constructor_count = 0, 0
    last_return_count = 0
    for index, (kind, graph, _, _) in enumerate(events, 1):
        payload = graph.root
        if kind.startswith('heos_'):
            _require(active is None and lease is None and payload['phase'] == 'source_trajectory_reconstruction',
                     'constructor_phase')
            paths = (payload['source_directory'], payload['manifest'])
            _require(all(type(p) is _Passive and p.kind == 'pathlib.PosixPath' and
                         type(p.values['path']) is str and Path(p.values['path']).is_absolute() for p in paths),
                     'constructor_paths')
            if kind == 'heos_started':
                _require(source_pair is None, 'constructor_pair')
                source_pair = (paths, 'kernel')
                constructors += 1
            elif kind == 'heos_kernel_returned':
                _require(source_pair is not None and source_pair[1] == 'kernel' and _same(paths, source_pair[0]),
                         'constructor_pair')
                _require(type(payload['kernel']) is _Passive and payload['kernel'].kind in _OPAQUE,
                         'constructor_kernel_label')
                source_pair = (paths, 'water')
            else:
                _require(source_pair is not None and source_pair[1] == 'water' and _same(paths, source_pair[0]),
                         'constructor_pair')
                _require(type(payload['water']) is _Passive and payload['water'].kind ==
                         'sludge_sandbox.water_heos.HEOSWaterProperties', 'constructor_water_label')
                source_pair = None
        elif kind == 'source_trajectory_reconstructed':
            _require(source_pair is None and active is None and lease is None, 'reconstruction_boundary')
            _require(constructors > 0, 'reconstruction_constructors')
            active_constructor_count, constructors = constructors, 0
        elif kind == 'managed_lease_started':
            _require(active is None and lease is None and source_pair is None and
                     payload['ordinal'] == len(leases) + 1 and type(payload['ordinal']) is int and
                     payload['phase'] == 'ordinary_source_segment' and payload['status'] == 'admitting' and
                     payload['audit'] is payload['primary_error'] is None and payload['secondary_errors'] == [],
                     'lease_started')
            lease = (payload['ordinal'], ordinal)
        elif kind == 'rhs_started':
            _require(lease is not None and active is None and ordinal < len(observations), 'callback_start_order')
            observation = observations[ordinal]
            ordinal += 1
            adapter = payload['adapter']
            _require(payload['phase'] == 'ordinary_source_segment' and type(adapter) is _Passive and adapter.kind ==
                     'sludge_sandbox.exact_source_column.ExactSourceColumn' and
                     adapter.values['identity'] == context.operator_identity and
                     adapter.values['modes'] == context.interface_modes, 'callback_operator')
            _require(_same(_materialize(payload['state']), observation.state) and payload['time'] == observation.time,
                     'callback_input')
            active = (payload, observation)
        elif kind == 'rhs_returned':
            _require(active is not None, 'callback_return_order')
            original, observation = active
            _require(all(_same(payload[key], original[key]) for key in ('phase', 'adapter', 'state', 'time')),
                     'callback_return_input')
            evaluation = _materialize(payload['evaluation'])
            sample = SavedSourceSample(state=observation.state, role=observation.role, evaluation=evaluation)
            _check_sample(sample, context)
            _require(evaluation.time == observation.time and _same(evaluation.rates, observation.rates), 'callback_rates')
            active = None
        elif kind == 'managed_lease_closed':
            _require(active is None and lease is not None and payload['ordinal'] == lease[0] and
                     payload['phase'] == 'ordinary_source_segment' and payload['status'] == 'closed' and
                     payload['primary_error'] is None and payload['secondary_errors'] == [] and
                     _nonnegative(payload['elapsed_seconds']), 'lease_closed')
            audit = payload['audit']
            _shape(audit, 'mode pid supervisor_pid closed rhs material_qualified', 'lease_audit_fields')
            _require(audit['mode'] == 'managed_single_rhs_boundary_v1' and audit['closed'] is True and
                     audit['material_qualified'] is False and all(type(audit[k]) is int and audit[k] > 0
                     for k in ('pid', 'supervisor_pid')) and type(audit['rhs']) is list and
                     len(audit['rhs']) == ordinal - lease[1], 'lease_audit')
            for j, (rhs, observation) in enumerate(zip(audit['rhs'], observations[lease[1]:ordinal]), 1):
                _shape(rhs, 'ordinal time status native_operations checks primary_error exit_errors elapsed_seconds',
                       'native_rhs_fields')
                _require(type(rhs['ordinal']) is int and rhs['ordinal'] == j and rhs['time'] == repr(observation.time) and
                         rhs['status'] == 'verified' and _integer(rhs['native_operations']) and
                         rhs['primary_error'] is None and rhs['exit_errors'] == [] and _nonnegative(rhs['elapsed_seconds']),
                         'native_rhs_scope')
                checks = rhs['checks']
                _require(type(checks) is list and len(checks) == 2 * active_constructor_count, 'native_checks')
                half = len(checks) // 2
                _require([c.get('stage') for c in checks if type(c) is dict] == ['entry']*half + ['exit']*half,
                         'native_entry_exit_order')
                for check in checks:
                    _shape(check, 'stage kernel_identity status config_sha256 fluid_sha256', 'native_check_fields')
                    _require(check['status'] == 'verified' and all(type(check[k]) is str and len(check[k]) == 64
                             and all(c in '0123456789abcdef' for c in check[k]) for k in
                             ('kernel_identity', 'config_sha256', 'fluid_sha256')), 'native_check_value')
                _require(all({k:v for k,v in left.items() if k != 'stage'} ==
                             {k:v for k,v in right.items() if k != 'stage'}
                             for left, right in zip(checks[:half], checks[half:])), 'native_entry_exit_binding')
            leases.append(payload)
            lease = None
        else:
            _require(active is None and lease is None and source_pair is None, 'terminal_boundary')
            saved = payload.values
            _require(saved['journal_events'] == index - 1 and type(saved['journal_events']) is int,
                     'terminal_journal_boundary')
            _require(dict(saved['counts']) == _count_events(events[:index], baseline), 'intermediate_counts')
            _require(_same(saved['managed_audits'], tuple(leases)), 'saved_lease_binding')
            if index != len(events):
                _require(saved['status'] == 'paused' and ordinal > last_return_count, 'nonterminal_return')
            last_return_count = ordinal
    _require(ordinal == len(observations) and leases and active is lease is source_pair is None, 'complete_callbacks')
    return leases


def _resume(packet_path, trajectory, events, parent_record, result, observations, reconstructed):
    packet_path = Path(packet_path)
    packet = read_source_trajectory_checkpoint(packet_path)
    _require(packet.parent_record.sha256 == parent_record.sha256, 'resume_parent')
    prefix = [(name, meta) for name, meta in packet.files.items() if name.startswith('events/')]
    prefix.sort()
    _require(len(prefix) < len(events), 'resume_new_events_required')
    for (name, (digest, size)), event in zip(prefix, events):
        _require(event[2] == digest and event[3] == size and
                 _read(packet_path / name) == _read(Path(trajectory) / name), 'resume_original_prefix_bytes')
    old = packet.checkpoint.result
    _require(_same(result.states[:len(old.states)], old.states) and result.times_s[:len(old.times_s)] == old.times_s and
             _same(result.steps[:len(old.steps)], old.steps) and
             _same(observations[:len(packet.checkpoint.observations)], packet.checkpoint.observations),
             'resume_original_numerical_prefix')
    claim = packet_path / '.restore-attempt'
    _require(claim.is_dir() and not claim.is_symlink() and
             {p.name for p in claim.iterdir()} == {'started.json', 'restored.json'}, 'resume_clean_claim')
    started = strict_json(_read(claim / 'started.json', 65536))
    restored = strict_json(_read(claim / 'restored.json', 65536))
    _shape(started, 'output started_wall_time_ns', 'claim_started_fields')
    _shape(restored, 'status output counts charged_segment_seconds', 'claim_restored_fields')
    target = str(Path(trajectory).absolute())
    _require(started['output'] == restored['output'] == target and
             type(started['started_wall_time_ns']) is int and started['started_wall_time_ns'] >= 0 and
             restored['status'] == 'live_session_restored', 'claim_output_lineage')
    _require(sum(index > len(prefix) for index, _ in reconstructed) == 1 and
             events[len(prefix)-1][0] == 'ordinary_segment_returned' and
             events[len(prefix)-1][1].root.values['status'] == 'paused', 'resume_single_suffix')
    last_reconstruction = reconstructed[-1][0]
    _require(last_reconstruction > len(prefix) and
             restored['counts'] == _count_events(events[:last_reconstruction], packet.parent_summary['counts']),
             'claim_reconstruction_counts')
    debit = float.fromhex(packet.envelope['charged_segment_seconds_hex'])
    _require(_nonnegative(restored['charged_segment_seconds']) and
             result.elapsed_seconds >= restored['charged_segment_seconds'] >= debit, 'resume_charged_time_floor')
    return packet, len(prefix), debit


def inspect_source_terminal(trajectory_directory, *, parent_directory, request, outcome, input_checkpoint=None):
    """Validate one bound completed managed journal without any physical call.

    ``request`` and ``outcome`` must first pass the execution service's closed
    envelope/path/runtime binding. The original parent and optional input packet
    are independently read here; absent private assets cannot become admission.
    """
    try:
        _require(type(request) is dict and type(outcome) is dict and request['operation'] in
                 ('source-advance', 'source-resume') and outcome['status'] == 'completed', 'operation')
        _require((input_checkpoint is not None) == (request['operation'] == 'source-resume'), 'input_packet_operation')
        events = _read_events(trajectory_directory)
        summary, _, record = read_run_with_source_record(parent_directory)
        _require(summary['status'] == 'completed' and record is not None and
                 summary['runtime_before'] == summary['runtime_after'] == outcome['runtime_before'] ==
                 outcome['runtime_after'], 'parent_runtime_binding')
        transition = record.roots['transition']
        _require(transition.numerical_event_accepted is True and transition.material_qualified is False,
                 'parent_accepted_transition')
        candidate = transition.candidates[1]
        initial, start = reify(candidate.reference.states[-1]), candidate.reference.times_s[-1]
        original_policy = reify(candidate.seed.policy)
        reconstructed = [(i, event[1].root) for i, event in enumerate(events, 1)
                         if event[0] == 'source_trajectory_reconstructed']
        _require(bool(reconstructed), 'missing_reconstruction')
        first = reconstructed[0][1]
        if request['operation'] == 'source-advance':
            _require(len(reconstructed) == 1, 'unexpected_reconstruction')
            end = T(F(request['end']['numerator'], request['end']['denominator']))
            step_sizes = SourceOrdinaryStepSizes(**request['step_sizes'])
        else:
            step_record = first['step_sizes']
            _require(type(step_record) is _Passive and step_record.kind ==
                     'sludge_sandbox.source_trajectory.SourceOrdinaryStepSizes', 'saved_step_sizes')
            step_sizes = SourceOrdinaryStepSizes(**step_record.values)
            end = first['end']
        policy = step_sizes.apply(original_policy)
        _require(type(end) is T and start < end, 'end_time')
        provenance = first['adapter_provenance']
        _shape(provenance, 'schema operator_identity energy_model_identity species_ids fixed_dry_mass_kg '
               'local_source_meaning total_energy_meaning source_column material_qualified scope', 'provenance_fields')
        context = SourceObservationContext(candidate.terminal.dry_adapter.identity,
            initial.energy_model_identity, provenance['fixed_dry_mass_kg'], candidate.terminal.dry_adapter.modes)
        contexts = [c for c in record.contexts if c.operator_identity == context.operator_identity]
        _require(contexts and all(c.fixed_dry_mass_kg == context.fixed_dry_mass_kg and
                 c.energy_identity == context.energy_identity and c.interface_modes == context.interface_modes
                 for c in contexts), 'parent_source_context')
        _require(provenance['schema'] == 'exact_source_column_v1' and
                 provenance['operator_identity'] == context.operator_identity and
                 provenance['energy_model_identity'] == context.energy_identity and
                 provenance['material_qualified'] is False and
                 provenance['local_source_meaning'] == 'liquid-to-vapor phase transfer; no chemical reaction' and
                 provenance['total_energy_meaning'] == 'source dry sensible energy plus liquid/gas internal energy' and
                 provenance['scope'] == 'fixed dry composition; no mechanical-driver or depletion-projection admission' and
                 provenance['species_ids'] == ('liquid_water', 'O2', 'N2', 'H2O'), 'source_provenance')
        expected = dict(parent_study_sha256=record.sha256, runtime=summary['runtime_before'],
            original_counts=summary['counts'], original_elapsed_wall_seconds=summary['elapsed_wall_seconds'],
            selected_candidate_index=1, start=start, end=end,
            scope='new_ordinary_segment_not_historical_controller_resume')
        for _, item in reconstructed:
            _require(all(_same(item[key], value) for key, value in expected.items()), 'reconstructed_problem')
            _require(_same(_materialize(item['original_reference_policy']), original_policy) and
                     _same(_materialize(item['ordinary_policy']), policy) and
                     type(item['step_sizes']) is _Passive and item['step_sizes'].values ==
                     {f.name:getattr(step_sizes, f.name) for f in fields(step_sizes)} and
                     _same(item['adapter_provenance'], provenance), 'reconstructed_policy_source')
        terminal = events[-1][1].root.values
        _require(terminal['status'] == 'completed' and terminal['reason'] is None and
                 terminal['parent_study_sha256'] == record.sha256 and type(terminal['selected_candidate_index']) is int and
                 terminal['selected_candidate_index'] == 1 and terminal['managed_execution'] is True and
                 all(terminal[k] is False for k in ('material_qualified', 'full_firing_cycle', 'archived_resume_authorized'))
                 and terminal['qualification'] == SourceTrajectoryResult.__dataclass_fields__['qualification'].default,
                 'terminal_scope')
        result, observations = _numerical(terminal['execution'], initial, start, end, policy)
        _audit_events(events, observations, context, summary['counts'])
        counts = _count_events(events, summary['counts'])
        _require(type(terminal['counts']) is tuple and terminal['counts'] == tuple(sorted(counts.items())) and
                 outcome['counts'] == counts and outcome['details']['accepted_steps'] == len(result.steps) and
                 outcome['details']['observations'] == len(observations) and
                 outcome['details']['parent_study_sha256'] == record.sha256, 'outcome_correspondence')
        balances = _audit_trajectory_balance(record, 1, result, initial, start, original_policy)
        _require(_same(_materialize(terminal['balances']), balances), 'full_chain_balances')
        config = load_source_run_config(_read(Path(parent_directory) / 'case.json', 1024 * 1024))
        limits = config.values['resources']
        _require(_nonnegative(terminal['cumulative_outer_seconds']) and
                 F(terminal['cumulative_outer_seconds']) >= F(summary['elapsed_wall_seconds']) + F(result.elapsed_seconds) and
                 terminal['cumulative_outer_seconds'] < limits['outer_seconds'] and
                 counts['rhs_started'] <= limits['total_callback_cap'] and counts['wet_started'] <= limits['wet_pressure_request_cap'],
                 'original_cumulative_limits')
        prefix_count, saved_debit, new_steps = 0, None, len(result.steps)
        if input_checkpoint is not None:
            packet, prefix_count, saved_debit = _resume(input_checkpoint, trajectory_directory, events,
                record, result, observations, reconstructed)
            _require(packet.checkpoint.problem.end_s == end and _same(packet.checkpoint.problem.policy, policy),
                     'saved_problem_binding')
            new_steps -= len(packet.checkpoint.result.steps)
        _require(type(request['pause_after_steps']) is int and request['pause_after_steps'] >= 0 and
                 (request['pause_after_steps'] == 0 or new_steps <= request['pause_after_steps']),
                 'requested_pause_steps')
        return dict(validation_scope=SCOPE, reported_status='completed', parent_study_sha256=record.sha256,
            accepted_steps=len(result.steps), new_accepted_steps=new_steps, observations=len(observations), lineage_counts=counts,
            journal_events=len(events), journal_bytes=sum(e[3] for e in events),
            event_sha256={f'{i:06d}.json':e[2] for i,e in enumerate(events,1)},
            preserved_prefix_events=prefix_count, saved_charged_segment_seconds=saved_debit,
            cumulative_outer_seconds=terminal['cumulative_outer_seconds'],
            controller_observation_roles=[dict(ordinal=o.ordinal, attempt_index=o.attempt_index, role=o.role)
                                          for o in observations],
            exact_start={'numerator':str(start.seconds.numerator),'denominator':str(start.seconds.denominator)},
            exact_end={'numerator':str(end.seconds.numerator),'denominator':str(end.seconds.denominator)},
            new_eos_calls=0, new_physical_integration=False, controller_arithmetic_replay=False,
            material_qualified=False, full_firing_cycle=False, training_eligible=False,
            restore_available=False, source_authentication=False)
    except (OSError, KeyError, TypeError, AttributeError, OverflowError, RecursionError) as exc:
        raise ValueError('source_terminal_invalid_or_unsupported:' + type(exc).__name__ + ':' + str(exc)) from exc
