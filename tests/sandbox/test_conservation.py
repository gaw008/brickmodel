"""Independent ledger audits of manufactured integrations and corrupted exports."""

from dataclasses import replace
import math

import numpy as np
import pytest

from sludge_sandbox.conservation import (
    ConservationAuditError, ConservationBasis, ConservationPolicy, audit_conservation,
)
from sludge_sandbox.integration import (
    ConservedState, IntegrationPolicy, IntegrationResult, Rates, StepLedger, integrate,
)


def basis(**changes):
    return ConservationBasis(**(dict(
        species_order=("C", "O2", "CO2"),
        molar_masses_kg_mol=(.012, .032, .044),
        element_order=("C", "O"), element_matrix=((1, 0, 1), (0, 2, 2)),
    ) | changes))


def audit_policy(**changes):
    return ConservationPolicy(**(dict(
        relative_tolerance=1e-10,
        amount_absolute_tolerance_mol=1e-12, amount_scale_mol=1.,
        mass_absolute_tolerance_kg=1e-14, mass_scale_kg=.1,
        element_absolute_tolerance_mol=1e-12, element_scale_mol=1.,
        energy_absolute_tolerance_j=1e-9, energy_scale_j=1.,
    ) | changes))


def run(*, inert=False, **policy_changes):
    initial = ConservedState([[2, 2, .1], [1, 2, .2]], [100, 120])

    def operator(state, time):
        if inert:
            return Rates(np.zeros((3, 3)), np.zeros(3), np.zeros((2, 3)), np.zeros(2))
        n = state.amounts_mol
        rate = .1*n[:, 0]*n[:, 1]
        reaction = np.column_stack((-rate, -rate, rate))
        face = [[0, .3+.1*time, 0],
                [0, .03*(n[0, 1]-n[1, 1]), .02*(n[0, 2]-n[1, 2])],
                [0, 0, .01*n[1, 2]]]
        return Rates(face, [3+time, .1*(state.internal_energy_j[0]-state.internal_energy_j[1]), -.3],
                     reaction, [.25, -.05])

    numerical = IntegrationPolicy(**(dict(
        initial_step_s=.1, maximum_step_s=.2, minimum_step_s=1e-10,
        relative_tolerance=1e-6, amount_absolute_tolerance_mol=1e-12,
        energy_absolute_tolerance_j=1e-9, amount_scale_mol=1., energy_scale_j=10.,
        maximum_steps=10000, maximum_rejections=1000, maximum_wall_seconds=10.,
    ) | policy_changes))
    return integrate(initial, operator, start_s=0., end_s=1., policy=numerical)


def change_step(result, index, field, location, addition):
    value = np.array(getattr(result.steps[index], field))
    value[location] += addition
    steps = list(result.steps)
    steps[index] = replace(steps[index], **{field: value})
    return replace(result, steps=tuple(steps))


def test_actual_open_reacting_integration_has_independent_species_mass_elements_and_u_audits():
    result = run()
    assert result.status == "completed"
    report = audit_conservation(result, basis=basis(), policy=audit_policy())
    assert report.status == "passed" and report.passed
    assert report.integration_status == "completed"
    assert report.audited_steps == len(result.steps)
    assert report.checks["cell_species_step"].count == len(result.steps)*2*3
    assert report.checks["reaction_element_cell_step"].count == len(result.steps)*2*2
    assert report.energy_scope == "stored_internal_energy_ledger_only"
    payload = report.to_dict()
    assert payload["thermodynamic_reconstruction"] == "not_evaluated"
    assert payload["species_order"] == ["C", "O2", "CO2"]
    assert payload["element_order"] == ["C", "O"]
    assert payload["basis"]["molar_masses_kg_mol"] == (.012, .032, .044)
    assert payload["basis"]["element_matrix"] == ((1, 0, 1), (0, 2, 2))
    assert report.initial.mass_kg == pytest.approx(3*.012+4*.032+.3*.044)
    assert report.initial.elements_mol == pytest.approx((3.3, 8.6))
    boundary_u = math.fsum(
        value for step in result.steps
        for value in (step.face_energy_j[0], -step.face_energy_j[-1], *step.cell_work_j)
    )
    assert report.final.stored_internal_energy_j-report.initial.stored_internal_energy_j == pytest.approx(boundary_u)


