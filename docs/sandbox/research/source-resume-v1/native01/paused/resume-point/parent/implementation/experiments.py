"""Bounded sequential manufactured experiments over the shared job service.

Frozen input hashes are local integrity evidence, not signatures or material
qualification. A recorded seed does not imply a random generator is implemented.
Incomplete interruption accounting is refused rather than refunded silently.
"""
from __future__ import annotations

from contextlib import contextmanager
from fractions import Fraction
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import time
from typing import Any, Callable, Iterator
import uuid

from .job_supervisor import SupervisionPolicy, read_job, supervise
from .run_provenance import evidence_paths, load_catalog
from .run_service import read_run, runtime_identity
from .verification_case import read_case


class ExperimentError(ValueError):
    def __init__(self, reason: str, code: str = 'invalid_experiment') -> None:
        super().__init__(reason)
        self.code = code


def _require(condition: bool, reason: str, code: str = 'invalid_experiment') -> None:
    if not condition:
        raise ExperimentError(reason, code)


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ExperimentError('nonfinite_json')


def _float(value: str) -> float:
    result = float(value)
    _require(math.isfinite(result), 'nonfinite_json')
    return result


def _load(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant, parse_float=_float)
    except (ValueError, RecursionError) as exc:
        raise ExperimentError('invalid_json:'+str(exc)) from exc


def _raw(value: Any) -> bytes:
    return (json.dumps(value, allow_nan=False, ensure_ascii=False, indent=2)+'\n').encode()


