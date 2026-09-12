"""Explicit SI conversions; changing material or inventory basis is not a unit conversion."""

from dataclasses import dataclass
import math


class UnitError(ValueError):
    """An unknown, incompatible, or nonnumeric unit conversion was requested."""


@dataclass(frozen=True)
class Unit:
    # Mass, length, time, temperature, amount of substance.
    dimensions: tuple[int, int, int, int, int]
    scale: float = 1.0
    offset: float = 0.0


UNITS = {
    "1": Unit((0, 0, 0, 0, 0)), "wt%": Unit((0, 0, 0, 0, 0), 0.01),
    "K": Unit((0, 0, 0, 1, 0)), "degC": Unit((0, 0, 0, 1, 0), 1.0, 273.15),
    "kg": Unit((1, 0, 0, 0, 0)), "g": Unit((1, 0, 0, 0, 0), 1e-3),
    "mol": Unit((0, 0, 0, 0, 1)), "kmol": Unit((0, 0, 0, 0, 1), 1e3),
    "m": Unit((0, 1, 0, 0, 0)), "mm": Unit((0, 1, 0, 0, 0), 1e-3),
    "um": Unit((0, 1, 0, 0, 0), 1e-6), "m2": Unit((0, 2, 0, 0, 0)),
    "m3": Unit((0, 3, 0, 0, 0)), "s": Unit((0, 0, 1, 0, 0)),
    "min": Unit((0, 0, 1, 0, 0), 60), "h": Unit((0, 0, 1, 0, 0), 3600),
    "1/s": Unit((0, 0, -1, 0, 0)), "1/min": Unit((0, 0, -1, 0, 0), 1 / 60),
    "Pa": Unit((1, -1, -2, 0, 0)), "kPa": Unit((1, -1, -2, 0, 0), 1e3),
    "MPa": Unit((1, -1, -2, 0, 0), 1e6), "bar": Unit((1, -1, -2, 0, 0), 1e5),
    "Pa*s": Unit((1, -1, -1, 0, 0)), "kg/m3": Unit((1, -3, 0, 0, 0)),
    "mol/m3": Unit((0, -3, 0, 0, 1)), "kg/mol": Unit((1, 0, 0, 0, -1)),
    "J": Unit((1, 2, -2, 0, 0)), "J/kg": Unit((0, 2, -2, 0, 0)),
    "MJ/kg": Unit((0, 2, -2, 0, 0), 1e6),
    "J/mol": Unit((1, 2, -2, 0, -1)), "kJ/mol": Unit((1, 2, -2, 0, -1), 1e3),
    "J/(kg*K)": Unit((0, 2, -2, -1, 0)), "J/(mol*K)": Unit((1, 2, -2, -1, -1)),
    "J/m3": Unit((1, -1, -2, 0, 0)), "W": Unit((1, 2, -3, 0, 0)),
    "W/m2": Unit((1, 0, -3, 0, 0)), "W/m3": Unit((1, -1, -3, 0, 0)),
    "W/(m*K)": Unit((1, 1, -3, -1, 0)), "W/(m2*K)": Unit((1, 0, -3, -1, 0)),
    "W/(m2*K4)": Unit((1, 0, -3, -4, 0)),
    "m/s": Unit((0, 1, -1, 0, 0)), "m2/s": Unit((0, 2, -1, 0, 0)),
    "mol/(m2*s)": Unit((0, -2, -1, 0, 1)), "mol/(m3*s)": Unit((0, -3, -1, 0, 1)),
    "1/K": Unit((0, 0, 0, -1, 0)), "K/s": Unit((0, 0, -1, 1, 0)),
    "K/min": Unit((0, 0, -1, 1, 0), 1 / 60),
}


def require_unit(name: str) -> Unit:
    if not isinstance(name, str) or name not in UNITS:
        raise UnitError(f"Unregistered unit: {name!r}")
    return UNITS[name]


def convert(value: float, source: str, target: str) -> float:
    """Convert a finite scalar, without coercing strings/bools or inferring a basis."""
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise UnitError("Conversion requires a finite numeric scalar")
    left, right = require_unit(source), require_unit(target)
    if left.dimensions != right.dimensions:
        raise UnitError(f"Incompatible units: {source} and {target}; explicit derivation required")
    result = (value * left.scale + left.offset - right.offset) / right.scale
    if not math.isfinite(result):
        raise UnitError("Conversion overflow")
    return result
