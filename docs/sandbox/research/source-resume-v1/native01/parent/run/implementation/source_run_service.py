"""Execute a declared HEOS/source-caloric wet-to-dry study with durable evidence.

The current profile is a manufactured geometry/transport verification case.
It exercises real source providers; it is not a complete sludge firing cycle.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import time

from .exact_event_clock import ExactEventTime
from .integration import IntegrationError, DomainExit
from .run_service import RunError, _json, _seal, runtime_identity
from .source_observation_record import SourceObservationContext
from .source_record_io import read_record_bytes, publish_record_bytes
from .source_run_journal import SourceRunJournal, raw_projection
from .source_study_record import _snapshot, encode_source_study, decode_source_study
from .source_study_schema import SourceStudyFailure

KIND = 'source_wet_to_dry_study_v1'
RECORD = 'source-study-record.json'


class _RunStop(IntegrationError):
    pass


class _SourceWorkflowBudgetStop(IntegrationError):
    """Private closed-worker signal for the original cumulative run budget."""


def _read(path, limit=64 * 1024 * 1024):
    return read_record_bytes(path, limit, size_reason='source_run_input_byte_limit',
                             regular_reason='source_run_regular_input_required')


def _publish(path, raw):
    publish_record_bytes(path, raw, temporary_prefix='.source-run-')


class _Recorder:
    def __init__(self, directory, cancel, begin):
        self.journal = SourceRunJournal(directory)
        self.cancel_callback, self.begin = cancel, begin
        self.limits = None
        self.stop_status = self.stop_reason = self.cancel_error = None
        self.phase = 'preparing'
        self.captures, self.contexts, self.candidates = [], [], []
        self.roots, self.initial_points = {}, []
        self.built = None
        self.active_rhs = None
        self.effective = None
        self.undurable_returns = []
        self.notification_failures = []
        self.managed_audits = []
        self.counts = dict(heos_started=0, heos_kernel_returned=0, heos_returned=0,
                           initial_energy_started=0, initial_energy_returned=0,
                           rhs_started=0, rhs_returned=0, wet_started=0, wet_returned=0)

    def cancelled(self):
        # Existing solvers require a bool-returning cooperative cancellation
        # function. A broken caller callback is recorded, never injected midway
        # through an integrator as an unrelated exception.
        if self.stop_status is not None:
            return True
        try:
            requested = self.cancel_callback() if self.cancel_callback is not None else False
            if type(requested) is not bool:
                raise ValueError('source_run_cancel_must_return_bool')
        except _SourceWorkflowBudgetStop as exc:
            self.stop_status, self.stop_reason = 'resource_limit', str(exc)
            return True
        except Exception as exc:
            self.cancel_error = exc
            self.stop_status, self.stop_reason = 'failed', 'cancel_callback_failed:' + str(exc)
            return True
        if requested:
            self.stop_status, self.stop_reason = 'cancelled', 'caller_requested_stop'
        elif self.limits is not None and time.monotonic() - self.begin >= self.limits['outer_seconds']:
            self.stop_status, self.stop_reason = 'resource_limit', 'source_run_outer_deadline'
        return self.stop_status is not None

    def guard(self):
        if self.cancelled():
            raise _RunStop(self.stop_reason)

    def context(self, adapter):
        value = SourceObservationContext(adapter.operator_identity, adapter.energy_model_identity,
            tuple(s.dry_mass_kg for s in adapter.column.storages), adapter.interfaces)
        if value not in self.contexts:
            self.contexts.append(value)
        return value

    def __call__(self, event, **payload):
        if event == 'rhs_started':
            self.active_rhs = None
        if event.endswith('_started'):
            self.guard()
            limit = {'rhs_started': 'total_callback_cap', 'wet_started': 'wet_pressure_request_cap'}.get(event)
            if limit and self.counts[event] >= self.limits[limit]:
                self.stop_status, self.stop_reason = 'resource_limit', 'source_run_' + limit
                self.journal.append('request_blocked', dict(event=event, reason=self.stop_reason))
                raise _RunStop(self.stop_reason)
        returned = event.endswith('_returned')
        if returned and event in self.counts:
            self.counts[event] += 1
        if event == 'rhs_returned':
            key = (id(payload['adapter']), id(payload['state']), id(payload['time']))
            _require(self.active_rhs is not None and self.active_rhs[0] == key,
                     'source_run_return_without_matching_start')
            # The physical return occurred even if the next disk write fails.
            self.active_rhs[1]['evaluation'] = payload['evaluation']
        elif event == 'initial_energy_returned':
            self.initial_points.append(payload['point'])
        elif event == 'candidate_returned':
            self.candidates.append(payload['candidate'])
        elif event == 'transition_returned':
            self.roots['transition'] = payload['result']
        elif event == 'rhs_failed' and self.active_rhs is not None:
            key = (id(payload['adapter']), id(payload['state']), id(payload['time']))
            _require(self.active_rhs[0] == key, 'source_run_failure_without_matching_start')
            exc = payload['exception']
            self.active_rhs[1].update(failure_kind=type(exc).__name__, failure=str(exc))
        try:
            reference = self.journal.append(event, dict(phase=self.phase, **payload))
        except Exception:
            if returned:
                self.undurable_returns.append(dict(event=event, phase=self.phase, payload=payload))
            raise
        if not returned and event in self.counts:
            self.counts[event] += 1
        if event == 'rhs_started':
            adapter = payload['adapter']
            context = self.context(adapter)
            capture = dict(ordinal=len(self.captures) + 1, phase=self.phase,
                packed_input=_snapshot(payload['state']), time=payload['time'],
                operator_identity=context.operator_identity, energy_identity=context.energy_identity,
                interface_modes=context.interface_modes, started_event=reference)
            self.captures.append(capture)
            self.active_rhs = ((id(adapter), id(payload['state']), id(payload['time'])), capture)
            if self.built is not None:
                capture['same_original_cell_storage_objects'] = tuple(
                    a is b for a, b in zip(adapter.column.storages, self.built.storages))
                capture['same_original_cell_volume_objects'] = tuple(
                    a.volume is b.volume for a, b in zip(adapter.column.storages, self.built.storages))
                if (len(adapter.column.storages) != len(self.built.storages)
                        or not all(capture['same_original_cell_storage_objects'])
                        or not all(capture['same_original_cell_volume_objects'])):
                    raise IntegrationError('source_run_original_storage_binding_changed')
        elif event == 'rhs_returned':
            key = (id(payload['adapter']), id(payload['state']), id(payload['time']))
            _require(self.active_rhs is not None and self.active_rhs[0] == key,
                     'source_run_return_without_matching_start')
            capture = self.active_rhs[1]
            capture['returned_event'] = reference
            try:
                capture['evaluation'] = _snapshot(payload['evaluation'])
            except Exception as exc:
                del capture['evaluation']
                capture.update(failure_kind=type(exc).__name__, failure=str(exc),
                    invalid_return_evidence=reference)
                raise
        elif event == 'rhs_failed' and self.active_rhs is not None:
            key = (id(payload['adapter']), id(payload['state']), id(payload['time']))
            _require(self.active_rhs[0] == key, 'source_run_failure_without_matching_start')
            exc = payload['exception']
            self.active_rhs[1].update(failure_kind=type(exc).__name__, failure=str(exc),
                                      failed_event=reference)
            self.active_rhs = None
        elif event == 'candidate_returned':
            self.phase = 'shifted_dry_candidate'
        return reference

    def stage(self, name, operation):
        self.phase = name
        self.guard()
        self.journal.append('stage_started', {'stage': name})
        value = operation()
        self.roots[name] = value
        self.journal.append('stage_returned', {'stage': name, 'value': value})
        self.guard()
        return value


def _require(ok, reason):
    if not ok:
        raise IntegrationError(reason)


def _managed_request(enabled: bool, config=None) -> None:
    """Reject opt-in misuse before constructing providers or opening a lease."""
    _require(type(enabled) is bool, 'source_managed_execution_must_be_bool')
    if enabled:
        from ._heos_rhs_scope import _require_workflow_entry
        _require_workflow_entry()
        if config is not None:
            from .source_run_config import WORKFLOW_PROFILE, RESUME_PROFILE
            _require(config.values['profile'] in (WORKFLOW_PROFILE, RESUME_PROFILE),
                     'source_managed_workflow_profile_required')


@contextmanager
def _managed_operation(recorder: _Recorder, adapter: object, *, enabled: bool,
                       deadline_monotonic: float) -> Iterator[None]:
    """Own one operation's lease; individual RHS bodies own native scopes.

    Closing and retaining the owned audit precede publication. A secondary close
    or journal error never replaces the operation's original exception.
    """
    if not enabled:
        yield
        return
    from ._heos_rhs_scope import _admit_workflow_worker, _close_worker, _worker_audit
    lease, primary = None, None
    entry = dict(ordinal=len(recorder.managed_audits) + 1, phase=recorder.phase,
                 status='admitting', audit=None, primary_error=None, secondary_errors=[])
    recorder.managed_audits.append(entry)
    started = time.monotonic()
    errors = []
    try:
        recorder.journal.append('managed_lease_started', entry)
        lease = _admit_workflow_worker(adapter, deadline_monotonic=deadline_monotonic)
        entry['status'] = 'active'
        yield
    except BaseException as exc:
        primary = exc
        entry['primary_error'] = dict(type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        if lease is not None:
            try:
                _close_worker(lease)
            except BaseException as exc:
                errors.append(('close', exc))
            try:
                entry['audit'] = _worker_audit(lease)
            except BaseException as exc:
                errors.append(('audit', exc))
        entry['status'] = 'closed' if primary is None and not errors else 'failed'
        entry['elapsed_seconds'] = time.monotonic() - started
        for stage, exc in errors:
            entry['secondary_errors'].append(dict(stage=stage, type=type(exc).__name__, reason=str(exc)))
        try:
            recorder.journal.append('managed_lease_closed', entry)
        except BaseException as exc:
            errors.append(('journal', exc))
            entry['status'] = 'failed'
            entry['secondary_errors'].append(dict(stage='journal', type=type(exc).__name__, reason=str(exc)))
        if primary is not None:
            for stage, exc in errors:
                primary.add_note('source managed ' + stage + ' also failed: ' + type(exc).__name__)
        elif errors:
            for stage, exc in errors[1:]:
                errors[0][1].add_note('source managed ' + stage + ' also failed: ' + type(exc).__name__)
            raise errors[0][1]


def _execute(built, recorder, config):
    from .source_run_builder import build_source_controls
    from .source_prefix_trial import evaluate_source_prefix_trial
    from .source_approach import propose_source_approach, evaluate_source_approach
    from .source_root_comparison import evaluate_source_root_refinement
    from .source_dry_transition import evaluate_source_dry_transition
    from .source_dry_shared_pressure import declare_source_shared_dry_volume
    from .source_wet_shared_pressure import declare_source_shared_wet_volume
    values = config.values
    settings, limits = values['study'], values['resources']
    recorder.built = built
    recorder.context(built.adapter)
    states = []
    recorder.phase = 'initial_energy'
    for index, (storage, state, temperature) in enumerate(zip(
            built.storages, built.unset_energy_states, built.initial_temperatures_k)):
        recorder('initial_energy_started', cell_index=index, state=state, temperature_k=temperature)
        try:
            point = storage.evaluate(state, temperature)
            recorder('initial_energy_returned', cell_index=index, point=point)
            states.append(replace(state, internal_energy_j=point.total_internal_energy_j))
            recorder.guard()
        except Exception as exc:
            try:
                recorder('initial_energy_failed', cell_index=index, exception=exc)
            except Exception as notification_error:
                recorder.notification_failures.append(dict(event='initial_energy_failed',
                    exception_type=type(notification_error).__name__, reason=str(notification_error)))
                exc.add_note('source initial energy failure notification failed: ' + type(notification_error).__name__)
            raise
    initial = built.adapter.pack(tuple(states))
    start_data = settings['start_seconds']
    start = ExactEventTime(Fraction(start_data['numerator'], start_data['denominator']))
    recorder.phase = 'probe'
    first = built.adapter.evaluate(initial, start)
    selected = settings['selected_cell_index']
    phase = first.source_evaluation.cells[selected].phase.phase_water_mol_s
    left = float(first.rates.face_species_mol_s[selected, 0])
    right = float(first.rates.face_species_mol_s[selected + 1, 0])
    net_loss = Fraction(phase) + Fraction(right) - Fraction(left)
    _require(math.isfinite(phase) and phase > 0 and net_loss > 0,
             'source_run_initial_phase_or_net_loss_not_positive')
    factor = settings['horizon_multiplier']
    horizon = (Fraction(factor['numerator'], factor['denominator']) *
               Fraction(states[selected].liquid_water_mol) / net_loss)
    _require(math.isfinite(float(horizon)) and float(horizon) > 0, 'source_run_unrepresentable_horizon')
    controls = build_source_controls(config, built, horizon=horizon)
    end = start.shifted(horizon)
    effective = dict(initial=initial, start=start, horizon=horizon, end=end,
        selected_phase_water_mol_s=phase, selected_left_liquid_mol_s=left,
        selected_right_liquid_mol_s=right, selected_net_liquid_loss_mol_s=net_loss,
        integration_policy=controls.integration_policy, event_policy=controls.event_policy)
    recorder.journal.append('derived_controls', effective)
    recorder.effective = effective
    seed = recorder.stage('seed', lambda: evaluate_source_prefix_trial(built.adapter, initial,
        start=start, end=end, integration_policy=controls.integration_policy,
        maximum_callbacks=limits['callback_cap'], cancel=recorder.cancelled))
    proposal = recorder.stage('proposal', lambda: propose_source_approach(seed, event_policy=controls.event_policy))
    _require(proposal.status == 'positive_numerical_proposal', 'source_run_no_positive_approach:' + proposal.status)
    approach = recorder.stage('approach', lambda: evaluate_source_approach(proposal,
        maximum_callbacks=limits['callback_cap'], cancel=recorder.cancelled))
    _require(approach.status == 'validated_positive_numerical_approach', 'source_run_approach:' + approach.status)
    refinement = recorder.stage('refinement', lambda: evaluate_source_root_refinement(approach,
        maximum_callbacks=limits['callback_cap'], cancel=recorder.cancelled))
    _require(refinement.clock is not None, 'source_run_independent_shifted_root_unavailable')
    _require(all(choice.order.earliest_labels == (('liquid', selected, 0),)
                 for choice in refinement.clock.choices), 'source_run_selected_first_root_changed')
    dry = declare_source_shared_dry_volume(built.storages[settings['shared_dry_cell_index']])
    wet = tuple(declare_source_shared_wet_volume(storage) if index in settings['shared_wet_cell_indices'] else None
                for index, storage in enumerate(built.storages))
    recorder.phase = 'coarse_dry_candidate'
    transition = evaluate_source_dry_transition(refinement, end=seed.end,
        maximum_callbacks_per_path=limits['dry_path_callback_cap'], cancel=recorder.cancelled,
        shared_volume=dry, shared_wet_volumes=wet)
    recorder.roots['transition'] = transition
    recorder.guard()
    _require(transition.material_qualified is False, 'source_run_material_qualification_forbidden')
    return effective, transition


def run_source_case(case_path, assets_root, output, *, cancel=None, replay_of=None,
                    managed_execution: bool = False):
    """Run installed providers from an explicit validated local asset tree.

    ``managed_execution`` additionally requires the closed workflow worker and
    its explicitly versioned profile; default callers retain per-call checks.
    """
    from .source_run_config import load_source_run_config, validate_source_run_assets
    from .source_run_builder import build_source_run
    from .source_run_observer import observer_scope
    _managed_request(managed_execution)
    directory = Path(output).absolute()
    directory.mkdir(parents=True, exist_ok=False)
    begin = time.monotonic()
    recorder = _Recorder(directory, cancel, begin)
    result = dict(schema='sandbox_run_v1', integration_kind=KIND, status='preparing', reason=None,
        scientific_status='manufactured_geometry_transport_with_source_water_and_dry_caloric',
        material_qualified=False, training_eligible=False, resume_authorized=False,
        full_firing_cycle=False, runtime_before=runtime_identity(), source_record=None,
        numerical_comparison_completed=False, numerical_event_accepted=False, replay_of=replay_of,
        source_assets_distribution='private_local_bundle_not_authorized_for_public_redistribution')
    config = None
    effective = None
    try:
        raw = _read(case_path, 1024 * 1024)
        _publish(directory / 'case.json', raw)
        result['case_sha256'] = hashlib.sha256(raw).hexdigest()
        result['original_case_available'] = True
        _json(directory / 'result.json', result)
        config = load_source_run_config(raw)
        _managed_request(managed_execution, config)
        result['config_sha256'] = config.sha256
        _publish(directory / 'config.json', config.canonical_bytes)
        recorder.limits = config.values['resources']
        recorder.guard()
        assets = validate_source_run_assets(config, assets_root=Path(assets_root))
        for item in config.values['assets']:
            target = directory / 'assets' / item['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            data = _read(assets.root / item['path'])
            _require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                     'source_run_asset_changed_during_copy:' + item['path'])
            _publish(target, data)
        frozen = validate_source_run_assets(config, assets_root=directory / 'assets')
        result['asset_manifest_sha256'] = frozen.sha256
        implementation = directory / 'implementation'
        implementation.mkdir()
        for path in sorted(Path(__file__).parent.glob('*.py')):
            _publish(implementation / path.name, path.read_bytes())
        with observer_scope(recorder):
            recorder.phase = 'construction'
            recorder.guard()
            built = build_source_run(config, frozen)
            recorder.journal.append('builder_returned', built.adapter.provenance())
            recorder.guard()
            with _managed_operation(recorder, built.adapter, enabled=managed_execution,
                    deadline_monotonic=begin + recorder.limits['outer_seconds']):
                effective, transition = _execute(built, recorder, config)
            if managed_execution:
                recorder.guard()
        result.update(status='completed', numerical_comparison_completed=True,
            numerical_event_accepted=transition.numerical_event_accepted,
            transition_status=transition.status, physical_end_seconds=float(transition.candidates[0].end.seconds))
    except KeyboardInterrupt as exc:
        recorder.stop_status, recorder.stop_reason = 'cancelled', 'keyboard_interrupt'
        recorder.roots['failure'] = SourceStudyFailure(type(exc).__name__, str(exc), recorder.phase, {})
        result.update(status='cancelled', reason=recorder.stop_reason)
    except Exception as exc:
        failure = SourceStudyFailure(type(exc).__module__ + '.' + type(exc).__qualname__, str(exc),
            recorder.phase, {'exception': exc, 'returned_candidates': tuple(recorder.candidates),
                             'cancel_callback_exception': recorder.cancel_error})
        recorder.roots['failure'] = failure
        result.update(status=recorder.stop_status or ('domain_exit' if isinstance(exc, DomainExit) else 'failed'),
                      reason=recorder.stop_reason or str(exc), exception_type=type(exc).__name__)
        try:
            recorder.journal.append('run_failed', failure)
        except Exception as recording_error:
            result['failure_journal_error'] = str(recording_error)
    finally:
        if 'case_sha256' not in result:
            missing = json.dumps(dict(schema='source_run_unavailable_case_v1',
                original_case_available=False, requested_path=str(case_path), reason=result['reason']),
                ensure_ascii=False, allow_nan=False).encode()
            _publish(directory / 'case.json', missing)
            result.update(case_sha256=hashlib.sha256(missing).hexdigest(), original_case_available=False)
        result['execution_status'] = result['status']
        metadata = dict(status=result['status'], reason=result['reason'], material_qualified=False,
            full_firing_cycle=False, case_sha256=result.get('case_sha256'), counts=dict(recorder.counts),
            effective_inputs=recorder.effective, initial_energy_points=raw_projection(tuple(recorder.initial_points)),
            undurable_returns=raw_projection(tuple(recorder.undurable_returns)),
            notification_failures=tuple(recorder.notification_failures),
            returned_candidates=tuple(recorder.candidates), config_sha256=result.get('config_sha256'))
        if managed_execution:
            audits = deepcopy(recorder.managed_audits)
            result.update(managed_execution=True, managed_audits=audits)
            metadata.update(managed_execution=True, managed_audits=audits)
        try:
            raw = encode_source_study(recorder.roots, contexts=tuple(recorder.contexts),
                captures=tuple(recorder.captures), metadata=metadata,
                provenance={'origin': 'actual_installed_source_run', 'scope': KIND})
            _publish(directory / RECORD, raw)
            result['source_record'] = {'path': RECORD, 'sha256': hashlib.sha256(raw).hexdigest()}
        except Exception as exc:
            result['source_record_error'] = {'exception_type': type(exc).__name__, 'reason': str(exc)}
            result['unvalidated_comparison_report'] = {key: result.get(key) for key in (
                'numerical_comparison_completed', 'numerical_event_accepted', 'transition_status', 'physical_end_seconds')}
            result.update(numerical_comparison_completed=False, numerical_event_accepted=False)
            result.pop('transition_status', None)
            result.pop('physical_end_seconds', None)
            if result['status'] == 'completed':
                result.update(status='failed', reason='source_study_publication_failed:' + str(exc))
        result.update(counts=recorder.counts, journal_events=recorder.journal.count,
            journal_bytes=recorder.journal.total_bytes, runtime_after=runtime_identity(),
            elapsed_wall_seconds=time.monotonic() - begin)
        if result['runtime_after'] != result['runtime_before']:
            result.update(status='failed', reason='source_run_runtime_changed')
        _json(directory / 'result.json', result)
        _seal(directory)
    return result


def verify_source_artifacts(directory, result, manifest):
    """Validate correspondence, separately from the outer artifact hashes."""
    if result.get('integration_kind') != KIND:
        if RECORD in manifest['files'] or 'source_record' in result or 'source_record_error' in result:
            raise RunError('source_run_kind_changed')
        return
    if (result.get('material_qualified') is not False or result.get('training_eligible') is not False
            or result.get('full_firing_cycle') is not False or result.get('resume_authorized') is not False):
        raise RunError('source_run_scope_changed')
    if result.get('status') != result.get('execution_status'):
        downgrade = (result.get('status') == 'failed' and
            (result.get('reason') == 'source_run_runtime_changed' or
             str(result.get('reason', '')).startswith('source_study_publication_failed:')))
        if not downgrade:
            raise RunError('source_run_terminal_status_changed')
    reference = result.get('source_record')
    if reference is None:
        if result.get('status') == 'completed' or not result.get('source_record_error'):
            raise RunError('source_run_missing_record')
        if result.get('numerical_comparison_completed') is not False or result.get('numerical_event_accepted') is not False:
            raise RunError('source_run_unvalidated_summary_changed')
        return
    if reference != {'path': RECORD, 'sha256': manifest['files'].get(RECORD)}:
        raise RunError('source_run_record_binding_changed')
    record_bytes = _read(Path(directory) / RECORD)
    if hashlib.sha256(record_bytes).hexdigest() != reference['sha256']:
        raise RunError('source_run_record_changed_after_validation')
    record = decode_source_study(record_bytes)
    managed = result.get('managed_execution', False)
    if (type(managed) is not bool or managed is not record.metadata.get('managed_execution', False)
            or _snapshot(result.get('managed_audits', ())) != record.metadata.get('managed_audits', ())):
        raise RunError('source_run_managed_audit_binding_changed')
    if (record.metadata['case_sha256'] != result['case_sha256']
            or record.metadata['counts'] != result['counts']
            or record.metadata['status'] != result['execution_status']
            or (result['status'] == result['execution_status'] and record.metadata['reason'] != result['reason'])):
        raise RunError('source_run_summary_changed')
    if result['execution_status'] != 'completed':
        if (result.get('numerical_comparison_completed') is not False
                or result.get('numerical_event_accepted') is not False
                or 'transition_status' in result or 'physical_end_seconds' in result):
            raise RunError('source_run_incomplete_summary_changed')
    else:
        transition = record.roots.get('transition')
        if (transition is None or result.get('numerical_comparison_completed') is not True
                or transition.numerical_event_accepted != result.get('numerical_event_accepted')
                or transition.status != result.get('transition_status')
                or float(transition.candidates[0].end.seconds) != result.get('physical_end_seconds')):
            raise RunError('source_run_transition_summary_changed')
    return record


def replay_source_case(directory, output, *, cancel=None):
    """Reconstruct a fresh run from frozen inputs; never call this a resume."""
    from .run_service import read_run
    directory = Path(directory)
    result, manifest = read_run(directory)
    if result.get('integration_kind') != KIND:
        raise RunError('source_run_kind_required')
    if runtime_identity() != result['runtime_before'] or result['runtime_after'] != result['runtime_before']:
        raise RunError('source_run_replay_runtime_changed')
    return run_source_case(directory / 'case.json', directory / 'assets', output, cancel=cancel,
                           replay_of=manifest['files']['result.json'])
