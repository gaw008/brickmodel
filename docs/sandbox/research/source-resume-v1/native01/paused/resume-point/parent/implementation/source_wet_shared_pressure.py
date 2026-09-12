"""Conditional smooth-liquid root differences for one explicit live volume.

The only EOS entry is ``collect_source_wet_pressure_pair``. Saved evidence is
checked passively. Four observations check consistency and root-end signs;
they do not establish the assumed domain-wide EOS error or liquid stability.
"""
from .source_run_observer import emit_source_event, emit_source_failure
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from fractions import Fraction as F
import math
import sys

from .deforming_solid_storage import _digest
from .mass_storage_bridge import upper
from .mass_wet_storage import lower, wet_fluid_pressure_bounds
from .rational_intervals import (
    RationalInterval, interval_difference, interval_divide_positive,
    interval_sum, residual_to_root_bound,
)
from .source_inverse_pressure import (
    PressureContinuation, SourceInversePressure, _require, propagate_declared_pressure,
)
from .source_net_prefix import _same
from .source_wet_storage import ManufacturedFixedFluidVolume, SourceWetStorage
from .water_properties import WaterState


SHARED_WET_ASSUMPTIONS = (
    'same_live_constant_available_volume_parameter_with_original_uncertainty',
    'smooth_continuous_stable_liquid_vP_nonpositive_on_entire_common_support',
    'original_epsilon_applies_to_native_fl_m_over_rho_minus_smooth_v_on_entire_support',
    'epsilon_scope_is_certificate_applicability_condition_not_proved_by_field_name_or_four_points',
    'original_caloric_and_abs_uP_bounds_cover_full_inverse_temperature_continuation',
    'finite_normal_binary64_forward_operations_over_entire_common_support',
    'current_saved_machine_residual_only_not_arbitrary_future_solver_outputs',
)


@dataclass(frozen=True)
class SourceSharedWetVolume:
    storage: SourceWetStorage
    volume: ManufacturedFixedFluidVolume
    object_identity: tuple[int, int]
    storage_identity: str
    input_binding: str
    volume_interval_m3: RationalInterval
    source_ids: tuple[str, ...]
    qualification: str = 'explicit_same_live_source_wet_volume_not_material_admission'
    source_certified: bool = False
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self) -> None:
        """Recheck original live parameter identity without an EOS query."""
        _require(type(self.storage) is SourceWetStorage
                 and type(self.volume) is ManufacturedFixedFluidVolume
                 and self.storage.volume is self.volume,
                 'same_live_source_storage_and_volume_required')
        expected = declare_source_shared_wet_volume(self.storage)
        _require(all(_same(getattr(self, f.name), getattr(expected, f.name))
                     for f in fields(self) if f.name not in ('storage', 'volume')),
                 'source_shared_wet_volume_declaration_changed')


def declare_source_shared_wet_volume(storage: SourceWetStorage) -> SourceSharedWetVolume:
    """Explicitly declare the actual storage's one constant uncertain V object."""
    _require(type(storage) is SourceWetStorage, 'actual_source_storage_required')
    storage._check()
    volume = storage.volume
    nominal, error = F(volume.value_m3), F(volume.error_m3)
    identity, sources = storage.model_identity, storage.source_ids
    return SourceSharedWetVolume(storage, volume, (id(storage), id(volume)), identity,
        _digest((identity, volume, sources)), (nominal-error, nominal+error), sources)


@dataclass(frozen=True)
class WetPairSupport:
    reported_pressure_boxes_pa: tuple[RationalInterval, RationalInterval]
    pressure_domain_pa: RationalInterval
    interval_pa: RationalInterval | None
    temperatures_k: tuple[float, float]
    requests: tuple[tuple[float, float, str], ...]
    endpoint_indices: tuple[tuple[int, int], ...]
    reason: str | None


@dataclass(frozen=True)
class WetVolumeObservation:
    ordinal: int
    temperature_k: float
    pressure_pa: float
    phase: str
    water_object_identity: int
    water_binding: str
    source_asset_sha256: tuple[tuple[str, str], ...]
    state: WaterState | None
    native_molar_volume_m3_mol: float | None
    exact_mass_density_ratio_m3_mol: F | None
    ratio_projection_m3_mol: F | None
    declared_volume_error_m3_mol: F
    failure_type: str | None = None
    failure_message: str | None = None


