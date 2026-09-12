"""USGS nominal pure-phase reaction enthalpy, without a kinetic or volume law.

All three species use the same 1995 compilation. The source Cp polynomial is
analytically integrated from 298.15 K; high-temperature formation columns use
a different element reference and must not replace that integral.
"""
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


FACTS_SHA256 = "b06ef79b8651c23661706a4ac7abd615d144f4758d88e732ebb107b29d844946"
SOURCE_SHA256 = "400e02f441084d2ea977588d03a265c98a8907aae46d697af85e2ea6ba6587a4"
METHOD_ID = "usgs1995_calcite_reaction_analytic_cp_integral_v1"
_CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN)
_STOICHIOMETRY = {"calcite": -1, "lime": 1, "carbon_dioxide": 1}
_ELEMENTS = {
    "calcite": {"Ca": 1, "C": 1, "O": 3},
    "lime": {"Ca": 1, "O": 1},
    "carbon_dioxide": {"C": 1, "O": 2},
}


class MineralThermochemistryError(ValueError):
    """Invalid input, altered source extraction, or temperature outside its domain."""


def _number(value: object, name: str) -> Decimal:
    if type(value) not in (str, int, float, Decimal):
        raise MineralThermochemistryError(f"finite_decimal_{name}_required")
    text = str(value)
    if len(text) > 128:
        raise MineralThermochemistryError(f"{name}_representation_too_large")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise MineralThermochemistryError(f"finite_decimal_{name}_required") from exc
    if (not number.is_finite() or len(number.as_tuple().digits) > 50
            or abs(number.as_tuple().exponent) > 1000):
        raise MineralThermochemistryError(f"finite_bounded_decimal_{name}_required")
    return number


def _read(path: Path, expected: str) -> dict[str, Any]:
    # Nonblocking open plus descriptor validation also handles a symlink or
    # path replacement with a FIFO without hanging before the size limit.
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise MineralThermochemistryError(f"regular_{path.name}_required")
        raw = stream.read(131073)
    if len(raw) > 131072 or hashlib.sha256(raw).hexdigest() != expected:
        raise MineralThermochemistryError(f"reviewed_{path.name}_changed")
    return json.loads(raw)


def _phase(species: dict[str, Any], temperature: Decimal, reference: Decimal) -> dict[str, Any]:
    a, b, c, d, e = (Decimal(species["cp"]["coefficients_nominal"][f"A{i}"])
                     for i in range(1, 6))
    t, r = temperature, reference
    cp = a + b*t + c/t**2 + d/t.sqrt() + e*t**2
    sensible = (a*(t-r) + b*(t**2-r**2)/2 + c*(1/r-1/t)
                + 2*d*(t.sqrt()-r.sqrt()) + e*(t**3-r**3)/3)
    h0 = Decimal(species["reference_298"]["hf_kj_mol"])*1000
    if cp <= 0:
        raise MineralThermochemistryError("nonpositive_source_heat_capacity")
    return {
        "formula": species["formula"],
        "phase": species["phase_description_printed"],
        "cp_j_mol_k": str(cp),
        "formation_enthalpy_298_j_mol": str(h0),
        "sensible_enthalpy_j_mol": str(sensible),
        "standard_enthalpy_coordinate_j_mol": str(h0+sensible),
        "molar_mass_g_mol": species["molar_mass_g_mol"],
        "reference_298_printed": species["reference_298"],
        "cp_coefficients_printed": species["cp"]["coefficients_printed"],
        "cp_coefficients_nominal": species["cp"]["coefficients_nominal"],
        "blank_coefficient_interpretation": species["cp"]["blank_cells_interpretation"],
    }


def _trace(facts: dict[str, Any]) -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for species in facts["species"]:
        prefix = f"species.{species['id']}"
        locators = {"reference_298": species["reference_298"]["locator"],
                    "cp_coefficients": species["cp"]["coefficient_locator"],
                    "cp_equation": facts["cp_equation"]["locator"]}
        for suffix, formula, dependencies in (
            ("formation_enthalpy_298_j_mol", "1000*hf_298_kJ_per_mol", [f"{prefix}.reference_298_printed.hf_kj_mol"]),
            ("cp_j_mol_k", facts["cp_equation"]["printed"], [f"{prefix}.cp_coefficients_nominal", "temperature_k"]),
            ("sensible_enthalpy_j_mol", facts["cp_equation"]["derived_sensible_enthalpy_formula"],
             [f"{prefix}.cp_coefficients_nominal", "reference_temperature_k", "temperature_k"]),
            ("standard_enthalpy_coordinate_j_mol", "hf(298.15 K)+integral(Cp,Tref,T)",
             [f"{prefix}.formation_enthalpy_298_j_mol", f"{prefix}.sensible_enthalpy_j_mol"]),
        ):
            paths[f"{prefix}.{suffix}"] = {
                "formula": formula, "dependencies": dependencies, "source_id": facts["source_id"],
                "source_species_id": species["id"], "source_locators": locators,
            }
    for suffix, formula, dependencies in (
        ("enthalpy_j_mol_extent", "sum(nu_i*h_i(T))",
         [f"species.{name}.standard_enthalpy_coordinate_j_mol" for name in _STOICHIOMETRY]),
        ("heat_capacity_change_j_mol_extent_k", "sum(nu_i*Cp_i(T))",
         [f"species.{name}.cp_j_mol_k" for name in _STOICHIOMETRY]),
        ("enthalpy_for_extent_j", "extent_mol*reaction.enthalpy_j_mol_extent",
         ["extent_mol", "reaction.enthalpy_j_mol_extent"]),
        ("mass_changes_kg", "nu_i*extent_mol*M_i_g_per_mol/1000",
         ["extent_mol", "reaction.stoichiometry_mol_per_mol_extent",
          *[f"species.{name}.molar_mass_g_mol" for name in _STOICHIOMETRY]]),
        ("element_changes_mol", "sum(nu_i*extent_mol*element_atoms_i)",
         ["extent_mol", "reaction.stoichiometry_mol_per_mol_extent",
          *[f"species.{name}.formula" for name in _STOICHIOMETRY]]),
    ):
        paths[f"reaction.{suffix}"] = {"formula": formula, "dependencies": dependencies}
    return paths


