"""Immutable continuous boundary designs in SI, without material defaults.

Exact rational interpolation of binary64 inputs avoids overflow in time spans
and value differences. Source IDs identify inputs; they do not admit a material.
"""
from bisect import bisect_left
from collections.abc import Mapping
from dataclasses import dataclass, field
from fractions import Fraction
import math
from numbers import Real
from types import MappingProxyType


class BoundaryProgramError(ValueError):
    """Invalid program, unrepresentable value, or evaluation outside its domain."""


# Binary64 representation allowance only; never a composition normalization.
MOLE_FRACTION_SUM_TOLERANCE = 8 * math.ulp(1.0)
_SCALAR_SI_UNITS = frozenset(('1', 'K', 'Pa', 'W', 's', 'm', 'mol/s', 'kg/s',
                              'W/m^2', 'W/m^2/K'))


def _number(value, name):
    try:
        result = float(value) if isinstance(value, Real) and not isinstance(value, bool) else math.nan
    except (ValueError, OverflowError):
        result = math.nan
    if not math.isfinite(result):
        raise BoundaryProgramError(f'invalid_{name}')
    return result


def _sequence(values, name):
    if isinstance(values, (str, bytes, Mapping)):
        raise BoundaryProgramError(f'invalid_{name}')
    try:
        return tuple(values)
    except TypeError as exc:
        raise BoundaryProgramError(f'invalid_{name}') from exc


def _label(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def _knots(values):
    result = tuple(_number(value, 'knot_time') for value in _sequence(values, 'knot_times'))
    if len(result) < 2 or any(right <= left for left, right in zip(result, result[1:])):
        raise BoundaryProgramError('strictly_increasing_knots_required_no_jumps')
    return result


def _column(values, count, name, *, positive=False):
    result = tuple(_number(value, name) for value in _sequence(values, name))
    if len(result) != count or (positive and any(value <= 0 for value in result)):
        raise BoundaryProgramError(f'invalid_{name}')
    return result


def _position(knots, time_s):
    time = _number(time_s, 'evaluation_time')
    if not knots[0] <= time <= knots[-1]:
        raise BoundaryProgramError('time_outside_program_domain')
    index = bisect_left(knots, time)
    if knots[index] == time:
        return time, index, None
    weight = (Fraction(time) - Fraction(knots[index-1])) / (Fraction(knots[index]) - Fraction(knots[index-1]))
    return time, index, weight


def _interpolate(values, index, weight):
    if weight is None:
        return values[index]
    return float((1-weight)*Fraction(values[index-1]) + weight*Fraction(values[index]))


@dataclass(frozen=True, kw_only=True)
class ProgramIdentity:
    program_id: str
    version: str
    classification: str
    source_ids: tuple[str, ...]

    def __post_init__(self):
        if not _label(self.program_id) or not _label(self.version):
            raise BoundaryProgramError('program_identity_required')
        if self.classification not in ('virtual_design_choice', 'measured_public_data', 'derived_from_evidence'):
            raise BoundaryProgramError('invalid_boundary_classification')
        sources = _sequence(self.source_ids, 'source_ids')
        if not sources or any(not _label(value) for value in sources) or len(set(sources)) != len(sources):
            raise BoundaryProgramError('unique_source_ids_required')
        object.__setattr__(self, 'source_ids', sources)


@dataclass(frozen=True, kw_only=True)
class ScalarProgram:
    identity: ProgramIdentity
    knot_times_s: tuple[float, ...]
    values: tuple[float, ...]
    unit: str

    def __post_init__(self):
        if not isinstance(self.identity, ProgramIdentity):
            raise BoundaryProgramError('explicit_program_identity_required')
        if not isinstance(self.unit, str) or self.unit not in _SCALAR_SI_UNITS:
            raise BoundaryProgramError('unsupported_SI_unit')
        knots = _knots(self.knot_times_s)
        object.__setattr__(self, 'knot_times_s', knots)
        object.__setattr__(self, 'values', _column(self.values, len(knots), 'scalar_values'))

    def at(self, time_s: float) -> float:
        _, index, weight = _position(self.knot_times_s, time_s)
        return _interpolate(self.values, index, weight)


@dataclass(frozen=True, kw_only=True)
class BoundaryState:
    """Output record; created by BoundaryProgram.at after validation."""
    identity: ProgramIdentity
    time_s: float
    gas_temperature_k: float
    radiation_temperature_k: float
    total_pressure_pa: float
    mole_fractions: Mapping[str, float]

    def __post_init__(self):
        object.__setattr__(self, 'mole_fractions', MappingProxyType(dict(self.mole_fractions)))


@dataclass(frozen=True, kw_only=True)
class BoundaryProgram:
    identity: ProgramIdentity
    knot_times_s: tuple[float, ...]
    gas_temperature_k: tuple[float, ...]
    radiation_temperature_k: tuple[float, ...]
    total_pressure_pa: tuple[float, ...]
    species_order: tuple[str, ...]
    mole_fractions: tuple[tuple[float, ...], ...]
    provenance_status: str = field(default='input_identity_only_not_material_admission', init=False)

    def __post_init__(self):
        if not isinstance(self.identity, ProgramIdentity):
            raise BoundaryProgramError('explicit_program_identity_required')
        knots = _knots(self.knot_times_s)
        object.__setattr__(self, 'knot_times_s', knots)
        for name in ('gas_temperature_k', 'radiation_temperature_k', 'total_pressure_pa'):
            object.__setattr__(self, name, _column(getattr(self, name), len(knots), name, positive=True))
        species = _sequence(self.species_order, 'species_order')
        if not species or any(not _label(name) for name in species) or len(set(species)) != len(species):
            raise BoundaryProgramError('unique_explicit_species_required')
        object.__setattr__(self, 'species_order', species)
        rows = tuple(_column(row, len(species), 'mole_fractions')
                     for row in _sequence(self.mole_fractions, 'mole_fractions'))
        if len(rows) != len(knots):
            raise BoundaryProgramError('mole_fraction_knot_count_mismatch')
        for row in rows:
            _check_composition(row)
        object.__setattr__(self, 'mole_fractions', rows)

    def at(self, time_s: float) -> BoundaryState:
        time, index, weight = _position(self.knot_times_s, time_s)
        fractions = tuple(_interpolate(tuple(row[k] for row in self.mole_fractions), index, weight)
                          for k in range(len(self.species_order)))
        _check_composition(fractions)
        return BoundaryState(
            identity=self.identity, time_s=time,
            gas_temperature_k=_interpolate(self.gas_temperature_k, index, weight),
            radiation_temperature_k=_interpolate(self.radiation_temperature_k, index, weight),
            total_pressure_pa=_interpolate(self.total_pressure_pa, index, weight),
            mole_fractions=dict(zip(self.species_order, fractions)),
        )

    def breakpoints_s(self, start_s: float, end_s: float) -> tuple[float, ...]:
        """Interior knots for integrate(..., breakpoints_s=...), endpoints excluded."""
        start, _, _ = _position(self.knot_times_s, start_s)
        end, _, _ = _position(self.knot_times_s, end_s)
        if end <= start:
            raise BoundaryProgramError('positive_time_interval_required')
        return tuple(time for time in self.knot_times_s if start < time < end)


def _check_composition(row):
    if any(value < 0 or value > 1 for value in row):
        raise BoundaryProgramError('mole_fraction_outside_unit_interval')
    if abs(math.fsum(row)-1) > MOLE_FRACTION_SUM_TOLERANCE:
        raise BoundaryProgramError('mole_fractions_must_sum_to_one_no_normalization')
