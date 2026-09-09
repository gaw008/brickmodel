"""Explicit rational numerical times; no implicit float conversion or solver admission."""
from dataclasses import dataclass
from fractions import Fraction
import math

SCHEMA = 'exact_event_time_v1'


def _rational(value: object) -> Fraction:
    if type(value) is not Fraction:
        raise ValueError('explicit_fraction_required')
    return value


@dataclass(frozen=True, order=True)
class ExactEventTime:
    """Canonical semantic seconds. Origin decomposition is not identity."""
    seconds: Fraction

    def __post_init__(self) -> None:
        _rational(self.seconds)

    @classmethod
    def from_origin(cls, origin: Fraction, offset: Fraction) -> 'ExactEventTime':
        return cls(_rational(origin) + _rational(offset))

    @classmethod
    def from_float(cls, value: float) -> 'ExactEventTime':
        """Adopt exactly a finite binary64 input, not its decimal spelling."""
        if type(value) is not float or not math.isfinite(value):
            raise ValueError('finite_binary64_required')
        return cls(Fraction(value))

    def shifted(self, duration_s: Fraction) -> 'ExactEventTime':
        return ExactEventTime(self.seconds + _rational(duration_s))

    def elapsed_since(self, other: 'ExactEventTime') -> Fraction:
        if type(other) is not ExactEventTime:
            raise ValueError('exact_event_time_required')
        return self.seconds-other.seconds

    def display(self) -> 'TimeDisplay':
        """A lossy display projection; overflow is explicitly unavailable."""
        try:
            value = float(self.seconds)
        except OverflowError:
            return TimeDisplay(None, None)
        if not math.isfinite(value):
            return TimeDisplay(None, None)
        return TimeDisplay(value, Fraction(value)-self.seconds)

    def to_record(self) -> dict:
        return {'schema': SCHEMA, 'numerator': self.seconds.numerator,
                'denominator': self.seconds.denominator}

    @classmethod
    def from_record(cls, value: object) -> 'ExactEventTime':
        if type(value) is not dict or set(value) != {'schema', 'numerator', 'denominator'}:
            raise ValueError('exact_time_record_fields_required')
        n, d = value['numerator'], value['denominator']
        if value['schema'] != SCHEMA or type(n) is not int or type(d) is not int or d <= 0:
            raise ValueError('canonical_rational_required')
        if math.gcd(n, d) != 1:
            raise ValueError('canonical_rational_required')
        return cls(Fraction(n, d))


@dataclass(frozen=True)
class TimeDisplay:
    seconds_binary64: float | None
    signed_projection_error_s: Fraction | None


@dataclass(frozen=True)
class ExactTimeInterval:
    lower: ExactEventTime
    upper: ExactEventTime

    def __post_init__(self) -> None:
        if type(self.lower) is not ExactEventTime or type(self.upper) is not ExactEventTime:
            raise ValueError('exact_interval_endpoints_required')
        if self.upper < self.lower:
            raise ValueError('ordered_interval_required')

    @property
    def width_s(self) -> Fraction:
        return self.upper.elapsed_since(self.lower)

    def contains(self, time: ExactEventTime) -> bool:
        if type(time) is not ExactEventTime:
            raise ValueError('exact_event_time_required')
        return self.lower <= time <= self.upper

    def to_record(self) -> dict:
        return {'schema': 'exact_event_interval_v1', 'lower': self.lower.to_record(),
                'upper': self.upper.to_record()}

    @classmethod
    def from_record(cls, value: object) -> 'ExactTimeInterval':
        if (type(value) is not dict or set(value) != {'schema', 'lower', 'upper'}
                or value['schema'] != 'exact_event_interval_v1'):
            raise ValueError('exact_interval_record_required')
        return cls(ExactEventTime.from_record(value['lower']), ExactEventTime.from_record(value['upper']))