def test_auditor_does_not_call_integrator_or_its_derivative_as_an_oracle(monkeypatch):
    result = run()

    def forbidden(*args, **kwargs):
        raise AssertionError("audit called the forward integrator")

    monkeypatch.setattr("sludge_sandbox.integration.integrate", forbidden)
    monkeypatch.setattr(Rates, "derivatives", forbidden)
    assert audit_conservation(result, basis=basis(), policy=audit_policy()).passed


def test_mutated_interior_species_face_is_found_locally_even_when_system_totals_cancel():
    result = change_step(run(), 1, "face_species_mol", (1, 1), .01)
    report = audit_conservation(result, basis=basis(), policy=audit_policy())
    assert not report.passed
    check = report.checks["cell_species_step"]
    assert check.max_absolute_residual == pytest.approx(.01)
    assert check.worst_location.step_index == 1
    assert check.worst_location.cell_index in (0, 1)
    assert check.worst_location.species_id == "O2"
    assert report.checks["system_species_step"].passed
    assert report.checks["system_mass_prefix"].passed


@pytest.mark.parametrize("field,location", [
    ("face_energy_j", 0), ("cell_work_j", 1),
])
def test_mutated_external_energy_or_work_is_rejected(field, location):
    result = change_step(run(), 0, field, location, .1)
    report = audit_conservation(result, basis=basis(), policy=audit_policy())
    assert not report.passed
    assert not report.checks["system_energy_step"].passed
    assert report.checks["system_energy_step"].worst_location.step_index == 0


def test_mutated_interior_energy_face_is_rejected_without_false_global_energy_error():
    result = change_step(run(), 0, "face_energy_j", 1, .1)
    report = audit_conservation(result, basis=basis(), policy=audit_policy())
    assert not report.checks["cell_energy_step"].passed
    assert report.checks["system_energy_step"].passed
    assert report.checks["system_energy_prefix"].passed


def test_reaction_source_tamper_is_rejected_even_when_states_are_coherently_changed():
    original = run()
    corrupted = change_step(original, 0, "reaction_species_mol", (0, 2), .01)
    states = [original.states[0]]
    for state in original.states[1:]:
        n = np.array(state.amounts_mol)
        n[0, 2] += .01
        states.append(ConservedState(n, state.internal_energy_j))
    report = audit_conservation(replace(corrupted, states=tuple(states)), basis=basis(), policy=audit_policy())
    assert report.checks["cell_species_step"].passed
    assert not report.checks["reaction_mass_cell_step"].passed
    assert not report.checks["reaction_element_cell_step"].passed
    assert not report.checks["system_mass_step"].passed
    assert not report.checks["system_element_prefix"].passed


def test_mass_and_element_basis_are_independently_applied():
    result = run()
    bad_mass = audit_conservation(result, basis=basis(molar_masses_kg_mol=(.024, .032, .044)), policy=audit_policy())
    assert not bad_mass.checks["reaction_mass_cell_step"].passed
    assert bad_mass.checks["reaction_element_cell_step"].passed
    bad_elements = audit_conservation(result, basis=basis(element_matrix=((1, 0, 1), (0, 2, 1))), policy=audit_policy())
    assert bad_elements.checks["reaction_mass_cell_step"].passed
    assert not bad_elements.checks["reaction_element_cell_step"].passed


