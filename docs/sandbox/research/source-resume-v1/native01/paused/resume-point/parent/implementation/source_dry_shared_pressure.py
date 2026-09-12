"""Full-temperature dry pressure differences for one explicit live volume parameter.

This conditional evidence uses the source model's ideal-gas caloric contract:
with no liquid, fixed dry mass and disabled reactions, U(T) is independent of V.
It grants no event or material qualification and does not change single-end bounds.
"""
from dataclasses import dataclass, fields
from fractions import Fraction as F
import math
import sys

from .deforming_solid_storage import _digest
from .mass_storage_bridge import upper
from .mass_wet_storage import wet_fluid_pressure_bounds
from .source_dry_pressure import SourceDryPressure
from .source_inverse_pressure import _require
from .source_net_prefix import _same
from .source_wet_storage import ManufacturedFixedFluidVolume, SourceWetStorage


SHARED_DRY_ASSUMPTIONS = (
    'same_live_constant_available_volume_parameter_with_original_uncertainty',
    'dry_ideal_gas_caloric_energy_independent_of_volume_with_fixed_source_mass',
    'independent_full_inverse_temperature_intervals',
    'actual_saved_fluid_error_and_reconstructed_original_volume_error_decomposition',
    'finite_normal_binary64_forward_rounding_over_entire_temperature_volume_box',
)


@dataclass(frozen=True)
class SourceSharedDryVolume:
    storage: SourceWetStorage
    volume: ManufacturedFixedFluidVolume
    object_identity: tuple[int, int]
    storage_identity: str
    input_binding: str
    volume_interval_m3: tuple[F, F]
    source_ids: tuple[str, ...]
    qualification: str = 'explicit_same_live_source_dry_volume_not_material_admission'
    source_certified: bool = False
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self) -> None:
        """Recheck live object identity and original content without any EOS call."""
        _require(type(self.storage) is SourceWetStorage
                 and type(self.volume) is ManufacturedFixedFluidVolume
                 and self.storage.volume is self.volume,
                 'same_live_source_storage_and_volume_required')
        expected = declare_source_shared_dry_volume(self.storage)
        _require(all(_same(getattr(self, item.name), getattr(expected, item.name))
                     for item in fields(self) if item.name not in ('storage', 'volume')),
                 'source_shared_dry_volume_declaration_changed')


def declare_source_shared_dry_volume(storage: SourceWetStorage) -> SourceSharedDryVolume:
    """Declare correlation only for this storage's actual constant volume object.

    Process-local object identities supplement the complete content binding. A
    JSON copy of this record alone cannot establish a new live shared parameter.
    """
    _require(type(storage) is SourceWetStorage, 'actual_source_storage_required')
    storage._check()
    volume = storage.volume
    nominal, error = F(volume.value_m3), F(volume.error_m3)
    identity, sources = storage.model_identity, storage.source_ids
    return SourceSharedDryVolume(storage, volume, (id(storage), id(volume)), identity,
        _digest((identity, volume, sources)), (nominal-error, nominal+error), sources)


@dataclass(frozen=True)
class SourceDryPressureErrorParts:
    nominal_fluid_lower_bound_pa: F
    actual_fluid_error_pa: F
    global_error_pa: F
    extra_volume_error_pa: F
    total_error_pa: F
    projection_error_pa: F
    inventory_sum_error_mol: F
    inventory_R_product_error_j_k: F
    box_rounding_error_pa: F
    retained_error_pa: F


@dataclass(frozen=True)
class SourceSharedDryPressurePair:
    shared_volume: SourceSharedDryVolume
    endpoints: tuple[SourceDryPressure, SourceDryPressure]
    input_binding: str
    error_parts: tuple[SourceDryPressureErrorParts, ...]
    ideal_interval_pa: tuple[F, F] | None
    joint_interval_pa: tuple[F, F] | None
    joint_bound_pa: F | None
    independent_bound_pa: F | None
    bound_pa: F | None
    status: str
    reason: str | None
    assumptions: tuple[str, ...] = SHARED_DRY_ASSUMPTIONS
    qualification: str = 'conditional_full_temperature_shared_dry_volume_not_event_or_material_admission'
    source_certified: bool = False
    event_admitted: bool = False
    material_qualified: bool = False

    def check(self) -> None:
        """Rebuild every input and derived bound using saved source records only."""
        _require(type(self.endpoints) is tuple and len(self.endpoints) == 2,
                 'two_actual_source_dry_endpoints_required')
        expected = enclose_source_dry_pressure_pair(*self.endpoints, shared_volume=self.shared_volume)
        _require(all(_same(getattr(self, item.name), getattr(expected, item.name))
                     for item in fields(self) if item.name not in ('shared_volume', 'endpoints')),
                 'source_shared_dry_pressure_result_changed')


class _UnrepresentableBox(ValueError):
    """The whole-box floating-point rounding contract could not be established."""


def _spacing(value: F) -> F:
    # A full ULP at an upward representable point covers every round-to-nearest
    # error below this positive normal magnitude, including a binade boundary.
    try:
        bound = upper(value)
    except (ValueError, OverflowError) as exc:
        raise _UnrepresentableBox('source_shared_dry_rounding_box_unrepresentable') from exc
    if not math.isfinite(bound) or bound < sys.float_info.min:
        raise _UnrepresentableBox('source_shared_dry_rounding_box_not_normal')
    return F(math.ulp(bound))


