"""Isolated data-only source execution, including persisted ordinary resume.

All physical work uses the existing source services. A supplied comparison
budget declares costs from other branches; it never replaces a source lineage's
own stored counters or time limits. It is not authentication of those costs.
"""
import hashlib
import json
from pathlib import Path
import sys
import threading
import time

from .source_record_io import read_record_bytes, publish_record_bytes

COUNTERS = ('heos_started', 'heos_kernel_returned', 'heos_returned',
    'initial_energy_started', 'initial_energy_returned', 'rhs_started',
    'rhs_returned', 'wet_started', 'wet_returned')


def _require(ok, reason):
    if not ok:
        raise ValueError('source_execution_' + reason)


def _load_request(raw):
    from .source_run_config import _integer, _nonfinite, _pairs, _shape, exact_config_fraction
    _require(type(raw) is bytes and 0 < len(raw) <= 65536, 'request_byte_limit')
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite, parse_int=_integer)
        _require(type(value) is dict, 'request_object')
        shape = dict(schema='str', operation='str', source='str', output='str', cancel_file='str')
        operation = value.get('operation')
        if operation == 'source-run':
            shape['assets_root'] = 'str'
        elif operation == 'source-advance':
            shape.update(end=dict(numerator='int', denominator='int'),
                step_sizes=dict(initial_step_s='float', maximum_step_s='float', rationale='str'),
                pause_after_steps='int')
        elif operation == 'source-resume':
            shape['pause_after_steps'] = 'int'
        else:
            raise ValueError('source_execution_operation')
        shape['shared_budget'] = ('NoneType' if value.get('shared_budget') is None else
            dict(other_counts={key: 'int' for key in COUNTERS}, outer_remaining_seconds='float',
                 total_callback_cap='int', wet_pressure_request_cap='int'))
        _shape(value, shape, 'source_execution_request')
        _require(value['schema'] == 'source_execution_request_v1', 'request_schema')
        for key in ('source', 'output') + (('assets_root',) if operation == 'source-run' else ()):
            _require(Path(value[key]).is_absolute() and '\x00' not in value[key], 'absolute_paths')
        _require(value['cancel_file'] == 'disabled' or
            (Path(value['cancel_file']).is_absolute() and '\x00' not in value['cancel_file']), 'cancel_path')
        if operation != 'source-run':
            _require(0 <= value['pause_after_steps'] <= 1_000_000, 'pause_steps')
        if operation == 'source-advance':
            _require(exact_config_fraction(value['end']) >= 0, 'end_time')
            sizes = value['step_sizes']
            _require(0 < sizes['initial_step_s'] <= sizes['maximum_step_s'], 'step_sizes')
        shared = value['shared_budget']
        if shared is not None:
            _require(all(0 <= n <= 1_000_000_000 for n in shared['other_counts'].values()) and
                0 < shared['outer_remaining_seconds'] <= 510. and
                0 < shared['total_callback_cap'] <= 97 and
                0 < shared['wet_pressure_request_cap'] <= 16, 'shared_budget_range')
            for start, returned in (('heos_started', 'heos_kernel_returned'),
                    ('heos_kernel_returned', 'heos_returned'),
                    ('initial_energy_started', 'initial_energy_returned'),
                    ('rhs_started', 'rhs_returned'), ('wet_started', 'wet_returned')):
                _require(shared['other_counts'][returned] <= shared['other_counts'][start], 'shared_counts_order')
        return value
    except (TypeError, OverflowError, RecursionError, UnicodeError) as exc:
        raise ValueError('source_execution_request_invalid') from exc


def _require_isolated_entry():
    if (__name__ != '__main__' or not sys.flags.isolated or
            threading.current_thread() is not threading.main_thread() or threading.active_count() != 1):
        raise RuntimeError('source_execution_isolated_module_process_required')


def _publish(path, value):
    publish_record_bytes(path, json.dumps(value, sort_keys=True, indent=2,
        allow_nan=False).encode() + b'\n', temporary_prefix='.source-execution-')


