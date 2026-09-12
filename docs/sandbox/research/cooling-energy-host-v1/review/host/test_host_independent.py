"""Independent algebraic host checks; no integrator or trajectory is invoked."""
from dataclasses import replace
from unittest.mock import patch

import numpy as np
import pytest

from sludge_sandbox.cooling_thermoelastic_plate import CoolingThermoelasticPlate
from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.integration import ConservedState, DomainExit, IntegrationError, _updated
from thermoelastic_energy_host import ThermoelasticEnergyHost
from thermoelastic_energy_storage import EnergyInversePolicy, ThermoelasticEnergyStorage


def make_host(*, plate_changes=None, inventory=None, policy_changes=None):
    plate = CoolingThermoelasticPlate(
        reference=ReferenceSlab(.02, .01, 2), biaxial_modulus_pa=1e9,
        linear_expansion_per_k=1e-4, stress_free_heat_capacity_j_m3_k=1e5,
        reference_temperature_k=300., conductivity_w_m_k=1.,
        temperature_bounds_k=(290., 310.), strain_bounds=(-.01, .01),
        outer_temperature_k=300., outer_boundary='fixed_temperature',
        coefficient_classification='manufactured', mechanical_regime='symmetric_free_plane_stress',
    )
    policy = EnergyInversePolicy(1e-10, 1e-9, 200, 160)
    return ThermoelasticEnergyHost(
        storage=ThermoelasticEnergyStorage(replace(plate, **(plate_changes or {}))),
        fixed_amounts_mol=[[0., 2.], [3., 0.]] if inventory is None else inventory,
        inverse_policy=replace(policy, **(policy_changes or {})),
    )


@pytest.mark.parametrize('change', [
    {'biaxial_modulus_pa': 2e9},
    {'linear_expansion_per_k': -1e-4},
    {'stress_free_heat_capacity_j_m3_k': 2e5},
    {'reference_temperature_k': 301.},
    {'reference': ReferenceSlab(.03, .01, 2)},
    {'reference': ReferenceSlab(.02, .02, 2)},
    {'temperature_bounds_k': (291., 310.)},
    {'strain_bounds': (-.02, .02)},
])
def test_independent_constitutive_or_geometry_change_rejects_old_energy(change):
    original = make_host()
    state, _ = original.state_from_temperatures((304., 301.))
    other = make_host(plate_changes=change)
    with pytest.raises(IntegrationError, match='identity'):
        other.evaluate(state, 0.)


def test_independent_heat_program_reuse_does_not_reinterpret_energy():
    original = make_host()
    state, _ = original.state_from_temperatures((304., 301.))
    other = make_host(plate_changes={'outer_temperature_k': 299., 'conductivity_w_m_k': 2.})
    assert other.energy_model_identity == original.energy_model_identity
    before = original.evaluate(state, 0.)
    after = other.evaluate(state, 0.)
    assert after.inverse.state.cell_energy_j == before.inverse.state.cell_energy_j
    assert after.rates.face_energy_w[-1] != before.rates.face_energy_w[-1]


def test_independent_inventory_lock_sees_one_bit_and_one_column_changes():
    model = make_host()
    state, _ = model.state_from_temperatures((304., 301.))
    for changed in (np.array([[0., np.nextafter(2., 3.)], [3., 0.]]),
                    np.array([[0., 2., 0.], [3., 0., 0.]])):
        invalid = ConservedState(changed, state.internal_energy_j, state.energy_model_identity)
        with pytest.raises(IntegrationError, match='fixed_inventory_changed'):
            model.evaluate(invalid, 0.)
    with pytest.raises(ValueError):
        state.amounts_mol.setflags(write=True)
    with pytest.raises(ValueError):
        state.internal_energy_j.setflags(write=True)


def test_independent_zero_species_update_preserves_native_inventory_bytes():
    model = make_host(inventory=[[0., np.nextafter(0., 1.)], [3., 0.]])
    state, _ = model.state_from_temperatures((304., 301.))
    evaluated = model.evaluate(state, 0.)
    dn, _ = evaluated.rates.derivatives(state)
    # Directly verify the native algebraic inventory update without a time step.
    updated = _updated(state.amounts_mol, dn, 1e-12, 'amount')
    assert updated.tobytes() == state.amounts_mol.tobytes() == model.fixed_amounts_mol.tobytes()


def test_independent_actual_stage_reused_and_extensive_power_is_correct():
    model = make_host()
    state, _ = model.state_from_temperatures((304., 301.))
    actual = CoolingThermoelasticPlate.evaluate
    seen = []
    def record(self, temperatures):
        result = actual(self, temperatures)
        seen.append(result)
        return result
    with patch.object(CoolingThermoelasticPlate, 'evaluate', record):
        evaluated = model.evaluate(state, 0.)
    assert len(seen) == 1
    assert evaluated.inverse.state.plate_evaluation is seen[0]
    plate = seen[0]
    np.testing.assert_array_equal(evaluated.rates.face_energy_w, plate.face_heat_outward_w)
    expected_power = np.array([2. * volume * point.stress_pa * plate.in_plane_strain_rate_per_s
                               for volume, point in zip(plate.reference_cell_volumes_m3, plate.points)])
    np.testing.assert_array_equal(evaluated.rates.cell_power_w, expected_power)
    _, du = evaluated.rates.derivatives(state)
    np.testing.assert_allclose(du, np.asarray(plate.cell_heat_in_w) + expected_power, rtol=0., atol=1e-14)
    assert tuple(evaluated.rates.cell_power_components_w) == ('mechanical_constraint',)
    assert state.mechanical_stretches is evaluated.rates.mechanical_rates_per_s is None


def test_independent_real_domain_and_iteration_errors_remain_distinct():
    model = make_host()
    state, _ = model.state_from_temperatures((304., 301.))
    outside = ConservedState(state.amounts_mol, [1e9, -1e9], state.energy_model_identity)
    with pytest.raises(DomainExit):
        model.evaluate(outside, 0.)
    limited = make_host(policy_changes={'maximum_iterations': 1})
    with pytest.raises(IntegrationError, match='iteration_limit'):
        limited.evaluate(state, 0.)
    with pytest.raises(IntegrationError):
        model.state_from_temperatures((304.,))
    with pytest.raises(DomainExit):
        model.state_from_temperatures((311., 301.))


def test_independent_foreign_same_shape_inventory_changes_identity():
    original = make_host()
    foreign = make_host(inventory=[[0., 2.], [4., 0.]])
    assert original.energy_model_identity != foreign.energy_model_identity
    state, _ = original.state_from_temperatures((304., 301.))
    with pytest.raises(IntegrationError, match='identity'):
        foreign.evaluate(state, 0.)
