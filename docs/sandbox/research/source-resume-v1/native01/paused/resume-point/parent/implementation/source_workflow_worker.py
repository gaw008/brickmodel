"""Closed installed worker for the original three-step source continuation gate.

The request is data only. A fresh parent study and both live ordinary sessions
share one budget; numeric checkpoint decoding never authorizes archived resume.
Native scopes belong to the service operations, not to this whole process.
"""
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

from .source_record_io import read_record_bytes, publish_record_bytes


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _load_request(raw):
    from .source_run_config import _integer, _nonfinite, _pairs, _shape
    shape = dict(schema='str', operation='str', case_path='str', assets_root='str',
        output='str', cancel_file='str', material_qualified='bool',
        segment=dict(duration_numerator='int', duration_denominator='int',
                     step_numerator='int', step_denominator='int', pause_after_steps='int'))
    _require(type(raw) is bytes and 0 < len(raw) <= 65536, 'source_workflow_request_byte_limit')
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite, parse_int=_integer)
        _shape(value, shape, 'source_workflow_request')
        _require(value['schema'] == 'source_workflow_request_v1' and
                 value['operation'] == 'fresh_parent_three_step_comparison' and
                 value['material_qualified'] is False, 'source_workflow_request_scope')
        _require(all(Path(value[key]).is_absolute() and '\x00' not in value[key]
                     for key in ('case_path', 'assets_root', 'output')), 'source_workflow_absolute_paths')
        _require(value['cancel_file'] == 'disabled' or (Path(value['cancel_file']).is_absolute()
                 and '\x00' not in value['cancel_file']), 'source_workflow_cancel_file')
        _require(value['segment'] == dict(duration_numerator=3, duration_denominator=64,
                 step_numerator=1, step_denominator=64, pause_after_steps=1),
                 'source_workflow_original_three_step_gate_required')
        return value
    except (TypeError, OverflowError, RecursionError, UnicodeError) as exc:
        raise ValueError('source_workflow_request_invalid') from exc


def _require_isolated_entry():
    if (__name__ != '__main__' or not sys.flags.isolated or
            threading.current_thread() is not threading.main_thread() or
            threading.active_count() != 1):
        raise RuntimeError('source_workflow_isolated_module_process_required')


def _publish(path, value):
    raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
    publish_record_bytes(path, raw, temporary_prefix='.source-workflow-')


class _WorkflowBudget:
    """Charge the parent once, then each session's actual incremental work."""
    def __init__(self, begin, limits, cancel_file):
        self.begin, self.limits, self.cancel_file = begin, limits, cancel_file
        self.parent = None
        self.sessions = []
        self.stop_reason = None
        self.user_requested = False

    def counts(self):
        if self.parent is None:
            return None  # Parent recorder has not yet returned; never claim zero.
        original = self.parent['counts']
        return {key: value + sum(s.recorder.counts[key] - value for s in self.sessions)
                for key, value in original.items()}

    def cancel(self):
        from .source_run_service import _SourceWorkflowBudgetStop
        if time.monotonic() - self.begin >= self.limits['outer_seconds']:
            self.stop_reason = 'combined_outer_seconds'
        actual = self.counts()
        if actual is not None:
            for key, limit in (('rhs_started', 'total_callback_cap'),
                               ('wet_started', 'wet_pressure_request_cap')):
                if actual[key] >= self.limits[limit]:
                    self.stop_reason = 'combined_' + limit
        if self.stop_reason is not None:
            raise _SourceWorkflowBudgetStop(self.stop_reason)
        self.user_requested = self.user_requested or bool(self.cancel_file and Path(self.cancel_file).exists())
        return self.user_requested


def _partial_admission_counts(directory):
    """Read only the saved integer counters, not executable model objects.

    An admission can fail before a session is returned. If its final diagnostic
    did not reach disk, the count is unknown, not zero. All journal bytes remain.
    """
    for path in sorted((directory / 'events').glob('*.json'), reverse=True):
        raw = read_record_bytes(path, 64 * 1024 * 1024,
            size_reason='source_workflow_event_byte_limit', regular_reason='source_workflow_event_regular_file')
        event = json.loads(raw)
        if event.get('event') != 'source_trajectory_admission_failed':
            continue
        graph = event['payload']
        root = graph['nodes'][graph['root']['ref']]['fields']
        counts = graph['nodes'][root['counts']['ref']]['fields']
        _require(all(type(key) is str and type(value) is int and value >= 0
                     for key, value in counts.items()), 'source_workflow_saved_actual_counts')
        return dict(counts)
    return None