def calculate_calcite_thermochemistry(
    source_directory: str | Path, *, temperature_k: object, extent_mol: object = "1",
) -> dict[str, Any]:
    """Return traceable nominal ΔH/ΔCp and stoichiometric changes at specified extent.

    Input numbers use their decimal spelling (including finite float repr).
    Extent is an explicitly prescribed amount, not a prediction of how much
    decomposes. No initial inventory, time, gas pressure, density, or heat-loss
    model is inferred. Scalar precision is computational, not experimental.
    """
    directory = Path(source_directory)
    facts = _read(directory / "facts.json", FACTS_SHA256)
    source = _read(directory / "source.json", SOURCE_SHA256)
    temperature = _number(temperature_k, "temperature_k")
    extent = _number(extent_mol, "extent_mol")
    lo, hi = map(Decimal, facts["reaction"]["common_selected_temperature_domain_k"])
    if not lo <= temperature <= hi:
        raise MineralThermochemistryError("temperature_outside_source_298.15_to_1200_K")
    if extent < 0:
        raise MineralThermochemistryError("negative_prescribed_extent")
    with localcontext(_CONTEXT):
        reference = Decimal(facts["reference_state"]["temperature_k"])
        phases = {s["id"]: _phase(s, temperature, reference) for s in facts["species"]}
        reaction_h = sum((nu*Decimal(phases[name]["standard_enthalpy_coordinate_j_mol"])
                          for name, nu in _STOICHIOMETRY.items()), Decimal(0))
        reaction_cp = sum((nu*Decimal(phases[name]["cp_j_mol_k"])
                           for name, nu in _STOICHIOMETRY.items()), Decimal(0))
        masses = {name: nu*extent*Decimal(phases[name]["molar_mass_g_mol"])/1000
                  for name, nu in _STOICHIOMETRY.items()}
        elements = {element: sum(nu*extent*_ELEMENTS[name].get(element, 0)
                                for name, nu in _STOICHIOMETRY.items())
                    for element in ("Ca", "C", "O")}
        if sum(masses.values()) != 0 or any(elements.values()):
            raise MineralThermochemistryError("nominal_reaction_not_balanced")
        reaction = {
            "id": facts["reaction"]["id"], "equation": "CaCO3(calcite) -> CaO(crystal) + CO2(ideal gas)",
            "extent_basis": facts["reaction"]["extent_basis"],
            "stoichiometry_mol_per_mol_extent": dict(_STOICHIOMETRY),
            "enthalpy_j_mol_extent": str(reaction_h),
            "heat_capacity_change_j_mol_extent_k": str(reaction_cp),
            "enthalpy_for_extent_j": str(extent*reaction_h),
            "mass_changes_kg": {name: str(value) for name, value in masses.items()},
            "element_changes_mol": {name: str(value) for name, value in elements.items()},
        }
    pdf = next(asset for asset in source["assets"] if asset["kind"] == "official_pdf")
    return {
        "schema": "calcite_thermochemistry_result_v1", "status": "calculated",
        "method_id": METHOD_ID, "temperature_k": str(temperature), "extent_mol": str(extent),
        "reference_temperature_k": facts["reference_state"]["temperature_k"],
        "standard_pressure_pa": facts["reference_state"]["pressure_pa"],
        "temperature_domain_k": [str(lo), str(hi)], "species": phases, "reaction": reaction,
        "source": {"id": source["source_id"], "title": source["title"], "authors": source["authors"],
                   "year": source["year"], "url": source["official_pdf_url"],
                   "original_pdf_sha256": pdf["sha256"], "original_pdf_bytes": pdf["bytes"],
                   "facts_sha256": FACTS_SHA256, "source_metadata_sha256": SOURCE_SHA256,
                   "reading": source["verification"], "rights": source["rights"],
                   "upstream_references_not_read": source["upstream_references_not_read"]},
        "trace": _trace(facts),
        "uncertainty": {"source_convention": facts["uncertainty"],
                        "reaction_enthalpy_uncertainty_j_mol": None,
                        "reason": "Cross-species covariance and temperature-fit error are unknown; printed estimates are not hard bounds."},
        "numerical_policy": {"decimal_precision": 80, "rounding": "ROUND_HALF_EVEN",
                             "input_max_significant_digits": 50, "input_max_absolute_exponent": 1000,
                             "precision_is_physical_uncertainty": False},
        "input_classification": {"temperature_k": "virtual_design_choice", "extent_mol": "virtual_design_choice"},
        "software": {"module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     "python": sys.version.split()[0]},
        "qualification": {"source_polynomial_evaluation_only": True,
                          "prescribed_extent_is_design_choice": True,
                          "extent_inventory_feasibility_checked": False,
                          "kinetic_model": None, "equilibrium_model": None,
                          "phase_stability_certified": False, "high_temperature_volume_model": None,
                          "full_firing_cycle": False, "MIA3_material_qualified": False,
                          "interpretation": "Nominal pure-phase standard enthalpy; neither reaction rate nor heat input of a kiln."},
    }