@dataclass(frozen=True)
class SourceWetPairEvidence:
    support: WetPairSupport
    attempts: tuple[WetVolumeObservation, ...]
    input_binding: str
    observation_binding: str
    assumptions: tuple[str, ...] = SHARED_WET_ASSUMPTIONS


@dataclass(frozen=True)
class SourceWetPressureErrorParts:
    volume_interval_m3_mol: RationalInterval
    low_root_sign_lower_m3: F
    high_root_sign_upper_m3: F
    compliance_lower_m3_pa: F
    actual_fluid_error_pa: F
    global_error_pa: F
    extra_volume_error_pa: F
    total_error_pa: F
    projection_error_pa: F
    liquid_product_projection_kg: F
    gas_product_projection_j: F
    liquid_rounding_residual_m3: F
    gas_rounding_residual_m3: F
    sum_rounding_residual_m3: F
    machine_residual_bound_m3: F
    saved_volume_residual_m3: F
    report_to_root_bound_pa: F
    retained_report_error_pa: F
    original_temperature_error_pa: F
    added_temperature_error_pa: F
    continuation: PressureContinuation


@dataclass(frozen=True)
class SourceSharedWetPressurePair:
    shared_volume: SourceSharedWetVolume
    endpoints: tuple[SourceInversePressure, SourceInversePressure]
    evidence: SourceWetPairEvidence
    input_binding: str
    error_parts: tuple[SourceWetPressureErrorParts, ...]
    residual_interval_m3: RationalInterval | None
    compliance_lower_m3_pa: F | None
    root_difference_bound_pa: F | None
    joint_bound_pa: F | None
    independent_bound_pa: F | None
    bound_pa: F | None
    status: str
    reason: str | None
    assumptions: tuple[str, ...] = SHARED_WET_ASSUMPTIONS
    qualification: str = 'conditional_full_temperature_shared_wet_volume_not_event_or_material_admission'
    source_certified: bool = False
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self) -> None:
        """Rebuild all bounds from saved WaterState records; never query EOS."""
        _require(type(self.endpoints) is tuple and len(self.endpoints) == 2,
                 'two_actual_source_wet_endpoints_required')
        expected = enclose_source_wet_pressure_pair(*self.endpoints,
            shared_volume=self.shared_volume, evidence=self.evidence)
        _require(all(_same(getattr(self, f.name), getattr(expected, f.name))
                     for f in fields(self) if f.name not in ('shared_volume', 'endpoints')),
                 'source_shared_wet_pressure_result_changed')


class SourceWetPairCollectionError(ValueError):
    """A failed explicit collection, including every actual attempt and return."""

    def __init__(self, stage: str, endpoints: tuple[SourceInversePressure, SourceInversePressure],
                 shared_volume: SourceSharedWetVolume, support: WetPairSupport,
                 attempts: tuple[WetVolumeObservation, ...], cause: BaseException):
        super().__init__(f'source_wet_pair_collection_{stage}: {type(cause).__name__}: {cause}')
        self.stage = stage
        self.endpoints = endpoints
        self.shared_volume = shared_volume
        self.support = support
        self.attempts = attempts
        self.exception_type = type(cause).__name__
        self.exception_message = str(cause)


def _inputs(a: SourceInversePressure, b: SourceInversePressure,
            shared: SourceSharedWetVolume) -> str:
    _require(type(a) is SourceInversePressure and type(b) is SourceInversePressure,
             'two_actual_source_wet_endpoints_required')
    _require(type(shared) is SourceSharedWetVolume, 'explicit_source_shared_wet_volume_required')
    shared.check()
    _require(a.storage is b.storage is shared.storage
             and a.storage.volume is b.storage.volume is shared.volume,
             'same_live_source_storage_and_volume_required')
    for endpoint in (a, b):
        endpoint.check()
        _original_decomposition(endpoint)
    return _digest((shared.input_binding, shared.object_identity,
        tuple((id(e), e.storage_identity, e.input_binding, e.initial_bounds_pa, e.continuation)
              for e in (a, b))))