def test_prefix_audit_finds_accumulating_subthreshold_errors_even_if_endpoint_cancels():
    result = run(inert=True)
    steps = len(result.steps)
    assert steps >= 6
    states = tuple(ConservedState(state.amounts_mol,
                                 state.internal_energy_j+[4e-11*min(index, steps-index), 0])
                   for index, state in enumerate(result.states))
    report = audit_conservation(replace(result, states=states), basis=basis(),
                                policy=audit_policy(relative_tolerance=0, energy_absolute_tolerance_j=1e-10))
    assert report.checks["cell_energy_step"].passed
    assert report.checks["system_energy_step"].passed
    assert not report.checks["system_energy_prefix"].passed
    assert report.final.stored_internal_energy_j == report.initial.stored_internal_energy_j
    assert report.checks["system_energy_prefix"].worst_location.end_s < result.times_s[-1]


def test_large_equal_throughflows_do_not_hide_small_inventory_or_impose_artifact_scaled_tolerance():
    result = run(inert=True)
    states = tuple(ConservedState(state.amounts_mol, [1e20, 1]) for state in result.states)
    ledgers = tuple(replace(step, face_species_mol=[[1e20, 0, 0]]*3,
                            face_energy_j=[1e20]*3) for step in result.steps)
    result = replace(result, states=states, steps=ledgers)
    assert audit_conservation(result, basis=basis(), policy=audit_policy()).passed
    corrupted = change_step(result, 0, "cell_work_j", 0, 1.)
    report = audit_conservation(corrupted, basis=basis(), policy=audit_policy())
    assert not report.checks["cell_energy_step"].passed
    assert not report.checks["system_energy_prefix"].passed
    assert report.checks["cell_energy_step"].max_absolute_residual == 1.
    assert report.checks["cell_energy_step"].limit == pytest.approx(1.1e-9)


def test_prefix_summation_retains_small_exchange_between_large_opposite_steps():
    result = run(inert=True)
    states = tuple(ConservedState(state.amounts_mol, [1e20 if index in (1, 2) else 0, 0])
                   for index, state in enumerate(result.states))
    steps = tuple(replace(step, cell_work_j=[{0: 1e20, 1: 1, 2: -1e20}.get(index, 0), 0])
                  for index, step in enumerate(result.steps))
    report = audit_conservation(replace(result, states=states, steps=steps),
                                basis=basis(), policy=audit_policy())
    # A naive accumulated total loses +1 after +1e20 and reports a false zero.
    check = report.checks["system_energy_prefix"]
    assert check.max_absolute_residual == 1.
    assert check.worst_location.step_index == 1
    assert check.worst_signed_residual == -1.


def test_derived_weighted_totals_that_overflow_fail_closed():
    with pytest.raises(ConservationAuditError):
        audit_conservation(run(inert=True),
                           basis=basis(molar_masses_kg_mol=(1e308, 1e308, 1e308)),
                           policy=audit_policy())


def test_rounded_weighted_products_cannot_hide_mass_and_atom_creation():
    n, a = 1e16, 1+2**-52
    states = (ConservedState([[n, 0]], [0]), ConservedState([[0, n+2]], [0]))
    step = StepLedger(0, 1, [[0, 0], [0, 0]], [0, 0], [[-n, n+2]], [0])
    result = IntegrationResult('completed', None, (0, 1), states, (step,), 0, 0, 0)
    quantities = ConservationBasis(('A', 'B'), (a, 1), ('C',), ((a, 1),))
    report = audit_conservation(result, basis=quantities,
                                policy=audit_policy(relative_tolerance=0,
                                                    mass_absolute_tolerance_kg=1e-9,
                                                    element_absolute_tolerance_mol=1e-9))
    assert not report.passed
    for name in ('reaction_mass_cell_step', 'reaction_element_cell_step',
                 'system_mass_prefix', 'system_element_prefix'):
        assert report.checks[name].max_absolute_residual == pytest.approx(.22044604925031308)


