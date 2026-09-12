"""Application boundary fixtures only; no worker, native provider or integration."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace as NS

import pytest

from sludge_sandbox import source_execution_service as service
from sludge_sandbox.source_execution_worker import COUNTERS


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    """Stub scientific readers, retaining real admission, hashes and report checks."""
    root = tmp_path.resolve()
    source = root / 'source.json'
    source.write_bytes(b'{"fixture":"manufactured application case"}\n')
    assets = root / 'assets'
    assets.mkdir()
    job = root / 'job'
    job.mkdir()
    runtime = {'manufactured_test_runtime': True}
    config = NS(values={'profile': 'source_multicell_wet_to_dry_heos_resume_v4'},
                sha256=hashlib.sha256(b'{"fixture":"canonical"}').hexdigest())
    monkeypatch.setattr(service, 'runtime_identity', lambda: runtime)
    monkeypatch.setattr(service, 'load_source_run_config', lambda raw: config)
    monkeypatch.setattr(service, 'required_source_assets', lambda profile: ())
    monkeypatch.setattr(service, 'validate_source_run_assets', lambda *a, **kw: NS(sha256='a'*64))
    request = dict(schema='source_execution_request_v1', operation='source-run',
        source=str(source), assets_root=str(assets), output=str(job / 'execution'),
        cancel_file=str(job / 'source-cancel'), shared_budget=None)
    request_path = root / 'request.json'
    write(request_path, request)
    return NS(root=root, job=job, source=source, assets=assets, runtime=runtime,
              config=config, request=request, request_path=request_path)


def prepare(fixture):
    write(fixture.request_path, fixture.request)
    return service.prepare_source_execution(fixture.request_path, fixture.job)


def result_fixture(fixture, monkeypatch):
    binding = prepare(fixture)
    output = fixture.job / 'execution'
    output.mkdir()
    (output / 'request.json').write_bytes(fixture.request_path.read_bytes())
    run = output / 'run'
    run.mkdir()
    (run / 'case.json').write_bytes(fixture.source.read_bytes())
    (run / 'config.json').write_bytes(b'{"fixture":"canonical"}')
    counts = dict.fromkeys(COUNTERS, 0)
    summary = dict(status='completed', reason=None, counts=counts,
        runtime_before=fixture.runtime, runtime_after=fixture.runtime,
        numerical_event_accepted=False, config_sha256=fixture.config.sha256,
        source_record={'sha256': 'b'*64}, material_qualified=False,
        training_eligible=False, full_firing_cycle=False, managed_execution=True,
        asset_manifest_sha256='a'*64)
    write(run / 'result.json', summary)
    manifest = {'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in run.iterdir()}}
    write(run / 'manifest.json', manifest)
    monkeypatch.setattr(service, 'read_run_with_source_record',
                        lambda path: (summary, manifest, NS(sha256='b'*64)))
    outcome = dict(schema='source_execution_outcome_v1', operation='source-run',
        status='completed', reason=None, details=dict(source_run_directory=str(run),
        numerical_event_accepted=False), counts=counts,
        declared_other_branch_counts=dict(counts), combined_counts=dict(counts),
        shared_budget_provenance='caller_declared_external_debits_not_authenticated',
        raw_case_sha256=binding['raw_case_sha256'], canonical_config_sha256=fixture.config.sha256,
        request_sha256=binding['request_sha256'], runtime_before=fixture.runtime,
        runtime_after=fixture.runtime, process_elapsed_seconds=0.1,
        material_qualified=False, training_eligible=False, full_firing_cycle=False,
        historical_study_resume_authorized=False)
    write(output / 'OUTCOME.json', outcome)
    return output, outcome, summary


def test_prepare_retains_exact_bytes_and_does_not_make_worker_output(fixture):
    raw = json.dumps(fixture.request, indent=3).encode() + b'\n\n'
    fixture.request_path.write_bytes(raw)
    binding = service.prepare_source_execution(fixture.request_path, fixture.job)
    assert (fixture.job / 'request.json').read_bytes() == raw
    assert binding['request_sha256'] == hashlib.sha256(raw).hexdigest()
    assert binding['operation'] == 'source-run'
    assert binding['runtime'] == fixture.runtime
    assert binding['preparation_seconds'] >= 0
    assert not (fixture.job / 'execution').exists()
    assert json.loads((fixture.job / 'INPUT_BINDING.json').read_bytes()) == binding


@pytest.mark.parametrize('change', [dict(output='/private/tmp/elsewhere'),
    dict(cancel_file='disabled'), dict(operation='python'), dict(source_resume_authorized=True),
    dict(shared_budget={'other_counts': dict.fromkeys(COUNTERS, 0),
        'outer_remaining_seconds': 1., 'total_callback_cap': 1, 'wet_pressure_request_cap': 1})])
def test_prepare_closed_control_and_fixed_paths(fixture, change):
    fixture.request.update(change)
    with pytest.raises(ValueError):
        prepare(fixture)
    assert not (fixture.job / 'execution').exists()
    assert not (fixture.job / 'INPUT_BINDING.json').exists()


@pytest.mark.parametrize('name', ['execution', 'source-cancel', 'INPUT_BINDING.json', 'request.json'])
def test_prepare_never_reuses_existing_or_broken_symlink_output(fixture, name):
    (fixture.job / name).symlink_to(fixture.root / 'missing')
    with pytest.raises(ValueError):
        prepare(fixture)


def test_input_symlink_and_asset_overlap_rejected(fixture):
    link = fixture.root / 'source-link.json'
    link.symlink_to(fixture.source)
    fixture.request['source'] = str(link)
    with pytest.raises(ValueError):
        prepare(fixture)
    fixture.request['source'] = str(fixture.source)
    fixture.request['assets_root'] = str(fixture.root)
    with pytest.raises(ValueError, match='overlap'):
        prepare(fixture)


@pytest.mark.parametrize('raw', [b'{"a":1,"a":2}', b'{"x":NaN}', b' '*65537,
    b'['*101+b'0'+b']'*101])
def test_request_bounds_before_publication(fixture, raw):
    fixture.request_path.write_bytes(raw)
    with pytest.raises(ValueError):
        service.prepare_source_execution(fixture.request_path, fixture.job)
    assert not (fixture.job / 'request.json').exists()


def test_completed_is_not_numerical_event_or_material_qualification(fixture, monkeypatch):
    result_fixture(fixture, monkeypatch)
    observed = service.inspect_source_execution(fixture.job, returncode=0)
    assert observed['status'] == observed['reported_status'] == 'completed'
    assert observed['record_valid'] is True
    assert observed['numerical_event_accepted'] is False
    assert observed['restore_available'] is False
    assert not any(observed['qualification'].values())
    assert observed['new_eos_calls'] == 0
    assert observed['new_physical_integration'] is False


@pytest.mark.parametrize('returncode,cause,status', [(1, None, 'abnormal_exit'),
    (-9, None, 'abnormal_exit'), (0, 'user_cancel', 'cancelled'),
    (0, 'wall_timeout', 'resource_limit'), (None, None, 'unverified_result')])
def test_process_observation_cannot_be_replaced_by_success_report(fixture, monkeypatch,
                                                                returncode, cause, status):
    result_fixture(fixture, monkeypatch)
    result = service.inspect_source_execution(fixture.job, returncode=returncode,
                                               termination_cause=cause)
    assert result['status'] == status
    assert result['reported_status'] == 'completed'
    assert result['record_valid'] is True
    assert result['restore_available'] is False


@pytest.mark.parametrize('change', [dict(material_qualified=True), dict(counts={}),
    dict(counts={**dict.fromkeys(COUNTERS, 0), 'rhs_started': True}),
    dict(combined_counts={**dict.fromkeys(COUNTERS, 0), 'rhs_started': 1}),
    dict(request_sha256='0'*64), dict(raw_case_sha256='0'*64),
    dict(canonical_config_sha256='0'*64), dict(runtime_after={'changed': True}),
    dict(details={'source_run_directory': '/private/tmp/unrelated', 'numerical_event_accepted': False}),
    dict(process_elapsed_seconds=True), dict(process_elapsed_seconds=float('inf')),
    dict(extra='unrecognized')])
def test_success_report_mutation_does_not_pass(fixture, monkeypatch, change):
    output, outcome, _ = result_fixture(fixture, monkeypatch)
    outcome.update(change)
    write(output / 'OUTCOME.json', outcome)
    result = service.inspect_source_execution(fixture.job, returncode=0)
    assert result['status'] == 'unverified_result'
    assert result['record_valid'] is False


def test_underlying_run_correspondence_and_request_copy_are_required(fixture, monkeypatch):
    output, _, summary = result_fixture(fixture, monkeypatch)
    summary['numerical_event_accepted'] = True
    assert not service.inspect_source_execution(fixture.job, returncode=0)['record_valid']
    summary['numerical_event_accepted'] = False
    (output / 'request.json').write_bytes(fixture.request_path.read_bytes() + b' ')
    assert not service.inspect_source_execution(fixture.job, returncode=0)['record_valid']


@pytest.mark.parametrize('field,value', [('managed_execution', False),
                                        ('asset_manifest_sha256', '0'*64)])
def test_run_cannot_change_admitted_managed_mode_or_asset_identity(fixture, monkeypatch, field, value):
    _, _, summary = result_fixture(fixture, monkeypatch)
    summary[field] = value
    assert not service.inspect_source_execution(fixture.job, returncode=0)['record_valid']


def failure():
    return dict(schema='source_execution_failure_v1', status='failed',
        exception_type='RuntimeError', reason='manufactured fixture failure',
        process_elapsed_seconds=0.1, operation_status=None, operation_reason=None,
        counts=None, count_completeness='unknown', combined_counts=None,
        stop_reason=None, secondary_errors=[], material_qualified=False,
        training_eligible=False, full_firing_cycle=False, historical_study_resume_authorized=False)


def test_failed_work_keeps_unknown_counts_and_original_exception(fixture):
    prepare(fixture)
    output = fixture.job / 'execution'
    output.mkdir()
    (output / 'request.json').write_bytes(fixture.request_path.read_bytes())
    write(output / 'FAILURE.json', failure())
    result = service.inspect_source_execution(fixture.job, returncode=1)
    assert result['status'] == 'run_failed'
    assert result['reported_status'] == 'failed'
    assert result['failure']['counts'] is None
    assert result['failure']['count_completeness'] == 'unknown'
    assert result['failure']['exception_type'] == 'RuntimeError'
    assert result['restore_available'] is False


def test_missing_and_conflicting_terminal_files_remain_unverified(fixture, monkeypatch):
    output, _, _ = result_fixture(fixture, monkeypatch)
    write(output / 'FAILURE.json', failure())
    conflicting = service.inspect_source_execution(fixture.job, returncode=0)
    assert conflicting['status'] == 'unverified_result'
    assert conflicting['outcome']['status'] == 'completed'
    assert conflicting['failure']['status'] == 'failed'
    (output / 'OUTCOME.json').unlink()
    (output / 'FAILURE.json').unlink()
    result = service.inspect_source_execution(fixture.job, returncode=-9)
    assert result['status'] == 'abnormal_exit'
    assert result['record_valid'] is False
    assert result['reported_status'] is None


@pytest.mark.parametrize('returncode', [True, False, 0.0])
def test_process_exit_code_cannot_be_coerced_to_zero(fixture, returncode):
    with pytest.raises(ValueError, match='returncode'):
        service.inspect_source_execution(fixture.job, returncode=returncode)


def test_persisted_process_observation_is_labelled_and_not_pid_liveness(fixture, monkeypatch):
    result_fixture(fixture, monkeypatch)
    write(fixture.job / 'job.json', dict(schema='sandbox_job_v1', operation='source-execute',
        input_binding=json.loads((fixture.job / 'INPUT_BINDING.json').read_bytes()),
        returncode=0, child_reaped=True, termination_cause=None, pid=999999))
    result = service.inspect_source_execution(fixture.job)
    assert result['status'] == 'completed'
    assert result['process_observation']['provenance'] == 'persisted_not_live_process_proof'


@pytest.mark.parametrize('claim', ['none', 'directory', 'failed', 'broken_symlink'])
def test_valid_packet_is_distinct_from_remaining_one_use_authority(tmp_path, monkeypatch, claim):
    packet = tmp_path.resolve() / 'packet'
    packet.mkdir()
    write(packet / 'manifest.json', {'fixture': True})
    write(packet / 'packet.json', {'fixture': True})
    fake = NS(envelope={'charged_segment_seconds_hex': (1.).hex()},
        files={}, parent_record=NS(sha256='b'*64),
        last_result=NS(counts=tuple(dict.fromkeys(COUNTERS, 0).items()),
                       execution=NS(result=NS(steps=(object(),)), observations=())),
        checkpoint=NS(problem=NS(start_s=NS(seconds=Fraction(1, 64)),
                                end_s=NS(seconds=Fraction(3, 64)))))
    monkeypatch.setattr(service, 'read_source_trajectory_checkpoint', lambda path: fake)
    if claim == 'broken_symlink':
        (packet / '.restore-attempt').symlink_to(packet / 'absent')
    elif claim != 'none':
        (packet / '.restore-attempt').mkdir()
        if claim == 'failed':
            write(packet / '.restore-attempt' / 'failed.json', {'status': 'failed'})
    result = service.inspect_source_checkpoint(packet)
    assert result['record_valid'] is True
    assert result['restore_available'] is (claim == 'none')
    assert not any(result['qualification'].values())


@pytest.mark.parametrize('marker', ['WORKER_FAILURE.json', 'SAVE_FAILURE.json', 'FINALIZING.json'])
def test_late_failure_revokes_packet_even_if_reader_would_ignore_extra_marker(tmp_path,
                                                                           monkeypatch, marker):
    packet = tmp_path.resolve() / 'packet'
    packet.mkdir()
    write(packet / marker, {})
    monkeypatch.setattr(service, 'read_source_trajectory_checkpoint',
                        lambda path: pytest.fail('late failure must precede packet validation'))
    result = service.inspect_source_checkpoint(packet)
    assert result['record_valid'] is False
    assert result['restore_available'] is False


def advance_fixture(fixture, monkeypatch):
    parent = fixture.root / 'parent'
    parent.mkdir()
    (parent / 'case.json').write_bytes(fixture.source.read_bytes())
    counts = dict.fromkeys(COUNTERS, 0)
    start = Fraction(2**80 + 19, 3)
    record = NS(sha256='b'*64, roots={'transition': NS(candidates=(None,
        NS(reference=NS(times_s=(NS(seconds=start),)))))})
    summary = dict(status='completed', numerical_event_accepted=True,
        counts=counts, config_sha256=fixture.config.sha256,
        runtime_before=fixture.runtime, runtime_after=fixture.runtime,
        asset_manifest_sha256='a'*64, managed_execution=True)
    monkeypatch.setattr(service, 'read_run_with_source_record', lambda path: (summary, {}, record))
    fixture.request.pop('assets_root')
    end = start + Fraction(3, 64)
    fixture.request.update(operation='source-advance', source=str(parent),
        end=dict(numerator=end.numerator, denominator=end.denominator), pause_after_steps=1,
        step_sizes=dict(initial_step_s=1/64, maximum_step_s=1/64,
                        rationale='Manufactured application fixture.'))
    return parent, summary, record


def test_advance_admission_keeps_exact_large_clock_and_original_parent_bytes(fixture, monkeypatch):
    parent, _, _ = advance_fixture(fixture, monkeypatch)
    binding = prepare(fixture)
    copied = json.loads((fixture.job / 'request.json').read_bytes())
    assert copied['end']['numerator'] > 2**80
    assert copied['end'] == fixture.request['end']
    assert binding['parent_study_sha256'] == 'b'*64
    assert binding['input_files']['case.json'][0] == hashlib.sha256((parent / 'case.json').read_bytes()).hexdigest()
    assert copied['pause_after_steps'] == 1


@pytest.mark.parametrize('field,value', [('runtime_after', {'old_runtime': True}),
    ('managed_execution', False), ('numerical_event_accepted', False),
    ('config_sha256', '0'*64), ('asset_manifest_sha256', '0'*64)])
def test_advance_admission_requires_original_accepted_managed_current_parent(fixture, monkeypatch,
                                                                            field, value):
    _, summary, _ = advance_fixture(fixture, monkeypatch)
    summary[field] = value
    with pytest.raises(ValueError):
        prepare(fixture)


def test_advance_endpoint_must_follow_parent(fixture, monkeypatch):
    _, _, record = advance_fixture(fixture, monkeypatch)
    start = record.roots['transition'].candidates[1].reference.times_s[-1].seconds
    fixture.request['end'] = dict(numerator=start.numerator, denominator=start.denominator)
    with pytest.raises(ValueError, match='end_must_follow_parent'):
        prepare(fixture)


@pytest.mark.parametrize('claim', ['directory', 'broken_symlink'])
def test_resume_preflight_refuses_consumed_input_before_packet_reader(fixture, monkeypatch, claim):
    parent, _, _ = advance_fixture(fixture, monkeypatch)
    packet = fixture.root / 'packet'
    shutil.copytree(parent, packet / 'parent')
    if claim == 'directory':
        (packet / '.restore-attempt').mkdir()
    else:
        (packet / '.restore-attempt').symlink_to(packet / 'absent')
    fixture.request.pop('end')
    fixture.request.pop('step_sizes')
    fixture.request.update(operation='source-resume', source=str(packet), pause_after_steps=0)
    monkeypatch.setattr(service, 'read_source_trajectory_checkpoint',
                        lambda path: pytest.fail('already claimed: reader and launch must not run'))
    with pytest.raises(ValueError, match='restore_already_claimed'):
        prepare(fixture)


def test_moved_advance_job_never_follows_historical_external_source(fixture, monkeypatch):
    advance_fixture(fixture, monkeypatch)
    binding = prepare(fixture)
    moved = fixture.root / 'moved-job'
    shutil.copytree(fixture.job, moved)
    monkeypatch.setattr(service, '_tree', lambda *a, **kw: pytest.fail('must reject before source read'))
    with pytest.raises(ValueError, match='moved_job_requires_explicit_input_rebinding'):
        service._bound_parent(moved, binding, fixture.request)


def test_nofollow_ancestor_and_fifo_reads_are_rejected_without_waiting(tmp_path):
    import os
    actual = tmp_path.resolve() / 'actual'
    actual.mkdir()
    (actual / 'source.json').write_bytes(b'{}')
    alias = actual.parent / 'alias'
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(OSError):
        service._read(alias / 'source.json')
    fifo = actual / 'fifo'
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match='regular_file'):
        service._read(fifo)


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":1e999}', b'{"x":NaN}'])
def test_archive_tree_strict_json_before_underlying_reader(tmp_path, raw):
    path = tmp_path.resolve()
    (path / 'source.json').write_bytes(raw)
    with pytest.raises(ValueError):
        service._tree(path)


def test_aggregate_tree_limits_are_enforced(tmp_path, monkeypatch):
    path = tmp_path.resolve()
    (path / 'one.json').write_bytes(b'{"x":[1,2,3]}')
    (path / 'two.json').write_bytes(b'{"x":[4,5,6]}')
    monkeypatch.setattr(service, 'MAX_TREE_JSON_VALUES', 7)
    with pytest.raises(ValueError, match='tree_json_work_limit'):
        service._tree(path)


@pytest.fixture
def restore_claim(tmp_path):
    source = tmp_path.resolve() / 'packet'
    target = tmp_path.resolve() / 'job' / 'execution'
    original = NS(envelope={'charged_segment_seconds_hex': (2.).hex()},
        last_result=NS(counts=tuple(dict.fromkeys(COUNTERS, 0).items())))
    saved = NS(envelope={'charged_segment_seconds_hex': (5.).hex()})
    request = {'output': str(target)}
    write(source / 'events/000001.json', {'event': 'ordinary_segment_returned', 'ordinal': 1})
    shutil.copytree(source / 'events', target / 'trajectory/events')
    events = ('heos_started', 'heos_kernel_returned', 'heos_returned', 'source_trajectory_reconstructed')
    for number, kind in enumerate(events, 2):
        write(target / f'trajectory/events/{number:06d}.json', {'event': kind, 'ordinal': number})
    counts = {**dict.fromkeys(COUNTERS, 0), 'heos_started': 1,
              'heos_kernel_returned': 1, 'heos_returned': 1}
    write(source / '.restore-attempt/started.json', {'output': str(target / 'trajectory'),
                                                   'started_wall_time_ns': 1})
    claim = dict(status='live_session_restored', output=str(target / 'trajectory'),
                 counts=counts, charged_segment_seconds=3.)
    write(source / '.restore-attempt/restored.json', claim)
    return source, request, original, saved, claim


def test_paused_claim_counts_and_saved_charge_match_new_reconstruction(restore_claim):
    source, request, original, saved, _ = restore_claim
    service._verify_paused_claim(source, request, original, saved)


@pytest.mark.parametrize('mutation', ['counts', 'charged_before_saved', 'charged_after_new_saved',
                                    'missing_reconstruction', 'failed', 'wrong_target'])
def test_paused_claim_cannot_reset_debit_or_misbind_reconstruction(restore_claim, mutation):
    source, request, original, saved, claim = restore_claim
    if mutation == 'counts':
        claim['counts'] = dict.fromkeys(COUNTERS, 0)
    elif mutation == 'charged_before_saved':
        claim['charged_segment_seconds'] = 1.
    elif mutation == 'charged_after_new_saved':
        claim['charged_segment_seconds'] = 6.
    elif mutation == 'missing_reconstruction':
        (Path(request['output']) / 'trajectory/events/000005.json').unlink()
    elif mutation == 'failed':
        write(source / '.restore-attempt/failed.json', {'status': 'failed'})
    else:
        claim['output'] = '/private/tmp/wrong-trajectory'
    write(source / '.restore-attempt/restored.json', claim)
    with pytest.raises(ValueError):
        service._verify_paused_claim(source, request, original, saved)


def paused_correspondence_fixture(tmp_path, monkeypatch, operation):
    """Real NumPy numerical problem, with explicitly fake passive packet shells."""
    import numpy as np
    from sludge_sandbox.exact_event_clock import ExactEventTime
    from sludge_sandbox.exact_integration_checkpoint import ExactIntegrationProblem
    from sludge_sandbox.integration import ConservedState, IntegrationPolicy
    from sludge_sandbox.source_trajectory import SourceOrdinaryStepSizes

    def packet(steps):
        policy = IntegrationPolicy(1/64, 1/64, 1/1024, 1e-5, 1e-6, 1e-6, 1., 1., 10, 10, 3.)
        state = ConservedState(np.array([[1., 2.], [3., 4.]]), np.array([5., 6.]))
        problem = ExactIntegrationProblem(state, ExactEventTime(Fraction(0)),
                                         ExactEventTime(Fraction(3, 64)), policy, ())
        return NS(envelope={'fixture': 'manufactured application shell'},
            last_result=NS(counts=tuple(dict.fromkeys(COUNTERS, 0).items()),
                reason='accepted_boundary_pause_requested',
                execution=NS(result=NS(steps=(None,) * steps), observations=())),
            files={'ordinary-checkpoint.json': ['a'*64, 0]},
            parent_record=NS(sha256='b'*64), checkpoint=NS(problem=problem),
            step_sizes=SourceOrdinaryStepSizes(1/64, 1/64, 'Manufactured numerical fixture.'))

    directory, source = tmp_path.resolve() / 'job', tmp_path.resolve() / 'source'
    saved, original = packet(1 if operation == 'source-advance' else 2), packet(1)
    request = dict(operation=operation, source=str(source), output=str(directory / 'execution'),
        pause_after_steps=1, end=dict(numerator=3, denominator=64),
        step_sizes=dict(initial_step_s=1/64, maximum_step_s=1/64,
                        rationale='Manufactured numerical fixture.'))
    checkpoint = dict(saved.envelope, directory=str(directory / 'execution/resume-point'),
        disposition='saved_and_live_session_suspended', counts=dict(saved.last_result.counts),
        checkpoint_sha256='a'*64)
    outcome = dict(counts=dict(saved.last_result.counts), reason=saved.last_result.reason,
        details=dict(saved_checkpoint=checkpoint, parent_study_sha256='b'*64,
            accepted_steps=len(saved.last_result.execution.result.steps), observations=0))
    monkeypatch.setattr(service, '_read_checkpoint', lambda path: original if path == source else saved)
    monkeypatch.setattr(service, '_tree', lambda *a, **kw: {})
    monkeypatch.setattr(service, '_bound_parent', lambda *a: source / 'parent')
    monkeypatch.setattr(service, '_verify_paused_claim', lambda *a: None)
    monkeypatch.setattr(service, '_read', lambda *a, **kw: b'{}')
    monkeypatch.setattr(service, '_exists', lambda *a: False)
    return (directory, {'input_files': {}}, request, outcome), saved, original


@pytest.mark.parametrize('operation', ['source-advance', 'source-resume'])
def test_paused_correspondence_preserves_real_numpy_problem_and_four_part_steps(tmp_path,
                                                                               monkeypatch, operation):
    args, _, _ = paused_correspondence_fixture(tmp_path, monkeypatch, operation)
    assert service._verify_paused(*args)['restore_available'] is True


@pytest.mark.parametrize('operation', ['source-advance', 'source-resume'])
@pytest.mark.parametrize('count', [0, 2])
def test_paused_request_must_match_newly_accepted_steps(tmp_path, monkeypatch, operation, count):
    args, _, _ = paused_correspondence_fixture(tmp_path, monkeypatch, operation)
    args[2]['pause_after_steps'] = count
    with pytest.raises(ValueError, match='paused_requested'):
        service._verify_paused(*args)


def test_resumed_pause_must_keep_original_numpy_state(tmp_path, monkeypatch):
    from dataclasses import replace
    args, saved, _ = paused_correspondence_fixture(tmp_path, monkeypatch, 'source-resume')
    initial = saved.checkpoint.problem.initial
    changed = replace(initial, internal_energy_j=initial.internal_energy_j + 1.)
    saved.checkpoint.problem = replace(saved.checkpoint.problem, initial=changed)
    with pytest.raises(ValueError, match='paused_resume_original_problem'):
        service._verify_paused(*args)