def _original_decomposition(endpoint: SourceInversePressure) -> tuple[F, F, F, F, F]:
    point = endpoint.inverse.point
    fluid = F(point.fluid.pressure_error_bound_pa)
    global_error, extra, total_float = wet_fluid_pressure_bounds(endpoint.storage.fluid_template,
        point.fluid, endpoint.state.gas_amounts_mol, point.temperature_k,
        F(endpoint.storage.volume.error_m3))
    _require(_same((point.global_pressure_error_pa, point.extra_pressure_error_pa, point.pressure_error_pa),
                  (float(global_error), float(extra), total_float)),
             'source_shared_wet_pressure_decomposition_changed')
    total = F(total_float)
    return fluid, global_error, extra, total, abs(total-fluid-extra)


def _support(endpoints: tuple[SourceInversePressure, SourceInversePressure]) -> WetPairSupport:
    boxes = tuple((F(e.inverse.point.pressure_pa)-F(e.inverse.point.pressure_error_pa),
                   F(e.inverse.point.pressure_pa)+F(e.inverse.point.pressure_error_pa)) for e in endpoints)
    domains = tuple(e.continuation.pressure_domain_pa for e in endpoints) + tuple(
        tuple(map(F, e.storage.fluid_template.envelope.pressure_range_pa)) for e in endpoints)
    domain = (max(d[0] for d in domains), min(d[1] for d in domains))
    temperatures = tuple(e.inverse.point.temperature_k for e in endpoints)
    interval = None
    requests, indices = [], []
    reason = None
    if any(e.continuation.status != 'conditional_pressure_enclosure' for e in endpoints):
        reason = 'source_wet_endpoint_domain_unresolved'
    else:
        hull = (min(b[0] for b in boxes), max(b[1] for b in boxes))
        if hull[0] <= 0:
            reason = 'source_shared_wet_support_domain_exit'
        else:
            try:
                projected = (lower(hull[0]), upper(hull[1]))
                if not all(math.isfinite(x) for x in projected):
                    raise ValueError('nonfinite support')
                interval = tuple(map(F, projected))
            except (ValueError, OverflowError):
                reason = 'source_shared_wet_support_unrepresentable'
            if interval is not None and not domain[0] <= interval[0] <= interval[1] <= domain[1]:
                reason = 'source_shared_wet_support_domain_exit'
    if reason is None:
        for temperature in temperatures:
            row = []
            for pressure in map(float, interval):
                request = (temperature, pressure, 'liquid')
                # All endpoints have this one actual water instance by _inputs.
                if request not in requests:
                    requests.append(request)
                row.append(requests.index(request))
            indices.append(tuple(row))
    return WetPairSupport(boxes, domain, interval, temperatures,
                          tuple(requests), tuple(indices), reason)


def _water_metadata(storage: SourceWetStorage) -> tuple[int, str, tuple[tuple[str, str], ...]]:
    water = storage.water
    assets = tuple(sorted(water.source_asset_sha256.items()))
    _require(all(type(k) is str and type(v) is str for k, v in assets),
             'source_wet_water_asset_metadata_changed')
    signature = _digest((type(water).__module__, type(water).__qualname__,
                         water.reference, water.implementation, water.source_ids, assets,
                         water.numerical_limits))
    return id(water), signature, assets


