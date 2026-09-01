from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..config import normalize_feedstocks
from ..types import CaseConfig
from .formula import ATOMIC_WEIGHTS_KG_PER_MOL, formula_element_moles, formula_molar_mass, parse_formula

GAS_FORMULAS = {
    "H2O": {"H": 2.0, "O": 1.0},
    "CO2": {"C": 1.0, "O": 2.0},
    "N2": {"N": 2.0},
    "SO2": {"S": 1.0, "O": 2.0},
}


@dataclass(frozen=True)
class ReactionPotential:
    id: str
    gas_moles_per_kg_dry: dict[str, float]
    feed_elements_released_mol_per_kg_dry: dict[str, float]
    oxygen_in_mol_O2_per_kg_dry: float
    reactant_mass_kg_per_kg_dry: float
    deltaH_J_per_kg_dry: float
    source_kind: str

    @property
    def gas_mass_kg_per_kg_dry(self) -> float:
        return sum(amount * formula_molar_mass(GAS_FORMULAS[species]) for species, amount in self.gas_moles_per_kg_dry.items())

    def element_balance_residual(self) -> dict[str, float]:
        left = dict(self.feed_elements_released_mol_per_kg_dry)
        left["O"] = left.get("O", 0.0) + 2.0 * self.oxygen_in_mol_O2_per_kg_dry
        right: dict[str, float] = {}
        for species, amount in self.gas_moles_per_kg_dry.items():
            for element, value in formula_element_moles(GAS_FORMULAS[species], amount).items():
                right[element] = right.get(element, 0.0) + value
        elements = set(left) | set(right)
        return {element: left.get(element, 0.0) - right.get(element, 0.0) for element in elements}


def _add(target: dict[str, float], values: dict[str, float]) -> None:
    for key, value in values.items():
        target[key] = target.get(key, 0.0) + value


def _component_mass_records(case: CaseConfig):
    for feed in case.raw["feedstocks"].values():
        feed_fraction = float(feed["dry_mass_fraction"])
        for component in feed["components"]:
            component_mass = feed_fraction * float(component["fraction"])
            yield component, component_mass


def initial_element_inventory(case: CaseConfig) -> dict[str, float]:
    inventory: dict[str, float] = {}
    for component, mass in _component_mass_records(case):
        if component["kind"] == "amorphous_oxide_pool":
            for oxide, fraction in component["oxide_fractions"].items():
                oxide_mass = mass * float(fraction)
                formula = parse_formula(oxide)
                amount = oxide_mass / formula_molar_mass(formula)
                _add(inventory, formula_element_moles(formula, amount))
        else:
            formula = component["formula"]
            amount = mass / formula_molar_mass(formula)
            _add(inventory, formula_element_moles(formula, amount))
    for feed in case.raw["feedstocks"].values():
        for element, amount in feed.get("trace_element_inventory_mol_per_kg_dry", {}).items():
            inventory[element] = inventory.get(element, 0.0) + float(feed["dry_mass_fraction"]) * float(amount)
    return inventory


def _parameter_pack() -> dict:
    root = Path(__file__).resolve().parents[3]
    return json.loads((root / "data" / "parameter_pack_synthetic_v1.json").read_text(encoding="utf-8"))


def reaction_potentials(case: CaseConfig) -> list[ReactionPotential]:
    pack = _parameter_pack()["reactions"]
    results: list[ReactionPotential] = []

    forming_water = float(case.raw["forming"]["moisture_wet_basis"])
    water_mass = forming_water / (1.0 - forming_water)
    water_mass += normalize_feedstocks(case).mixture_water_kg_per_kg_dry
    water_moles = water_mass / formula_molar_mass("H2O")
    water_heat = pack["free_water_removal"]["deltaH_J_kg_product"] * water_mass
    results.append(ReactionPotential(
        "free_water_removal", {"H2O": water_moles}, formula_element_moles("H2O", water_moles), 0.0,
        water_mass, water_heat, pack["free_water_removal"]["source_kind"],
    ))

    gas: dict[str, float] = {name: 0.0 for name in GAS_FORMULAS}
    feed_elements: dict[str, float] = {}
    oxygen_in = 0.0
    organic_mass = 0.0
    for component, mass in _component_mass_records(case):
        if component["kind"] != "organic_pseudocomponent":
            continue
        formula = parse_formula(component["formula"])
        amount = mass / formula_molar_mass(formula)
        atoms = formula_element_moles(formula, amount)
        _add(feed_elements, atoms)
        gas["CO2"] += atoms.get("C", 0.0)
        gas["H2O"] += atoms.get("H", 0.0) / 2.0
        gas["N2"] += atoms.get("N", 0.0) / 2.0
        gas["SO2"] += atoms.get("S", 0.0)
        product_oxygen_atoms = 2.0 * gas["CO2"] + gas["H2O"] + 2.0 * gas["SO2"]
        oxygen_in = max(0.0, (product_oxygen_atoms - feed_elements.get("O", 0.0)) / 2.0)
        organic_mass += mass
    organic_heat = pack["organic_oxidation"]["deltaH_J_kg_feed"] * organic_mass
    results.append(ReactionPotential(
        "organic_oxidation", {key: value for key, value in gas.items() if value > 0.0}, feed_elements,
        oxygen_in, organic_mass, organic_heat, pack["organic_oxidation"]["source_kind"],
    ))

    kaolinite_moles = 0.0
    kaolinite_mass = 0.0
    calcite_moles = 0.0
    calcite_mass = 0.0
    for component, mass in _component_mass_records(case):
        if component["id"] == "kaolinite":
            kaolinite_moles += mass / formula_molar_mass(component["formula"])
            kaolinite_mass += mass
        elif component["id"] == "calcite":
            calcite_moles += mass / formula_molar_mass(component["formula"])
            calcite_mass += mass
    dehydro_water = 2.0 * kaolinite_moles
    dehydro_mass = dehydro_water * formula_molar_mass("H2O")
    results.append(ReactionPotential(
        "kaolinite_dehydroxylation", {"H2O": dehydro_water}, formula_element_moles("H2O", dehydro_water),
        0.0, kaolinite_mass, pack["kaolinite_dehydroxylation"]["deltaH_J_kg_product"] * dehydro_mass,
        pack["kaolinite_dehydroxylation"]["source_kind"],
    ))
    carbonate_gas_mass = calcite_moles * formula_molar_mass("CO2")
    results.append(ReactionPotential(
        "carbonate_decomposition", {"CO2": calcite_moles}, formula_element_moles("CO2", calcite_moles),
        0.0, calcite_mass, pack["carbonate_decomposition"]["deltaH_J_kg_product"] * carbonate_gas_mass,
        pack["carbonate_decomposition"]["source_kind"],
    ))
    return results
