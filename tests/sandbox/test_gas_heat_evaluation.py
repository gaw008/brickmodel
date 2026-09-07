"""The work host must reuse the gas state actually used by transport."""
from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from sludge_sandbox.gas_heat_model import GasHeatModel
from sludge_sandbox.integration import DomainExit
from test_gas_heat_model import model


def test_evaluation_decodes_once_and_reports_actual_transport_pressure(monkeypatch):
    operator = model()
    state = operator.state_from_temperatures([[.8, .2], [.3, 1.2]], [600., 900.])
    original = GasHeatModel.temperatures_k
    calls = []

    def counted(self, incoming):
        calls.append(incoming)
        return original(self, incoming)

    monkeypatch.setattr(GasHeatModel, 'temperatures_k', counted)
    evaluation = operator.evaluate(state, 0.)
    assert calls == [state]
    assert evaluation.temperatures_k == pytest.approx((600., 900.))
    assert tuple(g.pressure_pa for g in evaluation.gas_states) == pytest.approx((4800., 10800.))
    assert evaluation.source_ids == operator.source_ids
    assert evaluation.rates.face_energy_w[1] != 0
    assert isinstance(evaluation.gas_states, tuple)
    with pytest.raises(FrozenInstanceError):
        evaluation.temperatures_k = (1., 2.)


def test_callable_preserves_all_evaluated_rates():
    operator = model()
    state = operator.state_from_temperatures([[.8, .2], [.3, 1.2]], [600., 900.])
    observation = operator.evaluate(state, .25)
    rates = operator(state, .25)
    for name in ('face_species_mol_s', 'face_energy_w', 'reaction_species_mol_s', 'cell_power_w'):
        np.testing.assert_array_equal(getattr(rates, name), getattr(observation.rates, name))


def test_evaluation_retains_property_domain_exit():
    from sludge_sandbox.integration import ConservedState
    operator = model()
    state = ConservedState([[1., 0.], [1., 0.]], [-1e20, -1e20])
    with pytest.raises(DomainExit):
        operator.evaluate(state, 0.)


def test_evaluation_matches_frozen_pre_extraction_operator_with_all_mechanisms(monkeypatch):
    """Golden values came from HEAD's old __call__, not the new evaluate path.

    Old complete source SHA256:
    6019ac11662e8cb79ce75d0ed786c753cfe419904f74901eee750e45737cdbd9.
    The reviewer compiled its unchanged AST method against the unchanged helpers.
    """
    from sludge_sandbox.gas_transport import ideal_gas_reservoir
    from test_gas_heat_model import caloric, gas_reaction

    thermo = caloric()
    reservoir = ideal_gas_reservoir(
        pressure_pa=15000, temperature_k=1100,
        mole_fractions={'A': .7, 'B': .3},
        molar_masses_kg_mol={'A': .012, 'B': .012}, gas_constant_j_mol_k=8,
    )
    operator = model(
        thermochemistry=thermo, reaction_network=gas_reaction(thermo),
        outer_reservoir=reservoir,
        outer_reservoir_source_ids=('manufactured:outer-gas-review',),
        outer_surface_temperature_k=lambda t: 800 + 100*t,
        outer_heat_source_ids=('manufactured:outer-heat-review',),
    )
    state = operator.state_from_temperatures([[.8, .2], [.3, 1.2]], [600, 900])
    face_inputs = []
    original_face = GasHeatModel._face

    def capture(self, left, right, *indices):
        face_inputs.append((left, right))
        return original_face(self, left, right, *indices)

    monkeypatch.setattr(GasHeatModel, '_face', capture)
    evaluation = operator.evaluate(state, .25)
    expected = {
        'face_species_mol_s': [[0., 0.], [.062399999999999706, -.14040000000000596],
                               [-.2706818181818279, .12749999999999584]],
        'face_energy_w': [0., -1567.9290000000951, -3421.810227273126],
        'reaction_species_mol_s': [[-.16000000000000003, .16000000000000003], [-.06, .06]],
        'cell_power_w': [0., 0.],
    }
    for name, values in expected.items():
        np.testing.assert_array_equal(getattr(evaluation.rates, name), values)
    assert face_inputs[0][0] is evaluation.gas_states[0]
    assert face_inputs[0][1] is evaluation.gas_states[1]
    assert face_inputs[1][0] is evaluation.gas_states[1]
    assert face_inputs[1][1] is reservoir
    assert evaluation.source_ids == (
        'manufactured:gas-heat-integration-v1',
        'manufactured:outer-gas-review', 'manufactured:outer-heat-review',
    )
