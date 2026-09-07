"""Mechanical-energy subtraction uncertainty must survive thermal inversion."""
from fractions import Fraction
import math

import pytest

from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.solid_fluid_storage import SolidFluidStorageError
from test_solid_fluid_storage import model
from test_rigid_storage import water, R


def inverse_inputs(water):
    storage = model(water)
    inventory = (0., {'fixture': .01}, {'fixture_solid': 2.})
    state = storage.evaluate_at_temperature(300., *inventory)
    return storage, state.internal_energy_j, inventory


def test_target_interval_is_contained_in_temperature_enclosure(water):
    storage, target, inventory = inverse_inputs(water)
    error = .001
    result = storage.temperature_from_energy(target, *inventory, (295., 310.),
        InversePolicy(.002, .0002, 100), target_energy_error_bound_j=error)
    # Independent fixed-composition, constant-Cv fixture: C=2*5+.01*(30-R).
    capacity = 10 + .01*(30-R)
    lo, hi = result.final_temperature_bracket_k
    assert lo <= 300-error/capacity <= 300+error/capacity <= hi
    assert result.target_energy_error_bound_j == error
    assert result.temperature_error_bound_k >= error/capacity


def test_target_uncertainty_cannot_be_silently_dropped_to_claim_precision(water):
    storage, target, inventory = inverse_inputs(water)
    with pytest.raises(SolidFluidStorageError, match='exceeds_inverse'):
        storage.temperature_from_energy(target, *inventory, (295., 310.),
            InversePolicy(1e-6, 1e-6, 100), target_energy_error_bound_j=.001)


def test_target_interval_must_fit_initial_certified_bracket(water):
    storage, target, inventory = inverse_inputs(water)
    with pytest.raises(SolidFluidStorageError, match='sign_uncertain'):
        storage.temperature_from_energy(target, *inventory, (299.99, 300.01),
            InversePolicy(1., 1., 100), target_energy_error_bound_j=1.)


def test_explicit_zero_matches_existing_scalar_target_path(water):
    storage, target, inventory = inverse_inputs(water)
    args = (target, *inventory, (295., 310.), InversePolicy(1e-6, 1e-6, 100))
    old = storage.temperature_from_energy(*args)
    zero = storage.temperature_from_energy(*args, target_energy_error_bound_j=0.)
    for name in ('target_energy_j', 'energy_residual_j', 'temperature_error_bound_k',
                 'final_temperature_bracket_k', 'iterations'):
        assert getattr(old, name) == getattr(zero, name)
    assert old.target_energy_error_bound_j == 0.


@pytest.mark.parametrize('error', [-1., Fraction(-1, 10**400), True, math.nan, math.inf, '1e-6'])
def test_invalid_target_bound_is_rejected(water, error):
    storage, target, inventory = inverse_inputs(water)
    with pytest.raises(SolidFluidStorageError):
        storage.temperature_from_energy(target, *inventory, (295., 310.),
            InversePolicy(1e-6, 1e-6, 100), target_energy_error_bound_j=error)


def test_nonrepresentable_positive_bound_is_rounded_outward_not_to_zero(water):
    storage, target, inventory = inverse_inputs(water)
    supplied = Fraction(1, 10**400)
    result = storage.temperature_from_energy(target, *inventory, (295., 310.),
        InversePolicy(1e-6, 1e-6, 100), target_energy_error_bound_j=supplied)
    assert Fraction(result.target_energy_error_bound_j) >= supplied
    assert result.target_energy_error_bound_j == math.nextafter(0., math.inf)