def _original_decomposition(endpoint: SourceDryPressure) -> tuple[F, F, F, F, F]:
    point = endpoint.inverse.point
    fluid = F(point.fluid.pressure_error_bound_pa)
    global_error, extra, total_float = wet_fluid_pressure_bounds(endpoint.storage.fluid_template,
        point.fluid, endpoint.state.gas_amounts_mol, point.temperature_k,
        F(endpoint.storage.volume.error_m3))
    expected = (float(global_error), float(extra), total_float)
    _require(_same((point.global_pressure_error_pa, point.extra_pressure_error_pa,
                    point.pressure_error_pa), expected),
             'source_shared_dry_pressure_decomposition_changed')
    total = F(total_float)
    return fluid, global_error, extra, total, abs(total-fluid-extra)


def _error_parts(endpoint: SourceDryPressure,
        decomposition: tuple[F, F, F, F, F]) -> SourceDryPressureErrorParts:
    ng, r = endpoint.continuation.inputs[:2]
    high = endpoint.continuation.temperature_interval_k[1]
    vmin = endpoint.continuation.volume_interval_m3[0]
    nhat_float = math.fsum(endpoint.state.gas_amounts_mol)
    nr_float = nhat_float*float(r)
    if not math.isfinite(nr_float) or min(nhat_float, nr_float) < sys.float_info.min:
        raise _UnrepresentableBox('source_shared_dry_rounding_box_not_normal')
    nhat, nr = F(nhat_float), F(nr_float)
    dn, dnr = abs(nhat-ng), abs(nr-nhat*r)
    product_rounding = _spacing(abs(nr)*high)
    box = ((dn*r+dnr)*high+product_rounding)/vmin + _spacing((abs(nr)*high+product_rounding)/vmin)
    fluid, global_error, extra, total, projection = decomposition
    return SourceDryPressureErrorParts(endpoint.initial_bounds_pa[0], fluid,
        global_error, extra, total, projection, dn, dnr, box, fluid+projection+box)


def enclose_source_dry_pressure_pair(a: SourceDryPressure, b: SourceDryPressure, *,
        shared_volume: SourceSharedDryVolume) -> SourceSharedDryPressurePair:
    """Bound Pa-Pb over both complete T intervals and their one shared V interval.

    The original independent radius remains visible. The joint interval retains
    actual fluid error, total-bound projection, and separate full-box rounding;
    no pressure error is subtracted from an old single-end certificate.
    """
    _require(type(a) is SourceDryPressure and type(b) is SourceDryPressure,
             'two_actual_source_dry_endpoints_required')
    _require(type(shared_volume) is SourceSharedDryVolume, 'explicit_source_shared_dry_volume_required')
    shared_volume.check()
    _require(a.storage is b.storage is shared_volume.storage
             and a.storage.volume is b.storage.volume is shared_volume.volume,
             'same_live_source_storage_and_volume_required')
    a.check()
    b.check()
    endpoints = (a, b)
    binding = _digest(tuple((end.storage_identity, end.input_binding,
                            end.initial_bounds_pa, end.continuation) for end in endpoints))
    decompositions = tuple(_original_decomposition(end) for end in endpoints)
    parts = ()
    ideal = joint = joint_bound = independent = selected = None

    def finish(reason: str | None) -> SourceSharedDryPressurePair:
        return SourceSharedDryPressurePair(shared_volume, endpoints, binding, parts,
            ideal, joint, joint_bound, independent, selected,
            'conditional_shared_dry_pressure_enclosure' if reason is None else 'unresolved', reason)

    if any(end.continuation.status != 'conditional_dry_pressure_enclosure' for end in endpoints):
        return finish('source_dry_endpoint_domain_unresolved')
    _require(a.continuation.inputs[1] == b.continuation.inputs[1]
             and all(end.continuation.volume_interval_m3 == shared_volume.volume_interval_m3
                     for end in endpoints), 'source_shared_dry_constant_binding_changed')
    independent = (abs(F(a.inverse.point.pressure_pa)-F(b.inverse.point.pressure_pa))
                   + a.continuation.radius_pa+b.continuation.radius_pa)
    try:
        parts = tuple(_error_parts(end, values) for end, values in zip(endpoints, decompositions))
    except _UnrepresentableBox as exc:
        return finish(str(exc))
    for end, error in zip(endpoints, parts):
        pressure_domain = end.continuation.pressure_domain_pa
        envelope_domain = tuple(map(F, end.storage.fluid_template.envelope.pressure_range_pa))
        lo, hi = max(pressure_domain[0], envelope_domain[0]), min(pressure_domain[1], envelope_domain[1])
        alo, ahi = end.continuation.analytic_interval_pa
        if not lo <= alo-error.retained_error_pa <= ahi+error.retained_error_pa <= hi:
            return finish('source_shared_dry_full_box_pressure_domain_exit')
    na, nb = (end.continuation.inputs[0] for end in endpoints)
    r = a.continuation.inputs[1]
    ta, tb = (end.continuation.temperature_interval_k for end in endpoints)
    numerator = (r*(na*ta[0]-nb*tb[1]), r*(na*ta[1]-nb*tb[0]))
    corners = tuple(n/v for n in numerator for v in shared_volume.volume_interval_m3)
    ideal = (min(corners), max(corners))
    margin = sum((part.retained_error_pa for part in parts), F())
    joint = (ideal[0]-margin, ideal[1]+margin)
    joint_bound = max(map(abs, joint))
    # The legacy independent interval has no separate proof of the new full-box
    # machine-error target. Preserve it for comparison, without taking a min
    # across differently established contracts.
    selected = joint_bound
    return finish(None)
