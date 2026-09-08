"""Validated accepted-prefix checkpoints; saved JSON never executes code.

The exact ledger audit uses the original policy allowances at every prefix.
A restarted integrator's locally accepted suffix remains speculative until this
whole-history audit passes. It does not establish physical or truncation accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import json
import math
from typing import Any

from .integration import ConservedState, IntegrationPolicy, StepLedger


class CheckpointError(ValueError):
    """A saved prefix is malformed, incompatible, or has exhausted its budget."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise CheckpointError(reason)


def _number(value: Any, name: str) -> float:
    _require(type(value) in (int, float), 'checkpoint_invalid_'+name)
    try:
        result = float(value)
    except OverflowError as exc:
        raise CheckpointError('checkpoint_invalid_'+name) from exc
    _require(math.isfinite(result), 'checkpoint_invalid_'+name)
    return result


def _fraction(value: Any) -> Fraction:
    _require(type(value) is dict and set(value) == {'numerator', 'denominator'},
             'checkpoint_invalid_fraction')
    a, b = value['numerator'], value['denominator']
    _require(type(a) is int and type(b) is int and b > 0, 'checkpoint_invalid_fraction')
    result = Fraction(a, b)
    _require(result.numerator == a and result.denominator == b, 'checkpoint_noncanonical_fraction')
    return result


def _binding(value: Any) -> tuple | str:
    if type(value) is list and value:
        return tuple(_binding(item) for item in value)
    _require(type(value) is str and bool(value) and value == value.strip(),
             'checkpoint_invalid_energy_binding')
    return value


def _state(value: Any) -> ConservedState:
    _require(type(value) is dict and set(value) == {
        'amounts_mol', 'internal_energy_j', 'energy_model_identity'}, 'checkpoint_invalid_state')
    identity = _binding(value['energy_model_identity'])
    _require(type(identity) is tuple, 'checkpoint_missing_energy_binding')
    return ConservedState(value['amounts_mol'], value['internal_energy_j'], identity)


def _ledger(value: Any) -> StepLedger:
    required = {'start_s', 'end_s', 'face_species_mol', 'face_energy_j',
                'reaction_species_mol', 'cell_work_j', 'cell_work_components_j',
                'component_quadrature_roundoff_j', 'component_sum_residual_j'}
    _require(type(value) is dict and set(value) == required, 'checkpoint_invalid_ledger')
    rounding = value['component_quadrature_roundoff_j']
    if rounding is not None:
        _require(type(rounding) is dict, 'checkpoint_invalid_component_roundoff')
        rounding = {key: tuple(_fraction(v) for v in values) for key, values in rounding.items()}
    ledger = StepLedger(_number(value['start_s'], 'ledger_time'),
                        _number(value['end_s'], 'ledger_time'),
                        value['face_species_mol'], value['face_energy_j'],
                        value['reaction_species_mol'], value['cell_work_j'],
                        value['cell_work_components_j'], rounding)
    saved = value['component_sum_residual_j']
    saved_residual = None if saved is None else tuple(_fraction(v) for v in saved)
    _require(saved_residual == ledger.component_sum_residual_j,
             'checkpoint_component_residual_mismatch')
    return ledger


def exact_state_equal(left: ConservedState, right: ConservedState) -> bool:
    """Preserve nested binding and binary float identity, including signed zero."""
    return (left.energy_model_identity == right.energy_model_identity and
            left.amounts_mol.shape == right.amounts_mol.shape and
            left.internal_energy_j.shape == right.internal_energy_j.shape and
            left.amounts_mol.tobytes() == right.amounts_mol.tobytes() and
            left.internal_energy_j.tobytes() == right.internal_energy_j.tobytes())


@dataclass(frozen=True)
class PrefixAudit:
    states: tuple[ConservedState, ...]
    ledgers: tuple[StepLedger, ...]
    times_s: tuple[float, ...]
    cumulative_component_residual_j: tuple[Fraction, ...] | None


