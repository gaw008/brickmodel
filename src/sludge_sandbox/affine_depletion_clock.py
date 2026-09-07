"""Exact arithmetic certificate for a sampled affine liquid-depletion clock."""
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Real
import struct
from collections.abc import Sequence


class AffineDepletionClockError(ValueError):
    """An affine crossing cannot satisfy the declared clock certificate."""


def _number(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise AffineDepletionClockError('invalid_'+name)
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise AffineDepletionClockError('invalid_'+name) from exc
    if not math.isfinite(result) or (result == 0 and value != 0):
        raise AffineDepletionClockError('invalid_'+name)
    return result


def _rates(values: Sequence[float]) -> tuple[float, ...]:
    try:
        result = tuple(_number(value, 'rate') for value in values)
    except TypeError as exc:
        raise AffineDepletionClockError('invalid_rates') from exc
    if not result:
        raise AffineDepletionClockError('empty_rates')
    return result


def _ordered(value: float) -> int:
    bits = struct.unpack('>Q', struct.pack('>d', value))[0]
    return (~bits & ((1 << 64)-1)) if bits >> 63 else bits | (1 << 63)


def _from_ordered(value: int) -> float:
    bits = value & ((1 << 63)-1) if value >> 63 else ~value & ((1 << 64)-1)
    return struct.unpack('>d', struct.pack('>Q', bits))[0]


@dataclass(frozen=True)
class AffineDepletionClockEvidence:
    start_s: float
    end_s: float
    liquid_rates_start_mol_s: tuple[float, ...]
    liquid_rates_mid_mol_s: tuple[float, ...]
    midpoint_s: float
    time_absolute_s: float
    start_inventory_mol: float

    def __post_init__(self) -> None:
        for name in ('start_s', 'end_s', 'midpoint_s', 'time_absolute_s', 'start_inventory_mol'):
            object.__setattr__(self, name, _number(getattr(self, name), name))
        if not self.start_s < self.midpoint_s < self.end_s or self.time_absolute_s <= 0:
            raise AffineDepletionClockError('invalid_clock_interval')
        for name in ('liquid_rates_start_mol_s', 'liquid_rates_mid_mol_s'):
            object.__setattr__(self, name, _rates(getattr(self, name)))
        if self.start_inventory_mol <= 0:
            raise AffineDepletionClockError('positive_start_inventory_required')
        if len(self.liquid_rates_start_mol_s) != len(self.liquid_rates_mid_mol_s):
            raise AffineDepletionClockError('rate_shape_mismatch')

    @property
    def event_time_rounding_s(self) -> Fraction:
        """Validate the immutable certificate and return an upper root-end gap."""
        h = Fraction(self.end_s)-Fraction(self.start_s)
        try:
            terms = tuple(float(h*a+h*h*b) for a, b in self._coefficients())
        except OverflowError as exc:
            raise AffineDepletionClockError('clock_panel_term_overflow') from exc
        residual = self.inventory_residual(self.start_inventory_mol, terms)
        if residual == 0:
            return Fraction()
        neighbor = math.nextafter(self.end_s, math.inf)
        budget = Fraction(self.time_absolute_s)
        return min(budget, Fraction(neighbor)-Fraction(self.end_s)) if math.isfinite(neighbor) else budget

    def _coefficients(self) -> tuple[tuple[Fraction, Fraction], ...]:
        hm = Fraction(self.midpoint_s)-Fraction(self.start_s)
        return tuple((Fraction(r0), (Fraction(rm)-Fraction(r0))/(2*hm))
                     for r0, rm in zip(self.liquid_rates_start_mol_s, self.liquid_rates_mid_mol_s))

    def inventory_residual(self, start_mol: float, terms: Sequence[float]) -> Fraction:
        amount = _number(start_mol, 'start_mol')
        if amount <= 0:
            raise AffineDepletionClockError('positive_start_inventory_required')
        if amount != self.start_inventory_mol:
            raise AffineDepletionClockError('clock_start_inventory_mismatch')
        coefficients = self._coefficients()
        checked_terms = tuple(_number(term, 'panel_term') for term in terms)
        if len(checked_terms) != len(coefficients):
            raise AffineDepletionClockError('clock_panel_term_mismatch')
        interval = Fraction(self.end_s)-Fraction(self.start_s)
        integrals = tuple(interval*a+interval*interval*b for a, b in coefficients)
        try:
            matches = all(float(value) == term for value, term in zip(integrals, checked_terms))
        except OverflowError as exc:
            raise AffineDepletionClockError('clock_panel_term_overflow') from exc
        if not matches:
            raise AffineDepletionClockError('clock_panel_term_mismatch')
        a = sum((item[0] for item in coefficients), Fraction())
        b = sum((item[1] for item in coefficients), Fraction())
        def polynomial(h: Fraction) -> Fraction:
            return Fraction(amount)+h*a+h*h*b
        residual = polynomial(interval)
        if a >= 0 or a+2*b*interval >= 0:
            raise AffineDepletionClockError('clock_nonmonotone_crossing')
        if residual < 0:
            raise AffineDepletionClockError('clock_endpoint_above_root')
        if residual == 0:
            return residual
        neighbor = math.nextafter(self.end_s, math.inf)
        if not math.isfinite(neighbor):
            raise AffineDepletionClockError('clock_unresolved_root')
        upper = Fraction(neighbor)-Fraction(self.start_s)
        if a+2*b*upper >= 0:
            raise AffineDepletionClockError('clock_nonmonotone_crossing')
        if polynomial(upper) >= 0:
            raise AffineDepletionClockError('clock_endpoint_not_nearest_downward_root')
        bound = min(Fraction(self.time_absolute_s), upper-interval)
        if polynomial(interval+bound) > 0:
            raise AffineDepletionClockError('clock_time_budget')
        return residual


def locate_affine_depletion_clock(start_s: float, midpoint_s: float, start_mol: float,
                                  start_rates: Sequence[float], mid_rates: Sequence[float],
                                  maximum_end_s: float, time_absolute_s: float) -> AffineDepletionClockEvidence:
    """Locate a unique decreasing crossing with at most 64 float-bit bisections."""
    template = AffineDepletionClockEvidence(start_s, maximum_end_s, tuple(start_rates), tuple(mid_rates), midpoint_s, time_absolute_s, start_mol)
    amount = _number(start_mol, 'start_mol')
    if amount <= 0:
        raise AffineDepletionClockError('positive_start_inventory_required')
    coefficients = template._coefficients()
    a = sum((item[0] for item in coefficients), Fraction())
    b = sum((item[1] for item in coefficients), Fraction())
    origin = Fraction(template.start_s)
    maximum_h = Fraction(template.end_s)-origin
    def polynomial(endpoint: float) -> Fraction:
        h = Fraction(endpoint)-origin
        return Fraction(amount)+a*h+b*h*h
    if a >= 0 or a+2*b*maximum_h >= 0:
        raise AffineDepletionClockError('clock_nonmonotone_crossing')
    if polynomial(template.end_s) > 0:
        raise AffineDepletionClockError('clock_no_root_in_enclosure')
    lo, hi = _ordered(template.start_s), _ordered(template.end_s)
    for _ in range(64):
        if lo == hi:
            break
        middle = (lo+hi+1)//2
        if polynomial(_from_ordered(middle)) >= 0:
            lo = middle
        else:
            hi = middle-1
    if lo != hi:
        raise AffineDepletionClockError('clock_search_exhausted')
    endpoint = _from_ordered(lo)
    evidence = AffineDepletionClockEvidence(template.start_s, endpoint,
        template.liquid_rates_start_mol_s, template.liquid_rates_mid_mol_s,
        template.midpoint_s, template.time_absolute_s, amount)
    h = Fraction(endpoint)-origin
    try:
        terms = tuple(float(h*x+h*h*y) for x, y in coefficients)
    except OverflowError as exc:
        raise AffineDepletionClockError('clock_panel_term_overflow') from exc
    evidence.inventory_residual(amount, terms)
    return evidence