def _validate_observation(observation: WetVolumeObservation, ordinal: int,
        request: tuple[float, float, str], storage: SourceWetStorage) -> WetVolumeObservation:
    _require(type(observation) is WetVolumeObservation
             and type(observation.ordinal) is int and observation.ordinal == ordinal
             and _same((observation.temperature_k, observation.pressure_pa, observation.phase), request)
             and _same((observation.water_object_identity, observation.water_binding,
                        observation.source_asset_sha256), _water_metadata(storage))
             and type(observation.declared_volume_error_m3_mol) is F
             and observation.declared_volume_error_m3_mol == F(storage.fluid_template.envelope.liquid_v_error_m3_mol)
             and observation.failure_type is None and observation.failure_message is None,
             'source_wet_observation_input_changed')
    state, water = observation.state, storage.water
    _require(type(state) is WaterState, 'actual_liquid_water_state_required')
    numeric = tuple(getattr(state, f.name) for f in fields(WaterState)
                    if f.name not in ('reference', 'implementation', 'method_id', 'phase'))
    _require(all(type(x) is float and math.isfinite(x) for x in numeric)
             and min(state.density_kg_m3, state.cp_j_kg_k, state.cv_j_kg_k) > 0
             and _same((state.temperature_k, state.pressure_pa, state.phase), request)
             and _same(state.reference, water.reference)
             and _same(state.implementation, water.implementation)
             and type(state.method_id) is str and bool(state.method_id.strip()),
             'source_wet_observation_source_or_state_changed')
    mass, density = state.molar_mass_kg_mol, state.density_kg_m3
    _require(type(mass) is float and math.isfinite(mass) and mass > 0,
             'source_wet_observation_molar_mass_changed')
    volume = mass/density
    _require(math.isfinite(volume) and volume > 0, 'source_wet_observation_ratio_unrepresentable')
    exact = F(mass)/F(density)
    return replace(observation, native_molar_volume_m3_mol=volume,
                   exact_mass_density_ratio_m3_mol=exact, ratio_projection_m3_mol=F(volume)-exact)


def _evidence(support: WetPairSupport, attempts: tuple[WetVolumeObservation, ...],
              binding: str) -> SourceWetPairEvidence:
    return SourceWetPairEvidence(support, attempts, binding, _digest((support, attempts)))


def collect_source_wet_pressure_pair(a: SourceInversePressure, b: SourceInversePressure, *,
        shared_volume: SourceSharedWetVolume,
        cancel: Callable[[], bool] | None = None) -> SourceSharedWetPressurePair:
    """Collect at most four unique explicit EOS points, preserving failure prefixes.

    No point is retried or moved after the support is fixed. Cancellation is
    checked before each unique request, so an unstarted request is not counted.
    Returned states are retained before their metadata or derived ratio checks.
    """
    _require(cancel is None or callable(cancel), 'explicit_wet_collection_cancel_required')
    binding = _inputs(a, b, shared_volume)
    endpoints = (a, b)
    support = _support(endpoints)
    attempts = []
    metadata = _water_metadata(shared_volume.storage)
    epsilon = F(shared_volume.storage.fluid_template.envelope.liquid_v_error_m3_mol)
    stage = 'prepare'
    observer_delivery = False
    state = None
    request = None
    try:
        for ordinal, request in enumerate(support.requests):
            state = None
            stage = 'cancel'
            if cancel is not None:
                cancelled = cancel()
                _require(type(cancelled) is bool, 'boolean_collection_cancel_required')
                _require(not cancelled, 'source_wet_pressure_collection_cancelled')
            stage = 'validate_inputs'
            _require(_inputs(a, b, shared_volume) == binding,
                     'source_wet_collection_original_binding_changed')
            stage = 'request'
            attempt = WetVolumeObservation(ordinal, *request, *metadata, None, None, None, None, epsilon)
            attempts.append(attempt)
            state = None
            observer_delivery = True
            emit_source_event('wet_started', storage=shared_volume.storage, request=request)
            observer_delivery = False
            _require(_inputs(a, b, shared_volume) == binding,
                     'source_wet_collection_original_binding_changed')
            state = shared_volume.storage.water.state_tp(request[0], request[1], phase=request[2])
            attempts[-1] = replace(attempt, state=state)
            observer_delivery = True
            emit_source_event('wet_returned', storage=shared_volume.storage, request=request, state=state)
            observer_delivery = False
            stage = 'validate_return'
            attempts[-1] = _validate_observation(attempts[-1], ordinal, request, shared_volume.storage)
        stage = 'enclose'
        return enclose_source_wet_pressure_pair(a, b, shared_volume=shared_volume,
                                               evidence=_evidence(support, tuple(attempts), binding))
    except BaseException as exc:
        emit_source_failure('wet_failed', exc, storage=shared_volume.storage, request=request, state=state)
        if observer_delivery or not isinstance(exc, Exception):
            raise
        if attempts and stage in ('request', 'validate_return'):
            attempts[-1] = replace(attempts[-1], failure_type=type(exc).__name__, failure_message=str(exc))
        raise SourceWetPairCollectionError(stage, endpoints, shared_volume, support, tuple(attempts), exc) from exc