def audit_integration(record: dict[str, Any], policy: IntegrationPolicy, *,
                      start_s: float, end_s: float) -> PrefixAudit:
    """Validate dimensions, continuity and original-initial exact ledger bounds."""
    states = tuple(_state(value) for value in record['states'])
    ledgers = tuple(_ledger(value) for value in record['steps'])
    times = tuple(_number(value, 'time') for value in record['times_s'])
    _require(len(states) == len(times) == len(ledgers)+1 and bool(states),
             'checkpoint_prefix_lengths')
    _require(times[0] == start_s and times[-1] <= end_s and
             all(a < b for a, b in zip(times, times[1:])), 'checkpoint_time_continuity')
    initial = states[0]
    cells, species = initial.amounts_mol.shape
    nsum = [[Fraction() for _ in range(species)] for _ in range(cells)]
    esum = [Fraction() for _ in range(cells)]
    csum = [Fraction() for _ in range(cells)]
    schema: object = ...
    for step, (before, after, ledger) in enumerate(zip(states, states[1:], ledgers)):
        _require(after.amounts_mol.shape == initial.amounts_mol.shape and
                 after.internal_energy_j.shape == initial.internal_energy_j.shape and
                 after.energy_model_identity == initial.energy_model_identity,
                 'checkpoint_state_identity_or_shape')
        _require(ledger.start_s == times[step] and ledger.end_s == times[step+1],
                 'checkpoint_ledger_time_continuity')
        _require(ledger.face_species_mol.shape == (cells+1, species) and
                 ledger.face_energy_j.shape == (cells+1,) and
                 ledger.reaction_species_mol.shape == (cells, species) and
                 ledger.cell_work_j.shape == (cells,), 'checkpoint_ledger_shape')
        current = None if ledger.cell_work_components_j is None else tuple(ledger.cell_work_components_j)
        if schema is ...:
            schema = current
        _require(current == schema, 'checkpoint_component_schema_changed')
        for cell in range(cells):
            for column in range(species):
                delta = (Fraction(float(ledger.face_species_mol[cell, column]))-
                         Fraction(float(ledger.face_species_mol[cell+1, column]))+
                         Fraction(float(ledger.reaction_species_mol[cell, column])))
                nsum[cell][column] += delta
                for origin, total in ((before, delta), (initial, nsum[cell][column])):
                    residual = (Fraction(float(after.amounts_mol[cell, column]))-
                                Fraction(float(origin.amounts_mol[cell, column]))-total)
                    _require(abs(residual) <= Fraction(policy.amount_absolute_tolerance_mol),
                             'checkpoint_cumulative_amount_roundoff')
            delta = (Fraction(float(ledger.face_energy_j[cell]))-
                     Fraction(float(ledger.face_energy_j[cell+1]))+
                     Fraction(float(ledger.cell_work_j[cell])))
            esum[cell] += delta
            for origin, total in ((before, delta), (initial, esum[cell])):
                residual = (Fraction(float(after.internal_energy_j[cell]))-
                            Fraction(float(origin.internal_energy_j[cell]))-total)
                _require(abs(residual) <= Fraction(policy.energy_absolute_tolerance_j),
                         'checkpoint_cumulative_energy_roundoff')
            if ledger.component_sum_residual_j is not None:
                csum[cell] += abs(ledger.component_sum_residual_j[cell])
                _require(csum[cell] <= Fraction(policy.energy_absolute_tolerance_j),
                         'checkpoint_cumulative_component_roundoff')
    expected = tuple(csum) if schema not in (..., None) else None
    saved = record.get('cumulative_absolute_component_residual_j')
    actual = None if saved is None else tuple(_fraction(v) for v in saved)
    _require(actual == expected, 'checkpoint_cumulative_component_record_mismatch')
    return PrefixAudit(states, ledgers, times, expected)


@dataclass(frozen=True)
class ResumePrefix:
    """Only immutable serialized evidence crosses the service preparation boundary."""
    parent_result_raw: bytes
    parent_manifest_raw: bytes
    parent_result_sha256: str
    parent_manifest_sha256: str

    def result(self) -> dict[str, Any]:
        return json.loads(self.parent_result_raw)


