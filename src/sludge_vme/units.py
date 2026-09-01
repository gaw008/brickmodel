from __future__ import annotations

ABSOLUTE_ZERO_C = -273.15


def degc_to_k(value_deg_c: float) -> float:
    value = float(value_deg_c)
    if value < ABSOLUTE_ZERO_C:
        raise ValueError("temperature is below absolute zero")
    return value + 273.15


def dry_mass_from_wet(wet_mass_kg: float, moisture_wet_basis: float) -> float:
    mass = float(wet_mass_kg)
    moisture = float(moisture_wet_basis)
    if mass < 0:
        raise ValueError("wet mass must be nonnegative")
    if not 0.0 <= moisture < 1.0:
        raise ValueError("wet-basis moisture must be in [0, 1)")
    return mass * (1.0 - moisture)


def water_per_dry_mass(moisture_wet_basis: float) -> float:
    moisture = float(moisture_wet_basis)
    if not 0.0 <= moisture < 1.0:
        raise ValueError("wet-basis moisture must be in [0, 1)")
    return moisture / (1.0 - moisture)
