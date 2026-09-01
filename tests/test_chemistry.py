from __future__ import annotations

from pathlib import Path

import pytest

from sludge_vme.chemistry.formula import formula_molar_mass, parse_formula
from sludge_vme.chemistry.stoichiometry import initial_element_inventory, reaction_potentials
from sludge_vme.config import load_case


ROOT = Path(__file__).resolve().parents[1]


def test_formula_parser_and_molar_mass() -> None:
    assert parse_formula("CaCO3") == {"Ca": 1.0, "C": 1.0, "O": 3.0}
    assert parse_formula({"C": 1, "H": 1.5, "O": 0.5})["H"] == pytest.approx(1.5)
    assert formula_molar_mass("H2O") == pytest.approx(0.018015, rel=2e-4)


def test_dry_feed_element_inventory_is_nonnegative_and_closes_mass() -> None:
    case = load_case(ROOT / "examples" / "tiny_synthetic.json")
    inventory = initial_element_inventory(case)
    assert all(value >= 0.0 for value in inventory.values())
    represented_mass = sum(value * formula_molar_mass({element: 1}) for element, value in inventory.items())
    assert represented_mass == pytest.approx(1.0, rel=1e-10)


def test_reaction_potentials_are_element_balanced() -> None:
    case = load_case(ROOT / "examples" / "tiny_synthetic.json")
    potentials = reaction_potentials(case)
    assert {item.id for item in potentials} == {
        "free_water_removal",
        "organic_oxidation",
        "kaolinite_dehydroxylation",
        "carbonate_decomposition",
    }
    for item in potentials:
        residual = item.element_balance_residual()
        assert max(abs(value) for value in residual.values()) < 1e-12
        assert item.gas_mass_kg_per_kg_dry > 0.0
        assert item.deltaH_J_per_kg_dry != 0.0
