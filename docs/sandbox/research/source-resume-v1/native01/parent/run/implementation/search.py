"""Bounded deterministic coordinate search within a manufactured fixture.

Selection addresses only the stated numerical objective and virtual constraints.
It is not brick-quality optimization, a global optimum or material admission.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import math
import os
from pathlib import Path
import time
from typing import Any, Callable
import uuid

from . import experiments as _experiments
from .experiments import prepare_experiment, run_experiment, read_experiment, compare_experiment
from .run_provenance import evidence_paths, load_catalog
from .run_service import runtime_identity
from .sensitivity import _design as _factor_design, _location, _METRICS


class SearchError(ValueError):
    def __init__(self, reason: str, code: str = 'invalid_search') -> None:
        super().__init__(reason)
        self.code = code


def _require(condition: bool, reason: str, code: str = 'invalid_search') -> None:
    if not condition:
        raise SearchError(reason, code)


# Reuse the experiment's strict JSON, local integrity, and outward-rounding rules.
_raw = _experiments._raw
_load = _experiments._load
_hash = _experiments._hash
_write = _experiments._write
_path = _experiments._path
_upper = _experiments._upper
_lower = _experiments._lower


def _number(value: Any) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    _require(valid, 'finite_number_required')
    return float(value)


def _spec(raw: bytes) -> dict[str, Any]:
    spec = _load(raw)
    _require(type(spec) is dict and set(spec) == {'schema', 'id', 'mode', 'baseline_case',
             'factors', 'objective', 'constraints', 'policy', 'budget'}, 'invalid_search_fields')
    _require(spec['schema'] == 'sandbox_search_v1', 'unsupported_search_schema')
    _require(spec['mode'] == 'manufactured_verification', 'material_evidence_not_admitted', 'evidence_incomplete')
    _factor_design(_raw({'schema': 'sandbox_sensitivity_v1', **{key: spec[key] for key in
                   ('id', 'mode', 'baseline_case', 'factors', 'budget')}}))
    for factor in spec['factors']:
        container, key = _location(spec['baseline_case'], factor['path'])
        _require(float(factor['low']) <= _number(container[key]) <= float(factor['high']),
                 'baseline_factor_outside_bounds')
    objective = spec['objective']
    _require(type(objective) is dict and set(objective) == {'metric', 'direction', 'units'},
             'invalid_objective_fields')
    _require(type(objective['metric']) is str and objective['metric'] in _METRICS and objective['direction'] in ('minimize', 'maximize') and
             objective['units'] == _METRICS[objective['metric']][0], 'invalid_objective')
    _require(type(spec['constraints']) is list, 'invalid_constraints')
    for constraint in spec['constraints']:
        _require(type(constraint) is dict and set(constraint) == {'metric', 'relation', 'value', 'units', 'classification'},
                 'invalid_constraint_fields')
        _require(type(constraint['metric']) is str and constraint['metric'] in _METRICS and constraint['units'] == _METRICS[constraint['metric']][0] and
                 constraint['relation'] in ('le', 'ge') and constraint['classification'] == 'virtual_design_choice',
                 'invalid_virtual_constraint')
        _number(constraint['value'])
    policy = spec['policy']
    _require(type(policy) is dict and set(policy) == {'maximum_generations', 'initial_step_fraction',
             'contraction', 'minimum_improvement', 'stagnation_generations'}, 'invalid_search_policy')
    _require(type(policy['maximum_generations']) is int and 2 <= policy['maximum_generations'] <= 4,
             'invalid_maximum_generations')
    _require(0 < _number(policy['initial_step_fraction']) <= .5 and
             0 < _number(policy['contraction']) < 1 and _number(policy['minimum_improvement']) >= 0,
             'invalid_step_or_improvement_policy')
    _require(type(policy['stagnation_generations']) is int and policy['stagnation_generations'] > 0,
             'invalid_stagnation_generations')
    return spec


def _values(case: dict[str, Any], spec: dict[str, Any]) -> list[float]:
    return [_number(container[key]) for container, key in
            (_location(case, factor['path']) for factor in spec['factors'])]


def _case(spec: dict[str, Any], values: list[float]) -> dict[str, Any]:
    case = deepcopy(spec['baseline_case'])
    for factor, value in zip(spec['factors'], values):
        container, key = _location(case, factor['path'])
        # Retain an unchanged baseline JSON number's original representation.
        if float(container[key]) != value:
            container[key] = value
    return case


def _generation(spec: dict[str, Any], index: int, parent: list[float], budget: dict[str, Any],
                parent_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates, mapping, omitted = [], [], []
    seen: set[tuple[float, ...]] = set()

    def add(identifier: str, values: list[float], changes: list[dict[str, Any]]) -> None:
        if tuple(values) in seen:
            omitted.append({'id': identifier, 'reason': 'duplicate_represented_candidate'})
            return
        seen.add(tuple(values))
        case = _case(spec, values)
        candidates.append({'id': identifier, 'case': case})
        mapping.append({'id': identifier, 'parent_id': parent_id, 'factor_values': values,
                        'changes': changes, 'case_sha256': _hash(_raw(case))})

    add('parent', list(parent), [])
    for coordinate, factor in enumerate(spec['factors']):
        step = ((Fraction(float(factor['high']))-Fraction(float(factor['low'])))*
                Fraction(float(spec['policy']['initial_step_fraction']))*
                Fraction(float(spec['policy']['contraction']))**index)
        for sign, label in ((-1, 'minus'), (1, 'plus')):
            identifier = f'f{coordinate:02d}-{label}'
            proposed = Fraction(parent[coordinate])+sign*step
            if not Fraction(float(factor['low'])) <= proposed <= Fraction(float(factor['high'])):
                omitted.append({'id': identifier, 'reason': 'outside_declared_factor_bounds'})
                continue
            value = float(proposed)
            if value == parent[coordinate]:
                omitted.append({'id': identifier, 'reason': 'unresolvable_at_current_float'})
                continue
            values = list(parent)
            values[coordinate] = value
            add(identifier, values, [{'factor_id': factor['id'], 'path': factor['path'],
                 'from': parent[coordinate], 'to': value, 'units': factor['units'],
                 'classification': factor['classification'],
                 'nominal_step': {'numerator': step.numerator, 'denominator': step.denominator}}])
    return {'schema': 'sandbox_experiment_v1', 'experiment_id': f'search-g{index:03d}',
            'mode': 'manufactured_verification', 'seed': 0, 'candidates': candidates,
            'budget': budget}, mapping, omitted


def prepare_search(spec_path: str | Path, output: str | Path, *,
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
    (inputs/'water').mkdir()
    for source in sorted(Path(water_directory).iterdir()):
        _require(source.is_file() and not source.is_symlink(), 'water_requires_regular_files')
        (inputs/'water'/source.name).write_bytes(source.read_bytes())
    if evidence_directory is not None:
        evidence_root = Path(evidence_directory).resolve()
        for name in evidence_paths(load_catalog()):
            source = _path(evidence_root, name)
            if source.is_file():
                target = _path(inputs/'evidence', name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
    manifest = {'schema': 'sandbox_search_inputs_v1', 'files': {
        path.relative_to(directory).as_posix(): _hash(path.read_bytes())
        for path in sorted(inputs.rglob('*')) if path.is_file()}}
    _write(directory/'inputs-manifest.json', manifest)
    (directory/'generations').mkdir()
    state = {'schema': 'sandbox_search_state_v1', 'id': spec['id'], 'status': 'prepared', 'reason': None,
             'inputs_manifest_sha256': _hash(_raw(manifest)), 'best': None, 'generations': [],
             'attempts_used': 0, 'charged_wall_seconds': 0.0, 'invocations': [],
             'scientific_status': 'manufactured_verification_only', 'material_qualified': False,
             'training_eligible': False}
    _write(directory/'state.json', state)
    return read_search(directory)


def _frozen(directory: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest_raw = (directory/'inputs-manifest.json').read_bytes()
    manifest = _load(manifest_raw)
    _require(manifest['schema'] == 'sandbox_search_inputs_v1', 'invalid_search_manifest')
    for name, digest in manifest['files'].items():
        _require(name.startswith('inputs/'), 'invalid_frozen_membership')
        _require(_hash(_path(directory, name).read_bytes()) == digest, 'search_frozen_input_changed:'+name)
    actual = {p.relative_to(directory).as_posix() for p in (directory/'inputs').rglob('*') if p.is_file()}
    _require(actual == set(manifest['files']), 'search_input_membership_changed')
    spec = _spec((directory/'inputs/spec.json').read_bytes())
    state = _load((directory/'state.json').read_bytes())
    _require(state['schema'] == 'sandbox_search_state_v1' and state['id'] == spec['id'] and
             state['inputs_manifest_sha256'] == _hash(manifest_raw), 'search_state_binding_mismatch')
    return spec, state, manifest


def _selection(spec: dict[str, Any], generation: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    outcomes = comparison['outcomes']
    mapping = generation['candidate_map']
    _require([o['id'] for o in outcomes] == [c['id'] for c in mapping], 'search_comparison_membership_mismatch')
    assessments, eligible = [], []
    for outcome, candidate in zip(outcomes, mapping):
        _require(outcome['case_sha256'] == candidate['case_sha256'], 'search_result_case_mismatch')
        row = {'id': outcome['id'], 'evaluation_outcome': outcome['outcome'], 'reason': outcome['reason'],
               'feasibility': 'unknown', 'objective_value': None, 'constraints': [],
               'result_sha256': outcome.get('result_sha256'), 'case_sha256': candidate['case_sha256']}
        if outcome['outcome'] == 'completed' and outcome.get('result_sha256'):
            try:
                metrics = outcome['metrics']
                value = _number(metrics[spec['objective']['metric']])
                checks = []
                for constraint in spec['constraints']:
                    actual = _number(metrics[constraint['metric']])
                    meets = actual <= constraint['value'] if constraint['relation'] == 'le' else actual >= constraint['value']
                    checks.append({**constraint, 'actual': actual, 'satisfied': meets})
                feasible = all(item['satisfied'] for item in checks)
                row.update(feasibility='feasible' if feasible else 'infeasible', objective_value=value, constraints=checks)
                if feasible:
                    eligible.append((candidate, row))
            except (ValueError, KeyError, TypeError) as exc:
                row['reason'] = 'objective_or_constraint_unavailable:'+str(exc)
        assessments.append(row)
    if not eligible:
        return {'selected': None, 'improved': False, 'reason': 'no_feasible_verified_candidate', 'assessments': assessments}
    direction = -1 if spec['objective']['direction'] == 'maximize' else 1
    # Parent appears first and wins exact ties; other ties preserve declared order.
    selected = min(eligible, key=lambda pair: direction*pair[1]['objective_value'])
    parent = next((pair for pair in eligible if pair[0]['id'] == 'parent'), None)
    improved = parent is None
    if parent is not None:
        improvement = direction*(Fraction(parent[1]['objective_value'])-Fraction(selected[1]['objective_value']))
        improved = improvement > Fraction(float(spec['policy']['minimum_improvement']))
        if not improved:
            selected = parent
    candidate, row = selected
    best = {'generation': generation['index'], 'candidate_id': candidate['id'],
            'case_sha256': candidate['case_sha256'], 'result_sha256': row['result_sha256'],
            'objective_value': row['objective_value'], 'factor_values': candidate['factor_values']}
    return {'selected': best, 'improved': improved,
            'reason': 'objective_improved' if improved and parent is not None else
                      'feasible_candidate_found' if parent is None else 'parent_retained', 'assessments': assessments}


def _history(directory: Path, spec: dict[str, Any], state: dict[str, Any],
             manifest: dict[str, Any], *, require_terminal_accounting: bool) -> tuple[Any, int, Fraction]:
    parent = _values(spec['baseline_case'], spec)
    parent_id, parent_sha, best = 'baseline', None, None
    attempts = 0
    experiment_wall = Fraction()
    frozen_runtime = _load((directory/'inputs/runtime.json').read_bytes())
    _require(len(state['generations']) <= spec['policy']['maximum_generations'], 'generation_limit_exceeded')
    _require({p.name for p in (directory/'generations').iterdir() if p.is_dir()} ==
             {f'g{index:03d}' for index in range(len(state['generations']))}, 'unverified_generation_interruption')
    for index, generation in enumerate(state['generations']):
        stem = f'generations/g{index:03d}'
        _require(generation['index'] == index and generation['experiment_artifact'] == stem+'/experiment' and
                 generation['spec_artifact'] == stem+'/spec.json' and generation['parent_id'] == parent_id and
                 generation['parent_result_sha256'] == parent_sha and generation['parent_values'] == parent,
                 'search_parent_lineage_mismatch')
        budget = generation['budget']
        _require(_number(generation['wall_charge_before']) >= 0, 'invalid_generation_wall_charge')
        _require(budget['maximum_jobs'] == spec['budget']['maximum_jobs']-generation['attempts_before'] and
                 generation['attempts_before'] == attempts and
                 budget['per_job_wall_seconds'] == spec['budget']['per_job_wall_seconds'] and
                 budget['cancel_grace_seconds'] == spec['budget']['cancel_grace_seconds'] and
                 0 < Fraction(budget['maximum_total_wall_seconds']) <= Fraction(spec['budget']['maximum_total_wall_seconds'])-
                 Fraction(generation['wall_charge_before']), 'generation_budget_binding_mismatch')
        generated, mapping, omitted = _generation(spec, index, parent, budget, parent_id)
        raw = _raw(generated)
        _require(generation['candidate_map'] == mapping and generation['omitted'] == omitted and
                 generation['spec_sha256'] == _hash(raw) and _path(directory, generation['spec_artifact']).read_bytes() == raw,
                 'generated_search_spec_mismatch')
        experiment_dir = _path(directory, generation['experiment_artifact'])
        experiment = read_experiment(experiment_dir)
        _require((experiment_dir/'inputs/spec.json').read_bytes() == raw, 'generation_experiment_spec_mismatch')
        _require(_load((experiment_dir/'inputs/runtime.json').read_bytes()) == frozen_runtime, 'generation_runtime_changed')
        expected_sources = {key: value for key, value in manifest['files'].items() if key.startswith(('inputs/water/', 'inputs/evidence/'))}
        actual_sources = {key: value for key, value in experiment['inputs_manifest']['files'].items() if key.startswith(('inputs/water/', 'inputs/evidence/'))}
        _require(actual_sources == expected_sources, 'generation_source_binding_changed')
        _require([(c['id'], c['case_sha256']) for c in experiment['candidates']] ==
                 [(c['id'], c['case_sha256']) for c in mapping], 'generation_case_binding_changed')
        attempts += len(experiment['attempts'])
        experiment_wall += Fraction(experiment['charged_wall_seconds'])
        if require_terminal_accounting:
            _experiments._accounting(experiment_dir, experiment, budget)
        if generation['status'] == 'completed':
            _require(experiment['status'] == 'completed', 'completed_generation_experiment_mismatch')
            selection = _selection(spec, generation, compare_experiment(experiment_dir))
            _require(generation['selection'] == selection, 'search_selection_binding_mismatch')
            if selection['selected'] is not None:
                best = selection['selected']
                parent, parent_sha = best['factor_values'], best['result_sha256']
                parent_id = f'g{index:03d}/'+best['candidate_id']
            else:
                _require(index == len(state['generations'])-1, 'generation_after_no_eligible_parent')
        else:
            _require(index == len(state['generations'])-1, 'unfinished_generation_before_successor')
    _require(state['best'] == best and state['attempts_used'] == attempts, 'search_best_or_attempt_count_mismatch')
    return best, attempts, experiment_wall


def read_search(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    try:
        spec, state, manifest = _frozen(directory)
        _history(directory, spec, state, manifest, require_terminal_accounting=False)
        return {**state, 'budget': spec['budget'], 'objective': spec['objective'], 'constraints': spec['constraints'],
                'observation_status': 'persisted_not_live_process_proof',
                'interpretation': 'Only the declared manufactured-fixture objective is compared. Constraints are virtual design screens, not product qualification. No global optimum, real-material validity or brick-quality claim.'}
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise SearchError('malformed_search_record') from exc


def _run_search(directory: str | Path, *, cancel: Callable[[], bool] | None = None) -> dict[str, Any]:
    directory = Path(directory)
    _require(cancel is None or callable(cancel), 'invalid_cancel_callback')
    # Independent outer lock serializes orchestration. Generation jobs retain
    # the existing supervisor's inherited native-child lock as well.
    with _experiments._lock(directory):
        began = time.monotonic()
        spec, state, manifest = _frozen(directory)
        _, attempts, experiment_wall = _history(directory, spec, state, manifest, require_terminal_accounting=True)
        _require(all(item['status'] == 'finished' for item in state['invocations']), 'unverified_search_interruption')
        _require(all(_number(item['elapsed_seconds']) >= 0 for item in state['invocations']),
                 'invalid_invocation_elapsed_seconds')
        recorded = sum((Fraction(item['elapsed_seconds']) for item in state['invocations']), Fraction())
        base_charge = Fraction(_number(state['charged_wall_seconds']))
        _require(base_charge >= recorded >= experiment_wall and attempts <= spec['budget']['maximum_jobs'],
                 'search_accounting_inconsistent')
        _require(runtime_identity() == _load((directory/'inputs/runtime.json').read_bytes()),
                 'search_runtime_changed_new_search_required')
        if state['status'] in ('completed', 'resource_limit', 'failed'):
            return read_search(directory)
        invocation = {'id': str(uuid.uuid4()), 'status': 'running', 'elapsed_seconds': None}
        state['invocations'].append(invocation)
        state.update(status='running', reason=None)
        _write(directory/'state.json', state)
        budget_cancel = False
        user_cancel = False

        def cancelled() -> bool:
            nonlocal budget_cancel, user_cancel
            budget_cancel = budget_cancel or (Fraction(spec['budget']['maximum_total_wall_seconds'])-
                base_charge-Fraction(time.monotonic()-began) <= Fraction(spec['budget']['cancel_grace_seconds']))
            user_cancel = user_cancel or bool(cancel is not None and cancel())
            return budget_cancel or user_cancel

        try:
            while True:
                _frozen(directory)
                _history(directory, spec, state, manifest, require_terminal_accounting=True)
                _require(runtime_identity() == _load((directory/'inputs/runtime.json').read_bytes()),
                         'search_runtime_changed_new_search_required')
                if cancelled():
                    state.update(status='resource_limit' if budget_cancel else 'paused',
                                 reason='global_wall_budget_reserved_for_grace' if budget_cancel else 'cancel_requested')
                    break
                generations = state['generations']
                if generations and generations[-1]['status'] != 'completed':
                    generation = generations[-1]
                else:
                    if len(generations) >= spec['policy']['maximum_generations']:
                        state.update(status='completed', reason='maximum_generations_reached')
                        break
                    stagnant = 0
                    for previous in reversed(generations):
                        if previous['selection']['improved']:
                            break
                        stagnant += 1
                    if stagnant >= spec['policy']['stagnation_generations']:
                        state.update(status='completed', reason='stagnation_limit_reached')
                        break
                    remaining_jobs = spec['budget']['maximum_jobs']-state['attempts_used']
                    remaining_wall = Fraction(spec['budget']['maximum_total_wall_seconds'])-base_charge-Fraction(time.monotonic()-began)
                    if remaining_jobs <= 0 or remaining_wall <= Fraction(spec['budget']['cancel_grace_seconds']):
                        state.update(status='resource_limit', reason='global_budget_exhausted')
                        break
                    index = len(generations)
                    best = state['best']
                    parent = _values(spec['baseline_case'], spec) if best is None else best['factor_values']
                    parent_id = 'baseline' if best is None else f"g{best['generation']:03d}/"+best['candidate_id']
                    allocation = {**spec['budget'], 'maximum_jobs': remaining_jobs,
                                  'maximum_total_wall_seconds': _lower(remaining_wall)}
                    wall_before = _lower(Fraction(spec['budget']['maximum_total_wall_seconds'])-remaining_wall)
                    generated, mapping, omitted = _generation(spec, index, parent, allocation, parent_id)
                    stem = f'generations/g{index:03d}'
                    generation = {'index': index, 'experiment_artifact': stem+'/experiment',
                        'spec_artifact': stem+'/spec.json', 'spec_sha256': _hash(_raw(generated)),
                        'parent_id': parent_id, 'parent_result_sha256': None if best is None else best['result_sha256'],
                        'parent_values': parent, 'budget': allocation, 'candidate_map': mapping, 'omitted': omitted,
                        'attempts_before': state['attempts_used'], 'wall_charge_before': wall_before, 'status': 'preparing'}
                    generations.append(generation)
                    _write(directory/'state.json', state)
                    _path(directory, stem).mkdir()
                    _path(directory, generation['spec_artifact']).write_bytes(_raw(generated))
                    prepare_experiment(_path(directory, generation['spec_artifact']),
                        _path(directory, generation['experiment_artifact']), water_directory=directory/'inputs/water',
                        evidence_directory=directory/'inputs/evidence')
                    generation['status'] = 'prepared'
                    _write(directory/'state.json', state)
                experiment_dir = _path(directory, generation['experiment_artifact'])
                result = run_experiment(experiment_dir, cancel=cancelled)
                state['attempts_used'] = sum(len(read_experiment(_path(directory, g['experiment_artifact']))['attempts']) for g in generations)
                generation['status'] = result['status']
                if result['status'] != 'completed':
                    state.update(status='resource_limit' if budget_cancel or result['status'] == 'resource_limit' else
                                 'paused' if result['status'] == 'paused' else 'failed', reason=result['reason'])
                    break
                selection = _selection(spec, generation, compare_experiment(experiment_dir))
                generation['selection'] = selection
                if selection['selected'] is None:
                    state.update(status='completed', reason='no_feasible_verified_candidate')
                    break
                state['best'] = selection['selected']
                _write(directory/'state.json', state)
        except BaseException as exc:
            state.update(status='failed', reason=str(exc), error_type=type(exc).__name__)
        finally:
            # Final saved-result/lineage audit is active orchestration work too.
            try:
                _history(directory, spec, state, manifest, require_terminal_accounting=True)
            except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
                state['outcome_before_final_audit'] = {
                    key: state[key] for key in ('status', 'reason', 'error_type') if key in state}
                state.update(status='failed', reason='final_search_history_unverified:'+str(exc))
            elapsed = time.monotonic()-began
            invocation.update(status='finished', elapsed_seconds=elapsed)
            state['charged_wall_seconds'] = _upper(base_charge+Fraction(elapsed))
            if state['charged_wall_seconds'] > spec['budget']['maximum_total_wall_seconds']:
                state['outcome_before_budget_check'] = {'status': state['status'], 'reason': state['reason']}
                state.update(status='resource_limit', reason='global_wall_budget_exceeded')
            _write(directory/'state.json', state)
        return {**state, 'budget': spec['budget'], 'objective': spec['objective'],
                'constraints': spec['constraints'], 'observation_status': 'persisted_not_live_process_proof'}


def run_search(directory: str | Path, *, cancel: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Run or resume the last paused generation under the original shared budget."""
    try:
        return _run_search(directory, cancel=cancel)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise SearchError('malformed_search_record') from exc
