"""Manufactured metadata tests, not evidence about a physical material."""

from copy import deepcopy

import pytest

from sludge_sandbox.evidence import EvidenceError, EvidenceRegistry


def registry_payload():
    source = {
        "id": "test-paper", "title": "Manufactured registry fixture",
        "authors": ["Test fixture"], "year": 2026,
        "url": "https://example.org/fixture", "read_status": "full_text_checked",
        "retrieved_at": "2026-09-07", "license": "test_fixture_only",
    }
    domain = {"material_classes": ["raw_sewage_sludge"], "atmospheres": ["air"],
              "temperature_K": [300.0, 800.0], "geometries": ["slab"]}
    parameter = {
        "id": "conductivity", "role": "physical_parameter",
        "evidence_kind": "measured_public_data", "value": 0.6,
        "unit": "W/(m*K)", "basis": "bulk effective conductivity",
        "citations": [{"source_id": "test-paper", "locator": "Table 1, row k",
                       "support": "value"}],
        "dependencies": [], "domain": domain,
        "applicability": {"status": "matched", "rationale": "Manufactured matching-domain test"},
        "uncertainty": {"status": "unquantified", "rationale": "Fixture has no error estimate"},
    }
    equation = deepcopy(parameter)
    equation.update(id="fourier", role="equation", value="q=-k*grad(T)",
                    evidence_kind="physical_law_or_constant", unit="W/m2",
                    dependencies=["conductivity"])
    equation["citations"] = [{"source_id": "test-paper", "locator": "Equation 1",
                              "support": "equation"}]
    output = deepcopy(parameter)
    output.update(id="surface_heat_flux", role="output", value=None,
                  evidence_kind="derived_from_evidence", unit="W/m2",
                  dependencies=["fourier"], citations=[])
    return {"schema_version": "1.0", "sources": [source],
            "nodes": [parameter, equation, output]}


CONTEXT = {"material_class": "raw_sewage_sludge", "atmosphere": "air",
           "temperature_K": [310.0, 700.0], "geometry": "slab"}


def test_trace_keeps_exact_source_locations_and_transitive_dependencies():
    registry = EvidenceRegistry.from_dict(registry_payload())
    trace = registry.trace("surface_heat_flux")
    assert [n["id"] for n in trace["nodes"]] == ["conductivity", "fourier", "surface_heat_flux"]
    assert trace["nodes"][0]["citations"][0]["locator"] == "Table 1, row k"
    assessment = registry.assess(["surface_heat_flux"], CONTEXT)
    assert assessment.allowed
    assert assessment.traceability_coverage == 1.0
    assert assessment.scientific_validation == "not_established_by_registry"
    assert assessment.source_assets == "not_checked"


def test_unknown_parameter_blocks_its_derived_outputs():
    payload = registry_payload()
    payload["nodes"][0].update(evidence_kind="unknown", value=None, citations=[])
    result = EvidenceRegistry.from_dict(payload).assess(["surface_heat_flux"], CONTEXT)
    assert not result.allowed
    assert any(i.code == "unknown_dependency" and i.node_id == "conductivity" for i in result.issues)


@pytest.mark.parametrize("change,code", [
    ({"atmosphere": "nitrogen"}, "outside_domain"),
    ({"material_class": "sewage_sludge_ash"}, "outside_domain"),
    ({"temperature_K": [310.0, 801.0]}, "outside_domain"),
    ({"geometry": "hollow_brick"}, "outside_domain"),
])
def test_citation_does_not_override_material_or_condition_mismatch(change, code):
    result = EvidenceRegistry.from_dict(registry_payload()).assess(
        ["surface_heat_flux"], CONTEXT | change)
    assert not result.allowed
    assert any(i.code == code for i in result.issues)


def test_missing_context_is_not_assumed_to_match():
    context = dict(CONTEXT)
    del context["atmosphere"]
    result = EvidenceRegistry.from_dict(registry_payload()).assess(["surface_heat_flux"], context)
    assert not result.allowed
    assert any(i.code == "context_missing" for i in result.issues)


@pytest.mark.parametrize("read_status", ["metadata_only", "abstract_only", "not_read"])
def test_unread_values_do_not_get_evidence_coverage(read_status):
    payload = registry_payload()
    payload["sources"][0]["read_status"] = read_status
    result = EvidenceRegistry.from_dict(payload).assess(["surface_heat_flux"], CONTEXT)
    assert not result.allowed
    assert result.traceability_coverage < 1.0


def test_background_citation_cannot_support_a_numeric_parameter():
    payload = registry_payload()
    payload["nodes"][0]["citations"][0]["support"] = "context"
    result = EvidenceRegistry.from_dict(payload).assess(["surface_heat_flux"], CONTEXT)
    assert not result.allowed
    assert any(i.code == "direct_evidence_missing" for i in result.issues)


def test_fixture_requires_explicit_mode_and_taints_downstream():
    payload = registry_payload()
    node = payload["nodes"][0]
    node.update(evidence_kind="manufactured_test_fixture", citations=[],
                rationale="Only verifies software behavior")
    registry = EvidenceRegistry.from_dict(payload)
    assert not registry.assess(["surface_heat_flux"], CONTEXT).allowed
    result = registry.assess(["surface_heat_flux"], CONTEXT, mode="manufactured")
    assert result.allowed
    assert result.result_lane == "manufactured_test_fixture"
    assert result.traceability_coverage < 1.0