class _ExecutionBudget:
    """Observe actual service counters, including failures before factory return."""
    def __init__(self, begin, limits, cancel_file, shared):
        self.begin, self.cancel_file = begin, cancel_file
        self.limits = dict(limits)
        self.other = {key: 0 for key in COUNTERS}
        if shared is not None:
            self.other.update(shared['other_counts'])
            self.limits['outer_seconds'] = min(limits['outer_seconds'], shared['outer_remaining_seconds'])
            for key in ('total_callback_cap', 'wet_pressure_request_cap'):
                self.limits[key] = min(limits[key], shared[key])
        self.recorder = None
        self.stop_reason = None
        self.user_requested = False

    def observe(self):
        from .source_run_observer import _sink
        from .source_run_service import _Recorder
        recorder = _sink.get()
        if type(recorder) is _Recorder:
            _require(self.recorder is None or self.recorder is recorder, 'unexpected_second_recorder')
            self.recorder = recorder
        return self.recorder

    def counts(self):
        recorder = self.observe()
        return None if recorder is None else dict(recorder.counts)

    def combined_counts(self):
        actual = self.counts()
        return None if actual is None else {key: actual[key] + self.other[key] for key in COUNTERS}

    def cancel(self):
        from .source_run_service import _SourceWorkflowBudgetStop
        actual = self.combined_counts()
        if time.monotonic() - self.begin >= self.limits['outer_seconds']:
            self.stop_reason = self.stop_reason or 'process_or_comparison_wall_limit'
        for key, limit in (('rhs_started', 'total_callback_cap'), ('wet_started', 'wet_pressure_request_cap')):
            count = self.other[key] if actual is None else actual[key]
            if count >= self.limits[limit]:
                self.stop_reason = self.stop_reason or 'comparison_' + limit
        if self.stop_reason is not None:
            raise _SourceWorkflowBudgetStop(self.stop_reason)
        self.user_requested = self.user_requested or bool(self.cancel_file and Path(self.cancel_file).exists())
        return self.user_requested


def _require_idle_scope():
    from . import _heos_rhs_scope as scope
    _require(scope._worker is None and scope._active is None, 'native_scope_not_closed')


