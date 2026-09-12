"""Bounded application admission and passive inspection of source workers.

This service never launches a worker, constructs an EOS or integrates physics.
Local digests bind original bytes; they are not source authentication. Recorded
worker status, process observation, result validity and restore authority remain
separate. A consumed packet is never repaired or granted another attempt.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time
from typing import Any

from .exact_integration_checkpoint import _same as numeric_same
from .run_service import read_run_with_source_record, runtime_identity
from .source_execution_worker import COUNTERS, _load_request
from .source_record_io import publish_record_bytes
from .source_run_config import (RESUME_PROFILE, exact_config_fraction,
    load_source_run_config, required_source_assets, validate_source_run_assets)
from .source_trajectory_record import read_source_trajectory_checkpoint

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TREE_BYTES = 1024 * 1024 * 1024
MAX_FILES = 10000
MAX_JSON_VALUES = 300000
MAX_TREE_JSON_VALUES = 3000000
MAX_DEPTH = 96
QUALIFICATION = dict(material_qualified=False, training_eligible=False,
    full_firing_cycle=False, historical_study_resume_authorized=False)
_FAILURE_MARKERS = ('WORKER_FAILURE.json', 'SAVE_FAILURE.json', 'FINALIZING.json')
_OUTCOME_FIELDS = set(('schema operation status reason details counts '
    'declared_other_branch_counts combined_counts shared_budget_provenance '
    'raw_case_sha256 canonical_config_sha256 request_sha256 runtime_before '
    'runtime_after process_elapsed_seconds').split()) | set(QUALIFICATION)
_FAILURE_FIELDS = set(('schema status exception_type reason process_elapsed_seconds '
    'operation_status operation_reason counts count_completeness combined_counts '
    'stop_reason secondary_errors').split()) | set(QUALIFICATION)
_BINDING_FIELDS = set(('schema job_directory operation source output cancel_file '
    'assets_root request_sha256 raw_case_sha256 canonical_config_sha256 runtime '
    'input_files asset_manifest_sha256 parent_study_sha256 preparation_seconds').split())


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError('source_execution_service_' + reason)


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _absolute(path: str | Path) -> Path:
    value = Path(path).absolute()
    _require('..' not in value.parts and '\x00' not in str(value), 'canonical_path')
    return value


def _descriptor(path: Path, *, directory: bool = False) -> int:
    """Open every component with no-follow, including ancestors of the file."""
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    current = os.open('/', flags | os.O_DIRECTORY)
    try:
        for index, part in enumerate(path.parts[1:]):
            final = index == len(path.parts) - 2
            child = os.open(part, flags | (os.O_DIRECTORY if directory or not final else 0),
                            dir_fd=current)
            os.close(current)
            current = child
        result, current = current, -1
        return result
    finally:
        if current >= 0:
            os.close(current)


def _directory(path: Path) -> None:
    descriptor = _descriptor(path, directory=True)
    os.close(descriptor)


def _read(path: Path, limit: int = MAX_FILE_BYTES) -> bytes:
    descriptor = _descriptor(path)
    try:
        opened = os.fstat(descriptor)
        _require(stat.S_ISREG(opened.st_mode), 'regular_file:' + path.name)
        _require(0 <= opened.st_size <= limit, 'byte_limit:' + path.name)
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        _require(len(raw) <= limit, 'byte_limit:' + path.name)
        return raw
    finally:
        os.close(descriptor)


def _exists(path: Path) -> bool:
    """A dangling symlink is an existing entry, especially for a restore claim."""
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _decode(raw: bytes) -> tuple[Any, int]:
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('source_execution_service_nonfinite_json')

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            _require(count <= MAX_JSON_VALUES and depth <= MAX_DEPTH, 'json_work_limit')
            if type(item) is dict:
                pending.extend((child, depth + 1) for child in item.values())
            elif type(item) is list:
                pending.extend((child, depth + 1) for child in item)
            elif type(item) is float:
                _require(math.isfinite(item), 'nonfinite_json')
        return value, count
    except (UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError('source_execution_service_invalid_json') from exc


def _json(path: Path, limit: int = 4 * 1024 * 1024) -> tuple[dict, bytes]:
    raw = _read(path, limit)
    value, _ = _decode(raw)
    _require(type(value) is dict, 'json_object:' + path.name)
    return value, raw


def _tree(directory: Path, *, allow_claim: bool = False) -> dict[str, list]:
    """Preflight existing readers with strict paths and aggregate work bounds."""
    _directory(directory)
    result, pending, total, entries, values = {}, [directory], 0, 0, 0
    while pending:
        current = pending.pop()
        _directory(current)
        with os.scandir(current) as children:
            for child in children:
                path = current / child.name
                name = path.relative_to(directory).as_posix()
                if allow_claim and name.split('/')[0] == '.restore-attempt':
                    continue
                entries += 1
                _require(entries <= MAX_FILES, 'tree_file_limit')
                mode = child.stat(follow_symlinks=False).st_mode
                _require(not stat.S_ISLNK(mode), 'tree_symlink:' + name)
                if stat.S_ISDIR(mode):
                    pending.append(path)
                    continue
                _require(stat.S_ISREG(mode), 'tree_regular_file:' + name)
                raw = _read(path)
                total += len(raw)
                _require(total <= MAX_TREE_BYTES, 'tree_byte_limit')
                if path.suffix == '.json':
                    _, used = _decode(raw)
                    values += used
                    _require(values <= MAX_TREE_JSON_VALUES, 'tree_json_work_limit')
                result[name] = [_hash(raw), len(raw)]
    return dict(sorted(result.items()))


def _publish(path: Path, raw: bytes) -> None:
    _directory(path.parent)
    publish_record_bytes(path, raw, temporary_prefix='.source-app-')


def _serial(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'


def _counts(value: Any) -> dict:
    _require(type(value) is dict and set(value) == set(COUNTERS) and
             all(type(v) is int and 0 <= v <= 1000000000 for v in value.values()), 'counts')
    for start, returned in (('heos_started', 'heos_kernel_returned'),
            ('heos_kernel_returned', 'heos_returned'), ('initial_energy_started', 'initial_energy_returned'),
            ('rhs_started', 'rhs_returned'), ('wet_started', 'wet_returned')):
        _require(value[returned] <= value[start], 'counts_order')
    return value


def _false_qualification(value: dict) -> None:
    _require(all(value.get(key) is False for key in QUALIFICATION), 'qualification_changed')


def _finite_time(value: Any) -> None:
    _require(type(value) in (int, float) and value >= 0 and math.isfinite(value), 'elapsed_seconds')


def _path_contract(request: dict, directory: Path, *, fresh: bool) -> None:
    _require(request['output'] == str(directory / 'execution') and
             request['cancel_file'] == str(directory / 'source-cancel'), 'fixed_output_cancel_paths')
    _require(request['shared_budget'] is None, 'external_budget_not_supported')
    source = _absolute(request['source'])
    # A case file can be in the same broad workspace, but the job cannot contain
    # it. Run/packet roots and the source asset root must be wholly disjoint.
    roots = [source if request['operation'] != 'source-run' else None,
             _absolute(request['assets_root']) if request['operation'] == 'source-run' else None]
    _require(not source.is_relative_to(directory), 'source_job_overlap')
    for root in roots:
        if root is not None:
            _require(not directory.is_relative_to(root) and not root.is_relative_to(directory), 'input_job_overlap')
    if fresh:
        _require(all(not _exists(directory / name) for name in
            ('request.json', 'INPUT_BINDING.json', 'execution', 'source-cancel')), 'existing_job_artifact')


def _admit_input(request: dict, runtime: dict) -> dict:
    source, operation = _absolute(request['source']), request['operation']
    case = (source if operation == 'source-run' else
            source / ('parent/case.json' if operation == 'source-resume' else 'case.json'))
    raw = _read(case, 65536)
    config = load_source_run_config(raw)
    _require(config.values['profile'] == RESUME_PROFILE, 'versioned_implementation_required')
    parent_digest = None
    if operation == 'source-run':
        asset_root = _absolute(request['assets_root'])
        _directory(asset_root)
        files = {'case.json': [_hash(raw), len(raw)]}
        for name, size, digest in required_source_assets(config.values['profile']):
            asset = _read(asset_root / name, size)
            _require(len(asset) == size and _hash(asset) == digest, 'source_asset_binding:' + name)
            files['assets/' + name] = [digest, size]
        assets = validate_source_run_assets(config, assets_root=asset_root)
    else:
        files = _tree(source, allow_claim=operation == 'source-resume')
        if operation == 'source-resume':
            _require(not _exists(source / '.restore-attempt'), 'restore_already_claimed')
            packet = _read_checkpoint(source)
            summary, record, assets = packet.parent_summary, packet.parent_record, packet.assets
            _require(packet.observations.metadata['managed_execution'] is True, 'managed_packet_required')
        else:
            summary, _, record = read_run_with_source_record(source)
            _require(record is not None and summary.get('status') == 'completed' and
                summary.get('numerical_event_accepted') is True, 'accepted_parent_required')
            assets = validate_source_run_assets(config, assets_root=source / 'assets')
            _require(assets.sha256 == summary['asset_manifest_sha256'], 'parent_asset_binding')
            _require(exact_config_fraction(request['end']) >
                     record.roots['transition'].candidates[1].reference.times_s[-1].seconds,
                     'end_must_follow_parent')
        _require(summary['runtime_before'] == summary['runtime_after'] == runtime, 'input_runtime_changed')
        _require(summary.get('managed_execution') is True, 'managed_parent_required')
        _require(summary['config_sha256'] == config.sha256, 'input_config_binding')
        parent_digest = record.sha256
        _require(files == _tree(source, allow_claim=operation == 'source-resume'), 'input_changed_during_admission')
    return dict(raw_case_sha256=_hash(raw), canonical_config_sha256=config.sha256,
        input_files=files, asset_manifest_sha256=assets.sha256, parent_study_sha256=parent_digest)


def prepare_source_execution(request_path: str | Path, job_directory: str | Path) -> dict:
    """Admit a fixed worker request without creating its output or running code."""
    begin = time.monotonic()
    try:
        directory = _absolute(job_directory)
        _directory(directory)
        raw = _read(_absolute(request_path), 65536)
        _decode(raw)
        request = _load_request(raw)
        _path_contract(request, directory, fresh=True)
        runtime = runtime_identity()
        admitted = _admit_input(request, runtime)
        _require(runtime_identity() == runtime, 'runtime_changed_during_admission')
        binding = dict(schema='source_execution_input_binding_v1', job_directory=str(directory),
            operation=request['operation'], source=request['source'], output=request['output'],
            cancel_file=request['cancel_file'], assets_root=request.get('assets_root'),
            request_sha256=_hash(raw), runtime=runtime, **admitted,
            preparation_seconds=time.monotonic() - begin)
        _publish(directory / 'request.json', raw)
        _publish(directory / 'INPUT_BINDING.json', _serial(binding))
        return binding
    except OSError as exc:
        raise ValueError('source_execution_service_input_unavailable:' + str(exc)) from exc


def _read_checkpoint(directory: Path):
    _directory(directory)
    _require(not any(_exists(directory / name) for name in _FAILURE_MARKERS), 'checkpoint_failure_marker')
    snapshot = _tree(directory, allow_claim=True)
    packet = read_source_trajectory_checkpoint(directory)
    _require(snapshot == _tree(directory, allow_claim=True), 'checkpoint_changed_during_validation')
    return packet


def _clock(value) -> dict:
    number = value.seconds
    return dict(numerator=str(number.numerator), denominator=str(number.denominator))


def inspect_source_checkpoint(packet_directory: str | Path) -> dict:
    """Passively distinguish a valid checkpoint from an unused local capability."""
    result = dict(schema='source_checkpoint_inspection_v1', record_valid=False,
        restore_available=False, qualification=dict(QUALIFICATION), new_eos_calls=0,
        new_physical_integration=False, validation_scope='unverified_source_checkpoint')
    try:
        directory = _absolute(packet_directory)
        packet = _read_checkpoint(directory)
        claimed = _exists(directory / '.restore-attempt')
        result.update(record_valid=True, restore_available=not claimed,
            restore_disposition='already_claimed_no_retry' if claimed else 'valid_local_unclaimed_packet',
            validation_scope='existing_source_checkpoint_controller_observation_balance_and_asset_checks',
            parent_study_sha256=packet.parent_record.sha256, counts=dict(packet.last_result.counts),
            accepted_steps=len(packet.last_result.execution.result.steps),
            observations=len(packet.last_result.execution.observations),
            exact_start=_clock(packet.checkpoint.problem.start_s),
            exact_end=_clock(packet.checkpoint.problem.end_s),
            charged_segment_seconds_hex=packet.envelope['charged_segment_seconds_hex'],
            packet_sha256=_hash(_read(directory / 'packet.json', 65536)),
            manifest_sha256=_hash(_read(directory / 'manifest.json', 4 * 1024 * 1024)),
            authority_scope='one local claim entry; copied directories are not globally authenticated')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        result['verification_error'] = str(exc)
    return result


def _load_binding(directory: Path) -> tuple[dict, dict, bytes]:
    binding, _ = _json(directory / 'INPUT_BINDING.json')
    _require(set(binding) == _BINDING_FIELDS and
             binding['schema'] == 'source_execution_input_binding_v1', 'input_binding_schema')
    raw = _read(directory / 'request.json', 65536)
    request = _load_request(raw)
    admitted_directory = _absolute(binding['job_directory'])
    _path_contract(request, admitted_directory, fresh=False)
    _require(binding['request_sha256'] == _hash(raw) and
        all(binding[key] == request[key] for key in ('operation', 'source', 'output', 'cancel_file')) and
        binding['assets_root'] == request.get('assets_root'), 'request_input_binding')
    _require(type(binding['runtime']) is dict and type(binding['input_files']) is dict and
             bool(binding['input_files']), 'input_binding_values')
    for name, value in binding['input_files'].items():
        _require(type(name) is str and not Path(name).is_absolute() and
            '..' not in Path(name).parts and '\\' not in name and type(value) is list and len(value) == 2 and
            type(value[0]) is str and len(value[0]) == 64 and type(value[1]) is int and value[1] >= 0,
            'input_file_binding')
    _finite_time(binding['preparation_seconds'])
    return binding, request, raw


def _process(directory: Path, binding: dict, returncode, cause) -> dict:
    provenance = 'caller_observed_reaped_process' if returncode is not None else 'unknown'
    if returncode is None and _exists(directory / 'job.json'):
        saved, _ = _json(directory / 'job.json')
        _require(saved.get('schema') == 'sandbox_job_v1' and saved.get('operation') == 'source-execute' and
                 saved.get('input_binding') == binding, 'persisted_job_binding')
        if saved.get('child_reaped') is True and type(saved.get('returncode')) is int:
            returncode = saved['returncode']
            if cause is None:
                cause = saved.get('termination_cause')
            provenance = 'persisted_not_live_process_proof'
    _require(returncode is None or type(returncode) is int, 'returncode')
    _require(cause is None or cause in ('user_cancel', 'wall_timeout'), 'termination_cause')
    return dict(returncode=returncode, termination_cause=cause, provenance=provenance,
        zero_exit_observed=returncode == 0, live_pid_checked=False)


def _validate_outcome(outcome: dict, request: dict, binding: dict) -> None:
    _require(set(outcome) == _OUTCOME_FIELDS and outcome['schema'] == 'source_execution_outcome_v1',
             'outcome_schema')
    _require(outcome['operation'] == request['operation'] and
        outcome['status'] in ('completed', 'paused') and
        (outcome['reason'] is None or type(outcome['reason']) is str), 'outcome_status')
    _false_qualification(outcome)
    _finite_time(outcome['process_elapsed_seconds'])
    _counts(outcome['counts'])
    _counts(outcome['combined_counts'])
    _require(_counts(outcome['declared_other_branch_counts']) == dict.fromkeys(COUNTERS, 0) and
        outcome['combined_counts'] == outcome['counts'], 'combined_counts')
    _require(outcome['shared_budget_provenance'] == 'caller_declared_external_debits_not_authenticated',
             'shared_budget_provenance')
    for report_key, binding_key in (('request_sha256', 'request_sha256'),
            ('raw_case_sha256', 'raw_case_sha256'), ('canonical_config_sha256', 'canonical_config_sha256')):
        _require(outcome[report_key] == binding[binding_key], report_key + '_binding')
    _require(outcome['runtime_before'] == outcome['runtime_after'] == binding['runtime'], 'outcome_runtime')
    details = outcome['details']
    _require(type(details) is dict, 'outcome_details')
    if request['operation'] == 'source-run':
        _require(outcome['status'] == 'completed' and
            set(details) == {'source_run_directory', 'numerical_event_accepted'} and
            details['source_run_directory'] == str(Path(request['output']) / 'run') and
            type(details['numerical_event_accepted']) is bool, 'source_run_details')
    else:
        expected = {'trajectory_directory', 'parent_study_sha256', 'accepted_steps', 'observations'}
        if outcome['status'] == 'paused':
            _require(request['pause_after_steps'] > 0, 'unrequested_pause')
            expected.add('saved_checkpoint')
        _require(set(details) == expected and
            details['trajectory_directory'] == str(Path(request['output']) / 'trajectory') and
            details['parent_study_sha256'] == binding['parent_study_sha256'] and
            all(type(details[k]) is int and 0 <= details[k] <= 1000000
                for k in ('accepted_steps', 'observations')), 'trajectory_details')


def _validate_failure(failure: dict) -> None:
    _require(set(failure) == _FAILURE_FIELDS and failure['schema'] == 'source_execution_failure_v1' and
        failure['status'] in ('failed', 'cancelled', 'resource_limit', 'domain_exit'), 'failure_schema')
    _false_qualification(failure)
    _finite_time(failure['process_elapsed_seconds'])
    _require(all(type(failure[key]) is str for key in ('exception_type', 'reason')) and
        all(failure[key] is None or type(failure[key]) is str
            for key in ('operation_status', 'operation_reason', 'stop_reason')), 'failure_values')
    if failure['counts'] is None:
        _require(failure['combined_counts'] is None and failure['count_completeness'] == 'unknown',
                 'failure_unknown_counts')
    else:
        _require(_counts(failure['counts']) == _counts(failure['combined_counts']) and
            failure['count_completeness'] == 'complete_observed_counts', 'failure_counts')
    errors = failure['secondary_errors']
    _require(type(errors) is list and all(type(row) is dict and
        set(row) == {'stage', 'exception_type', 'reason'} and
        all(type(value) is str for value in row.values()) for row in errors), 'failure_secondary_errors')


def _verify_run(directory: Path, binding: dict, outcome: dict) -> dict:
    before = _tree(directory)
    summary, manifest, record = read_run_with_source_record(directory)
    _require(before == _tree(directory), 'run_changed_during_validation')
    _require(record is not None and summary['status'] == outcome['status'] and
        summary.get('reason') == outcome['reason'] and summary['counts'] == outcome['counts'] and
        summary['runtime_before'] == summary['runtime_after'] == binding['runtime'] and
        summary['config_sha256'] == binding['canonical_config_sha256'] and
        summary.get('managed_execution') is True and
        summary.get('asset_manifest_sha256') == binding['asset_manifest_sha256'] and
        summary['numerical_event_accepted'] is outcome['details']['numerical_event_accepted'] and
        manifest['files']['case.json'] == binding['raw_case_sha256'] and
        manifest['files']['config.json'] == binding['canonical_config_sha256'], 'source_run_correspondence')
    for name, expected in binding['input_files'].items():
        _require(before.get(name) == expected, 'run_input_file_binding:' + name)
    return dict(validation_scope='existing_source_run_manifest_and_source_record_correspondence_checked',
        numerical_event_accepted=summary['numerical_event_accepted'], restore_available=False,
        artifact_bindings=dict(parent_study_sha256=record.sha256,
            manifest_sha256=_hash(_read(directory / 'manifest.json')), result_sha256=manifest['files']['result.json']))


def _bound_parent(directory: Path, binding: dict, request: dict) -> Path:
    # Do not follow an old absolute source path merely because it survived inside
    # a moved archive. This first adapter has no external rebinding authority.
    _require(str(directory) == binding['job_directory'], 'moved_job_requires_explicit_input_rebinding')
    source = _absolute(request['source'])
    _require(_tree(source, allow_claim=request['operation'] == 'source-resume') == binding['input_files'],
             'original_input_changed')
    return source if request['operation'] == 'source-advance' else source / 'parent'


def _verify_paused(directory: Path, binding: dict, request: dict, outcome: dict) -> dict:
    packet_path = directory / 'execution/resume-point'
    packet = _read_checkpoint(packet_path)
    last = packet.last_result
    details = outcome['details']
    saved = dict(packet.envelope, directory=str(Path(request['output']) / 'resume-point'),
        disposition='saved_and_live_session_suspended', counts=dict(last.counts),
        checkpoint_sha256=packet.files['ordinary-checkpoint.json'][0])
    _require(details['saved_checkpoint'] == saved and outcome['counts'] == dict(last.counts) and
        outcome['reason'] == last.reason and details['parent_study_sha256'] == packet.parent_record.sha256 and
        details['accepted_steps'] == len(last.execution.result.steps) and
        details['observations'] == len(last.execution.observations), 'paused_report_correspondence')
    events = _tree(directory / 'execution/trajectory/events')
    _require(events == _tree(packet_path / 'events'), 'paused_journal_correspondence')
    if request['operation'] == 'source-advance':
        _require(type(request['pause_after_steps']) is int and request['pause_after_steps'] > 0 and
            len(last.execution.result.steps) == request['pause_after_steps'], 'paused_requested_step_count')
        _require(_tree(packet_path / 'parent') == binding['input_files'], 'paused_original_parent_binding')
        _require(packet.checkpoint.problem.end_s.seconds == exact_config_fraction(request['end']),
                 'paused_requested_end')
        _require(packet.step_sizes is not None and
            packet.step_sizes.binding() == (request['step_sizes']['initial_step_s'],
                request['step_sizes']['maximum_step_s'], request['step_sizes']['rationale'],
                'numerical_policy'), 'paused_requested_steps')
    else:
        _bound_parent(directory, binding, request)
        source = _absolute(request['source'])
        original = _read_checkpoint(source)
        _require(type(request['pause_after_steps']) is int and request['pause_after_steps'] > 0 and
            len(last.execution.result.steps) - len(original.last_result.execution.result.steps) ==
            request['pause_after_steps'], 'paused_requested_new_step_count')
        _require(numeric_same(packet.checkpoint.problem, original.checkpoint.problem) and
            _tree(packet_path / 'parent') == _tree(source / 'parent'), 'paused_resume_original_problem')
        for name, evidence in _tree(source / 'events').items():
            _require(events.get(name) == evidence, 'paused_resume_event_prefix')
        _verify_paused_claim(source, request, original, packet)
    return dict(validation_scope='existing_source_checkpoint_plus_worker_request_and_journal_correspondence_checked',
        restore_available=not _exists(packet_path / '.restore-attempt'),
        artifact_bindings=dict(parent_study_sha256=packet.parent_record.sha256,
            packet_sha256=_hash(_read(packet_path / 'packet.json', 65536)),
            manifest_sha256=_hash(_read(packet_path / 'manifest.json'))))


def _verify_restore_claim(source: Path, request: dict) -> dict:
    claim = source / '.restore-attempt'
    _directory(claim)
    _require(not _exists(claim / 'failed.json'), 'restore_claim_failed')
    started, _ = _json(claim / 'started.json', 65536)
    restored, _ = _json(claim / 'restored.json', 65536)
    target = str(Path(request['output']) / 'trajectory')
    _require(set(started) == {'output', 'started_wall_time_ns'} and started['output'] == target and
        type(started['started_wall_time_ns']) is int and
        set(restored) == {'status', 'output', 'counts', 'charged_segment_seconds'} and
        restored['status'] == 'live_session_restored' and restored['output'] == target, 'restore_claim_binding')
    _counts(restored['counts'])
    _finite_time(restored['charged_segment_seconds'])
    return restored


def _verify_paused_claim(source: Path, request: dict, original, saved) -> None:
    """Bind restoration cost to the copied prefix and actual reconstruction."""
    restored = _verify_restore_claim(source, request)
    counts = dict(original.last_result.counts)
    old_events = _tree(source / 'events')
    current_directory = Path(request['output']) / 'trajectory/events'
    current_events = _tree(current_directory)
    _require(old_events.keys() <= current_events.keys(), 'restore_claim_missing_prefix')
    reconstructed = False
    for name in current_events:
        if name in old_events:
            _require(current_events[name] == old_events[name], 'restore_claim_original_prefix')
            continue
        event, _ = _json(current_directory / name, MAX_FILE_BYTES)
        if event['event'] == 'source_trajectory_reconstructed':
            reconstructed = True
            break
        if event['event'] in COUNTERS:
            counts[event['event']] += 1
    _require(reconstructed and counts == restored['counts'], 'restore_claim_reconstruction_counts')
    old_charge = float.fromhex(original.envelope['charged_segment_seconds_hex'])
    new_charge = float.fromhex(saved.envelope['charged_segment_seconds_hex'])
    _require(old_charge <= restored['charged_segment_seconds'] <= new_charge,
             'restore_claim_saved_charge')


def inspect_source_execution(job_directory: str | Path, *, returncode: int | None = None,
                             termination_cause: str | None = None) -> dict:
    """Inspect original reports and bound artifacts, without launch or restoration."""
    _require(returncode is None or type(returncode) is int, 'returncode')
    _require(termination_cause is None or termination_cause in ('user_cancel', 'wall_timeout'),
             'termination_cause')
    result = dict(schema='source_execution_inspection_v1', status='unverified_result',
        reported_status=None, record_valid=False, restore_available=False,
        validation_scope='unverified_source_execution', artifact_bindings={},
        qualification=dict(QUALIFICATION), new_eos_calls=0, new_physical_integration=False,
        process_observation=dict(returncode=returncode, termination_cause=termination_cause,
            provenance='caller_observed_reaped_process' if returncode is not None else 'unknown',
            zero_exit_observed=returncode == 0, live_pid_checked=False))
    try:
        directory = _absolute(job_directory)
        binding, request, raw = _load_binding(directory)
        observation = _process(directory, binding, returncode, termination_cause)
        result.update(operation=request['operation'], process_observation=observation)
        output = directory / 'execution'
        _require(_read(output / 'request.json', 65536) == raw, 'worker_request_bytes_changed')
        outcome_exists, failure_exists = _exists(output / 'OUTCOME.json'), _exists(output / 'FAILURE.json')
        result['terminal_files'] = dict(outcome=outcome_exists, failure=failure_exists)
        if outcome_exists and failure_exists:
            # Keep both reported facts even though their publication conflicts.
            result['outcome'], _ = _json(output / 'OUTCOME.json')
            result['failure'], _ = _json(output / 'FAILURE.json')
            result['reported_status'] = result['outcome'].get('status')
        _require(outcome_exists != failure_exists,
                 'conflicting_terminal_publication' if outcome_exists else 'missing_terminal_publication')
        if failure_exists:
            failure, failure_raw = _json(output / 'FAILURE.json')
            result.update(reported_status=failure.get('status'), failure=failure)
            _validate_failure(failure)
            result.update(record_valid=True, status='run_failed',
                validation_scope='worker_failure_schema_and_exact_request_binding_checked',
                artifact_bindings=dict(request_sha256=_hash(raw), failure_sha256=_hash(failure_raw)),
                run_reason=failure['reason'])
            if failure['status'] in ('cancelled', 'resource_limit'):
                result['status'] = failure['status']
        else:
            outcome, outcome_raw = _json(output / 'OUTCOME.json')
            result.update(reported_status=outcome.get('status'), outcome=outcome)
            _validate_outcome(outcome, request, binding)
            if request['operation'] == 'source-run':
                checked = _verify_run(output / 'run', binding, outcome)
            elif outcome['status'] == 'paused':
                checked = _verify_paused(directory, binding, request, outcome)
            else:
                from .source_terminal_record import inspect_source_terminal
                parent = _bound_parent(directory, binding, request)
                checked = inspect_source_terminal(output / 'trajectory', parent_directory=parent,
                    request=request, outcome=outcome,
                    input_checkpoint=_absolute(request['source']) if request['operation'] == 'source-resume' else None)
                checked = {**checked, 'restore_available': False}
            result.update(checked, record_valid=True, status=outcome['status'],
                run_reason=outcome['reason'])
            result['artifact_bindings'].update(request_sha256=_hash(raw), outcome_sha256=_hash(outcome_raw))
            if request['operation'] == 'source-resume' or (
                    request['operation'] == 'source-advance' and outcome['status'] == 'completed'):
                _bound_parent(directory, binding, request)
        # Detect changed originals after the operation-specific passive reader.
        _require(_load_binding(directory) == (binding, request, raw), 'binding_changed_during_inspection')
        _require(_read(output / 'request.json', 65536) == raw, 'worker_request_changed_during_inspection')
        name, original = ('FAILURE.json', failure_raw) if failure_exists else ('OUTCOME.json', outcome_raw)
        _require(_read(output / name) == original, 'terminal_changed_during_inspection')
        _require(_exists(output / 'OUTCOME.json') is outcome_exists and
            _exists(output / 'FAILURE.json') is failure_exists, 'terminal_publication_changed_during_inspection')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        result.update(status='unverified_result', record_valid=False, restore_available=False,
                      verification_error=str(exc))
    observation = result['process_observation']
    code, cause = observation['returncode'], observation['termination_cause']
    if cause is not None:
        result['status'] = 'resource_limit' if cause == 'wall_timeout' else 'cancelled'
        result['restore_available'] = False
    elif type(code) is int and code != 0 and (result['reported_status'] in (None, 'completed', 'paused')):
        result['status'], result['restore_available'] = 'abnormal_exit', False
    elif code is None and result['status'] in ('completed', 'paused'):
        result['status'], result['restore_available'] = 'unverified_result', False
    return result
