"""Algebraic native-interface tests, without executing a time trajectory."""
from dataclasses import replace

import numpy as np
import pytest

from sludge_sandbox.cooling_thermoelastic_plate import CoolingThermoelasticPlate
from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.integration import ConservedState, DomainExit, IntegrationError
from sludge_sandbox.thermoelastic_energy_host import ThermoelasticEnergyHost, ThermoelasticEnergyHostError
from sludge_sandbox.thermoelastic_energy_storage import (
    EnergyDomainError, EnergyInversePolicy, EnergyStorageError, ThermoelasticEnergyStorage,
)


def plate():
    return CoolingThermoelasticPlate(
        reference=ReferenceSlab(.02, .01, 2), biaxial_modulus_pa=1e9,
        linear_expansion_per_k=1e-4, stress_free_heat_capacity_j_m3_k=1e5,
        reference_temperature_k=300., conductivity_w_m_k=1.,
        temperature_bounds_k=(290., 310.), strain_bounds=(-.01, .01),
        outer_temperature_k=300., outer_boundary='fixed_temperature',
        coefficient_classification='manufactured',
        mechanical_regime='symmetric_free_plane_stress')


def host(**changes):
    # These explicit test inventory entries only exercise immutable bookkeeping.
    # They neither determine the volumetric heat capacity nor identify a material.
    options = dict(storage=ThermoelasticEnergyStorage(plate()),
                   fixed_amounts_mol=np.array([[2.], [3.]]),
                   inverse_policy=EnergyInversePolicy(energy_tolerance_j=1e-10,
                       temperature_tolerance_k=1e-9, maximum_iterations=200, square_root_bits=160))
    return ThermoelasticEnergyHost(**{**options, **changes})


def test_extensive_energy_and_native_work_are_the_same_stage():
    model = host()
    state, certificate = model.state_from_temperatures((304., 301.))
    result = model.evaluate(state, 0.)
    np.testing.assert_allclose(result.inverse.state.temperatures_k, (304., 301.), atol=1e-9, rtol=0)
    assert state.mechanical_stretches is None
    assert state.energy_model_identity == model.energy_model_identity
    np.testing.assert_array_equal(state.internal_energy_j, certificate.cell_energy_j)
    dn, du = result.rates.derivatives(state)
    evaluated = result.inverse.state.plate_evaluation
    np.testing.assert_array_equal(dn, np.zeros((2, 1)))
    np.testing.assert_allclose(du, np.array(evaluated.cell_u_rates_j_m3_s)*.0001, atol=1e-11, rtol=1e-12)
    assert np.any(result.rates.cell_power_w != 0.)
    np.testing.assert_array_equal(result.rates.cell_power_w,
                                  result.rates.cell_power_components_w['mechanical_constraint'])
    assert result.material_qualified is result.full_cycle_qualified is result.chemical_mass_qualified is False


def test_host_reuses_single_final_plate_evaluation(monkeypatch):
    model = host()
    state, _ = model.state_from_temperatures((304., 301.))
    original = CoolingThermoelasticPlate.evaluate
    calls = []
    def counted(self, temperatures):
        calls.append(temperatures)
        return original(self, temperatures)
    monkeypatch.setattr(CoolingThermoelasticPlate, 'evaluate', counted)
    model.evaluate(state, .1)
    assert len(calls) == 1


def test_inventory_is_an_immutable_snapshot_and_cannot_change():
    inventory = np.array([[2.], [3.]])
    model = host(fixed_amounts_mol=inventory)
    inventory[0, 0] = 10.
    assert model.fixed_amounts_mol[0, 0] == 2.
    with pytest.raises(ValueError):
        model.fixed_amounts_mol.flags.writeable = True
    state, _ = model.state_from_temperatures((304., 301.))
    changed = ConservedState([[2.001], [3.]], state.internal_energy_j,
                             energy_model_identity=state.energy_model_identity)
    with pytest.raises(ThermoelasticEnergyHostError, match='inventory_changed'):
        model.evaluate(changed, 0.)


def test_energy_law_is_bound_but_boundary_and_tolerance_do_not_change_u_identity():
    model = host()
    state, _ = model.state_from_temperatures((304., 301.))
    changed_law = host(storage=ThermoelasticEnergyStorage(replace(plate(), linear_expansion_per_k=0.)))
    with pytest.raises(ThermoelasticEnergyHostError, match='identity'):
        changed_law.evaluate(state, 0.)
    insulated = host(storage=ThermoelasticEnergyStorage(replace(plate(), outer_boundary='adiabatic')),
                     inverse_policy=replace(model.inverse_policy, temperature_tolerance_k=2e-9))
    assert insulated.energy_model_identity == model.energy_model_identity
    assert insulated.evaluate(state, 0.).rates.face_energy_w[-1] == 0.


@pytest.mark.parametrize('kind', ['untagged', 'mechanical'])
def test_incompatible_native_state_rejected(kind):
    model = host()
    state, _ = model.state_from_temperatures((304., 301.))
    changed = ConservedState(state.amounts_mol, state.internal_energy_j,
                             energy_model_identity=None if kind == 'untagged' else state.energy_model_identity,
                             mechanical_stretches=np.ones(3) if kind == 'mechanical' else None)
    with pytest.raises(ThermoelasticEnergyHostError):
        model.evaluate(changed, 0.)


@pytest.mark.parametrize('error', [EnergyDomainError, EnergyStorageError])
def test_proven_domain_exit_and_numerical_failure_remain_distinct(monkeypatch, error):
    model = host()
    state, _ = model.state_from_temperatures((304., 301.))
    def fail(*args, **kwargs):
        raise error('manufactured_test_failure')
    monkeypatch.setattr(ThermoelasticEnergyStorage, 'inverse', fail)
    expected = DomainExit if error is EnergyDomainError else ThermoelasticEnergyHostError
    with pytest.raises(expected, match='manufactured_test_failure'):
        model.evaluate(state, 0.)


@pytest.mark.parametrize('inventory', [np.empty((2, 0)), [[True], [2.]], [[-1.], [2.]], [[1.]], [[float('nan')], [2.]], [[-0.], [2.]]])
def test_explicit_valid_nonempty_inventory_is_required(inventory):
    with pytest.raises(IntegrationError):
        host(fixed_amounts_mol=inventory)


@pytest.mark.parametrize('time', [True, float('nan'), float('inf'), '0'])
def test_invalid_time_rejected_before_decoding(time):
    model = host()
    state, _ = model.state_from_temperatures((304., 301.))
    with pytest.raises(ThermoelasticEnergyHostError, match='finite_time'):
        model.evaluate(state, time)
