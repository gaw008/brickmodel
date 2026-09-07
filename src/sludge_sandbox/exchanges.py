"""One face's heat and species enthalpy rates for conservative assembly.

Interior rates are positive left-to-right; boundary heat is positive into the
body. These functions do not supply material coefficients or integrate energy.
"""

from dataclasses import dataclass
import math
from numbers import Real
from typing import Iterable

from .gas_transport import GasFaceExchange
from .thermochemistry import Thermochemistry


class ExchangeError(ValueError):
    """An exchange input, thermodynamic convention, or computed rate is invalid."""


def _number(value: object, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    try:
        valid = isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
        result = float(value) if valid else math.nan
    except (OverflowError, ValueError):
        result = math.nan
    if (not math.isfinite(result) or (positive and result <= 0)
            or (nonnegative and result < 0)):
        raise ExchangeError(f"Invalid finite value for {name}")
    return result


def _sum(values: Iterable[float]) -> float:
    try:
        return _number(math.fsum(values), "energy rate")
    except (OverflowError, ValueError) as exc:
        raise ExchangeError("Energy rate exceeds finite range") from exc


def conduction_rate_w(left_temperature_k: float, right_temperature_k: float, *, area_m2: float,
                      left_distance_m: float, right_distance_m: float,
                      left_conductivity_w_m_k: float, right_conductivity_w_m_k: float) -> float:
    """Fourier rate with each half-cell resistance; zero k explicitly insulates."""
    left = _number(left_temperature_k, "left T", positive=True)
    right = _number(right_temperature_k, "right T", positive=True)
    area = _number(area_m2, "area", positive=True)
    dl = _number(left_distance_m, "left distance", positive=True)
    dr = _number(right_distance_m, "right distance", positive=True)
    kl = _number(left_conductivity_w_m_k, "left k", nonnegative=True)
    kr = _number(right_conductivity_w_m_k, "right k", nonnegative=True)
    if kl == 0 or kr == 0:
        return 0.0
    resistance = _number(dl / kl + dr / kr, "thermal resistance per area", positive=True)
    return _number(area * ((left - right) / resistance), "conduction rate")


@dataclass(frozen=True)
class BoundaryHeat:
    convective_in_w: float
    radiative_in_w: float

    @property
    def total_in_w(self) -> float:
        return _sum((self.convective_in_w, self.radiative_in_w))


def boundary_heat(*, surface_temperature_k: float, gas_temperature_k: float,
                  radiation_temperature_k: float, area_m2: float, convection_w_m2_k: float,
                  emissivity: float, stefan_boltzmann_w_m2_k4: float) -> BoundaryHeat:
    """Gray surface facing a prescribed blackbody radiative environment, view factor 1.

    Radiation_temperature is an effective radiative ambient, not automatically the
    physical wall temperature of a finite-gray enclosure or participating gas.
    """
    surface = _number(surface_temperature_k, "surface T", positive=True)
    gas = _number(gas_temperature_k, "gas T", positive=True)
    radiative = _number(radiation_temperature_k, "radiative ambient T", positive=True)
    area = _number(area_m2, "area", positive=True)
    h = _number(convection_w_m2_k, "convection coefficient", nonnegative=True)
    epsilon = _number(emissivity, "emissivity", nonnegative=True)
    sigma = _number(stefan_boltzmann_w_m2_k4, "Stefan-Boltzmann constant", positive=True)
    if epsilon > 1:
        raise ExchangeError("Emissivity must be at most one")
    convection = _number(area * h * (gas - surface), "convective rate")
    try:
        radiation = (area * epsilon * sigma * (radiative - surface) * (radiative + surface)
                     * (radiative**2 + surface**2)) if epsilon and radiative != surface else 0.0
    except OverflowError as exc:
        raise ExchangeError("Radiative rate exceeds finite range") from exc
    return BoundaryHeat(convection, _number(radiation, "radiative rate"))


@dataclass(frozen=True)
class GasEnthalpyExchange:
    diffusive_w: float
    advective_w: float
    thermochemistry_source_ids: tuple[str, ...]
    provenance_status: str

    @property
    def total_w(self) -> float:
        return _sum((self.diffusive_w, self.advective_w))


def gas_enthalpy_exchange(exchange: GasFaceExchange, thermo: Thermochemistry) -> GasEnthalpyExchange:
    """Attach enthalpy to the actual diffusion and advection, not a second heat source.

    Diffusion uses common face temperature; advection uses donor temperature.
    The same signed result is subtracted/added on the two cells by the assembler.
    """
    if not isinstance(exchange, GasFaceExchange) or not isinstance(thermo, Thermochemistry):
        raise ExchangeError("Validated gas exchange and thermochemistry are required")
    if exchange.gas_constant_j_mol_k != thermo.gas_constant_j_mol_k:
        raise ExchangeError("EOS and thermochemistry must use the same gas constant")
    if (exchange.diffusive_mol_s.keys() != exchange.advective_mol_s.keys()
            or exchange.diffusive_mol_s.keys() != exchange.net_mol_s.keys()):
        raise ExchangeError("Species sets differ across exchange components")
    diffuse, advect, sources = [], [], set(thermo.constant_source_ids)
    for name in exchange.diffusive_mol_s:
        gas = thermo.species(name)
        d = _number(exchange.diffusive_mol_s[name], "diffusive species rate")
        a = _number(exchange.advective_mol_s[name], "advective species rate")
        net = _number(exchange.net_mol_s[name], "net species rate")
        if net != _sum((d, a)):
            raise ExchangeError("Inconsistent net species flow and energy-bearing components")
        if d != 0:
            segment = gas.segment_for(exchange.face_temperature_k)
            diffuse.append(_number(d * segment.enthalpy_j_mol(exchange.face_temperature_k),
                                   "diffusive species enthalpy rate"))
            sources.update((*gas.source_ids, *segment.source_ids))
        if a != 0:
            if exchange.advective_donor_temperature_k is None:
                raise ExchangeError("Nonzero advection requires a donor temperature")
            segment = gas.segment_for(exchange.advective_donor_temperature_k)
            advect.append(_number(a * segment.enthalpy_j_mol(exchange.advective_donor_temperature_k),
                                  "advective species enthalpy rate"))
            sources.update((*gas.source_ids, *segment.source_ids))
    return GasEnthalpyExchange(_sum(diffuse), _sum(advect), tuple(sorted(sources)),
                              thermo.provenance_status)