def _write(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_bytes(_raw(value))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _safe_id(value: Any) -> str:
    _require(type(value) is str and re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', value) is not None,
             'invalid_identifier')
    return value


def _bounded(value: Any, maximum: float, name: str, *, integer: bool = False) -> None:
    try:
        valid = (type(value) is int if integer else type(value) in (int, float)) and math.isfinite(value) and 0 < value <= maximum
    except OverflowError:
        valid = False
    _require(valid, 'invalid_'+name)


def _spec(raw: bytes) -> dict[str, Any]:
    spec = _load(raw)
    _require(type(spec) is dict and set(spec) == {'schema', 'experiment_id', 'mode', 'seed', 'candidates', 'budget'},
             'invalid_spec_fields')
    _require(spec['schema'] == 'sandbox_experiment_v1', 'unsupported_schema')
    _require(spec['mode'] == 'manufactured_verification', 'material_evidence_not_admitted', 'evidence_incomplete')
    _safe_id(spec['experiment_id'])
    _require(type(spec['seed']) is int and spec['seed'] >= 0, 'invalid_seed')
    candidates = spec['candidates']
    _require(type(candidates) is list and 1 <= len(candidates) <= 20, 'invalid_candidates')
    seen = set()
    for candidate in candidates:
        _require(type(candidate) is dict and set(candidate) == {'id', 'case'}, 'invalid_candidate_fields')
        identifier = _safe_id(candidate['id'])
        _require(identifier not in seen, 'duplicate_candidate_id')
        seen.add(identifier)
    budget = spec['budget']
    _require(type(budget) is dict and set(budget) == {'maximum_jobs', 'maximum_total_wall_seconds',
             'per_job_wall_seconds', 'cancel_grace_seconds'}, 'invalid_budget_fields')
    for name, maximum in (('maximum_jobs', 20), ('maximum_total_wall_seconds', 600),
                          ('per_job_wall_seconds', 120), ('cancel_grace_seconds', 5)):
        _bounded(budget[name], maximum, name, integer=name == 'maximum_jobs')
    return spec


def _path(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    _require(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name and str(relative) == name,
             'invalid_artifact_path')
    path = root/name
    _require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'invalid_artifact_path')
    return path


def _upper(value: Fraction) -> float:
    rounded = float(value)
    return math.nextafter(rounded, math.inf) if Fraction(rounded) < value else rounded


def _lower(value: Fraction) -> float:
    rounded = float(value)
    return math.nextafter(rounded, 0.0) if Fraction(rounded) > value else rounded


def prepare_experiment(spec_path: str | Path, output: str | Path, *,
                       water_directory: str | Path,
                       evidence_directory: str | Path | None = None) -> dict[str, Any]:
    raw = Path(spec_path).read_bytes()
    spec = _spec(raw)
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=False)
    inputs = directory/'inputs'
    inputs.mkdir()
    (inputs/'spec.json').write_bytes(raw)
    _write(inputs/'runtime.json', runtime_identity())
    (inputs/'cases').mkdir()
    candidates = []
    for candidate in spec['candidates']:
        identifier = candidate['id']
        path = inputs/'cases'/(identifier+'.json')
        path.write_bytes(_raw(candidate['case']))
        entry = {'id': identifier, 'case_artifact': 'inputs/cases/'+identifier+'.json',
                 'case_sha256': _hash(path.read_bytes()), 'classification': 'manufactured_verification',
                 'status': 'pending', 'reason': None, 'attempt_ids': []}
        try:
            case = read_case(path)
            entry['model_id'] = case.payload['model_id']
        except ValueError as exc:
            code = getattr(exc, 'code', 'invalid_case')
            entry.update(status='not_runnable', classification=code if code in
                         ('evidence_incomplete', 'unsupported_model', 'invalid_case') else 'invalid_case',
                         reason=str(exc))
        candidates.append(entry)
    (inputs/'water').mkdir()
    for source in sorted(Path(water_directory).iterdir()):
        _require(source.is_file() and not source.is_symlink(), 'water_requires_regular_files')
        (inputs/'water'/source.name).write_bytes(source.read_bytes())
    missing = []
    evidence_root = None if evidence_directory is None else Path(evidence_directory).resolve()
    for name in evidence_paths(load_catalog()):
        source = None if evidence_root is None else _path(evidence_root, name)
        if source is not None and source.is_file():
            destination = _path(inputs/'evidence', name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        else:
            missing.append(name)
    experiment_uuid = str(uuid.uuid4())
    _write(inputs/'preparation.json', {'experiment_uuid': experiment_uuid, 'candidates': candidates,
           'missing_evidence_assets': missing, 'seed_semantics': 'Recorded only; no random generator is used.'})
    files = {p.relative_to(directory).as_posix(): _hash(p.read_bytes()) for p in sorted(inputs.rglob('*')) if p.is_file()}
    manifest = {'schema': 'sandbox_experiment_inputs_v1', 'files': files}
    _write(directory/'inputs-manifest.json', manifest)
    (directory/'jobs').mkdir()
    state = {'schema': 'sandbox_experiment_state_v1', 'experiment_uuid': experiment_uuid,
             'experiment_id': spec['experiment_id'], 'inputs_manifest_sha256': _hash(_raw(manifest)),
             'status': 'prepared', 'reason': None, 'candidates': candidates, 'attempts': [],
             'invocations': [], 'charged_wall_seconds': 0.0, 'consumed_cancel_request_id': None,
             'scientific_status': 'manufactured_verification_only', 'material_qualified': False,
             'training_eligible': False}
    _write(directory/'state.json', state)
    return read_experiment(directory)


def _verified(directory: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        return _verified_records(directory)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ExperimentError('malformed_experiment_record') from exc


def _verified_records(directory: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest_raw = (directory/'inputs-manifest.json').read_bytes()
    manifest = _load(manifest_raw)
    _require(type(manifest) is dict and manifest.get('schema') == 'sandbox_experiment_inputs_v1' and
             type(manifest.get('files')) is dict, 'invalid_inputs_manifest')
    for name, digest in manifest['files'].items():
        _require(name.startswith('inputs/'), 'invalid_input_membership')
        path = _path(directory, name)
        _require(path.is_file() and _hash(path.read_bytes()) == digest, 'frozen_input_changed:'+name)
    actual = {p.relative_to(directory).as_posix() for p in (directory/'inputs').rglob('*') if p.is_file()}
    _require(actual == set(manifest['files']), 'frozen_input_membership_changed')
    spec = _spec((directory/'inputs/spec.json').read_bytes())
    state = _load((directory/'state.json').read_bytes())
    preparation = _load((directory/'inputs/preparation.json').read_bytes())
    _require(state['schema'] == 'sandbox_experiment_state_v1' and
             state['inputs_manifest_sha256'] == _hash(manifest_raw) and
             state['experiment_uuid'] == preparation['experiment_uuid'] and
             state['experiment_id'] == spec['experiment_id'], 'experiment_state_binding_mismatch')
    _require(len(state['candidates']) == len(preparation['candidates']), 'candidate_membership_changed')
    for current, frozen in zip(state['candidates'], preparation['candidates']):
        for key in ('id', 'case_artifact', 'case_sha256', 'classification'):
            _require(current[key] == frozen[key], 'candidate_input_binding_mismatch')
    return spec, state, manifest


def read_experiment(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    spec, state, manifest = _verified(directory)
    return {**state, 'budget': spec['budget'], 'seed': spec['seed'],
            'observation_status': 'persisted_not_live_process_proof',
            'inputs_manifest': manifest}


def request_experiment_cancel(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    _, state, _ = _verified(directory)
    request = {'schema': 'sandbox_experiment_cancel_v1', 'experiment_uuid': state['experiment_uuid'],
               'request_id': str(uuid.uuid4())}
    _write(directory/'cancel.json', request)
    return {**request, 'status': 'request_recorded_not_cancellation_confirmation'}


@contextmanager
def _lock(directory: Path) -> Iterator[None]:
    fd = os.open(directory/'.experiment.lock', os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ExperimentError('experiment_already_owned') from exc
        yield
    finally:
        os.close(fd)


def _job(directory: Path, attempt: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    job_directory = _path(directory, attempt['job_artifact'])
    job = read_job(job_directory)
    raw = (job_directory/'job.json').read_bytes()
    _require(_load(raw) == {k: v for k, v in job.items() if k != 'observation_status'}, 'job_changed_during_read')
    return job, raw


def _bound_result(directory: Path, attempt: dict[str, Any], candidate: dict[str, Any],
                  manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    run_directory = _path(directory, attempt['job_artifact'])/'run'
    result, run_manifest = read_run(run_directory)
    frozen_runtime = _load((directory/'inputs/runtime.json').read_bytes())
    _require(result['case_sha256'] == candidate['case_sha256'] and
             result['runtime_before'] == result['runtime_after'] == frozen_runtime,
             'result_case_or_runtime_mismatch')
    expected_sources = {name[len('inputs/'):] for name in manifest['files']
                        if name.startswith(('inputs/water/', 'inputs/evidence/'))}
    actual_sources = {name for name in run_manifest['files'] if name.startswith(('water/', 'evidence/'))}
    _require(actual_sources == expected_sources, 'result_source_membership_mismatch')
    for name, digest in frozen_runtime['modules'].items():
        _require(run_manifest['files'].get('implementation/'+name) == digest, 'result_implementation_mismatch')
    _require(run_manifest['files'].get('equation_catalog.json') ==
             frozen_runtime['catalogs']['wet-slab-equations-v1.json'], 'result_catalog_mismatch')
    for name, digest in manifest['files'].items():
        if name.startswith(('inputs/water/', 'inputs/evidence/')):
            _require(run_manifest['files'].get(name[len('inputs/'):]) == digest, 'result_source_mismatch:'+name)
    return result, run_manifest


def _accounting(directory: Path, state: dict[str, Any], budget: dict[str, Any]) -> None:
    try:
        _accounting_records(directory, state, budget)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ExperimentError('malformed_accounting_record') from exc


def _accounting_records(directory: Path, state: dict[str, Any], budget: dict[str, Any]) -> None:
    _require(len(state['attempts']) <= budget['maximum_jobs'], 'attempt_budget_exceeded')
    seen = set()
    candidates = {c['id']: c for c in state['candidates']}
    linked = {identifier: [] for identifier in candidates}
    actual_job_wall = Fraction()
    for attempt in state['attempts']:
        _require(attempt['id'] not in seen, 'duplicate_attempt')
        seen.add(attempt['id'])
        _require(str(uuid.UUID(attempt['id'])) == attempt['id'] and
                 attempt['job_artifact'] == 'jobs/'+attempt['id'] and
                 attempt['candidate_id'] in candidates, 'invalid_attempt_binding')
        linked[attempt['candidate_id']].append(attempt['id'])
        _require(attempt['status'] == 'terminal', 'unverified_interruption')
        job, raw = _job(directory, attempt)
        _require(_hash(raw) == attempt['job_sha256'], 'saved_job_binding_changed')
        safe_no_launch = job.get('pid') is None and job['status'] in ('cancelled', 'refused')
        _require(job.get('child_reaped') is True or safe_no_launch, 'unverified_interruption')
        elapsed = job['elapsed_wall_seconds']
        _bounded(elapsed, float('inf'), 'saved_job_wall')
        actual_job_wall += Fraction(elapsed)
    _require(all(candidates[key]['attempt_ids'] == value for key, value in linked.items()),
             'candidate_attempt_binding_mismatch')
    actual_jobs = {p.name for p in (directory/'jobs').iterdir() if p.is_dir()}
    _require(actual_jobs == seen, 'unverified_interruption')
    charged = Fraction()
    for invocation in state['invocations']:
        _require(invocation['status'] == 'finished', 'unverified_interruption')
        value = invocation['elapsed_seconds']
        _bounded(value, float('inf'), 'invocation_elapsed')
        charged += Fraction(value)
    _require(type(state['charged_wall_seconds']) in (int, float) and
             math.isfinite(state['charged_wall_seconds']) and state['charged_wall_seconds'] >= 0,
             'invalid_charged_wall')
    _require(Fraction(state['charged_wall_seconds']) >= charged >= actual_job_wall,
             'wall_accounting_inconsistent')


def _operation(directory: Path, candidate: dict[str, Any], state: dict[str, Any],
               manifest: dict[str, Any]) -> tuple[str, Path, str | None]:
    if not candidate['attempt_ids']:
        return 'run', _path(directory, candidate['case_artifact']), None
    previous = next(a for a in state['attempts'] if a['id'] == candidate['attempt_ids'][-1])
    job, _ = _job(directory, previous)
    _require(job['status'] == 'cancelled', 'candidate_not_cooperatively_cancelled')
    if job.get('pid') is None and job.get('reason') == 'cancelled_before_launch':
        return 'run', _path(directory, candidate['case_artifact']), previous['id']
    result, _ = _bound_result(directory, previous, candidate, manifest)
    _require(result['status'] == 'cancelled', 'cancelled_result_required')
    integration = result.get('integration')
    if integration is None or (type(integration) is dict and not integration.get('steps')):
        return 'run', _path(directory, candidate['case_artifact']), previous['id']
    _require(integration['status'] == 'cancelled' and integration['reason'] == 'cancel_requested',
             'accepted_prefix_not_resumable')
    return 'resume', _path(directory, previous['job_artifact'])/'run', previous['id']


def run_experiment(directory: str | Path, *, cancel: Callable[[], bool] | None = None) -> dict[str, Any]:
    directory = Path(directory)
    _require(cancel is None or callable(cancel), 'invalid_cancel_callback')
    with _lock(directory):
        began = time.monotonic()
        spec, state, manifest = _verified(directory)
        budget = spec['budget']
        _accounting(directory, state, budget)
        frozen_runtime = _load((directory/'inputs/runtime.json').read_bytes())
        _require(runtime_identity() == frozen_runtime, 'experiment_runtime_changed_new_experiment_required')
        if state['charged_wall_seconds'] >= budget['maximum_total_wall_seconds']:
            state.update(status='resource_limit', reason='total_wall_budget_exhausted')
            _write(directory/'state.json', state)
            return read_experiment(directory)
        base_charge = Fraction(state['charged_wall_seconds'])
        invocation = {'id': str(uuid.uuid4()), 'status': 'running', 'elapsed_seconds': None}
        state['invocations'].append(invocation)
        state.update(status='running', reason=None)
        _write(directory/'state.json', state)
        observed_request: str | None = None

        def cancelled() -> bool:
            nonlocal observed_request
            path = directory/'cancel.json'
            if path.exists():
                _require(not path.is_symlink(), 'invalid_cancel_request_path')
                request = _load(path.read_bytes())
                _require(request['schema'] == 'sandbox_experiment_cancel_v1' and
                         request['experiment_uuid'] == state['experiment_uuid'] and
                         str(uuid.UUID(request['request_id'])) == request['request_id'], 'invalid_cancel_request')
                if request['request_id'] != state['consumed_cancel_request_id']:
                    observed_request = request['request_id']
            return observed_request is not None or bool(cancel is not None and cancel())

        try:
            for candidate in state['candidates']:
                if candidate['status'] not in ('pending', 'paused'):
                    continue
                if cancelled():
                    state.update(status='paused', reason='cancel_requested')
                    break
                _verified(directory)
                _require(runtime_identity() == frozen_runtime, 'experiment_runtime_changed_new_experiment_required')
                remaining = Fraction(budget['maximum_total_wall_seconds'])-base_charge-Fraction(time.monotonic()-began)
                grace = Fraction(budget['cancel_grace_seconds'])
                if len(state['attempts']) >= budget['maximum_jobs'] or remaining <= grace:
                    state.update(status='resource_limit', reason='remaining_experiment_budget_insufficient')
                    break
                work = _lower(min(Fraction(budget['per_job_wall_seconds']), remaining-grace))
                if work <= 0:
                    state.update(status='resource_limit', reason='remaining_experiment_budget_unrepresentable')
                    break
                try:
                    operation, source, parent_id = _operation(directory, candidate, state, manifest)
                except (ValueError, KeyError, TypeError) as exc:
                    candidate.update(status='failed', reason='unresumable_candidate:'+str(exc))
                    continue
                remaining = Fraction(budget['maximum_total_wall_seconds'])-base_charge-Fraction(time.monotonic()-began)
                if remaining <= grace:
                    state.update(status='resource_limit', reason='remaining_experiment_budget_insufficient')
                    break
                work = _lower(min(Fraction(budget['per_job_wall_seconds']), remaining-grace))
                if work <= 0:
                    state.update(status='resource_limit', reason='remaining_experiment_budget_unrepresentable')
                    break
                attempt_id = str(uuid.uuid4())
                attempt = {'id': attempt_id, 'candidate_id': candidate['id'], 'operation': operation,
                           'parent_attempt_id': parent_id, 'job_artifact': 'jobs/'+attempt_id,
                           'status': 'running', 'policy': {'maximum_wall_seconds': work,
                           'cancel_grace_seconds': float(grace)}}
                state['attempts'].append(attempt)
                candidate['attempt_ids'].append(attempt_id)
                candidate['status'] = 'running'
                _write(directory/'state.json', state)
                kwargs: dict[str, Any] = {'cancel': cancelled}
                if operation == 'run':
                    kwargs.update(water_directory=directory/'inputs/water', evidence_directory=directory/'inputs/evidence')
                supervise(operation, source, directory/attempt['job_artifact'],
                          SupervisionPolicy(work, float(grace)), **kwargs)
                job, job_raw = _job(directory, attempt)
                safe_no_launch = job.get('pid') is None and job['status'] in ('cancelled', 'refused')
                _require(job.get('child_reaped') is True or safe_no_launch, 'unverified_interruption')
                attempt.update(status='terminal', job_sha256=_hash(job_raw), outcome=job['status'])
                candidate.update(status='failed', reason=job.get('reason'))
                if job['status'] == 'cancelled':
                    candidate.update(status='paused', reason='cancel_requested')
                try:
                    result, run_manifest = _bound_result(directory, attempt, candidate, manifest)
                    attempt['result_sha256'] = run_manifest['files']['result.json']
                    if job['status'] == 'completed' and job['returncode'] == 0 and result['status'] == 'completed':
                        candidate.update(status='completed', reason=None, result_attempt_id=attempt_id)
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    attempt['result_verification_error'] = str(exc)
                    if candidate['status'] != 'paused':
                        candidate['reason'] = 'unverified_result:'+str(exc)
                _write(directory/'state.json', state)
                if job['status'] == 'cancelled' or cancelled():
                    state.update(status='paused', reason='cancel_requested')
                    break
            else:
                state.update(status='completed', reason='all_candidates_terminal_not_all_candidates_successful')
        except BaseException as exc:
            state.update(status='failed', reason=str(exc), error_type=type(exc).__name__)
        finally:
            elapsed = time.monotonic()-began
            invocation.update(status='finished', elapsed_seconds=elapsed)
            state['charged_wall_seconds'] = _upper(base_charge+Fraction(elapsed))
            if state['charged_wall_seconds'] > budget['maximum_total_wall_seconds']:
                state['outcome_before_budget_check'] = {'status': state['status'], 'reason': state['reason']}
                state.update(status='resource_limit', reason='total_wall_budget_exceeded')
            if observed_request is not None:
                state['consumed_cancel_request_id'] = observed_request
            _write(directory/'state.json', state)
        return {**state, 'budget': spec['budget'], 'seed': spec['seed'],
                'observation_status': 'persisted_not_live_process_proof', 'inputs_manifest': manifest}


def compare_experiment(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    spec, state, manifest = _verified(directory)
    outcomes = []
    for candidate in state['candidates']:
        item: dict[str, Any] = {'id': candidate['id'], 'outcome': candidate['status'],
            'reason': candidate['reason'], 'classification': candidate['classification'],
            'case_sha256': candidate['case_sha256'], 'metrics': None,
            'result_sha256': None, 'material_qualified': False}
        if candidate['status'] == 'completed':
            try:
                attempt = next(a for a in state['attempts'] if a['id'] == candidate['result_attempt_id'])
                job, job_raw = _job(directory, attempt)
                _require(_hash(job_raw) == attempt['job_sha256'] and job['status'] == 'completed' and
                         job['returncode'] == 0 and job.get('child_reaped') is True, 'completed_job_binding_mismatch')
                result, result_manifest = _bound_result(directory, attempt, candidate, manifest)
                _require(result['status'] == 'completed' and
                         result_manifest['files']['result.json'] == attempt['result_sha256'], 'completed_result_binding_mismatch')
                initial, final = result['integration']['states'][0], result['integration']['states'][-1]
                snapshot = result['final_snapshot']
                temperatures = snapshot['temperature_k']
                pressures = snapshot['pressure_pa']
                case = read_case(_path(directory, candidate['case_artifact']))
                species = case.payload['initial']['species_order']
                water = [species.index('H2O'), species.index('H2O_liquid')]
                def total_water(value: dict[str, Any]) -> float:
                    return math.fsum(row[index] for row in value['amounts_mol'] for index in water)
                final_energy = math.fsum(final['internal_energy_j'])
                metrics = {'final_temperature_span_k': max(temperatures)-min(temperatures),
                           'maximum_final_pressure_pa': max(pressures),
                           'final_total_water_mol': total_water(final),
                           'change_total_water_mol': total_water(final)-total_water(initial),
                           'final_total_internal_energy_j': final_energy,
                           'change_total_internal_energy_j': final_energy-math.fsum(initial['internal_energy_j'])}
                initial_snapshot = result.get('initial_snapshot')
                if initial_snapshot and initial_snapshot.get('temperature_k') and initial_snapshot.get('pressure_pa'):
                    metrics['change_temperature_span_k'] = metrics['final_temperature_span_k']-(max(initial_snapshot['temperature_k'])-min(initial_snapshot['temperature_k']))
                    metrics['change_maximum_pressure_pa'] = metrics['maximum_final_pressure_pa']-max(initial_snapshot['pressure_pa'])
                _require(all(math.isfinite(value) for value in metrics.values()), 'nonfinite_comparison_metric')
                item.update(metrics=metrics, result_sha256=attempt['result_sha256'],
                            trace_quantities={'temperature': 'temperature_k', 'pressure': 'pressure_pa',
                                              'water_inventory': 'amounts_mol', 'total_energy': 'internal_energy_j'})
            except (ValueError, OSError, KeyError, TypeError, StopIteration, OverflowError, IndexError) as exc:
                item.update(outcome='unverified_result', reason=str(exc))
        outcomes.append(item)
    comparison = {'schema': 'sandbox_experiment_comparison_v1', 'experiment_id': spec['experiment_id'],
                  'scientific_status': 'manufactured_verification_only', 'material_qualified': False,
                  'training_eligible': False, 'outcomes': outcomes,
                  'interpretation': 'Descriptive saved-result metrics only. No ranking, brick quality, success probability or material validity is inferred. internal_energy_j is the model conserved total thermal-plus-skeleton energy. Source asset presence is not scientific applicability.'}
    return comparison
