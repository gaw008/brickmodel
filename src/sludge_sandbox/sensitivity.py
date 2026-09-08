"""Deterministic two-level manufactured designs and saved-result contrasts.

This module generates existing experiment inputs and analyzes their verified
results. It adds no solver, uncertainty distribution, causal estimate or material
qualification. Main effects average the supplied factorial endpoints only.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

from .experiments import prepare_experiment, read_experiment, compare_experiment
from . import experiments as experiment_module


class SensitivityError(ValueError):
    def __init__(self, reason: str, code: str = 'invalid_sensitivity') -> None:
        super().__init__(reason)
        self.code = code


FACTOR_ALLOWLIST: dict[str, dict[str, str]] = {
    '/transport/coupled_conductivity_w_m_k': {'units': 'W/(m*K)', 'classification': 'manufactured_test_fixture'},
    '/transport/coupled_water_diffusivity_m2_s': {'units': 'm2/s', 'classification': 'manufactured_test_fixture'},
    '/reaction/prefactor_mol_m3_s': {'units': 'mol/(m3*s)', 'classification': 'manufactured_test_fixture'},
    '/initial/parent_temperatures_k/0': {'units': 'K', 'classification': 'virtual_design_choice'},
    '/initial/parent_temperatures_k/1': {'units': 'K', 'classification': 'virtual_design_choice'},
}
_METRICS = {
    'final_temperature_span_k': ('K', 'temperature_k'),
    'maximum_final_pressure_pa': ('Pa', 'pressure_pa'),
    'final_total_water_mol': ('mol', 'amounts_mol'),
    'change_total_water_mol': ('mol', 'amounts_mol'),
    'final_total_internal_energy_j': ('J', 'internal_energy_j'),
    'change_total_internal_energy_j': ('J', 'internal_energy_j'),
    'change_temperature_span_k': ('K', 'temperature_k'),
    'change_maximum_pressure_pa': ('Pa', 'pressure_pa'),
}


def _require(condition: bool, reason: str, code: str = 'invalid_sensitivity') -> None:
    if not condition:
        raise SensitivityError(reason, code)


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _raw(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n').encode()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def _number(value: Any, name: str) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    _require(valid, 'invalid_finite_number:'+name)
    return float(value)


def _parse_float(value: str) -> float:
    return _number(float(value), 'JSON')


def _constant(value: str) -> None:
    raise SensitivityError('nonfinite_json')


def _load(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_float=_parse_float,
                          parse_constant=_constant)
    except (ValueError, RecursionError) as exc:
        raise SensitivityError('invalid_json:'+str(exc)) from exc


def _identifier(value: Any) -> None:
    _require(type(value) is str and re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', value) is not None,
             'invalid_identifier')


def _location(case: dict[str, Any], pointer: str) -> tuple[Any, str | int]:
    # The five literal allowlisted paths need no generic pointer interpreter.
    tokens = pointer.split('/')[1:]
    value: Any = case
    try:
        for token in tokens[:-1]:
            value = value[int(token)] if isinstance(value, list) else value[token]
        key: str | int = int(tokens[-1]) if isinstance(value, list) else tokens[-1]
        _number(value[key], pointer)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise SensitivityError('factor_path_missing_or_nonnumeric:'+pointer) from exc
    return value, key


def _design(raw: bytes) -> dict[str, Any]:
    spec = _load(raw)
    _require(type(spec) is dict and set(spec) == {'schema', 'id', 'mode', 'baseline_case', 'factors', 'budget'},
             'invalid_design_fields')
    _require(spec['schema'] == 'sandbox_sensitivity_v1', 'unsupported_design_schema')
    _identifier(spec['id'])
    _require(spec['mode'] == 'manufactured_verification', 'material_evidence_not_admitted', 'evidence_incomplete')
    baseline = spec['baseline_case']
    _require(type(baseline) is dict, 'baseline_case_object_required')
    factors = spec['factors']
    _require(type(factors) is list and 1 <= len(factors) <= 3, 'one_to_three_factors_required')
    ids, paths = set(), set()
    for factor in factors:
        _require(type(factor) is dict and set(factor) == {'id', 'path', 'low', 'high', 'classification', 'units'},
                 'invalid_factor_fields')
        _identifier(factor['id'])
        path = factor['path']
        _require(type(path) is str and path in FACTOR_ALLOWLIST, 'factor_path_not_allowed')
        _require(factor['id'] not in ids and path not in paths, 'duplicate_factor_id_or_path')
        ids.add(factor['id'])
        paths.add(path)
        expected = FACTOR_ALLOWLIST[path]
        _require(factor['classification'] == expected['classification'], 'factor_classification_mismatch')
        _require(factor['units'] == expected['units'], 'factor_units_mismatch')
        low, high = _number(factor['low'], 'factor_low'), _number(factor['high'], 'factor_high')
        _require(low < high, 'factor_levels_not_strictly_ordered_representable')
        _location(baseline, path)
        if path.startswith('/transport/'):
            _require(baseline.get('transport_mode') == 'coupled', 'inactive_factor:'+path, 'inactive_factor')
        if path.startswith('/initial/'):
            _require(baseline.get('profile') == 'gradient', 'inactive_factor:'+path, 'inactive_factor')
    budget = spec['budget']
    _require(type(budget) is dict and set(budget) == {'maximum_jobs', 'maximum_total_wall_seconds',
             'per_job_wall_seconds', 'cancel_grace_seconds'}, 'invalid_budget_fields')
    for name, maximum in (('maximum_jobs', 20), ('maximum_total_wall_seconds', 600),
                          ('per_job_wall_seconds', 120), ('cancel_grace_seconds', 5)):
        value = _number(budget[name], name)
        _require(0 < value <= maximum and (name != 'maximum_jobs' or type(budget[name]) is int),
                 'invalid_budget:'+name)
    return spec


def _generated(spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = []
    mapping = []
    for index, endpoints in enumerate(product(('low', 'high'), repeat=len(spec['factors']))):
        case = deepcopy(spec['baseline_case'])
        levels = {}
        for factor, endpoint in zip(spec['factors'], endpoints):
            container, key = _location(case, factor['path'])
            container[key] = factor[endpoint]
            levels[factor['id']] = endpoint
        identifier = f'cell-{index:03d}'
        candidates.append({'id': identifier, 'case': case})
        mapping.append({'id': identifier, 'levels': levels, 'case_sha256': _hash(_raw(case))})
    return {'schema': 'sandbox_experiment_v1', 'experiment_id': spec['id'],
            'mode': 'manufactured_verification', 'seed': 0, 'candidates': candidates,
            'budget': deepcopy(spec['budget'])}, mapping


def _manifest(raw: bytes, generated_raw: bytes, mapping: list[dict[str, Any]]) -> dict[str, Any]:
    return {'schema': 'sandbox_sensitivity_design_manifest_v1',
            'files': {'design.json': _hash(raw), 'generated-experiment.json': _hash(generated_raw)},
            'experiment_spec_sha256': _hash(generated_raw), 'candidates': mapping,
            'ordering': 'Factor order is design order; low precedes high; final factor varies fastest.',
            'generation': 'Complete deterministic Cartesian endpoints; no random sampling.'}


def prepare_sensitivity(spec_path: str | Path, output: str | Path, *,
                        water_directory: str | Path,
                        evidence_directory: str | Path | None = None) -> dict[str, Any]:
    raw = Path(spec_path).read_bytes()
    spec = _design(raw)
    generated, mapping = _generated(spec)
    generated_raw = _raw(generated)
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'design.json').write_bytes(raw)
    (directory/'generated-experiment.json').write_bytes(generated_raw)
    manifest = _manifest(raw, generated_raw, mapping)
    (directory/'design-manifest.json').write_bytes(_raw(manifest))
    experiment = prepare_experiment(directory/'generated-experiment.json', directory/'experiment',
                                    water_directory=water_directory, evidence_directory=evidence_directory)
    return {'schema': 'sandbox_sensitivity_preparation_v1', 'status': 'prepared',
            'id': spec['id'], 'design_sha256': _hash(raw),
            'design_manifest_sha256': _hash(_raw(manifest)),
            'factor_count': len(spec['factors']), 'candidate_count': len(mapping),
            'factors': spec['factors'], 'candidate_levels': mapping,
            'experiment_directory': str((directory/'experiment').resolve()), 'experiment': experiment,
            'scientific_status': 'manufactured_verification_only', 'material_qualified': False}


def _verified(directory: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    for name in ('design.json', 'generated-experiment.json', 'design-manifest.json'):
        _require(not (directory/name).is_symlink(), 'invalid_design_artifact_path')
    raw = (directory/'design.json').read_bytes()
    spec = _design(raw)
    generated, mapping = _generated(spec)
    expected_raw = _raw(generated)
    manifest_raw = (directory/'design-manifest.json').read_bytes()
    manifest = _load(manifest_raw)
    _require(manifest == _manifest(raw, expected_raw, mapping), 'design_manifest_mismatch')
    _require((directory/'generated-experiment.json').read_bytes() == expected_raw,
             'generated_experiment_changed')
    experiment = read_experiment(directory/'experiment')
    _require((directory/'experiment/inputs/spec.json').read_bytes() == expected_raw and
             experiment['inputs_manifest']['files']['inputs/spec.json'] == _hash(expected_raw),
             'frozen_experiment_spec_mismatch')
    _require([candidate['id'] for candidate in experiment['candidates']] == [item['id'] for item in mapping],
             'factorial_candidate_order_mismatch')
    for candidate, expected, source in zip(experiment['candidates'], mapping, generated['candidates']):
        _require(candidate['case_artifact'] == 'inputs/cases/'+expected['id']+'.json' and
                 candidate['case_sha256'] == expected['case_sha256'], 'factorial_case_binding_mismatch')
        case_path = directory/'experiment'/candidate['case_artifact']
        _require(not case_path.is_symlink() and case_path.read_bytes() == _raw(source['case']),
                 'factorial_case_content_mismatch')
    return spec, manifest, experiment, mapping


def _represented(value: Fraction) -> float:
    try:
        number = float(value)
    except OverflowError as exc:
        raise SensitivityError('contrast_not_representable') from exc
    _require(math.isfinite(number) and (number != 0 or value == 0), 'contrast_not_representable')
    return number


def analyze_sensitivity(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    spec, manifest, experiment, mapping = _verified(directory)
    comparison = compare_experiment(directory/'experiment')
    outcomes = comparison['outcomes']
    _require([item['id'] for item in outcomes] == [item['id'] for item in mapping],
             'comparison_candidate_order_mismatch')
    for item, expected in zip(outcomes, mapping):
        _require(item['case_sha256'] == expected['case_sha256'], 'comparison_case_binding_mismatch')
    contrasts = []
    for factor in spec['factors']:
        group: dict[str, Any] = {**factor, 'method': 'two_level_contrast' if len(spec['factors']) == 1 else
                                'averaged_factorial_contrast', 'metrics': {}}
        low_indexes = [i for i, item in enumerate(mapping) if item['levels'][factor['id']] == 'low']
        high_indexes = [i for i, item in enumerate(mapping) if item['levels'][factor['id']] == 'high']
        _require(len(low_indexes) == len(high_indexes) == len(mapping)//2, 'unbalanced_factorial_design')
        for name, (unit, quantity) in _METRICS.items():
            reasons = []
            for item in outcomes:
                if item['outcome'] != 'completed' or not item.get('result_sha256'):
                    reasons.append({'candidate_id': item['id'], 'reason': item.get('reason') or item['outcome']})
                elif type(item.get('metrics')) is not dict or name not in item['metrics']:
                    reasons.append({'candidate_id': item['id'], 'reason': 'metric_unavailable:'+name})
            metric: dict[str, Any] = {'status': 'unknown', 'contrast': None, 'per_unit_slope': None,
                'units': unit, 'slope_units': '('+unit+')/('+factor['units']+')',
                'trace_quantity': quantity, 'required_candidates': len(mapping),
                'low_candidate_ids': [mapping[i]['id'] for i in low_indexes],
                'high_candidate_ids': [mapping[i]['id'] for i in high_indexes],
                'reasons': reasons}
            if not reasons:
                try:
                    values = [Fraction(_number(item['metrics'][name], name)) for item in outcomes]
                    mean_low = sum((values[i] for i in low_indexes), Fraction())/len(low_indexes)
                    mean_high = sum((values[i] for i in high_indexes), Fraction())/len(high_indexes)
                    effect = mean_high-mean_low
                    delta = Fraction(float(factor['high']))-Fraction(float(factor['low']))
                    effect_float, slope_float = _represented(effect), _represented(effect/delta)
                    metric.update(status='computed', contrast=effect_float, per_unit_slope=slope_float,
                                  mean_low=_represented(mean_low), mean_high=_represented(mean_high))
                except (ValueError, OverflowError) as exc:
                    metric['reasons'] = [{'reason': str(exc)}]
            group['metrics'][name] = metric
        contrasts.append(group)
    return {'schema': 'sandbox_sensitivity_analysis_v1', 'id': spec['id'],
            'analysis_implementation_sha256': _hash(Path(__file__).read_bytes()),
            'metric_provider_implementation_sha256': _hash(Path(experiment_module.__file__).read_bytes()),
            'analysis_python_version': sys.version,
            'status': 'analyzed', 'design_sha256': manifest['files']['design.json'],
            'design_manifest_sha256': _hash((directory/'design-manifest.json').read_bytes()),
            'experiment_inputs_manifest_sha256': experiment['inputs_manifest_sha256'],
            'generated_spec_sha256': manifest['experiment_spec_sha256'],
            'candidate_levels': mapping, 'outcomes': outcomes, 'contrasts': contrasts,
            'scientific_status': 'manufactured_verification_only', 'material_qualified': False,
            'training_eligible': False,
            'interpretation': 'Each contrast is mean(high)-mean(low) over the complete declared Cartesian design. A missing, failed or unverified required endpoint makes that contrast unknown; successful subsets are never selected. Slopes divide by the declared endpoint difference. Numerical policies, mesh and other unfactored case values remain unchanged. These endpoint averages are not global sensitivity, Sobol indices, causal estimates, confidence intervals, uncertainty distributions, brick-quality rankings or material qualification. Saved energy metrics include thermal plus skeleton energy.'}
