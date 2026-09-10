"""N3 actual source terminal with manufactured water and liquid mobility."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest

from test_source_wet_column import setup
from test_source_liquid_column import config
from test_source_prefix_trial import POLICY
from test_depletion_integration import policies
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.source_prefix_trial import evaluate_source_prefix_trial
from sludge_sandbox.source_approach import propose_source_approach, evaluate_source_approach
from sludge_sandbox.source_root_comparison import evaluate_source_root_refinement
from sludge_sandbox.source_terminal import build_source_terminal


def prepare_multicell(patch, base=None, *, zero_dry_mobility=True):
    """One public fixture constructor; pass an existing base to avoid nested setup."""
    if base is None:
        base, _ = setup(patch, count=3)
    assert base.cell_count == 3
    storages = tuple(replace(s, volume=replace(s.volume, error_m3=1e-12)) for s in base.storages)
    liquid = config(3, permeability=1e-18)
    table = replace(liquid.relations[0], saturation_knots=(0., 1e-18, 1.),
        permeability_m2=(1e-18,)*3, relative_permeability=(0. if zero_dry_mobility else .5, .5, .5),
        viscosity_pa_s=(.001,)*3, relation_kind='tabulated_saturation_relation')
    liquid = replace(liquid, relations=(table,)*3,
        connections=(replace(liquid.connections[0], status='disabled'), liquid.connections[1]))
    faces = tuple(replace(face, conductivities_w_m_k=(0., 0.), diffusivities_m2_s=(0.,)*3,
                          permeability_m2=0.) for face in base.faces)
    model = replace(base, storages=storages, faces=faces, liquid_transport=liquid,
                    transfer_coefficients_mol_s_pa=(0., 1e-9, 0.))
    states = []
    for i, storage in enumerate(storages):
        state = storage.state(1e-11 if i == 1 else .25,
                              (.1875 if i == 1 else .125, .25, 1e-12), 0.)
        states.append(replace(state, internal_energy_j=storage.evaluate(state, 325.).total_internal_energy_j))
    adapter = ExactSourceColumn(model)
    initial = adapter.pack(tuple(states))
    probe = adapter.evaluate(initial, T(F()))
    rate = probe.rates
    loss = (F(float(rate.face_species_mol_s[2,0]))-F(float(rate.face_species_mol_s[1,0]))
            -F(float(rate.reaction_species_mol_s[1,0])))
    assert loss > 0 and probe.source_evaluation.faces[2].liquid_mol_s > 0
    horizon = F(3,2)*F(states[1].liquid_water_mol)/loss
    numerical = replace(POLICY, initial_step_s=float(horizon), maximum_step_s=float(horizon),
        minimum_step_s=2**-30, maximum_steps=8, maximum_wall_seconds=30.)
    seed = evaluate_source_prefix_trial(adapter, initial, start=T(F()), end=T(horizon),
                                       integration_policy=numerical, maximum_callbacks=16)
    assert seed.reason == 'source_prefix_negative_inventory_minimum', seed.reason
    assert len(seed.captures) == 2
    event = replace(policies()[1], maximum_refinements=32, terminal_method='affine_midpoint',
        roundoff_policy=replace(policies()[1].roundoff_policy,
                               molar_mass_kg_mol=model.chemical.reference.molar_mass_kg_mol))
    approach = evaluate_source_approach(propose_source_approach(seed, event_policy=event), maximum_callbacks=16)
    assert approach.status == 'validated_positive_numerical_approach', approach.reason
    refinement = evaluate_source_root_refinement(approach, maximum_callbacks=16)
    assert refinement.clock is not None, refinement.reason
    return refinement, seed.end


@pytest.fixture(scope='module')
def actual_multicell():
    with pytest.MonkeyPatch.context() as patch:
        yield prepare_multicell(patch)


def test_actual_N3_selects_middle_cell_and_keeps_shared_liquid_energy_ledger(actual_multicell):
    refinement, _ = actual_multicell
    seed = refinement.approach.proposal.original_trial
    terminal = build_source_terminal(seed, event_policy=refinement.approach.proposal.event_policy)
    assert terminal.selected_cell_index == 1
    assert terminal.root_order.order.earliest_labels == (('liquid', 1, 0),)
    assert terminal.corrected_state.amounts_mol[1,0] == 0.
    assert np.all(terminal.corrected_state.amounts_mol[[0,2],0] > 0)
    assert terminal.dry_adapter.interfaces == ('existing_liquid','depleted_no_nucleation','existing_liquid')
    np.testing.assert_array_equal(terminal.corrected_state.amounts_mol[[0,2]], terminal.prefix.raw_state.amounts_mol[[0,2]])
    np.testing.assert_array_equal(terminal.corrected_state.internal_energy_j, terminal.prefix.raw_state.internal_energy_j)
    ledger = terminal.prefix.ledger
    assert ledger.face_species_mol[2,0] > 0 and ledger.face_energy_j[2] != 0
    assert ledger.face_species_mol[1,0] == 0 and ledger.face_energy_j[1] == 0
    assert terminal.clock.signed_terms_mol == (float(ledger.face_species_mol[1,0]),
        -float(ledger.face_species_mol[2,0]), float(ledger.reaction_species_mol[1,0]))
    assert terminal.clock.positive_evaporated_mol > 0
    terminal.check()


def test_actual_darcy_and_donor_enthalpy_reconstructed_independently(actual_multicell):
    refinement, _ = actual_multicell
    seed = refinement.approach.proposal.original_trial
    terminal = build_source_terminal(seed, event_policy=refinement.approach.proposal.event_policy)
    column = seed.adapter.column
    projection_nonzero = False
    for capture in seed.captures[:2]:
        raw = capture.evaluation.source_evaluation
        left, right = raw.liquid_states[1:3]
        face = raw.faces[2]
        geometry = column.faces[1]
        # The preregistered two wet samples lie on the declared table plateau.
        assert min(left.saturation, right.saturation) > 1e-18
        mobility = F(1e-18)*F(.5)/F(.001)
        q = F(geometry.area_m2)*(F(left.pressure_pa)-F(right.pressure_pa))/(F(geometry.half_widths_m[0])/mobility+F(geometry.half_widths_m[1])/mobility)
        exact_n = q/F(left.molar_volume_m3_mol)
        exact_q = exact_n*F(left.enthalpy_j_mol)
        assert q > 0 and face.liquid_exchange.donor == 'left'
        assert face.liquid_mol_s == float(exact_n)
        assert face.liquid_enthalpy_w == float(exact_q)
        projection = F(float(exact_q))-F(float(exact_n))*F(left.enthalpy_j_mol)
        assert face.liquid_enthalpy_projection_w == projection
        projection_nonzero |= projection != 0
    assert projection_nonzero
    pieces = {key: values for key, values, _ in terminal.prefix.integrals}
    transfer = pieces['face_species_mol_s'][2*4]
    energy = pieces['face_energy_w'][2]
    assert transfer > 0 and energy != 0
    for i in range(3):
        expected_n = (F(float(seed.initial.amounts_mol[i,0])) + pieces['face_species_mol_s'][i*4]
            -pieces['face_species_mol_s'][(i+1)*4]+pieces['reaction_species_mol_s'][i*4])
        expected_u = F(float(seed.initial.internal_energy_j[i]))+pieces['face_energy_w'][i]-pieces['face_energy_w'][i+1]
        assert F(float(terminal.prefix.raw_state.amounts_mol[i,0]))-expected_n == terminal.prefix.full_residual_mol[i*4]
        assert F(float(terminal.prefix.raw_state.internal_energy_j[i]))-expected_u == terminal.prefix.full_residual_j[i]
    assert sum((pieces['face_energy_w'][i]-pieces['face_energy_w'][i+1] for i in range(3)), F()) == 0
    assert sum((pieces['face_species_mol_s'][i*4]-pieces['face_species_mol_s'][(i+1)*4] for i in range(3)), F()) == 0


@pytest.mark.parametrize('path_index', [0, 1])
def test_selected_cell_is_distinct_from_prior_path_index(actual_multicell, path_index):
    refinement, _ = actual_multicell
    seed = (refinement.approach.proposal.original_trial, refinement.shifted_trial)[path_index]
    terminal = build_source_terminal(seed, event_policy=refinement.approach.proposal.event_policy,
                                     prior_clock=refinement.clock, root_index=path_index)
    assert terminal.selected_cell_index == 1 and terminal.root_index == path_index
    assert terminal.clock.iterations == terminal.reused_clock_rounds+terminal.additional_clock_rounds
    for changed in (replace(terminal, selected_cell_index=0), replace(terminal, selected_cell_index=True)):
        with pytest.raises(ValueError):
            changed.check()
    terminal.check()


def test_passive_terminal_checks_use_saved_observations_only(actual_multicell, monkeypatch):
    from sludge_sandbox.source_wet_storage import SourceWetStorage
    from sludge_sandbox.water_properties import WaterProperties
    refinement, _ = actual_multicell
    seed = refinement.approach.proposal.original_trial
    def forbidden(*args, **kwargs):
        pytest.fail('passive terminal check called a physical provider')
    monkeypatch.setattr(ExactSourceColumn, 'evaluate', forbidden)
    monkeypatch.setattr(SourceWetStorage, 'evaluate', forbidden)
    monkeypatch.setattr(SourceWetStorage, 'invert', forbidden)
    monkeypatch.setattr(WaterProperties, 'state_tp', forbidden)
    terminal = build_source_terminal(seed, event_policy=refinement.approach.proposal.event_policy)
    terminal.check()


def test_actual_selected_dry_mode_uses_predeclared_zero_mobility(actual_multicell):
    refinement, _ = actual_multicell
    seed = refinement.approach.proposal.original_trial
    terminal = build_source_terminal(seed, event_policy=refinement.approach.proposal.event_policy)
    observed = terminal.dry_adapter.evaluate(terminal.corrected_state, terminal.clock.lower)
    assert observed.source_evaluation.faces[2].liquid_exchange.status == 'zero_mobility'
    assert observed.source_evaluation.faces[2].liquid_mol_s == 0.
    assert observed.source_evaluation.cells[1].phase.phase_water_mol_s == 0.
    assert observed.source_states[0].liquid_water_mol > 0 and observed.source_states[2].liquid_water_mol > 0
    assert terminal.dry_adapter.column.liquid_transport is seed.adapter.column.liquid_transport


@pytest.mark.parametrize('which', ['donor', 'enthalpy', 'projection', 'source', 'decoded_pressure'])
def test_saved_face_detail_changes_are_rejected_without_EOS(actual_multicell, which):
    from sludge_sandbox.source_terminal_liquid import check_source_terminal_liquid
    refinement, _ = actual_multicell
    seed = refinement.approach.proposal.original_trial
    terminal = build_source_terminal(seed, event_policy=refinement.approach.proposal.event_policy)
    raw = terminal.panel.first.evaluation.source_evaluation
    face = raw.faces[2]
    if which == 'donor':
        face = replace(face, liquid_exchange=replace(face.liquid_exchange, donor='right'))
    elif which == 'enthalpy':
        face = replace(face, liquid_enthalpy_w=face.liquid_enthalpy_w+1.)
    elif which == 'projection':
        face = replace(face, liquid_enthalpy_projection_w=F(1))
    elif which == 'source':
        face = replace(face, liquid_exchange=replace(face.liquid_exchange, source_ids=('invented',)))
    else:
        states = list(raw.liquid_states)
        states[1] = replace(states[1], pressure_error_pa=0.)
        raw = replace(raw, liquid_states=tuple(states))
    raw = replace(raw, faces=(*raw.faces[:2], face, raw.faces[3]))
    first = replace(terminal.panel.first, evaluation=replace(terminal.panel.first.evaluation, source_evaluation=raw))
    # Direct saved-record validator adverse probe, not a fabricated actual trial.
    with pytest.raises(ValueError):
        check_source_terminal_liquid(replace(terminal.panel, first=first), seed.adapter.column)


@pytest.mark.parametrize('interior,donor', [(F(1,4), 'left'), (F(-1), 'right'), (F(), None)])
def test_affine_donor_sign_checks_extrapolated_upper_not_only_samples(actual_multicell, interior, donor):
    from sludge_sandbox.source_terminal_liquid import _check_affine_donors
    refinement, _ = actual_multicell
    raw = refinement.approach.proposal.original_trial.captures[0].evaluation.source_evaluation
    face = replace(raw.faces[2], liquid_mol_s=1.)
    later = replace(face, liquid_mol_s=float(interior), liquid_exchange=replace(face.liquid_exchange, donor=donor))
    # Pure manufactured scalar sign probe. In the first case both sample J>0,
    # but the affine endpoint at h=2 is negative.
    with pytest.raises(ValueError, match='affine_liquid_donor_change'):
        _check_affine_donors((face,), (later,), F(1), F(2))
