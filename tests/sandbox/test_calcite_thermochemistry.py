"""Pure-source reaction thermochemistry: independent integration and boundaries."""
from decimal import Decimal, localcontext
import json
from pathlib import Path
import shutil

import pytest
from scipy.integrate import quad

from sludge_sandbox.calcite_thermochemistry import (
    MineralThermochemistryError, calculate_calcite_thermochemistry,
)


DATA = Path(__file__).resolve().parents[2] / "data/sandbox/research/calcite-thermochemistry-v1"


def test_reference_reaction_and_specified_extent_are_balanced():
    result = calculate_calcite_thermochemistry(DATA, temperature_k="298.15", extent_mol="0.25")
    reaction = result["reaction"]
    assert Decimal(reaction["enthalpy_j_mol_extent"]) == Decimal("178800")
    assert Decimal(reaction["enthalpy_for_extent_j"]) == Decimal("44700")
    assert Decimal(reaction["mass_changes_kg"]["carbon_dioxide"]) == Decimal("0.0110025")
    assert sum(map(Decimal, reaction["mass_changes_kg"].values())) == 0
    assert all(Decimal(v) == 0 for v in reaction["element_changes_mol"].values())
    assert result["qualification"]["kinetic_model"] is None
    assert result["qualification"]["full_firing_cycle"] is False
    assert result["uncertainty"]["reaction_enthalpy_uncertainty_j_mol"] is None


@pytest.mark.parametrize("temperature", ["350", "650", "900", "1200"])
def test_source_sensible_heat_matches_independent_quadrature(temperature):
    facts = json.loads((DATA / "facts.json").read_text())
    result = calculate_calcite_thermochemistry(DATA, temperature_k=temperature)
    for species in facts["species"]:
        a, b, c, d, e = (float(species["cp"]["coefficients_nominal"][f"A{i}"]) for i in range(1, 6))
        integral, error = quad(lambda t: a + b*t + c/t**2 + d/t**0.5 + e*t*t,
                               298.15, float(temperature), epsabs=1e-8, epsrel=1e-12)
        actual = result["species"][species["id"]]
        # This is a numerical integration comparison, not experimental tolerance.
        assert abs(float(actual["sensible_enthalpy_j_mol"]) - integral) <= max(1e-8, error*4)
        expected = float(species["reference_298"]["hf_kj_mol"])*1000 + integral
        assert float(actual["standard_enthalpy_coordinate_j_mol"]) == pytest.approx(expected, abs=1e-8)


def test_no_ambient_decimal_context_or_high_temperature_formation_column_substitution():
    expected = calculate_calcite_thermochemistry(DATA, temperature_k="1000")
    with localcontext() as context:
        context.prec = 6
        actual = calculate_calcite_thermochemistry(DATA, temperature_k="1000")
    assert actual == expected
    # The book's hf(T) column changes the element reference with T. It is not h(T).
    calcite = Decimal(actual["species"]["calcite"]["standard_enthalpy_coordinate_j_mol"])
    assert abs(calcite - Decimal("-1199100")) > Decimal("1000")
    assert actual["qualification"]["phase_stability_certified"] is False


@pytest.mark.parametrize("temperature", [True, None, "NaN", "Infinity", "350 degC", "298", "1200.01", "1e999999"])
def test_invalid_or_out_of_source_temperature_is_rejected(temperature):
    with pytest.raises(MineralThermochemistryError):
        calculate_calcite_thermochemistry(DATA, temperature_k=temperature)


@pytest.mark.parametrize("extent", [True, None, "NaN", "-0.1", "1e999999"])
def test_invalid_extent_is_not_replaced_with_default(extent):
    with pytest.raises(MineralThermochemistryError):
        calculate_calcite_thermochemistry(DATA, temperature_k="400", extent_mol=extent)


def test_changed_source_is_rejected_and_zero_extent_does_not_change_thermochemistry(tmp_path):
    shutil.copytree(DATA, tmp_path / "source")
    changed = tmp_path / "source/facts.json"
    changed.write_bytes(changed.read_bytes() + b" ")
    with pytest.raises(MineralThermochemistryError, match="facts"):
        calculate_calcite_thermochemistry(tmp_path / "source", temperature_k="400")
    result = calculate_calcite_thermochemistry(DATA, temperature_k="400", extent_mol="0")
    assert Decimal(result["reaction"]["enthalpy_for_extent_j"]) == 0
    assert Decimal(result["reaction"]["enthalpy_j_mol_extent"]) > 0


def test_every_calculated_quantity_has_equation_and_source_path():
    result = calculate_calcite_thermochemistry(DATA, temperature_k="800")
    trace = result["trace"]
    # Every dependency is an actual path in the published result, not a label
    # that requires an unstated external lookup or an absent parent object.
    for entry in trace.values():
        for dependency in entry["dependencies"]:
            value = result
            for part in dependency.split("."):
                value = value[part]
            assert value is not None
    for key in ("reaction.enthalpy_j_mol_extent", "reaction.heat_capacity_change_j_mol_extent_k",
                "reaction.enthalpy_for_extent_j", "reaction.mass_changes_kg"):
        assert trace[key]["formula"]
        assert trace[key]["dependencies"]
    for phase in result["species"]:
        entry = trace[f"species.{phase}.standard_enthalpy_coordinate_j_mol"]
        assert entry["source_locators"]["reference_298"]["pdf_one_based_page"] > 0
        assert entry["source_locators"]["cp_coefficients"]["pdf_one_based_page"] > 0
    assert result["source"]["original_pdf_sha256"] == "ca89fc07fd110a0441f3bc01d5fe67d749a944da2e7f2537520dbaf367f49dd8"


def test_cli_and_python_call_the_same_thermochemistry(capsys):
    from sludge_sandbox.cli import main
    status = main(["calcite-thermochemistry", "--source-data", str(DATA),
                   "--temperature-k", "800", "--extent-mol", "0.1"])
    assert status == 0
    assert json.loads(capsys.readouterr().out) == calculate_calcite_thermochemistry(
        DATA, temperature_k="800", extent_mol="0.1")