def _require_idle_scope():
    from . import _heos_rhs_scope as scope
    _require(scope._worker is None and scope._active is None, 'source_workflow_scope_not_closed')


def _verify_paths(baseline, prefix, finished, paused, start, end, record, budget, raw_checkpoint):
    """Original dynamic gate: real conduction, accepted states and both paths."""
    import numpy as np
    from .exact_integration_checkpoint import _same
    from .source_study_schema import reify
    numerical = finished.execution.result
    _require(_same(replace(baseline.execution.result, elapsed_seconds=0.),
                   replace(numerical, elapsed_seconds=0.)), 'source_workflow_paths_differ')
    _require(_same(baseline.execution.observations, finished.execution.observations)
             and _same(prefix.execution.result.steps, numerical.steps[:1])
             and baseline.balances == finished.balances, 'source_workflow_observations_or_balances_differ')
    _require(numerical.times_s[0] == start and numerical.times_s[-1] == end
             and len(numerical.steps) == 3 and numerical.evaluations == 22
             and numerical.rejected_trials == 0, 'source_workflow_three_step_endpoint')
    _require(any(np.any(step.face_energy_j[1:-1]) for step in numerical.steps)
             and np.any(numerical.states[-1].internal_energy_j != numerical.states[0].internal_energy_j)
             and all(np.array_equal(s.amounts_mol, numerical.states[0].amounts_mol)
                     for s in numerical.states), 'source_workflow_closed_conduction_required')
    first = paused.recorder.captures[0]['evaluation'].source_evaluation
    last = paused.recorder.captures[-1]['evaluation'].source_evaluation
    actual_last = finished.execution.observations[-1]
    _require(paused.recorder.captures[-1]['time'] == end
             and _same(reify(paused.recorder.captures[-1]['packed_input']), numerical.states[-1])
             and actual_last.role == 'accepted' and actual_last.time == end
             and _same(actual_last.state, numerical.states[-1]), 'source_workflow_actual_final_observation')
    delta_t = [F(b.inverse.point.fluid.mechanical.temperature_k) - F(a.inverse.point.fluid.mechanical.temperature_k)
               for a, b in zip(first.cells, last.cells)]
    bounds = [F(a.inverse.temperature_error_bound_k) + F(b.inverse.temperature_error_bound_k)
              for a, b in zip(first.cells, last.cells)]
    _require(any(abs(delta) > bound for delta, bound in zip(delta_t, bounds))
             and any(face.shared_evaluation.conduction_w != 0 for face in first.faces[1:-1]),
             'source_workflow_resolved_nonstationary_temperature_required')
    changes = []
    for old, new, step in zip(numerical.states, numerical.states[1:], numerical.steps):
        _require(step.face_energy_j[0] == step.face_energy_j[-1] == 0, 'source_workflow_closed_energy_boundary')
        change = sum(F(float(x)) for x in new.internal_energy_j) - sum(F(float(x)) for x in old.internal_energy_j)
        _require(abs(change) <= F(paused.reference_policy.energy_absolute_tolerance_j),
                 'source_workflow_global_energy_balance')
        changes.append(float(change))
    actual, parent = budget.counts(), budget.parent
    _require(actual['rhs_started'] == actual['rhs_returned'] == parent['counts']['rhs_started'] + 44 <= 97
             and actual['heos_started'] == actual['heos_kernel_returned'] == actual['heos_returned'] == 12
             and actual['initial_energy_started'] == actual['initial_energy_returned'] == 3
             and actual['wet_started'] == actual['wet_returned'] == parent['counts']['wet_started'] <= 16,
             'source_workflow_actual_work_counts')
    _require(all(not getattr(result, key) for result in (baseline, finished)
                 for key in ('material_qualified', 'full_firing_cycle', 'archived_resume_authorized')),
             'source_workflow_qualification_changed')
    audits = [parent['managed_audits'], baseline.managed_audits, finished.managed_audits]
    _require([len(a) for a in audits] == [1, 1, 2] and
             all(a['status'] == 'closed' and a['audit']['closed'] is True
                 and all(rhs['status'] == 'verified' for rhs in a['audit']['rhs'])
                 for group in audits for a in group), 'source_workflow_managed_audits_not_closed')
    return dict(total_actual_counts=actual, parent_counts=parent['counts'],
        branch_counts=[dict(x.counts) for x in (baseline, finished)],
        exact_start=start.to_record(), exact_end=end.to_record(), physical_end_seconds=float(end.seconds),
        accepted_steps=3, evaluations_per_branch=22, temperature_change_k=list(map(float, delta_t)),
        paired_inverse_temperature_bounds_k=list(map(float, bounds)),
        energy_change_j=(numerical.states[-1].internal_energy_j - numerical.states[0].internal_energy_j).tolist(),
        global_energy_changes_j=changes, balance_rows=len(finished.balances),
        checkpoint_sha256=hashlib.sha256(raw_checkpoint).hexdigest(), checkpoint_bytes=len(raw_checkpoint),
        controller_roundtrip=True, paths_equal_except_elapsed=True, parent_study_sha256=record.sha256,
        managed_audits=audits, material_qualified=False, training_eligible=False,
        full_firing_cycle=False, archived_source_resume_authorized=False)


