"""Source endpoint error accounting, without event execution or fresh physics.

Pressure intervals refer to each reported temperature. They do not include the
pressure change over the temperature inverse's uncertainty interval.
"""
from dataclasses import dataclass, fields
from fractions import Fraction as F
import math

from .depletion_integration import DepletionPolicy
from .exact_record import pack, unpack, _policy, canonical
from .integration import IntegrationError
from .source_net_panel import SavedSourceSample, _validate
from .source_net_prefix import _same
from .source_prefix_trial import SourcePrefixTrial, _bounds


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise IntegrationError(reason)


def _copy_policy(policy: DepletionPolicy | None) -> DepletionPolicy | None:
    if policy is None:
        return None
    _require(type(policy) is DepletionPolicy, 'explicit_depletion_policy_required')
    # Reuse the original strict codec: rebuild every nested policy through its
    # constructor and verify exact types/values, without restoring any host.
    original = pack(policy)
    copy = _policy(unpack(original))
    _require(pack(copy) == original, 'event_policy_revalidation_changed_values')
    return copy


def _policy_binding(policy: DepletionPolicy | None) -> str:
    return canonical(pack(policy)).decode('utf-8')


@dataclass(frozen=True)
class SourceEndpointDifferences:
    samples: tuple[SavedSourceSample, SavedSourceSample]
    operator_identity: tuple
    energy_identity: tuple
    fixed_dry_mass_kg: tuple
    sample_bindings: tuple[str, str]
    amount_differences_mol: tuple[tuple[F, ...], ...]
    energy_differences_j: tuple[F, ...]
    # Each row is (T_a, error_T_a, P_a, error_P_a, T_b, error_T_b, P_b, error_P_b).
    inverse_inputs: tuple[tuple[F, ...], ...]
    temperature_bounds_k: tuple[F, ...]
    reported_pressure_bounds_pa: tuple[F, ...]
    maxima: tuple[F, F, F, F]
    comparison_time_offset_s: F
    qualification: str = 'saved_source_endpoint_intervals_at_reported_temperatures'

    def check(self) -> None:
        expected = measure_source_endpoint_pair(*self.samples,
            operator_identity=self.operator_identity, energy_identity=self.energy_identity,
            fixed_dry_mass_kg=self.fixed_dry_mass_kg)
        _require(_same(self, expected), 'source_endpoint_measurements_changed')


def measure_source_endpoint_pair(first: SavedSourceSample, second: SavedSourceSample, *,
        operator_identity: tuple, energy_identity: tuple,
        fixed_dry_mass_kg: tuple) -> SourceEndpointDifferences:
    """Measure two saved actual endpoints; does not establish trajectory accuracy.

    This entry also supports previously saved observations. Their provenance and
    native evaluation remain separate evidence; no live host is manufactured.
    """
    _require(type(fixed_dry_mass_kg) is tuple and bool(fixed_dry_mass_kg)
             and all(type(m) is float and math.isfinite(m) and m > 0 for m in fixed_dry_mass_kg),
             'complete_fixed_source_masses_required')
    samples = first, second
    bindings = tuple(_validate(s,operator_identity,energy_identity,fixed_dry_mass_kg)
                     for s in samples)
    _require(first.evaluation.time == second.evaluation.time, 'same_endpoint_time_required')
    a, b = first.state, second.state
    amounts = tuple(tuple(abs(F(float(x))-F(float(y))) for x,y in zip(row_a,row_b))
                    for row_a,row_b in zip(a.amounts_mol,b.amounts_mol))
    energy = tuple(abs(F(float(x))-F(float(y)))
                   for x,y in zip(a.internal_energy_j,b.internal_energy_j))
    left, right = _bounds(first.evaluation), _bounds(second.evaluation)
    inputs = tuple(tuple(map(F,(*a,*b))) for a,b in zip(left,right))
    temperature = tuple(abs(v[0]-v[4])+v[1]+v[5] for v in inputs)
    pressure = tuple(abs(v[2]-v[6])+v[3]+v[7] for v in inputs)
    maxima = max(x for row in amounts for x in row), max(energy), max(temperature), max(pressure)
    return SourceEndpointDifferences(samples,operator_identity,energy_identity,fixed_dry_mass_kg,
        bindings,amounts,energy,inputs,temperature,pressure,maxima,F())


@dataclass(frozen=True)
class SourceEndpointComparison:
    trial: SourcePrefixTrial
    event_policy: DepletionPolicy | None
    policy_binding: str
    differences: SourceEndpointDifferences
    integration_discrepancy: float
    # N, U, T, and pressure at reported T. None means no declared event policy.
    gates: tuple[bool | None, ...]
    status: str
    full_inverse_pressure_gate: str
    event_time_gate: str = 'not_evaluated'
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self) -> None:
        _require(_policy_binding(self.event_policy) == self.policy_binding, 'source_event_policy_binding')
        expected = compare_source_trial_endpoints(self.trial,event_policy=self.event_policy)
        _require(all(_same(getattr(self,f.name),getattr(expected,f.name))
                     for f in fields(self) if f.name != 'trial'), 'source_endpoint_comparison_changed')


def compare_source_trial_endpoints(trial: SourcePrefixTrial, *,
        event_policy: DepletionPolicy | None) -> SourceEndpointComparison:
    """Compare a checked successful prefix/reference under explicit event gates.

    Exceeding an interval upper bound fails to certify the tolerance; it does
    not prove the unknown states differ by more than the requested tolerance.
    The policy's correction/packet settings are retained, never executed here.
    """
    _require(type(trial) is SourcePrefixTrial, 'actual_source_trial_required')
    trial.check()
    _require(trial.status == 'validated_positive_numerical_trial', 'validated_source_trial_required')
    policy = _copy_policy(event_policy)
    first, second = trial.captures[2], trial.captures[-1]
    data = measure_source_endpoint_pair(
        SavedSourceSample(first.state,first.evaluation,first.role),
        SavedSourceSample(second.state,second.evaluation,second.role),
        operator_identity=trial.operator_identity,energy_identity=trial.energy_identity,
        fixed_dry_mass_kg=trial.fixed_dry_mass_kg)
    if policy is None:
        gates = (None,)*4
        status = 'missing_explicit_event_policy'
    else:
        limits = (policy.amount_absolute_mol,policy.energy_absolute_j,
                  policy.temperature_absolute_k,policy.pressure_absolute_pa)
        gates = tuple(value <= F(limit) for value,limit in zip(data.maxima,limits))
        status = ('reported_endpoint_gates_satisfied' if all(gates)
                  else 'endpoint_tolerance_not_certified')
    # With exactly zero inverse-T error, the prescribed-temperature interval
    # already has the full inverse-temperature scope. This is still no event.
    has_temperature_error = any(row[1] or row[5] for row in data.inverse_inputs)
    pressure_gate = ('unresolved' if has_temperature_error or policy is None else
                     'within_tolerance' if gates[3] else 'not_certified')
    return SourceEndpointComparison(trial,policy,_policy_binding(policy),data,trial.discrepancy,
                                    gates,status,pressure_gate)