class _UnresolvedBox(ValueError):
    """The declared whole-support numerical contract cannot be established."""


def _normal_interval(lo: F, hi: F) -> None:
    if not F(sys.float_info.min) <= lo <= hi <= F(sys.float_info.max):
        raise _UnresolvedBox('source_shared_wet_rounding_box_not_normal')


def _spacing(value: F) -> F:
    _normal_interval(value, value)
    try:
        bound = upper(value)
    except (ValueError, OverflowError) as exc:
        raise _UnresolvedBox('source_shared_wet_rounding_box_unrepresentable') from exc
    if not math.isfinite(bound):
        raise _UnresolvedBox('source_shared_wet_rounding_box_unrepresentable')
    return F(math.ulp(bound))


def _error_parts(endpoint: SourceInversePressure, support: WetPairSupport,
        observations: tuple[WetVolumeObservation, WetVolumeObservation],
        volume: RationalInterval) -> SourceWetPressureErrorParts:
    low, high = observations
    epsilon = low.declared_volume_error_m3_mol
    vbox = (F(high.native_molar_volume_m3_mol)-epsilon, F(low.native_molar_volume_m3_mol)+epsilon)
    nl, ng, r, B, t, et, p, old_ep = endpoint.continuation.inputs
    jlo, jhi = support.interval_pa
    # Four points check consistency, not the full-domain stability hypothesis.
    if vbox[0] <= 0 or vbox[0] > vbox[1]:
        raise _UnresolvedBox('source_shared_wet_liquid_volume_box_unresolved')
    sign_low = nl*(F(low.native_molar_volume_m3_mol)-epsilon)+ng*r*t/jlo-volume[1]
    sign_high = nl*(F(high.native_molar_volume_m3_mol)+epsilon)+ng*r*t/jhi-volume[0]
    if sign_low < 0 or sign_high > 0:
        raise _UnresolvedBox('source_shared_wet_root_existence_unresolved')
    compliance = ng*r*t/jhi**2
    if vbox[0] <= epsilon:
        raise _UnresolvedBox('source_shared_wet_rounding_box_not_normal')
    floor, cap = (vbox[0]-epsilon)/2, 2*(vbox[1]+epsilon)
    mass = F(low.state.molar_mass_kg_mol)
    _require(_same(low.state.molar_mass_kg_mol, high.state.molar_mass_kg_mol),
             'source_wet_observation_molar_mass_changed')
    rho_min, rho_max = mass/cap, mass/floor
    _normal_interval(floor, cap)
    _normal_interval(rho_min, rho_max)
    liquid_product_float = endpoint.state.liquid_water_mol*float(mass)
    gas_sum_float = math.fsum(endpoint.state.gas_amounts_mol)
    nr_float = gas_sum_float*float(r)
    nrt_float = nr_float*float(t)
    for value in (liquid_product_float, gas_sum_float, nr_float, nrt_float):
        if not math.isfinite(value):
            raise _UnresolvedBox('source_shared_wet_rounding_box_unrepresentable')
        _normal_interval(F(value), F(value))
    product, nrt = F(liquid_product_float), F(nrt_float)
    _normal_interval(nl*mass, nl*mass)
    _normal_interval(product/rho_max, product/rho_min)
    _normal_interval(nrt/jhi, nrt/jlo)
    delta_product, delta_nrt = abs(product-nl*mass), abs(nrt-ng*r*t)
    liquid_round = _spacing(product/rho_min)
    gas_round = _spacing(nrt/jlo)
    gl = nl*(epsilon+_spacing(cap))+delta_product/rho_min+liquid_round
    gg = delta_nrt/jlo+gas_round
    gs = 2*_spacing(product/rho_min+liquid_round+nrt/jlo+gas_round+volume[1])
    gamma = gl+gg+gs
    saved_residual = F(endpoint.inverse.point.fluid.mechanical.volume_residual_m3)
    zeta = (abs(saved_residual)+gamma)/compliance
    fluid, global_error, extra, total, projection = _original_decomposition(endpoint)
    radius = max(old_ep, abs(p-jlo), abs(jhi-p))
    continuation = propagate_declared_pressure(nl, ng, r, B, t, et, p, radius,
        temperature_domain_k=endpoint.continuation.temperature_domain_k,
        pressure_domain_pa=support.pressure_domain_pa)
    if continuation.status != 'conditional_pressure_enclosure':
        raise _UnresolvedBox('source_shared_wet_temperature_continuation_unresolved')
    old_slope = endpoint.continuation.slope_pa_k
    used_slope = max(old_slope, continuation.slope_pa_k)
    return SourceWetPressureErrorParts(vbox, sign_low, sign_high, compliance, fluid,
        global_error, extra, total, projection, delta_product, delta_nrt, gl, gg, gs,
        gamma, saved_residual, zeta, fluid+projection+zeta, old_slope*et,
        (used_slope-old_slope)*et, continuation)