def _execute_request(request_path):
    _require_isolated_entry()
    begin = time.monotonic()
    raw = read_record_bytes(request_path, 65536, size_reason='source_workflow_request_byte_limit',
                            regular_reason='source_workflow_request_regular_file')
    request = _load_request(raw)
    output = Path(request['output'])
    output.mkdir(parents=True, exist_ok=False)
    publish_record_bytes(output / 'request.json', raw, temporary_prefix='.source-workflow-')
    budget, opening, configured = None, None, False
    try:
        from ._heos_rhs_scope import _configure_workflow_deadline, _clear_workflow_deadline
        from .exact_event_clock import ExactEventTime as T
        from .exact_integration_checkpoint import _same
        from .exact_integration_checkpoint_codec import encode_exact_checkpoint, decode_exact_checkpoint
        from .run_service import read_run_with_source_record, runtime_identity
        from .source_run_config import load_source_run_config, WORKFLOW_PROFILE
        from .source_run_service import run_source_case
        from .source_trajectory import SourceOrdinaryStepSizes, open_source_trajectory
        runtime = runtime_identity()
        case_raw = read_record_bytes(request['case_path'], 65536,
            size_reason='source_workflow_case_byte_limit', regular_reason='source_workflow_case_regular_file')
        config = load_source_run_config(case_raw)
        _require(config.values['profile'] == WORKFLOW_PROFILE, 'source_workflow_implementation_required')
        limits = config.values['resources']
        _require(limits['outer_seconds'] <= 510. and limits['total_callback_cap'] <= 97
                 and limits['wet_pressure_request_cap'] <= 16, 'source_workflow_original_budget_ceiling')
        budget = _WorkflowBudget(begin, limits, '' if request['cancel_file'] == 'disabled' else request['cancel_file'])
        _configure_workflow_deadline(begin + limits['outer_seconds'])
        configured = True
        publish_record_bytes(output / 'case.json', case_raw, temporary_prefix='.source-workflow-')
        budget.parent = run_source_case(output / 'case.json', Path(request['assets_root']),
            output / 'parent', cancel=budget.cancel, managed_execution=True)
        _require_idle_scope()
        _require(budget.parent['status'] == 'completed' and budget.parent['numerical_event_accepted'],
                 'source_workflow_parent_not_numerically_accepted:' + str(budget.parent.get('reason')))
        print(json.dumps(dict(phase='parent_completed', counts=budget.parent['counts'],
                              elapsed_seconds=time.monotonic() - begin)), flush=True)
        _, _, record = read_run_with_source_record(output / 'parent')
        start = record.roots['transition'].candidates[1].end
        segment = request['segment']
        end = T(start.seconds + F(segment['duration_numerator'], segment['duration_denominator']))
        step = float(F(segment['step_numerator'], segment['step_denominator']))
        sizes = SourceOrdinaryStepSizes(step, step,
            'Original three-step conduction gate: 1/64 s initial/maximum steps; original tolerances and resources.')

        def open_segment(name):
            nonlocal opening
            opening = output / name
            session = open_source_trajectory(output / 'parent', opening, end=end,
                step_sizes=sizes, cancel=budget.cancel, managed_execution=True)
            budget.sessions.append(session)
            opening = None
            _require_idle_scope()
            _require(session.recorder.counts['rhs_started'] == budget.parent['counts']['rhs_started']
                     and all(session.recorder.counts[key] == budget.parent['counts'][key] + 4
                             for key in ('heos_started', 'heos_kernel_returned', 'heos_returned'))
                     and session.recorder.counts['initial_energy_started'] == budget.parent['counts']['initial_energy_started'],
                     'source_workflow_reconstruction_actual_counts')
            return session

        continuous = open_segment('continuous')
        baseline = continuous.advance()
        _require_idle_scope()
        _require(baseline.status == 'completed', 'source_workflow_continuous:' + str(baseline.reason))
        print(json.dumps(dict(phase='continuous_completed', counts=budget.counts(),
                              elapsed_seconds=time.monotonic() - begin)), flush=True)
        paused = open_segment('paused')
        prefix = paused.advance(pause_after_steps=segment['pause_after_steps'])
        _require_idle_scope()
        _require(prefix.status == 'paused' and len(prefix.execution.result.steps) == 1,
                 'source_workflow_original_one_step_pause_required')
        checkpoint = prefix.execution.checkpoint
        raw_checkpoint = encode_exact_checkpoint(checkpoint)
        publish_record_bytes(output / 'ordinary-checkpoint.json', raw_checkpoint, temporary_prefix='.source-workflow-')
        restored = decode_exact_checkpoint(read_record_bytes(output / 'ordinary-checkpoint.json',
            64 * 1024 * 1024, size_reason='source_workflow_checkpoint_byte_limit',
            regular_reason='source_workflow_checkpoint_regular_file'))
        _require(_same(restored, checkpoint) and paused.checkpoint is checkpoint,
                 'source_workflow_numeric_roundtrip_or_live_checkpoint_changed')
        finished = paused.advance()  # Original live checkpoint; decoded data stays passive.
        _require_idle_scope()
        _require(finished.status == 'completed', 'source_workflow_paused:' + str(finished.reason))
        result = _verify_paths(baseline, prefix, finished, paused, start, end, record, budget, raw_checkpoint)
        _require(not budget.cancel(), 'source_workflow_cancelled_before_publication')
        _require(runtime_identity() == runtime, 'source_workflow_runtime_changed')
        _clear_workflow_deadline()
        configured = False
        result.update(status='completed', case_sha256=config.sha256,
            request_sha256=hashlib.sha256(raw).hexdigest(), runtime_before=runtime, runtime_after=runtime_identity(),
            elapsed_seconds=time.monotonic() - begin, parent_elapsed_seconds=budget.parent['elapsed_wall_seconds'])
        _publish(output / 'ACCEPTANCE.json', result)
        return result
    except BaseException as exc:
        secondary, partial = [], None
        if opening is not None:
            try:
                partial = _partial_admission_counts(opening)
            except BaseException as reading:
                secondary.append(dict(stage='partial_admission_counts', type=type(reading).__name__, reason=str(reading)))
        counts = None if budget is None else budget.counts()
        if partial is not None and counts is not None:
            original = budget.parent['counts']
            counts = {key: value + partial[key] - original[key] for key, value in counts.items()}
        stops = [] if budget is None else [s.recorder.stop_status for s in budget.sessions]
        parent_status = None if budget is None or budget.parent is None else budget.parent['status']
        if budget is not None and time.monotonic() - begin >= budget.limits['outer_seconds']:
            budget.stop_reason = budget.stop_reason or 'combined_outer_seconds'
        status = ('resource_limit' if (budget is not None and budget.stop_reason is not None)
                  or 'resource_limit' in stops or parent_status == 'resource_limit' else
                  'cancelled' if 'cancelled' in stops or parent_status == 'cancelled'
                  or isinstance(exc, KeyboardInterrupt) or (budget is not None and budget.user_requested) else 'failed')
        if configured:
            try:
                _clear_workflow_deadline()
                configured = False
            except BaseException as closing:
                secondary.append(dict(stage='clear_deadline', type=type(closing).__name__, reason=str(closing)))
        failure = dict(status=status, exception_type=type(exc).__name__, reason=str(exc),
            elapsed_seconds=time.monotonic() - begin, total_known_actual_counts=counts,
            count_completeness='unknown_or_lower_bound' if counts is None or (opening is not None and partial is None)
                               else 'complete_observed_counts',
            admission_directory=None if opening is None else str(opening), partial_admission_counts=partial,
            stop_reason=None if budget is None else budget.stop_reason, secondary_errors=secondary,
            material_qualified=False, training_eligible=False, full_firing_cycle=False,
            archived_source_resume_authorized=False)
        try:
            _publish(output / 'FAILURE.json', failure)
        except BaseException as saving:
            exc.add_note('source workflow failure publication also failed: ' + repr(saving))
        raise


def main():
    _require_isolated_entry()
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -I -m sludge_sandbox.source_workflow_worker REQUEST.json')
    _execute_request(Path(sys.argv[1]))


if __name__ == '__main__':
    main()
