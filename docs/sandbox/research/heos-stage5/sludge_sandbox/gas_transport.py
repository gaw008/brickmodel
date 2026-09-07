"""Ideal-gas pore states and one shared, signed gas exchange per current face.

Mixture-averaged diffusion uses the mass frame and mole-fraction gradients.
Coefficients and their material/source eligibility are supplied by the caller.
This module supplies neither energy fluxes nor a time integrator.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from numbers import Real
from types import MappingProxyType


class GasTransportError(ValueError):
    """An input or derived value leaves the supported finite open-gas domain."""


def _number(value, name: str, *, nonnegative=False, positive=False) -> float:
    try:
        valid = isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
        converted = float(value) if valid else math.nan
    except (OverflowError, ValueError):
        converted = math.nan
    if not math.isfinite(converted) or (positive and converted <= 0) or (nonnegative and converted < 0):
        raise GasTransportError(f"{name} requires a finite {'positive' if positive else 'nonnegative' if nonnegative else 'numeric'} value")
    return converted


def _species_values(values, name: str, *, positive=False) -> dict[str, float]:
    if not isinstance(values, Mapping) or not values:
        raise GasTransportError(f"{name} requires a nonempty species mapping")
    result = {}
    for species, value in values.items():
        if not isinstance(species, str) or not species.strip() or species != species.strip():
            raise GasTransportError(f"{name} requires nonempty, trimmed species names")
        result[species] = _number(value, f"{name}[{species}]", nonnegative=True, positive=positive)
    return result


def _same_species(left: Mapping, right: Mapping, name: str) -> None:
    if left.keys() != right.keys():
        raise GasTransportError(f"{name} must explicitly include the same full species set, including carrier gases")


def _sum(values, name: str) -> float:
    try:
        return _number(math.fsum(values), name)
    except (OverflowError, ValueError) as exc:
        raise GasTransportError(f"{name} exceeds finite numeric range") from exc


def _readonly(values: Mapping[str, float]) -> Mapping[str, float]:
    return MappingProxyType(dict(values))


@dataclass(frozen=True)
class GasState:
    """Validated intensive state, built from actual pore gas or an explicit reservoir.

    Concentrations are mol / m3 of current GAS volume, never of bulk volume.
    The constructor copies all mappings so a face sees one consistent snapshot.
    """

    temperature_k: float
    concentrations_mol_m3: Mapping[str, float]
    molar_masses_kg_mol: Mapping[str, float]
    gas_constant_j_mol_k: float
    reservoir_input_mole_fractions: Mapping[str, float] | None = field(default=None, kw_only=True)
    pressure_pa: float = field(init=False)
    density_kg_m3: float = field(init=False)
    mean_molar_mass_kg_mol: float = field(init=False)
    mole_fractions: Mapping[str, float] = field(init=False)
    mass_fractions: Mapping[str, float] = field(init=False)
    reservoir_input_fraction_sum: float | None = field(init=False)
    reservoir_max_abs_fraction_correction: float | None = field(init=False)

    def __post_init__(self):
        temperature = _number(self.temperature_k, "temperature_k", positive=True)
        gas_constant = _number(self.gas_constant_j_mol_k, "gas_constant_j_mol_k", positive=True)
        concentrations = _species_values(self.concentrations_mol_m3, "concentrations_mol_m3")
        masses = _species_values(self.molar_masses_kg_mol, "molar_masses_kg_mol", positive=True)
        _same_species(concentrations, masses, "molar masses")
        total = _number(_sum(concentrations.values(), "total concentration"), "total concentration", positive=True)
        mole_fractions = {k: c / total for k, c in concentrations.items()}
        mean_mass = _number(_sum((mole_fractions[k] * masses[k] for k in masses), "mean molar mass"), "mean molar mass", positive=True)
        density = _number(total * mean_mass, "gas density", positive=True)
        pressure = _number(total * gas_constant * temperature, "gas pressure", positive=True)
        mass_fractions = {k: mole_fractions[k] * masses[k] / mean_mass for k in masses}
        reservoir_input = self.reservoir_input_mole_fractions
        input_sum = None
        maximum_correction = None
        if reservoir_input is not None:
            reservoir_input = _species_values(reservoir_input, "reservoir_input_mole_fractions")
            _same_species(masses, reservoir_input, "Reservoir input fractions")
            input_sum = _sum(reservoir_input.values(), "reservoir input fraction sum")
            if not math.isclose(input_sum, 1.0, rel_tol=1e-12, abs_tol=0):
                raise GasTransportError("Reservoir input mole fractions must sum to one")
            if any(not math.isclose(mole_fractions[k], reservoir_input[k] / input_sum,
                                    rel_tol=1e-12, abs_tol=1e-15) for k in masses):
                raise GasTransportError("Reservoir input snapshot is inconsistent with the gas state")
            maximum_correction = max(abs(mole_fractions[k] - reservoir_input[k]) for k in masses)
            reservoir_input = _readonly(reservoir_input)
        for name, value in {
            "temperature_k": temperature,
            "gas_constant_j_mol_k": gas_constant,
            "concentrations_mol_m3": _readonly(concentrations),
            "molar_masses_kg_mol": _readonly(masses),
            "mole_fractions": _readonly(mole_fractions),
            "mass_fractions": _readonly(mass_fractions),
            "mean_molar_mass_kg_mol": mean_mass,
            "density_kg_m3": density,
            "pressure_pa": pressure,
            "reservoir_input_mole_fractions": reservoir_input,
            "reservoir_input_fraction_sum": input_sum,
            "reservoir_max_abs_fraction_correction": maximum_correction,
        }.items():
            object.__setattr__(self, name, value)


def ideal_gas_state(inventories_mol: Mapping[str, float], *, temperature_k: float,
                    gas_volume_m3: float, molar_masses_kg_mol: Mapping[str, float],
                    gas_constant_j_mol_k: float) -> GasState:
    """Compute pressure/composition from all actual gas inventories and current Vgas.

    Negative inventory and nonpositive Vgas raise; there is no vacuum composition,
    injected carrier, clipping, or inferred fraction of open pores.
    """
    inventory = _species_values(inventories_mol, "inventories_mol")
    volume = _number(gas_volume_m3, "gas_volume_m3", positive=True)
    concentrations = {k: n / volume for k, n in inventory.items()}
    return GasState(temperature_k, concentrations, molar_masses_kg_mol, gas_constant_j_mol_k)


def ideal_gas_reservoir(*, pressure_pa: float, temperature_k: float,
                        mole_fractions: Mapping[str, float],
                        molar_masses_kg_mol: Mapping[str, float],
                        gas_constant_j_mol_k: float) -> GasState:
    """Explicit prescribed reservoir; a finite reservoir instead uses ideal_gas_state.

    Fractions must sum to one within 1e-12 relative floating-point tolerance.
    Only that roundoff-sized discrepancy is normalized, explicitly, at construction.
    """
    pressure = _number(pressure_pa, "pressure_pa", positive=True)
    temperature = _number(temperature_k, "temperature_k", positive=True)
    gas_constant = _number(gas_constant_j_mol_k, "gas_constant_j_mol_k", positive=True)
    fractions = _species_values(mole_fractions, "mole_fractions")
    total_fraction = _sum(fractions.values(), "sum of mole fractions")
    if not math.isclose(total_fraction, 1.0, rel_tol=1e-12, abs_tol=0):
        raise GasTransportError("Reservoir mole fractions must sum to one")
    rt = _number(gas_constant * temperature, "R*T", positive=True)
    concentration = _number(pressure / rt, "reservoir concentration", positive=True)
    concentrations = {k: concentration * (x / total_fraction) for k, x in fractions.items()}
    return GasState(temperature, concentrations, molar_masses_kg_mol, gas_constant,
                    reservoir_input_mole_fractions=fractions)


@dataclass(frozen=True)
class GasFaceExchange:
    """Rates are mol/s across the entire face; positive means left to right.

    Apply -net to the left inventory and +net to the right exactly once. The caller
    obtains species enthalpies at face_temperature_k for diffusion and at the
    advective donor temperature for advection from the same thermochemical model.
    """

    net_mol_s: Mapping[str, float]
    diffusive_mol_s: Mapping[str, float]
    advective_mol_s: Mapping[str, float]
    darcy_velocity_m_s: float
    advective_donor: str | None
    advective_donor_temperature_k: float | None
    face_temperature_k: float
    face_density_kg_m3: float
    face_input_fraction_sum: float
    face_max_abs_fraction_correction: float
    gas_constant_j_mol_k: float
    diffusion_correction_velocity_m_s: float
    diffusion_correction_donor: str | None

    @property
    def net_direction(self) -> Mapping[str, str]:
        return MappingProxyType({k: "left_to_right" if v > 0 else "right_to_left" if v < 0 else "stationary"
                                 for k, v in self.net_mol_s.items()})


def face_exchange(left: GasState, right: GasState, *, area_m2: float, distance_m: float,
                  face_left_weight: float, effective_diffusivities_m2_s: Mapping[str, float],
                  permeability_m2: float, relative_permeability: float,
                  viscosity_pa_s: float) -> GasFaceExchange:
    """Mixture-averaged mass-frame diffusion plus no-gravity Darcy on one face.

    D_eff uses mole-fraction gradients and TOTAL face area. K is absolute normal
    permeability; kr is the explicit gas relative permeability. The caller must
    assemble coefficients for half-cell resistances and current geometry.
    face_left_weight=d_right/(d_left+d_right) sets linear face p, T, and X.
    Advective mass fractions use the Darcy donor; density uses the face EOS.
    The diffusion correction is itself discretized upwind by its drift velocity.
    This first-order choice preserves an inward derivative at zero inventory.
    """
    if not isinstance(left, GasState) or not isinstance(right, GasState):
        raise GasTransportError("Both sides must be validated GasState instances")
    _same_species(left.mole_fractions, right.mole_fractions, "Both gas states")
    if left.molar_masses_kg_mol != right.molar_masses_kg_mol:
        raise GasTransportError("Both sides must use identical species molar masses")
    if left.gas_constant_j_mol_k != right.gas_constant_j_mol_k:
        raise GasTransportError("Both sides must use the same gas constant")
    area = _number(area_m2, "area_m2", positive=True)
    distance = _number(distance_m, "distance_m", positive=True)
    weight = _number(face_left_weight, "face_left_weight", nonnegative=True)
    relative = _number(relative_permeability, "relative_permeability", nonnegative=True)
    if weight > 1 or relative > 1:
        raise GasTransportError("face_left_weight and relative_permeability must be at most one")
    permeability = _number(permeability_m2, "permeability_m2", nonnegative=True)
    viscosity = _number(viscosity_pa_s, "viscosity_pa_s", positive=True)
    diffusion = _species_values(effective_diffusivities_m2_s, "effective_diffusivities_m2_s")
    _same_species(left.mole_fractions, diffusion, "Diffusion coefficients")
    masses = left.molar_masses_kg_mol

    def interpolate(a, b):
        return weight * a + (1 - weight) * b

    face_x = {k: interpolate(left.mole_fractions[k], right.mole_fractions[k]) for k in masses}
    face = ideal_gas_reservoir(
        pressure_pa=interpolate(left.pressure_pa, right.pressure_pa),
        temperature_k=interpolate(left.temperature_k, right.temperature_k),
        mole_fractions=face_x, molar_masses_kg_mol=masses,
        gas_constant_j_mol_k=left.gas_constant_j_mol_k,
    )
    velocity = _number(-(permeability * relative / viscosity) * ((right.pressure_pa - left.pressure_pa) / distance), "Darcy velocity")
    donor = left if velocity > 0 else right if velocity < 0 else None
    star = {k: _number(-face.density_kg_m3 * (masses[k] / face.mean_molar_mass_kg_mol)
                       * diffusion[k] * ((right.mole_fractions[k] - left.mole_fractions[k]) / distance),
                       f"uncorrected diffusive mass flux[{k}]") for k in masses}
    total_star = _sum(star.values(), "uncorrected total diffusive mass flux")
    correction_velocity = _number(-total_star / face.density_kg_m3, "diffusion correction velocity")
    correction_donor = left if total_star < 0 else right if total_star > 0 else None
    # A centered Y can extract a species whose inventory is zero. Treat the
    # correction drift as one shared upwind mass flux, retaining sum(j_diff)=0.
    correction = {k: -total_star * correction_donor.mass_fractions[k]
                  if correction_donor is not None else 0.0 for k in masses}
    diffusive = {k: _number(area * (star[k] + correction[k]) / masses[k],
                            f"diffusive molar rate[{k}]") for k in masses}
    advective = {k: _number(area * face.density_kg_m3 * donor.mass_fractions[k] * velocity / masses[k],
                            f"advective molar rate[{k}]") if donor is not None else 0.0 for k in masses}
    net = {k: _sum((diffusive[k], advective[k]), f"net molar rate[{k}]") for k in masses}
    return GasFaceExchange(
        _readonly(net), _readonly(diffusive), _readonly(advective), velocity,
        "left" if velocity > 0 else "right" if velocity < 0 else None,
        donor.temperature_k if donor is not None else None,
        face.temperature_k, face.density_kg_m3,
        face.reservoir_input_fraction_sum, face.reservoir_max_abs_fraction_correction,
        left.gas_constant_j_mol_k,
        correction_velocity,
        "left" if total_star < 0 else "right" if total_star > 0 else None,
    )