def enclose_source_wet_pressure_pair(a: SourceInversePressure, b: SourceInversePressure, *,
        shared_volume: SourceSharedWetVolume,
        evidence: SourceWetPairEvidence) -> SourceSharedWetPressurePair:
    """Passive bound from frozen common-support liquid observations.

    Selected bound is the joint bound. The older independent result remains
    visible and is never minimized against this separately established target.
    """
    binding = _inputs(a, b, shared_volume)
    endpoints, support = (a, b), _support((a, b))
    _require(type(evidence) is SourceWetPairEvidence and type(evidence.attempts) is tuple
             and _same(evidence.assumptions, SHARED_WET_ASSUMPTIONS)
             and _same(evidence.support, support) and evidence.input_binding == binding
             and evidence.observation_binding == _digest((evidence.support, evidence.attempts))
             and len(evidence.attempts) == len(support.requests), 'source_wet_pair_evidence_changed')
    for ordinal, (attempt, request) in enumerate(zip(evidence.attempts, support.requests)):
        expected = _validate_observation(attempt, ordinal, request, shared_volume.storage)
        _require(_same(expected, attempt), 'source_wet_observation_ratio_changed')
    parts = ()
    residual = compliance = root_bound = joint = independent = selected = None

    def finish(reason: str | None) -> SourceSharedWetPressurePair:
        return SourceSharedWetPressurePair(shared_volume, endpoints, evidence, binding,
            parts, residual, compliance, root_bound, joint, independent, selected,
            'conditional_shared_wet_pressure_enclosure' if reason is None else 'unresolved', reason)

    if all(e.continuation.radius_pa is not None for e in endpoints):
        independent = (abs(F(a.inverse.point.pressure_pa)-F(b.inverse.point.pressure_pa))
                       + a.continuation.radius_pa+b.continuation.radius_pa)
    if support.reason is not None:
        return finish(support.reason)
    try:
        for endpoint, indices in zip(endpoints, support.endpoint_indices):
            observations = tuple(evidence.attempts[i] for i in indices)
            parts += (_error_parts(endpoint, support, observations, shared_volume.volume_interval_m3),)
    except _UnresolvedBox as exc:
        return finish(str(exc))
    na, nb = (F(e.state.liquid_water_mol) for e in endpoints)
    gas_a, gas_b = (sum(map(F, e.state.gas_amounts_mol), F()) for e in endpoints)
    r = a.continuation.inputs[2]
    ta, tb = map(F, support.temperatures_k)
    liquid = interval_difference(tuple(na*v for v in parts[0].volume_interval_m3_mol),
                                 tuple(nb*v for v in parts[1].volume_interval_m3_mol))
    numerator = r*(gas_a*ta-gas_b*tb)
    gas = interval_divide_positive((numerator, numerator), support.interval_pa)
    residual = interval_sum((liquid, gas))
    compliance = min(part.compliance_lower_m3_pa for part in parts)
    root_bound = residual_to_root_bound(residual, compliance)
    joint = root_bound+sum((part.retained_report_error_pa+part.original_temperature_error_pa
                           +part.added_temperature_error_pa for part in parts), F())
    selected = joint
    return finish(None)
