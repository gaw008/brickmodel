"""Opt-in exact query/knots for existing validated binary64 boundary programs."""
from bisect import bisect_left
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from collections.abc import Mapping
from sludge_sandbox.boundary_program import BoundaryProgram, ScalarProgram, ProgramIdentity, _check_composition
from sludge_sandbox.exact_event_clock import ExactEventTime


@dataclass(frozen=True)
class ExactBoundaryState:
    identity: ProgramIdentity
    time: ExactEventTime
    gas_temperature_k: float
    radiation_temperature_k: float
    total_pressure_pa: float
    mole_fractions: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'mole_fractions', MappingProxyType(dict(self.mole_fractions)))


@dataclass(frozen=True)
class ExactProgramView:
    """Translate the FULL schedule explicitly; original program remains unchanged."""
    program: BoundaryProgram | ScalarProgram
    schedule_translation_s: Fraction = Fraction(0)

    def __post_init__(self) -> None:
        if type(self.program) not in (BoundaryProgram, ScalarProgram):
            raise ValueError('explicit_validated_program_required')
        if type(self.schedule_translation_s) is not Fraction:
            raise ValueError('exact_schedule_translation_required')

    @property
    def knots(self) -> tuple[ExactEventTime, ...]:
        return tuple(ExactEventTime.from_origin(Fraction(k), self.schedule_translation_s)
                     for k in self.program.knot_times_s)

    def position(self, time: ExactEventTime) -> tuple[int, Fraction | None]:
        if type(time) is not ExactEventTime:
            raise ValueError('exact_event_time_required')
        knots = self.knots
        if not knots[0] <= time <= knots[-1]:
            raise ValueError('time_outside_program_domain')
        index = bisect_left(knots, time)
        if knots[index] == time:
            return index, None
        return index, time.elapsed_since(knots[index-1])/knots[index].elapsed_since(knots[index-1])

    def at(self, time: ExactEventTime) -> ExactBoundaryState | float:
        index, weight = self.position(time)
        def interpolate(values):
            if weight is None:
                return values[index]
            return float((1-weight)*Fraction(values[index-1])+weight*Fraction(values[index]))
        if type(self.program) is ScalarProgram:
            return interpolate(self.program.values)
        p = self.program
        amounts = tuple(interpolate(tuple(row[k] for row in p.mole_fractions))
                        for k in range(len(p.species_order)))
        _check_composition(amounts)
        return ExactBoundaryState(p.identity, time, interpolate(p.gas_temperature_k),
                                  interpolate(p.radiation_temperature_k), interpolate(p.total_pressure_pa),
                                  dict(zip(p.species_order, amounts)))

    def breakpoints(self, start: ExactEventTime, end: ExactEventTime) -> tuple[ExactEventTime, ...]:
        self.position(start)
        self.position(end)
        if end <= start:
            raise ValueError('positive_time_interval_required')
        return tuple(k for k in self.knots if start < k < end)
