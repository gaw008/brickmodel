"""Local single-use ordinary source checkpoints, with real reconstruction.

This record preserves a managed directory's integrity and measured cost. It is
not source authentication, a historical study-controller resume or a portable
provider object. Offline waiting is diagnostic; existing charged work is kept.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import time

from .exact_integration_checkpoint import ExactCheckpointRun, _same as numeric_same
from .exact_integration_checkpoint_codec import encode_exact_checkpoint, decode_exact_checkpoint
from .run_service import read_run_with_source_record, runtime_identity
from .source_observation_schema import strict_json
from .source_record_io import read_record_bytes, publish_record_bytes
from .source_run_journal import raw_projection
from .source_run_config import load_source_run_config, validate_source_run_assets
from .source_study_record import encode_source_study, decode_source_study, _snapshot
from .source_study_schema import reify
from .source_trajectory import (SourceTrajectorySession, SourceTrajectoryResult,
    SourceOrdinaryStepSizes, _upper_float, _audit_trajectory_balance, _open_source_trajectory)

SCHEMA = 'source_trajectory_checkpoint_v1'
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TREE_BYTES = 1024 * 1024 * 1024
MAX_FILES = 10000
FINALIZATION_ALLOWANCE_SECONDS = 1.
CLAIM = '.restore-attempt'
FINALIZING = 'FINALIZING.json'
_META = set(('schema status parent_study_sha256 parent_counts parent_elapsed_seconds counts '
    'constructor_counts operator_identity energy_identity interface_modes fixed_dry_mass_kg '
    'reference_policy step_sizes balances managed_execution managed_audits runtime '
    'last_result_cumulative_outer_seconds last_result_journal_events last_result_reason '
    'offline_history journal_count journal_bytes historical_object_identity_scope').split())
_ENVELOPE = {'schema', 'status', 'source_resume_authorized', 'historical_study_resume_authorized',
    'material_qualified', 'full_firing_cycle', 'charged_segment_seconds_hex',
    'suspended_wall_time_ns', 'finalization_allowance_seconds_hex'}


class SourceTrajectoryRecordError(ValueError):
    """Incomplete, inconsistent, already-consumed or out-of-budget evidence."""


def _require(ok, reason):
    if not ok:
        raise SourceTrajectoryRecordError('source_trajectory_record_' + reason)


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, limit=MAX_FILE_BYTES):
    return read_record_bytes(path, limit, size_reason='source_trajectory_record_byte_limit',
                             regular_reason='source_trajectory_record_regular_file')


def _publish(path, raw):
    publish_record_bytes(path, raw, temporary_prefix='.trajectory-')


def _json(path, value):
    _publish(path, json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def _files(directory, *, allow_claim=False):
    result, size = {}, 0
    _require(directory.is_dir() and not directory.is_symlink(), 'regular_directory')
    for path in sorted(directory.rglob('*')):
        name = path.relative_to(directory).as_posix()
        if allow_claim and name.split('/')[0] == CLAIM:
            continue
        _require(not path.is_symlink(), 'symlink_forbidden')
        if path.is_dir():
            continue
        raw = _read(path)
        size += len(raw)
        _require(size <= MAX_TREE_BYTES and len(result) < MAX_FILES, 'tree_limit')
        result[name] = (_hash(raw), len(raw))
    return result


def _copy_tree(source, destination, expected):
    destination.mkdir(parents=True, exist_ok=False)
    for name, (digest, size) in expected.items():
        relative = PurePosixPath(name)
        _require(not relative.is_absolute() and '..' not in relative.parts and
                 str(relative) == name and '\\' not in name, 'relative_file_path')
        path = source / name
        _require(not path.is_symlink() and path.resolve().is_relative_to(source.resolve()), 'copy_path')
        raw = _read(path)
        _require(len(raw) == size and _hash(raw) == digest, 'changed_during_copy:' + name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        _publish(target, raw)


def _raw_value(graph, value, active=None, depth=0):
    """Expand a saved raw node for bounded field comparison, never import types."""
    _require(depth <= 96, 'raw_depth')
    if type(value) is dict and set(value) == {'ref'}:
        active = set() if active is None else active
        key = value['ref']
        _require(key not in active and key in graph['nodes'], 'raw_reference')
        active = active | {key}
        return _raw_value(graph, graph['nodes'][key], active, depth + 1)
    if type(value) is dict:
        return {k: _raw_value(graph, v, active, depth + 1) for k, v in value.items()}
    if type(value) is list:
        return [_raw_value(graph, v, active, depth + 1) for v in value]
    return value


def _raw_expected(value):
    graph = raw_projection(value)
    return _raw_value(graph, graph['root'])


def _owned_audit(value):
    """Restore only the original JSON-like audit containers, never live objects."""
    if isinstance(value, Mapping):
        return {key: _owned_audit(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_owned_audit(item) for item in value]
    _require(value is None or type(value) in (str, int, bool, float), 'audit_json_value')
    return value


def _journal(directory, expected_count, expected_bytes):
    entries, total = {}, 0
    paths = sorted((directory / 'events').glob('*.json'))
    _require(type(expected_count) is int and len(paths) == expected_count, 'journal_count')
    for index, path in enumerate(paths, 1):
        _require(path.name == f'{index:06d}.json', 'journal_order')
        raw = _read(path); total += len(raw)
        event = strict_json(raw)
        _require(type(event) is dict and set(event) == {'event', 'ordinal', 'payload'} and
                 type(event['ordinal']) is int and event['ordinal'] == index, 'journal_event')
        entries['events/' + path.name] = (event, _hash(raw))
    _require(type(expected_bytes) is int and total == expected_bytes, 'journal_bytes')
    return entries


def _event(entries, reference, name):
    _require(isinstance(reference, Mapping) and set(reference) == {'path', 'sha256'} and
             reference['path'] in entries, 'capture_event_reference')
    event, digest = entries[reference['path']]
    _require(event['event'] == name and digest == reference['sha256'], 'capture_event_binding')
    graph = event['payload']
    root = graph['nodes'][graph['root']['ref']]
    return graph, root['fields']


def _event_input(graph, fields, state, when, capture, meta):
    _require(_raw_value(graph, fields['state']) == _raw_expected(state) and
             _raw_value(graph, fields['time']) == _raw_expected(when) and
             fields['phase'] == capture['phase'], 'journal_callback_input')
    live = _raw_value(graph, fields['adapter'])
    _require(live.get('live_reference_only') is True and
             live.get('identity') == _raw_expected(meta['operator_identity']) and
             live.get('modes') == _raw_expected(meta['interface_modes']), 'journal_callback_operator')


def _audit_observations(checkpoint, observations, entries, meta):
    _require(len(checkpoint.observations) == len(observations.captures), 'source_callback_count')
    references = []
    for ordinal, (original, capture, validated) in enumerate(zip(
            checkpoint.observations, observations.captures, observations.observations), 1):
        state = reify(capture['packed_input'])
        _require(capture['ordinal'] == ordinal and numeric_same(state, original.state) and
                 capture['time'] == original.time and
                 capture['operator_identity'] == meta['operator_identity'] and
                 capture['energy_identity'] == meta['energy_identity'] and
                 capture['interface_modes'] == meta['interface_modes'], 'source_callback_input')
        graph, fields = _event(entries, capture['started_event'], 'rhs_started')
        references.append(capture['started_event']['path'])
        _event_input(graph, fields, state, original.time, capture, meta)
        if original.validated:
            _require(validated is not None and capture.get('failure') is None and
                     numeric_same(validated.sample.evaluation.rates, original.rates), 'source_callback_rates')
            graph, fields = _event(entries, capture['returned_event'], 'rhs_returned')
            _event_input(graph, fields, state, original.time, capture, meta)
            references.append(capture['returned_event']['path'])
            _require(_raw_value(graph, fields['evaluation']) ==
                     _raw_expected(validated.sample.evaluation), 'journal_callback_return')
        else:
            _require(original.failure_kind == 'DomainExit' and original.rates is None and
                     validated is None and capture.get('evaluation') is None and
                     capture.get('failure_kind') == original.failure_kind and
                     capture.get('failure') == original.failure_message, 'source_callback_failure')
            graph, fields = _event(entries, capture['failed_event'], 'rhs_failed')
            _event_input(graph, fields, state, original.time, capture, meta)
            references.append(capture['failed_event']['path'])
            failure = _raw_value(graph, fields['exception'])
            _require(failure['type'].rsplit('.', 1)[-1] == original.failure_kind and
                     failure['message'] == original.failure_message, 'journal_callback_failure')
    actual = [path for path, (e, _) in entries.items() if e['event'] in ('rhs_started', 'rhs_returned', 'rhs_failed')]
    _require(references == actual, 'source_callback_journal_order')
    parent, counts = meta['parent_counts'], meta['counts']
    _require(set(counts) == set(parent) and all(type(v) is int and v >= 0 for v in counts.values()), 'counter_types')
    for key, old in parent.items():
        _require(type(old) is int and counts[key] == old + sum(e['event'] == key for e, _ in entries.values()),
                 'actual_cumulative_count:' + key)


def _audit_controller(checkpoint, last, entries, meta, step_sizes):
    """Bind the controller to the original request and actual published return."""
    expected = dict(parent_study_sha256=meta['parent_study_sha256'],
        runtime=runtime_identity(), original_counts=dict(meta['parent_counts']),
        original_elapsed_wall_seconds=meta['parent_elapsed_seconds'], selected_candidate_index=1,
        start=checkpoint.problem.start_s, end=checkpoint.problem.end_s,
        original_reference_policy=reify(meta['reference_policy']),
        ordinary_policy=checkpoint.problem.policy, step_sizes=step_sizes)
    reconstructed = [event for event, _ in entries.values()
                     if event['event'] == 'source_trajectory_reconstructed']
    _require(bool(reconstructed), 'original_reconstruction_missing')
    for event in reconstructed:
        graph = event['payload']
        fields = _raw_value(graph, graph['root'])['fields']
        _require(all(fields.get(key) == _raw_expected(value) for key, value in expected.items()),
                 'original_reconstructed_problem')
        provenance = fields['adapter_provenance']['fields']
        _require(all(provenance[key] == _raw_expected(meta[key]) for key in
                     ('operator_identity', 'fixed_dry_mass_kg')) and
                 provenance['energy_model_identity'] == _raw_expected(meta['energy_identity']),
                 'original_reconstructed_source')
    _require(type(last.journal_events) is int and last.journal_events + 1 == len(entries),
             'last_return_journal_boundary')
    event = entries[f'events/{last.journal_events + 1:06d}.json'][0]
    _require(event['event'] == 'ordinary_segment_returned' and
             _raw_value(event['payload'], event['payload']['root']) == _raw_expected(last),
             'actual_ordinary_return')


@dataclass
class SourceTrajectoryCheckpointRecord:
    directory: Path
    envelope: dict
    files: dict
    checkpoint: object
    observations: object
    parent_summary: dict
    parent_record: object
    config: object
    assets: object
    balances: tuple
    last_result: SourceTrajectoryResult
    step_sizes: SourceOrdinaryStepSizes | None
    begin: float = 0.
    offline_history: tuple = ()
    recorder: object = None  # Runtime-only failure retention, never encoded.

    def load_recorder(self, recorder):
        self.recorder = recorder
        meta = self.observations.metadata
        recorder.counts = dict(meta['counts'])
        source = self.directory / 'events'
        wanted = {name.removeprefix('events/'): value for name, value in self.files.items()
                  if name.startswith('events/')}
        # _Recorder made its empty events directory; retain exact old ordinals.
        for name, (digest, size) in wanted.items():
            raw = _read(source / name)
            _require(len(raw) == size and _hash(raw) == digest, 'journal_changed_before_copy')
            _publish(recorder.journal.directory / name, raw)
        recorder.journal.count, recorder.journal.total_bytes = meta['journal_count'], meta['journal_bytes']
        recorder.contexts, recorder.captures = list(self.observations.contexts), list(self.observations.captures)
        recorder.managed_audits = [_owned_audit(item) for item in meta['managed_audits']]


def read_source_trajectory_checkpoint(directory) -> SourceTrajectoryCheckpointRecord:
    """Validate all saved source, journal, controller and balance links, no EOS."""
    directory = Path(directory).absolute()
    _require(not (directory / FINALIZING).exists(), 'unfinished_finalization')
    manifest = strict_json(_read(directory / 'manifest.json', 4 * 1024 * 1024))
    _require(type(manifest) is dict and set(manifest) == {'schema', 'files'} and
             manifest['schema'] == SCHEMA and type(manifest['files']) is dict, 'manifest_schema')
    files = _files(directory, allow_claim=True)
    files.pop('manifest.json', None)
    _require({k: list(v) for k, v in files.items()} == manifest['files'], 'manifest_files')
    _require({'packet.json', 'source-observations.json', 'ordinary-checkpoint.json'} <= set(files), 'required_files')
    envelope = strict_json(_read(directory / 'packet.json', 65536))
    _require(type(envelope) is dict and set(envelope) == _ENVELOPE and envelope['schema'] == SCHEMA and
             envelope['status'] == 'suspended_offline' and envelope['source_resume_authorized'] is True and
             envelope['historical_study_resume_authorized'] is False and
             envelope['material_qualified'] is False and envelope['full_firing_cycle'] is False, 'packet_scope')
    debit = float.fromhex(envelope['charged_segment_seconds_hex'])
    allowance = float.fromhex(envelope['finalization_allowance_seconds_hex'])
    _require(math.isfinite(debit) and debit >= 0 and debit.hex() == envelope['charged_segment_seconds_hex'] and
             allowance == FINALIZATION_ALLOWANCE_SECONDS and type(envelope['suspended_wall_time_ns']) is int,
             'saved_wall_debit')
    summary, _, parent = read_run_with_source_record(directory / 'parent')
    _require(summary['status'] == 'completed' and parent is not None and
             summary['runtime_before'] == summary['runtime_after'] == runtime_identity(), 'parent_runtime')
    config = load_source_run_config(_read(directory / 'parent/case.json', 1024 * 1024))
    from .source_run_config import RESUME_PROFILE
    _require(config.values['profile'] == RESUME_PROFILE, 'explicit_resume_profile')
    assets = validate_source_run_assets(config, assets_root=directory / 'parent/assets')
    _require(assets.sha256 == summary['asset_manifest_sha256'], 'parent_assets')
    checkpoint = decode_exact_checkpoint(_read(directory / 'ordinary-checkpoint.json'))
    observations = decode_source_study(_read(directory / 'source-observations.json'))
    meta = observations.metadata
    _require(not observations.roots and set(meta) == _META and meta['schema'] == SCHEMA and
             meta['status'] == 'paused' and meta['parent_study_sha256'] == parent.sha256 and
             meta['parent_counts'] == summary['counts'] and
             meta['parent_elapsed_seconds'] == summary['elapsed_wall_seconds'] and
             meta['runtime'] == _snapshot(runtime_identity()), 'metadata_parent_binding')
    candidate = parent.roots['transition'].candidates[1]
    _require(parent.roots['transition'].numerical_event_accepted is True and
             parent.roots['transition'].material_qualified is False, 'parent_event')
    original_policy = reify(candidate.seed.policy)
    step_sizes = None if meta['step_sizes'] is None else SourceOrdinaryStepSizes(*meta['step_sizes'])
    expected_policy = original_policy if step_sizes is None else step_sizes.apply(original_policy)
    _require(numeric_same(checkpoint.problem.initial, reify(candidate.reference.states[-1])) and
             checkpoint.problem.start_s == candidate.reference.times_s[-1] and
             numeric_same(checkpoint.problem.policy, expected_policy) and
             numeric_same(reify(meta['reference_policy']), original_policy) and
             checkpoint.problem.breakpoints_s == (), 'original_problem_policy')
    modes, identity = candidate.terminal.dry_adapter.modes, candidate.terminal.dry_adapter.identity
    _require(meta['operator_identity'] == identity and meta['interface_modes'] == modes and
             meta['energy_identity'] == checkpoint.problem.initial.energy_model_identity and
             type(meta['managed_execution']) is bool and
             all(c.operator_identity == identity and c.energy_identity == meta['energy_identity'] and
                 c.interface_modes == modes and c.fixed_dry_mass_kg == meta['fixed_dry_mass_kg']
                 for c in observations.contexts), 'source_identity')
    entries = _journal(directory, meta['journal_count'], meta['journal_bytes'])
    _audit_observations(checkpoint, observations, entries, meta)
    _require(all(a['status'] == 'closed' and a['audit']['closed'] is True and
                 not a['secondary_errors'] and a['primary_error'] is None for a in meta['managed_audits']),
             'clean_closed_leases')
    balances = _audit_trajectory_balance(parent, 1, checkpoint.result, checkpoint.problem.initial,
                                         checkpoint.problem.start_s, original_policy)
    _require(_snapshot(balances) == meta['balances'], 'original_cumulative_balances')
    _require(debit >= checkpoint.result.elapsed_seconds and
             debit + meta['parent_elapsed_seconds'] >= meta['last_result_cumulative_outer_seconds'], 'elapsed_floor')
    _require(tuple(sorted((k, v) for k, v in meta['counts'].items() if not k.startswith('rhs_'))) ==
             meta['constructor_counts'], 'constructor_counts')
    execution = ExactCheckpointRun(checkpoint.result, checkpoint, checkpoint.observations, checkpoint)
    last = SourceTrajectoryResult(execution, balances, tuple(sorted(meta['counts'].items())),
        meta['last_result_cumulative_outer_seconds'], parent.sha256, 1,
        meta['last_result_journal_events'], 'paused', meta['last_result_reason'],
        managed_execution=meta['managed_execution'], managed_audits=tuple(_owned_audit(meta['managed_audits'])))
    _audit_controller(checkpoint, last, entries, meta, step_sizes)
    return SourceTrajectoryCheckpointRecord(directory, envelope, files, checkpoint, observations,
        summary, parent, config, assets, balances, last, step_sizes,
        offline_history=tuple(reify(meta['offline_history'])))


def _close_session(session):
    session.checkpoint, session.closed = None, True
    session._continuation_state = (session.checkpoint, session.last_result, session.closed)


def save_source_trajectory(session: SourceTrajectorySession, output: str | Path) -> dict:
    """Publish one closed local packet and suspend this live session permanently."""
    _require(type(session) is SourceTrajectorySession, 'actual_live_session')
    session._check()
    from .source_run_config import RESUME_PROFILE
    _require(session.built.config.values['profile'] == RESUME_PROFILE, 'explicit_resume_profile')
    last, cp = session.last_result, session.checkpoint
    _require(not session.closed and last is not None and last.status == 'paused' and cp is not None and
             last.execution.checkpoint is cp and session.last_execution is last.execution and
             last.execution.failure is None and session.recorder.stop_status is None and
             not hasattr(session, 'last_failure') and not hasattr(session, 'publication_failure') and
             not session.recorder.undurable_returns and not session.recorder.notification_failures and
             tuple(sorted(session.recorder.counts.items())) == last.counts == session.last_counts,
             'clean_issued_pause_required')
    from . import _heos_rhs_scope as scope
    _require(scope._worker is None and scope._active is None, 'closed_scope_required')
    directory = Path(output).absolute()
    parent = session.parent_directory
    journal = session.recorder.journal
    _require(not directory.resolve().is_relative_to(parent.resolve()) and
             not directory.resolve().is_relative_to(journal.directory.parent.resolve()), 'separate_output')
    directory.mkdir(parents=True, exist_ok=False)
    try:
        _json(directory / FINALIZING, dict(status='unfinished_finalization', resume_authorized=False))
        session.recorder.guard()
        parent_summary, _, original = read_run_with_source_record(parent)
        _require(original.sha256 == session.record.sha256 and parent_summary['counts'] == dict(session.parent_counts),
                 'live_parent_changed')
        metadata = dict(schema=SCHEMA, status='paused', parent_study_sha256=session.record.sha256,
            parent_counts=dict(session.parent_counts), parent_elapsed_seconds=session.parent_elapsed_seconds,
            counts=dict(session.recorder.counts), constructor_counts=session.constructor_counts,
            operator_identity=session.adapter.operator_identity, energy_identity=session.adapter.energy_model_identity,
            interface_modes=session.adapter.interfaces,
            fixed_dry_mass_kg=tuple(s.dry_mass_kg for s in session.built.storages),
            reference_policy=session.reference_policy,
            step_sizes=None if session.step_sizes is None else session.step_sizes.binding(), balances=session.balances,
            managed_execution=session.managed_execution, managed_audits=tuple(session.recorder.managed_audits),
            runtime=session.runtime, last_result_cumulative_outer_seconds=last.cumulative_outer_seconds,
            last_result_journal_events=last.journal_events, last_result_reason=last.reason,
            offline_history=session.offline_history, journal_count=journal.count, journal_bytes=journal.total_bytes,
            historical_object_identity_scope='old_capture_same_object_flags_apply_only_to_original_process')
        _publish(directory / 'ordinary-checkpoint.json', encode_exact_checkpoint(cp))
        source_bytes = encode_source_study({}, contexts=tuple(session.recorder.contexts),
                                           captures=tuple(session.recorder.captures), metadata=metadata)
        _publish(directory / 'source-observations.json', source_bytes)
        _copy_tree(parent, directory / 'parent', _files(parent))
        _copy_tree(journal.directory, directory / 'events', _files(journal.directory))
        saved_observations = decode_source_study(source_bytes)
        entries = _journal(directory, journal.count, journal.total_bytes)
        _audit_observations(cp, saved_observations, entries, saved_observations.metadata)
        _audit_controller(cp, last, entries, saved_observations.metadata, session.step_sizes)
        _require(_snapshot(session._audit(cp.result)) == saved_observations.metadata['balances'],
                 'save_cumulative_balance')
        files = _files(directory)
        files.pop(FINALIZING)
        # Full save/read/replay/copy cost precedes the suspend boundary. A fixed
        # conservative debit covers the bounded final manifest publication tail.
        started = time.monotonic()
        debit = _upper_float(F(started - session.begin) + F(FINALIZATION_ALLOWANCE_SECONDS))
        _require(debit < session.policy.maximum_wall_seconds and
                 F(debit) + F(session.parent_elapsed_seconds) < F(session.recorder.limits['outer_seconds']),
                 'original_wall_budget_exhausted')
        envelope = dict(schema=SCHEMA, status='suspended_offline', source_resume_authorized=True,
            historical_study_resume_authorized=False, material_qualified=False, full_firing_cycle=False,
            charged_segment_seconds_hex=debit.hex(), suspended_wall_time_ns=time.time_ns(),
            finalization_allowance_seconds_hex=FINALIZATION_ALLOWANCE_SECONDS.hex())
        _json(directory / 'packet.json', envelope)
        packet_raw = _read(directory / 'packet.json')
        files['packet.json'] = (_hash(packet_raw), len(packet_raw))
        manifest = {name: list(value) for name, value in files.items()}
        _close_session(session)  # Revoke live authority before publishing the packet.
        _json(directory / 'manifest.json', dict(schema=SCHEMA, files=manifest))
        result = dict(envelope, directory=str(directory), disposition='saved_and_live_session_suspended',
                      counts=dict(session.recorder.counts), checkpoint_sha256=manifest['ordinary-checkpoint.json'][0])
        session.recorder.guard()
        _require(time.monotonic() - started <= FINALIZATION_ALLOWANCE_SECONDS, 'finalization_deadline')
        (directory / FINALIZING).unlink()  # Final publication boundary, never removed on failure.
        return result
    except BaseException as exc:
        _close_session(session)
        (directory / 'manifest.json').unlink(missing_ok=True)
        try:
            _json(directory / 'SAVE_FAILURE.json', dict(status=session.recorder.stop_status or 'failed',
                type=type(exc).__name__, reason=str(exc),
                counts=session.recorder.counts, elapsed_segment_seconds=time.monotonic() - session.begin))
        except BaseException as secondary:
            exc.add_note('source trajectory save failure publication: ' + type(secondary).__name__)
        raise


def restore_source_trajectory(saved_directory: str | Path, output: str | Path, *,
                              cancel=None, managed_execution: bool = False) -> SourceTrajectorySession:
    """Consume one local packet, passively audit, then construct new real providers."""
    from .source_run_service import _managed_request
    _managed_request(managed_execution)
    begin = time.monotonic()
    entry_wall_ns = time.time_ns()
    directory, output = Path(saved_directory).absolute(), Path(output).absolute()
    _require(not output.resolve().is_relative_to(directory.resolve()), 'separate_restore_output')
    output.mkdir(parents=True, exist_ok=False)
    claim = directory / CLAIM
    try:
        claim.mkdir(exist_ok=False)  # Atomic one-use lineage fence, including failures.
    except BaseException:
        raise SourceTrajectoryRecordError('source_trajectory_record_restore_already_claimed_or_missing')
    packet, session = None, None
    try:
        _json(claim / 'started.json', dict(output=str(output), started_wall_time_ns=time.time_ns()))
        packet = read_source_trajectory_checkpoint(directory)
        _require(managed_execution is packet.observations.metadata['managed_execution'], 'execution_mode_changed')
        debit = float.fromhex(packet.envelope['charged_segment_seconds_hex'])
        packet.begin = math.nextafter(begin - debit, -math.inf)
        now_ns, anchor = entry_wall_ns, packet.envelope['suspended_wall_time_ns']
        diagnostic = dict(seconds=None if now_ns < anchor else (now_ns - anchor) / 1e9,
                          status='clock_discontinuity' if now_ns < anchor else 'diagnostic_only_not_charged')
        packet.offline_history = (*packet.offline_history, diagnostic)
        _require(time.monotonic() - packet.begin < packet.checkpoint.problem.policy.maximum_wall_seconds and
                 F(time.monotonic() - packet.begin) + F(packet.parent_summary['elapsed_wall_seconds']) <
                 F(packet.config.values['resources']['outer_seconds']), 'original_wall_budget_exhausted')
        session = _open_source_trajectory(directory / 'parent', output,
            end=packet.checkpoint.problem.end_s, cancel=cancel, step_sizes=packet.step_sizes,
            managed_execution=managed_execution, resume=packet)
        _json(claim / 'restored.json', dict(status='live_session_restored', output=str(output),
            counts=session.recorder.counts, charged_segment_seconds=time.monotonic() - session.begin))
        return session
    except BaseException as exc:
        if session is not None:
            _close_session(session)
            session.publication_failure = exc
        recorder = None if packet is None else packet.recorder
        if recorder is not None:
            try:
                recorder.journal.append('source_trajectory_admission_failed', dict(exception=exc,
                    counts=recorder.counts, execution=None if session is None else session.last_execution,
                    cumulative_outer_seconds=_upper_float(F(packet.parent_summary['elapsed_wall_seconds']) +
                                                          F(time.monotonic() - packet.begin))))
            except BaseException as secondary:
                exc.add_note('source trajectory restore failure journal: ' + type(secondary).__name__)
        try:
            _json(claim / 'failed.json', dict(status='failed_or_unfinished_no_free_retry',
                type=type(exc).__name__, reason=str(exc), new_active_seconds=time.monotonic() - begin,
                counts=None if recorder is None else dict(recorder.counts)))
        except BaseException as secondary:
            exc.add_note('source trajectory restore claim publication: ' + type(secondary).__name__)
        raise