@pytest.mark.parametrize('quantity', ['energy', 'species'])
def test_opposite_cell_drifts_cannot_cancel_in_system_prefix(quantity):
    result = run(inert=True, initial_step_s=.1, maximum_step_s=.1)
    states = []
    for index, state in enumerate(result.states):
        n, u = state.amounts_mol.copy(), state.internal_energy_j.copy()
        if quantity == 'energy':
            u += np.array([1, -1])*index*.5e-9
        else:
            n[:, 0] += np.array([1, -1])*index*.5e-12
        states.append(ConservedState(n, u))
    report = audit_conservation(replace(result, states=tuple(states)), basis=basis(),
                                policy=audit_policy(relative_tolerance=0))
    assert report.checks[f'cell_{quantity}_step'].passed
    assert report.checks[f'system_{quantity}_prefix'].passed
    assert not report.passed
    assert not report.checks[f'cell_{quantity}_prefix'].passed


def test_partial_prefix_is_distinguished_from_a_completed_simulation():
    result = run(maximum_steps=1)
    assert result.status == "resource_limit"
    report = audit_conservation(result, basis=basis(), policy=audit_policy())
    assert report.passed and not report.trajectory_completed
    assert report.integration_status == "resource_limit"


def test_no_accepted_steps_are_not_an_audit_pass():
    result = run()
    result = replace(result, status="cancelled", times_s=result.times_s[:1],
                     states=result.states[:1], steps=())
    report = audit_conservation(result, basis=basis(), policy=audit_policy())
    assert report.status == "not_evaluated_no_steps" and not report.passed
    assert all(check.count == 0 for check in report.checks.values())


@pytest.mark.parametrize("change", [
    {"times_s": (0, 1)}, {"steps": ()}, {"status": "invented_pass"}, {"status": ["completed"]},
])
def test_inconsistent_trajectory_shape_and_status_fail_closed(change):
    with pytest.raises(ConservationAuditError):
        audit_conservation(replace(run(), **change), basis=basis(), policy=audit_policy())


def test_mismatched_step_times_or_ledger_shape_fail_closed():
    result = run()
    for broken in (replace(result.steps[0], start_s=-1),
                   replace(result.steps[0], face_species_mol=[[0, 0, 0]]),
                   replace(result.steps[0], end_s=float("nan"))):
        with pytest.raises(ConservationAuditError):
            audit_conservation(replace(result, steps=(broken, *result.steps[1:])),
                               basis=basis(), policy=audit_policy())


@pytest.mark.parametrize("change", [
    {"species_order": ("C", "C", "CO2")}, {"molar_masses_kg_mol": (.012, 0, .044)},
    {"molar_masses_kg_mol": (.012, True, .044)}, {"element_order": ("C", "C")},
    {"element_matrix": ((1, 0, 1), (0, -2, 2))}, {"element_matrix": ((1, 0, 1),)},
    {"element_matrix": ((1, 0, 1), (0, 0, 2))},
    {"element_matrix": ((1, 0, 1), (0, float("nan"), 2))},
])
def test_invalid_or_uncovered_species_basis_is_rejected(change):
    with pytest.raises(ConservationAuditError):
        basis(**change)


@pytest.mark.parametrize("change", [
    {"energy_scale_j": 0}, {"mass_scale_kg": True}, {"relative_tolerance": -1},
    {"amount_absolute_tolerance_mol": float("inf")}, {"energy_scale_j": "1"},
    {"relative_tolerance": 0, "energy_absolute_tolerance_j": 0},
])
def test_invalid_absolute_tolerance_or_fixed_scale_is_rejected(change):
    with pytest.raises(ConservationAuditError):
        audit_policy(**change)


def test_report_and_basis_are_immutable_and_report_export_is_json_ready():
    import json
    values = [[1, 0, 1], [0, 2, 2]]
    quantities = basis(element_matrix=values)
    values[0][0] = 900
    assert quantities.element_matrix[0][0] == 1
    report = audit_conservation(run(), basis=quantities, policy=audit_policy())
    with pytest.raises(TypeError):
        report.checks["cell_energy_step"] = None
    payload = report.to_dict()
    json.dumps(payload, allow_nan=False)
    payload["species_order"][0] = "changed"
    assert report.species_order[0] == "C"
