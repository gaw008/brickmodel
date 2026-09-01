from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..chemistry.stoichiometry import initial_element_inventory
from ..types import CaseConfig
from .minimal_backend import MinimalGibbsBackend


SUPPORTED_PURE_PHASE_IDS = {
    "quartz",
    "kaolinite",
    "illite_pseudo",
    "hematite",
    "calcite",
}
SUPPORTED_OXIDES = {"SiO2", "Al2O3", "Fe2O3", "CaO", "MgO", "Na2O", "K2O"}


def assess_thermo_coverage(case: CaseConfig, temperature_K: float, pressure_Pa: float) -> dict[str, Any]:
    """Assess input mapping while explicitly refusing an oxide-liquid equilibrium claim."""
    source_path = Path(__file__).resolve().parents[3] / "data" / "sources.json"
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    candidates: list[dict[str, Any]] = []
    represented_mass = 0.0
    phase_forming_mass = 0.0
    outside_domain_reasons: list[str] = []
    missing_species: set[str] = set()

    for feed in case.raw["feedstocks"].values():
        feed_fraction = float(feed["dry_mass_fraction"])
        for component in feed["components"]:
            component_mass = feed_fraction * float(component["fraction"])
            if component["kind"] == "organic_pseudocomponent":
                continue
            phase_forming_mass += component_mass
            if component["kind"] == "amorphous_oxide_pool":
                oxides = component["oxide_fractions"]
                iron_fraction = float(oxides.get("Fe2O3", 0.0))
                if iron_fraction > 0.80:
                    outside_domain_reasons.append("amorphous Fe2O3 fraction exceeds screening mapping domain 0.80")
                supported_fraction = 0.0
                for oxide, fraction in oxides.items():
                    if oxide in SUPPORTED_OXIDES:
                        supported_fraction += float(fraction)
                    else:
                        missing_species.add(str(oxide))
                # Only mapping coverage is credited; amorphous material receives no
                # equilibrium/liquid-database credit.
                represented_mass += 0.50 * component_mass * supported_fraction
                candidates.append({"id": component["id"], "oxide_fractions": dict(oxides)})
            else:
                candidates.append({"id": component["id"], "formula": dict(component["formula"])})
                if component["id"] in SUPPORTED_PURE_PHASE_IDS:
                    represented_mass += component_mass
                else:
                    missing_species.add(str(component["id"]))

    mapping_coverage = represented_mass / max(phase_forming_mass, 1e-30)
    if outside_domain_reasons:
        mapping_coverage = 0.0
        status = "not_evaluated_outside_composition_domain"
    else:
        status = "not_evaluated_missing_oxide_liquid_database"

    backend = MinimalGibbsBackend(source_hash=source_hash)
    backend_result = backend.equilibrate(
        temperature_K,
        pressure_Pa,
        initial_element_inventory(case),
        candidates,
    )
    return {
        "mapping_coverage_score": float(mapping_coverage),
        "status": status,
        "outside_domain_reasons": outside_domain_reasons,
        "missing_species_or_phases": sorted(missing_species),
        "backend_call": {
            "backend": type(backend).__name__,
            "status": backend_result.status,
            "coverage_score": backend_result.coverage_score,
            "missing_phases": backend_result.missing_phases,
            "source_hash": backend_result.source_hash,
        },
        "hard_pass_allowed": False,
        "validity": "composition mapping only; no multicomponent oxide-liquid Gibbs database",
    }
