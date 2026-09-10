"""Fixed kg solids stay model parameters; only fluid amounts occupy mol slots."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest

from test_source_liquid_column import setup
from test_programmed_source_wet_column import setup as furnace_setup
from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.integration import ConservedState, IntegrationPolicy
from sludge_sandbox.integration import DomainExit
from sludge_sandbox.exact_integration import integrate_exact


@pytest.mark.parametrize('count', [1, 3, 4])
def test_fixed_kg_and_fluid_mol_roundtrip(monkeypatch, count):
    model, initial = setup(monkeypatch, count=count)
    host = ExactSourceColumn(model)
    packed = host.pack(initial)
    assert packed.amounts_mol.shape == (count, 4)
    assert host.species_ids == ('liquid_water', 'O2', 'N2', 'H2O')
    assert host.liquid_index == 0 and host.vapor_index == 3
    assert host.unpack(packed) == initial
    assert packed.energy_model_identity == host.energy_model_identity
    assert not host.provenance()['material_qualified']
    for i, state in enumerate(initial):
        assert tuple(packed.amounts_mol[i]) == (state.liquid_water_mol, *state.gas_amounts_mol)
        assert packed.internal_energy_j[i] == state.internal_energy_j
        assert host.provenance()['fixed_dry_mass_kg'][i] == state.solid_mass_kg[0]


def test_single_evaluation_and_shared_face_mapping(monkeypatch):
    model, initial = setup(monkeypatch)
    host = ExactSourceColumn(model)
    from sludge_sandbox.source_wet_column import SourceWetColumn
    original = SourceWetColumn.evaluate
    calls = []
    def observed(self, states):
        calls.append(states)
        return original(self, states)
    monkeypatch.setattr(SourceWetColumn, 'evaluate', observed)
    packed = host.pack(initial)
    out = host.evaluate(packed, T(F()))
    assert calls == [initial]
    rates = out.rates
    for i, face in enumerate(out.source_evaluation.faces):
        assert tuple(rates.face_species_mol_s[i]) == (getattr(face, 'liquid_mol_s', 0.), *face.gas_mol_s)
        assert rates.face_energy_w[i] == face.energy_w
    for i, cell in enumerate(out.source_evaluation.cells):
        phase = cell.phase.phase_water_mol_s
        assert tuple(rates.reaction_species_mol_s[i]) == (-phase, 0., 0., phase)
    assert np.all(rates.cell_power_w == 0) and rates.mechanical_rates_per_s is None
    rates.derivatives(packed)


def test_foreign_binding_layout_mechanics_and_time_rejected_before_evaluation(monkeypatch):
    model, initial = setup(monkeypatch)
    host = ExactSourceColumn(model)
    state = host.pack(initial)
    from sludge_sandbox.source_wet_column import SourceWetColumn
    monkeypatch.setattr(SourceWetColumn, 'evaluate', lambda *a, **k: pytest.fail('invalid input reached physics'))
    for invalid in (replace(state, energy_model_identity=None),
                    replace(state, energy_model_identity=('foreign',)),
                    replace(state, amounts_mol=state.amounts_mol[:, :3]),
                    replace(state, mechanical_stretches=np.ones(4))):
        with pytest.raises(ValueError): host.evaluate(invalid, T(F()))
    with pytest.raises(ValueError): host.evaluate(state, 0.)
    object.__setattr__(model, 'transfer_coefficients_mol_s_pa', (2e-9,)*3)
    with pytest.raises(ValueError): host.unpack(state)


@pytest.mark.parametrize('change', [{'chemical_reference_power_w': F(1)},
                                  {'phase_transfer_included': True},
                                  {'solid_kg_s': ()}, {'gas_mol_s': (F(),)}])
def test_disabled_chemistry_contract_is_not_silently_discarded(monkeypatch, change):
    model, initial = setup(monkeypatch, count=1)
    host = ExactSourceColumn(model)
    from sludge_sandbox.source_wet_column import SourceWetColumn
    original = SourceWetColumn.evaluate
    def altered(self, states):
        out = original(self, states)
        cell = replace(out.cells[0], chemistry=replace(out.cells[0].chemistry, **change))
        return replace(out, cells=(cell,))
    monkeypatch.setattr(SourceWetColumn, 'evaluate', altered)
    with pytest.raises(ValueError, match='cannot_hide_active_chemistry'):
        host.evaluate(host.pack(initial), T(F()))


def test_exact_dry_mode_keeps_energy_identity_and_refuses_active_dry_liquid_face(monkeypatch):
    model, initial = setup(monkeypatch)
    dry = replace(initial[1], liquid_water_mol=0., gas_amounts_mol=(.25, .25, 0.))
    dry = replace(dry, internal_energy_j=model.storages[1].evaluate(dry, 327.).total_internal_energy_j)
    host = ExactSourceColumn(model)
    state = host.pack((initial[0], dry, initial[2]))
    with pytest.raises(ValueError): host.with_depleted_cells(host.pack(initial), (1,))
    switched = host.with_depleted_cells(state, (1,))
    assert switched.energy_model_identity == host.energy_model_identity
    assert switched.operator_identity != host.operator_identity
    assert switched.unpack(state)[1].liquid_water_mol == 0.
    with pytest.raises(ValueError): switched.evaluate(state, T(F()))
    disabled = ExactSourceColumn(replace(switched.column, liquid_transport=None))
    assert disabled.evaluate(state, T(F())).source_evaluation.cells[1].phase.phase_water_mol_s == 0.


def test_program_time_and_breakpoints_are_exact(monkeypatch):
    origin = F(10**18)
    model, initial = furnace_setup(monkeypatch, count=1, knots=(0., .005, .015625), translation=origin)
    host = ExactSourceColumn(model)
    start, end = T(origin), T(origin+F(1, 64))
    assert host.breakpoints(start, end) == (T(origin+F(.005)),)
    at = T(origin+F(1, 256))
    out = host.evaluate(host.pack(initial), at)
    assert out.time == at and out.source_evaluation.boundary.time == at
    assert out.rates.face_species_mol_s[-1, 0] == 0.
    assert out.rates.face_energy_w[-1] == out.source_evaluation.faces[-1].energy_w


def test_actual_source_column_runs_through_existing_exact_integrator(monkeypatch):
    model, initial = setup(monkeypatch)
    host = ExactSourceColumn(model)
    packed = host.pack(initial)
    policy = IntegrationPolicy(1/128, 1/128, 1/4096, 1e-8, 1e-7, 1e-3, 1., 1e5, 8, 8, 35.)
    run = integrate_exact(packed, host, start_s=T(F()), end_s=T(F(1, 128)), policy=policy)
    assert run.status == 'completed', run.reason
    assert run.times_s[-1] == T(F(1, 128)) and len(run.steps) > 0
    final = host.unpack(run.states[-1])
    assert tuple(s.solid_mass_kg for s in final) == tuple(s.solid_mass_kg for s in initial)
    assert any(a.liquid_water_mol != b.liquid_water_mol for a, b in zip(final, initial))
    assert all(s.energy_model_identity == host.energy_model_identity for s in run.states)
    initial_water = sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in initial)
    final_water = sum(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in final)
    assert abs(final_water-initial_water) < F(1e-14)
    assert abs(sum(F(s.internal_energy_j) for s in final)-sum(F(s.internal_energy_j) for s in initial)) < F(1e-8)


@pytest.mark.parametrize(('error', 'status'), [(ValueError('source_failure'), 'numerical_failure'),
                                            (DomainExit('physical_domain'), 'domain_exit')])
def test_callback_failures_keep_structured_initial_prefix(monkeypatch, error, status):
    model, initial = setup(monkeypatch, count=1)
    host = ExactSourceColumn(model)
    packed = host.pack(initial)
    from sludge_sandbox.source_wet_column import SourceWetColumn
    def fail(*args): raise error
    monkeypatch.setattr(SourceWetColumn, 'evaluate', fail)
    policy = IntegrationPolicy(1/128, 1/128, 1/4096, 1e-8, 1e-7, 1e-3, 1., 1e5, 8, 8, 35.)
    run = integrate_exact(packed, host, start_s=T(F()), end_s=T(F(1, 128)), policy=policy)
    assert run.status == status and str(error) in run.reason
    assert run.states == (packed,) and run.times_s == (T(F()),) and not run.steps