def _execute_request(request_path):
    _require_isolated_entry()
    begin = time.monotonic()
    raw = read_record_bytes(request_path, 65536, size_reason='source_execution_request_byte_limit',
                            regular_reason='source_execution_request_regular_file')
    request = _load_request(raw)
    output = Path(request['output'])
    output.mkdir(parents=True, exist_ok=False)
    budget, configured, session, result, saved = None, False, None, None, None
    try:
        publish_record_bytes(output / 'request.json', raw, temporary_prefix='.source-execution-')
        from ._heos_rhs_scope import _configure_workflow_deadline, _clear_workflow_deadline
        from .exact_event_clock import ExactEventTime
        from .run_service import runtime_identity
        from .source_run_config import load_source_run_config, RESUME_PROFILE, exact_config_fraction
        from .source_run_service import run_source_case
        from .source_trajectory import SourceOrdinaryStepSizes, open_source_trajectory
        from .source_trajectory_record import restore_source_trajectory, save_source_trajectory
        source, operation = Path(request['source']), request['operation']
        case_path = (source if operation == 'source-run' else
                     source / ('parent/case.json' if operation == 'source-resume' else 'case.json'))
        case_raw = read_record_bytes(case_path, 65536, size_reason='source_execution_case_byte_limit',
                                    regular_reason='source_execution_case_regular_file')
        config = load_source_run_config(case_raw)
        _require(config.values['profile'] == RESUME_PROFILE, 'versioned_implementation_required')
        runtime = runtime_identity()
        budget = _ExecutionBudget(begin, config.values['resources'],
            '' if request['cancel_file'] == 'disabled' else request['cancel_file'], request['shared_budget'])
        _require(not budget.cancel(), 'cancelled_before_admission')
        _configure_workflow_deadline(begin + budget.limits['outer_seconds'])
        configured = True
        if operation == 'source-run':
            result = run_source_case(source, Path(request['assets_root']), output / 'run',
                cancel=budget.cancel, managed_execution=True)
            status, reason, counts = result['status'], result.get('reason'), result['counts']
            details = dict(source_run_directory=str(output / 'run'),
                numerical_event_accepted=result['numerical_event_accepted'])
        else:
            if operation == 'source-advance':
                session = open_source_trajectory(source, output / 'trajectory',
                    end=ExactEventTime(exact_config_fraction(request['end'])),
                    step_sizes=SourceOrdinaryStepSizes(**request['step_sizes']),
                    cancel=budget.cancel, managed_execution=True)
            else:
                session = restore_source_trajectory(source, output / 'trajectory',
                    cancel=budget.cancel, managed_execution=True)
            result = session.advance(pause_after_steps=request['pause_after_steps'] or None)
            status, reason, counts = result.status, result.reason, dict(result.counts)
            details = dict(trajectory_directory=str(output / 'trajectory'),
                parent_study_sha256=result.parent_study_sha256,
                accepted_steps=len(result.execution.result.steps),
                observations=len(result.execution.observations))
        _require_idle_scope()
        _require(runtime_identity() == runtime, 'runtime_changed')
        _require(status in ('completed', 'paused'), 'operation_' + status + ':' + str(reason))
        _require(not budget.cancel(), 'cancelled_before_publication')
        if status == 'paused':
            saved = save_source_trajectory(session, output / 'resume-point')
            _require(session.closed and saved['source_resume_authorized'] is True, 'save_did_not_suspend')
            details['saved_checkpoint'] = saved
        _require(not budget.cancel(), 'cancelled_after_save')
        _require_idle_scope()
        _clear_workflow_deadline()
        configured = False
        outcome = dict(schema='source_execution_outcome_v1', operation=operation, status=status, reason=reason,
            details=details, counts=counts, declared_other_branch_counts=dict(budget.other),
            combined_counts={key: counts[key] + budget.other[key] for key in COUNTERS},
            shared_budget_provenance='caller_declared_external_debits_not_authenticated',
            raw_case_sha256=hashlib.sha256(case_raw).hexdigest(), canonical_config_sha256=config.sha256,
            request_sha256=hashlib.sha256(raw).hexdigest(), runtime_before=runtime, runtime_after=runtime_identity(),
            process_elapsed_seconds=time.monotonic() - begin,
            material_qualified=False, training_eligible=False, full_firing_cycle=False,
            historical_study_resume_authorized=False)
        _require(not budget.cancel(), 'cancelled_before_outcome')
        _publish(output / 'OUTCOME.json', outcome)
        return outcome
    except BaseException as exc:
        secondary = []
        recorder = None if budget is None else budget.observe()
        if budget is not None and time.monotonic() - begin >= budget.limits['outer_seconds']:
            budget.stop_reason = budget.stop_reason or 'process_or_comparison_wall_limit'
        status = ('resource_limit' if (budget is not None and budget.stop_reason is not None) or
                  (recorder is not None and recorder.stop_status == 'resource_limit') else
                  'cancelled' if isinstance(exc, KeyboardInterrupt) or
                  (budget is not None and budget.user_requested) or
                  (recorder is not None and recorder.stop_status == 'cancelled') else 'failed')
        if configured:
            try:
                _clear_workflow_deadline()
            except BaseException as cleanup:
                secondary.append(dict(stage='clear_deadline', exception_type=type(cleanup).__name__, reason=str(cleanup)))
        if saved is not None:
            try:
                _publish(output / 'resume-point' / 'WORKER_FAILURE.json', dict(reason=str(exc)))
            except BaseException as cleanup:
                secondary.append(dict(stage='invalidate_checkpoint', exception_type=type(cleanup).__name__, reason=str(cleanup)))
        actual = None if recorder is None else dict(recorder.counts)
        failure = dict(schema='source_execution_failure_v1', status=status,
            exception_type=type(exc).__name__, reason=str(exc), process_elapsed_seconds=time.monotonic() - begin,
            counts=actual, count_completeness='unknown' if actual is None else 'complete_observed_counts',
            combined_counts=None if actual is None else {key: actual[key] + budget.other[key] for key in COUNTERS},
            stop_reason=None if budget is None else budget.stop_reason, secondary_errors=secondary,
            material_qualified=False, training_eligible=False, full_firing_cycle=False,
            historical_study_resume_authorized=False)
        try:
            _publish(output / 'FAILURE.json', failure)
        except BaseException as saving:
            exc.add_note('source execution failure publication also failed: ' + repr(saving))
        raise


def main():
    _require_isolated_entry()
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -I -m sludge_sandbox.source_execution_worker REQUEST.json')
    _execute_request(Path(sys.argv[1]))


if __name__ == '__main__':
    main()
