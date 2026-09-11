"""Dedicated data-only process for one source RHS comparison, never a resume.

Invoke with the installed interpreter's ``-I -m`` flags. The worker builds a
closed source model, checks one explicit numerical query and exits. No caller
callbacks, plugins, deserialized objects or interactive execution enter the RHS.
This operational isolation does not attest against hostile code in this process.
"""
import cProfile
from fractions import Fraction
import hashlib
import io
import json
import math
import os
from pathlib import Path
import pstats
import sys
import threading
import time

from .source_record_io import read_record_bytes, publish_record_bytes


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _load_request(raw):
    """Validate a bounded JSON query before importing native constructors."""
    from .source_run_config import _integer, _nonfinite, _pairs, _shape
    shape = dict(schema='str', execution_mode='str', case_path='str', assets_root='str',
        output='str', amounts_mol=[['float'] * 4 for _ in range(3)],
        internal_energy_j=['float'] * 3, time={'numerator': 'int', 'denominator': 'int'},
        interface_modes=['str'] * 3, origin={'kind': 'str', 'sha256': 'str'},
        timeout_seconds='float', material_qualified='bool')
    _require(type(raw) is bytes and 0 < len(raw) <= 65536, 'source_rhs_request_byte_limit')
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_nonfinite, parse_int=_integer)
        _shape(value, shape, 'source_rhs_request')
        _require(value['schema'] == 'source_rhs_request_v1' and
                 value['execution_mode'] in ('managed_single_rhs_v1', 'per_call') and
                 value['material_qualified'] is False, 'source_rhs_request_scope')
        _require(all(Path(value[key]).is_absolute() and '\x00' not in value[key]
                     for key in ('case_path', 'assets_root', 'output')), 'source_rhs_absolute_paths')
        _require(0 < value['timeout_seconds'] <= 120., 'source_rhs_request_deadline')
        _require(value['time']['numerator'] >= 0 and value['time']['denominator'] > 0 and
                 math.gcd(value['time']['numerator'], value['time']['denominator']) == 1,
                 'source_rhs_request_exact_time')
        _require(value['origin']['kind'] == 'saved_numerical_query_not_resume' and
                 len(value['origin']['sha256']) == 64 and
                 all(c in '0123456789abcdef' for c in value['origin']['sha256']),
                 'source_rhs_request_origin')
        for row, mode in zip(value['amounts_mol'], value['interface_modes']):
            _require(all(x >= 0 for x in row) and math.fsum(row[1:]) > 0,
                     'source_rhs_request_inventory')
            _require(mode in ('existing_liquid', 'depleted_no_nucleation') and
                     (row[0] == 0. if mode == 'depleted_no_nucleation' else row[0] > 0.),
                     'source_rhs_request_exact_interface_mode')
        return value
    except (TypeError, OverflowError, RecursionError, UnicodeError) as exc:
        raise ValueError('source_rhs_request_invalid') from exc


def _require_isolated_entry():
    if (__name__ != '__main__' or not sys.flags.isolated or
            threading.current_thread() is not threading.main_thread() or
            threading.active_count() != 1):
        raise RuntimeError('source_rhs_isolated_module_process_required')


def _publish(path, value):
    raw = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n'
    publish_record_bytes(path, raw, temporary_prefix='.source-rhs-')


def _save_profile(profiler, output):
    profiler.disable()
    profiler.dump_stats(output / 'profile.pstats')
    stream = io.StringIO()
    if profiler.getstats():
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative').print_stats(60)
        stats.sort_stats('tottime').print_stats(40)
    publish_record_bytes(output / 'PROFILE.txt', stream.getvalue().encode(), temporary_prefix='.source-rhs-')


