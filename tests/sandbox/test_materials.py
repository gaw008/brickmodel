"""Manufactured bookkeeping values: these tests do not define a raw-sludge material."""

import pytest

from sludge_sandbox.materials import (
    FeedPortion, MassAnalysis, MaterialError, MaterialIdentity, prepare_green_batch,
)


def identity(name="sludge", material_class="raw_sewage_sludge"):
    return MaterialIdentity(name, material_class, "manufactured-batch", ("fixture:identity",))


def test_dry_feed_native_water_and_added_forming_water_are_counted_once():
    sludge = FeedPortion(identity(), 2.0, 0.8, "fixture:sludge-water")
    clay = FeedPortion(identity("clay", "clay"), 6.0, 0.1, "fixture:clay-water")
    result = prepare_green_batch((sludge, clay), added_water_kg=1.0)
    assert result.dry_mass_kg == 8.0
    assert result.native_water_kg == pytest.approx(8 + 2/3)
    assert result.total_water_kg == pytest.approx(9 + 2/3)
    assert result.wet_mass_kg == pytest.approx(17 + 2/3)
    assert result.moisture_wet_fraction == pytest.approx((9 + 2/3)/(17 + 2/3))
    assert result.dry_mass_fractions == {"sludge": 0.25, "clay": 0.75}
    assert result.required_evidence_ids == (
        "fixture:clay-water", "fixture:identity", "fixture:sludge-water")
    assert result.scientific_status == "bookkeeping_only_sources_not_resolved"


def test_wet_input_conversion_preserves_original_total_mass():
    portion = FeedPortion.from_wet_mass(identity(), wet_mass_kg=10, native_water_wet_fraction=0.8,
                                        water_evidence_id="fixture:water")
    batch = prepare_green_batch((portion,), added_water_kg=0)
    assert batch.dry_mass_kg == pytest.approx(2)
    assert batch.wet_mass_kg == pytest.approx(10)


def test_raw_sludge_and_sludge_ash_keep_distinct_material_identities():
    ash = identity("ash", "sewage_sludge_ash")
    assert ash.material_class != identity().material_class
    with pytest.raises(MaterialError):
        identity(material_class="Raw SSA")


@pytest.mark.parametrize("moisture", [None, -0.01, 1.0, float("nan"), True, 10**1000])
def test_unknown_or_invalid_native_water_is_not_assumed_zero(moisture):
    with pytest.raises(MaterialError):
        FeedPortion(identity(), 1, moisture, "fixture:water")


def test_duplicate_feed_ids_cannot_overwrite_a_contribution():
    portion = FeedPortion(identity(), 1, 0.5, "fixture:water")
    with pytest.raises(MaterialError):
        prepare_green_batch((portion, portion), added_water_kg=0)


def test_mass_analysis_preserves_basis_and_does_not_normalize_partial_xrf():
    values = {"SiO2": 0.51, "Al2O3": 0.27}
    analysis = MassAnalysis("oxide", "dry_solid", values, "partial", "fixture:xrf")
    values["SiO2"] = 0.9
    assert dict(analysis.fractions) == {"SiO2": 0.51, "Al2O3": 0.27}
    assert analysis.unassigned_fraction == pytest.approx(0.22)
    assert analysis.kind == "oxide"
    with pytest.raises(TypeError):
        analysis.fractions["SiO2"] = 0.9


@pytest.mark.parametrize("kind,basis,values,closure", [
    ("oxide", "wet_total", {"SiO2": 1.0}, "complete"),
    ("mineral_phase", "normalized_oxides", {"SiO2": 1.0}, "complete"),
    ("elemental", "dry_solid", {"C": 0.5}, "complete"),
    ("oxide", "dry_solid", {"SiO2": 0.7, "LOI": 0.4}, "partial"),
    ("oxide", "dry_solid", {"SiO2": 0.6, "LOI": 0.4}, "complete"),
    ("elemental", "dry_solid", {"C": 0.6, "SiO2": 0.4}, "complete"),
    ("elemental", "dry_solid", {"C": 1e308, "N": 1e308}, "partial"),
    ("elemental", "dry_solid", {"C": None}, "partial"),
    ("mineral_phase", "dry_solid", {"SiO2": 1.0}, "complete"),
])
def test_incompatible_analysis_or_nonclosed_inventory_is_rejected(kind, basis, values, closure):
    with pytest.raises(MaterialError):
        MassAnalysis(kind, basis, values, closure, "fixture:analysis")


@pytest.mark.parametrize("water", [-1, None, float("inf"), True])
def test_forming_water_must_be_an_explicit_finite_nonnegative_amount(water):
    with pytest.raises(MaterialError):
        prepare_green_batch((FeedPortion(identity(), 1, 0, "fixture:water"),), added_water_kg=water)


def test_mineral_phase_identity_requires_its_own_evidence_not_an_oxide_label():
    phases = MassAnalysis("mineral_phase", "dry_solid", {"quartz": 0.5}, "partial",
                          "fixture:xrd", phase_identity_node_ids={"quartz": "fixture:quartz-phase"})
    assert phases.phase_identity_node_ids["quartz"] == "fixture:quartz-phase"