def test_material_constant_cannot_be_relabelled_as_design_choice():
    payload = registry_payload()
    payload["nodes"][0].update(evidence_kind="virtual_design_choice", rationale="Fake permission")
    with pytest.raises(EvidenceError, match="role"):
        EvidenceRegistry.from_dict(payload)


@pytest.mark.parametrize("mutation", ["cycle", "missing_dependency", "duplicate", "nan", "unknown_unit"])
def test_invalid_graph_rejected_before_any_solver_runs(mutation):
    payload = registry_payload()
    if mutation == "cycle":
        payload["nodes"][0]["dependencies"] = ["surface_heat_flux"]
    elif mutation == "missing_dependency":
        payload["nodes"][0]["dependencies"] = ["not-present"]
    elif mutation == "duplicate":
        payload["nodes"].append(deepcopy(payload["nodes"][0]))
    elif mutation == "nan":
        payload["nodes"][0]["value"] = float("nan")
    else:
        payload["nodes"][0]["unit"] = "mystery-unit"
    with pytest.raises(EvidenceError):
        EvidenceRegistry.from_dict(payload)


def test_modifying_input_or_returned_trace_does_not_change_registry():
    payload = registry_payload()
    registry = EvidenceRegistry.from_dict(payload)
    payload["nodes"][0]["value"] = 999.0
    trace = registry.trace("surface_heat_flux")
    trace["nodes"][0]["value"] = 999.0
    assert registry.trace("conductivity")["nodes"][0]["value"] == 0.6


def test_conditional_model_is_explicit_exploration_not_evidence_prediction():
    payload = registry_payload()
    payload["nodes"][0]["applicability"]["status"] = "conditional"
    registry = EvidenceRegistry.from_dict(payload)
    assert not registry.assess(["surface_heat_flux"], CONTEXT).allowed
    result = registry.assess(["surface_heat_flux"], CONTEXT, mode="exploratory")
    assert result.allowed
    assert result.result_lane == "exploratory"
    assert result.issues


def test_unknown_never_becomes_a_number_even_in_exploratory_mode():
    payload = registry_payload()
    payload["nodes"][0].update(evidence_kind="unknown", value=None, citations=[])
    assert not EvidenceRegistry.from_dict(payload).assess(
        ["surface_heat_flux"], CONTEXT, mode="exploratory").allowed


@pytest.mark.parametrize("value", [[], {}, {"value": None}, ["not-a-number"], [True], 10**1000])
def test_structured_parameter_placeholders_cannot_pass(value):
    payload = registry_payload()
    payload["nodes"][0]["value"] = value
    with pytest.raises(EvidenceError):
        EvidenceRegistry.from_dict(payload)


def test_derived_label_cannot_launder_a_design_choice_into_a_material_property():
    payload = registry_payload()
    decision = deepcopy(payload["nodes"][0])
    decision.update(id="chosen_k", role="design_input", evidence_kind="virtual_design_choice",
                    citations=[], rationale="Exploration choice only")
    payload["nodes"].append(decision)
    payload["nodes"][0].update(evidence_kind="derived_from_evidence", dependencies=["chosen_k"],
                               citations=[], derivation="k=chosen_k")
    result = EvidenceRegistry.from_dict(payload).assess(["conductivity"], CONTEXT)
    assert not result.allowed
    assert result.traceability_coverage == 0
    assert any(i.code == "physical_evidence_root_missing" for i in result.issues)


@pytest.mark.parametrize("field", ["evidence_kind", "role"])
def test_unhashable_enums_give_structured_validation_errors(field):
    payload = registry_payload()
    payload["nodes"][0][field] = []
    with pytest.raises(EvidenceError):
        EvidenceRegistry.from_dict(payload)


def test_duplicate_json_keys_cannot_replace_an_unknown_value(tmp_path):
    import json
    raw = json.dumps(registry_payload()).replace('"value": 0.6', '"value": null, "value": 0.6', 1)
    path = tmp_path / "duplicate.json"
    path.write_text(raw)
    with pytest.raises(EvidenceError):
        EvidenceRegistry.from_file(path)


def test_derived_equation_requires_recorded_derivation():
    payload = registry_payload()
    payload["nodes"][1].update(evidence_kind="derived_from_evidence", citations=[])
    with pytest.raises(EvidenceError, match="derivation"):
        EvidenceRegistry.from_dict(payload)


def test_measured_number_does_not_establish_an_arbitrary_derived_equation():
    payload = registry_payload()
    payload["nodes"][1].update(evidence_kind="derived_from_evidence", citations=[],
                               value="q=k*42", derivation="Multiply measured k by 42")
    result = EvidenceRegistry.from_dict(payload).assess(["surface_heat_flux"], CONTEXT)
    assert not result.allowed
    assert any(i.code == "equation_evidence_root_missing" for i in result.issues)


def test_derived_equation_traces_an_upstream_sourced_relation():
    payload = registry_payload()
    equation = deepcopy(payload["nodes"][1])
    equation.update(id="integrated_fourier", evidence_kind="derived_from_evidence", citations=[],
                    dependencies=["fourier"], value="Q=A*q", unit="W",
                    derivation="Integrate uniform Fourier flux over the specified surface area")
    payload["nodes"].append(equation)
    result = EvidenceRegistry.from_dict(payload).assess(["integrated_fourier"], CONTEXT)
    assert result.allowed
    assert result.scientific_validation == "not_established_by_registry"