def _execute_request(request_path):
    _require_isolated_entry()
    begin = time.monotonic()
    raw = read_record_bytes(request_path, 65536, size_reason='source_rhs_request_byte_limit',
                            regular_reason='source_rhs_request_regular_file')
    request = _load_request(raw)
    output = Path(request['output'])
    output.mkdir(parents=True, exist_ok=False)
    publish_record_bytes(output / 'request.json', raw, temporary_prefix='.source-rhs-')
    profiler = cProfile.Profile()
    admission = recorder = None
    admission_closed = False
    profile_attempted = False
    try:
        from ._heos_rhs_scope import _admit_worker, _close_worker, _worker_audit
        from .exact_event_clock import ExactEventTime
        from .run_service import runtime_identity
        from .source_run_builder import build_source_run
        from .source_run_config import load_source_run_config, validate_source_run_assets, RHS_PROFILE
        from .source_run_observer import observer_scope
        from .source_run_service import _Recorder

        runtime = runtime_identity()
        case_raw = read_record_bytes(request['case_path'], 65536,
            size_reason='source_rhs_case_byte_limit', regular_reason='source_rhs_case_regular_file')
        config = load_source_run_config(case_raw)
        _require(request['execution_mode'] != 'managed_single_rhs_v1' or config.values['profile'] == RHS_PROFILE,
                 'source_rhs_managed_implementation_required')
        assets = validate_source_run_assets(config, assets_root=Path(request['assets_root']))
        publish_record_bytes(output / 'case.json', config.canonical_bytes, temporary_prefix='.source-rhs-')
        recorder = _Recorder(output, None, begin)
        recorder.limits = config.values['resources']
        deadline = begin + min(request['timeout_seconds'], recorder.limits['outer_seconds'])
        with observer_scope(recorder):
            recorder.phase = 'source_rhs_new_implementation_reconstruction'
            recorder.guard()
            built = build_source_run(config, assets)
            recorder.built = built
            states = tuple(storage.state(row[0], tuple(row[1:]), energy)
                for storage, row, energy in zip(built.storages, request['amounts_mol'],
                                                request['internal_energy_j']))
            initial = built.adapter.pack(states)
            depleted = tuple(i for i, mode in enumerate(request['interface_modes'])
                             if mode == 'depleted_no_nucleation')
            adapter = built.adapter.with_depleted_cells(initial, depleted)
            _require(adapter.interfaces == tuple(request['interface_modes']), 'source_rhs_modes_changed')
            clock = ExactEventTime(Fraction(request['time']['numerator'], request['time']['denominator']))
            recorder.journal.append('source_rhs_query_admitted', dict(
                scope='new_implementation_numerical_query_not_resume', request=request,
                initial=initial, time=clock, adapter_provenance=adapter.provenance(),
                runtime=runtime, asset_manifest_sha256=assets.sha256))
            _require(time.monotonic() < deadline, 'source_rhs_deadline_before_admission')
            if request['execution_mode'] == 'managed_single_rhs_v1':
                admission = _admit_worker(adapter, supervisor_pid=os.getppid(), deadline_monotonic=deadline)
            reconstruction_seconds = time.monotonic() - begin
            recorder.phase = 'single_source_rhs_comparison'
            started = time.monotonic()
            try:
                profiler.enable()
                adapter.evaluate(initial, clock)
            finally:
                profiler.disable()
            rhs_seconds = time.monotonic() - started
            _require(time.monotonic() < deadline, 'source_rhs_deadline_after_evaluation')
        if admission is not None:
            _close_worker(admission)
            admission_closed = True
        built.check()
        _require(runtime_identity() == runtime, 'source_rhs_runtime_changed')
        counts = dict(recorder.counts)
        _require(all(counts[key] == expected for key, expected in (
            ('heos_started', 4), ('heos_kernel_returned', 4), ('heos_returned', 4),
            ('rhs_started', 1), ('rhs_returned', 1), ('initial_energy_started', 0),
            ('initial_energy_returned', 0), ('wet_started', 0), ('wet_returned', 0))),
            'source_rhs_actual_work_count')
        audit = None if admission is None else _worker_audit(admission)
        profile_attempted = True
        _save_profile(profiler, output)
        _publish(output / 'RESULT.json', dict(status='completed', execution_mode=request['execution_mode'],
            elapsed_seconds=time.monotonic() - begin, reconstruction_seconds=reconstruction_seconds,
            rhs_profiled_seconds=rhs_seconds, counts=counts, runtime=runtime, config_sha256=config.sha256,
            request_sha256=hashlib.sha256(raw).hexdigest(), asset_manifest_sha256=assets.sha256,
            managed_audit=audit,
            accepted_steps=0, source_resume_authorized=False, material_qualified=False,
            scope='single_new_implementation_numerical_query_not_resume'))
    except BaseException as exc:
        profiler.disable()
        secondary_errors = []
        if admission is not None and not admission_closed:
            try:
                _close_worker(admission)
            except BaseException as closing:
                exc.add_note('source RHS worker close also failed: ' + repr(closing))
                secondary_errors.append(dict(stage='close', exception=type(closing).__name__, reason=str(closing)))
        audit = None
        if admission is not None:
            try:
                audit = _worker_audit(admission)
            except BaseException as auditing:
                secondary_errors.append(dict(stage='audit', exception=type(auditing).__name__, reason=str(auditing)))
        if not profile_attempted:
            profile_attempted = True
            try:
                _save_profile(profiler, output)
            except BaseException as saving:
                secondary_errors.append(dict(stage='profile', exception=type(saving).__name__, reason=str(saving)))
        try:
            _publish(output / 'FAILURE.json', dict(status='failed', exception=type(exc).__name__,
                reason=str(exc), notes=getattr(exc, '__notes__', []),
                elapsed_seconds=time.monotonic() - begin,
                counts=None if recorder is None else dict(recorder.counts),
                managed_audit=audit, secondary_errors=secondary_errors,
                accepted_steps=0, source_resume_authorized=False, material_qualified=False))
        except BaseException as saving:
            exc.add_note('source RHS failure save also failed: ' + repr(saving))
        raise
    finally:
        profiler.disable()


def main():
    _require_isolated_entry()
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -I -m sludge_sandbox.source_managed_worker REQUEST.json')
    _execute_request(Path(sys.argv[1]))


if __name__ == '__main__':
    main()