def validate_cancelled(result: dict[str, Any], policy: IntegrationPolicy, *,
                       start_s: float, end_s: float) -> PrefixAudit:
    _require(type(result) is dict and type(result.get('integration')) is dict,
             'checkpoint_invalid_integration_record')
    _require(result.get('status') == 'cancelled' and
             result['integration'].get('status') == 'cancelled' and
             result['integration'].get('reason') == 'cancel_requested',
             'checkpoint_requires_cancelled_integration')
    record = result['integration']
    audit = audit_integration(record, policy, start_s=start_s, end_s=end_s)
    _require(bool(audit.ledgers) and audit.times_s[-1] < end_s,
             'checkpoint_requires_interior_accepted_step')
    for name in ('evaluations', 'rejected_trials'):
        _require(type(record[name]) is int and record[name] >= 0, 'checkpoint_invalid_'+name)
    _require(_number(record['elapsed_seconds'], 'elapsed_seconds') >= 0,
             'checkpoint_invalid_elapsed_seconds')
    remaining_policy(record, policy)
    return audit


def remaining_policy(record: dict[str, Any], original: IntegrationPolicy) -> IntegrationPolicy:
    steps = original.maximum_steps-len(record['steps'])
    rejections = original.maximum_rejections-record['rejected_trials']
    wall = Fraction(original.maximum_wall_seconds)-Fraction(record['elapsed_seconds'])
    _require(steps > 0 and rejections > 0 and wall > 0, 'checkpoint_budget_exhausted')
    rounded_wall = float(wall)
    if Fraction(rounded_wall) > wall:
        rounded_wall = math.nextafter(rounded_wall, 0.0)
    _require(rounded_wall > 0, 'checkpoint_budget_unrepresentable')
    return replace(original, maximum_steps=steps, maximum_rejections=rejections,
                   maximum_wall_seconds=rounded_wall)


def merge_integration(parent: dict[str, Any], suffix: dict[str, Any],
                      policy: IntegrationPolicy, *, start_s: float,
                      end_s: float) -> tuple[dict[str, Any], dict[str, Any]]:
    """Admit only suffix prefixes satisfying the original whole-history guards."""
    from .verification_case import encode

    merged = json.loads(json.dumps(parent, allow_nan=False))
    _require(parent['times_s'][-1] == suffix['times_s'][0] and
             exact_state_equal(_state(parent['states'][-1]), _state(suffix['states'][0])),
             'checkpoint_suffix_join_mismatch')
    _require(len(suffix['states']) == len(suffix['times_s']) == len(suffix['steps'])+1,
             'checkpoint_suffix_lengths')
    residual = parent.get('cumulative_absolute_component_residual_j')
    cumulative = None if residual is None else [_fraction(v) for v in residual]
    accepted = 0
    failure = None
    for index, item in enumerate(suffix['steps']):
        proposed = {**merged, 'times_s': merged['times_s']+[suffix['times_s'][index+1]],
                    'states': merged['states']+[suffix['states'][index+1]],
                    'steps': merged['steps']+[item]}
        try:
            ledger = _ledger(item)
            _require((cumulative is None) == (ledger.component_sum_residual_j is None),
                     'checkpoint_component_schema_changed')
            next_cumulative = None if cumulative is None else [
                old+abs(delta) for old, delta in zip(cumulative, ledger.component_sum_residual_j)]
            proposed['cumulative_absolute_component_residual_j'] = encode(next_cumulative)
            audit_integration(proposed, policy, start_s=start_s, end_s=end_s)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            failure = str(exc)
            break
        merged, cumulative = proposed, next_cumulative
        accepted += 1
    elapsed_exact = Fraction(parent['elapsed_seconds'])+Fraction(suffix['elapsed_seconds'])
    elapsed_upper = float(elapsed_exact)
    if Fraction(elapsed_upper) < elapsed_exact:
        elapsed_upper = math.nextafter(elapsed_upper, math.inf)
    merged.update(status='numerical_failure' if failure else suffix['status'],
                  reason=failure or suffix['reason'],
                  evaluations=parent['evaluations']+suffix['evaluations'],
                  rejected_trials=parent['rejected_trials']+suffix['rejected_trials'],
                  elapsed_seconds=elapsed_upper)
    return merged, {'schema': 'sandbox_resume_ledger_audit_v1',
                    'accepted_suffix_steps': accepted,
                    'speculative_suffix_steps': len(suffix['steps']),
                    'original_prefix_steps': len(parent['steps']),
                    'status': 'failed' if failure else 'passed', 'reason': failure,
                    'scope': 'Every retained merged prefix checked by exact binary-float Fraction sums against original initial N/E and original absolute tolerances, including cumulative absolute component-sum residuals. No truncation or material certification.'}
