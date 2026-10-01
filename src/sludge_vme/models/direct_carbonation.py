"""Conditional portlandite carbonation, callable by the explicit host channel.

The donor/affinity law is an assumed phenomenology. A caller supplies the
macroscopic mobility and its provenance/applicability; no brick A/E or rate
default is inferred from surface speeds, atomistic barriers or endpoint DoC.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

import numpy as np


@dataclass(frozen=True)
class DirectCarbonationMobility:
    """Explicit mobility in 1/s; every provenance/domain field is required."""

    value_per_s: float | np.ndarray
    source: str
    status: Literal["literature", "assumed", "measured"]
    identity: str
    applicability: Mapping[str, object]


def direct_carbonation_sources(
    *,
    temperature_k: float | np.ndarray,
    delta_mu_j_mol: float | np.ndarray,
    portlandite_mol: float | np.ndarray,
    calcite_mol: float | np.ndarray,
    co2_pressure_pa: float | np.ndarray,
    water_vapor_pressure_pa: float | np.ndarray,
    gas_constant_j_mol_k: float,
    reference_pressure_pa: float,
    mobility: DirectCarbonationMobility,
    stoichiometry: Mapping[str, float],
) -> dict[str, object]:
    """Return instantaneous extent/source rates and entropy production.

    Preconditions: stoichiometry is portlandite:-1, CO2:-1, calcite:+1,
    H2O:+1; delta_mu uses this same forward orientation and complete current
    chemical potentials. T/R/Pr are positive; the physical-domain dissipation
    proof requires nonnegative donors/partial pressures and positive mobility.
    Signed donor inputs are retained algebraically outside that proof domain.

    r has mol/s units, species sources are nu*r, and production is W/K.
    This returns a candidate independent extent derivative, not an integrated
    extent or independent trajectory closure. No separate reaction heat is
    added. Host coupling uses the same species U/S/volume ledger.
    The law is continuous but generally not smooth at zero affinity and is
    not a microscopic detailed-balance or measured wet-film kinetic law.
    """
    temperature = np.asarray(temperature_k)
    delta_mu = np.asarray(delta_mu_j_mol)
    affinity = delta_mu / (gas_constant_j_mol_k * temperature)
    forward = affinity.real <= 0
    forward_drive = -np.expm1(np.where(forward, affinity, 0))
    reverse_drive = -np.expm1(np.where(forward, 0, -affinity))
    rate = mobility.value_per_s * (
        portlandite_mol * co2_pressure_pa / reference_pressure_pa * forward_drive
        - calcite_mol * water_vapor_pressure_pa / reference_pressure_pa * reverse_drive
    )
    return {
        "extent_rate_mol_s": rate,
        "species_sources_mol_s": {name: coefficient * rate for name, coefficient in stoichiometry.items()},
        "entropy_production_w_k": -rate * delta_mu / temperature,
        "dimensionless_affinity": affinity,
        "mobility_contract": {
            "value_per_s": mobility.value_per_s,
            "source": mobility.source,
            "status": mobility.status,
            "identity": mobility.identity,
            "applicability": dict(mobility.applicability),
        },
        "rate_law_identity": "assumed_affinity_donor_phenomenology",
    }
