"""Low-W energy continuity in actual storage classes with manufactured fluid callbacks."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from test_arlabosse_sorption_column import setup as source_setup
from sludge_sandbox.arlabosse_low_moisture import ArlabosseLowMoisture
from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage
from sludge_sandbox.phase_storage import InversePolicy


def setup(monkeypatch):
    column, states = source_setup(monkeypatch)
    old = column.storages[0]
    low = ArlabosseLowMoisture(old.wet)
    storage = LowMoistureSorptionStorage(old.base,old.wet,old.pressure_domain_pa,excess=low)
    return storage, old, states[0].gas_amounts_mol


@pytest.mark.parametrize('nc',[0., .01, .04, .1, .2])
def test_complete_energy_inverse_through_low_water_and_exact_dry_limit(monkeypatch,nc):
    storage, old, gas = setup(monkeypatch)
    state = storage.state(nc,gas,0.)
    p = storage.evaluate(state,330.)
    base = old.base.evaluate(old.base.state(nc,gas,0.),330.)
    w = F(nc)*F(storage.wet._mass)/F(storage.dry_mass_kg)
    ex = storage.excess.evaluate(330.,w)
    assert p.excess_internal_energy_j == F(storage.dry_mass_kg)*ex.h_ex_j_kg_dry
    assert p.excess_helmholtz_energy_j == p.excess_internal_energy_j-F(330)*p.excess_entropy_j_k
    residual = F(p.total_internal_energy_j)-F(base.total_internal_energy_j)-p.excess_internal_energy_j
    assert abs(residual) <= F(p.energy_error_j)
    assert p.closed_heat_capacity_j_k == base.closed_heat_capacity_j_k
    target = replace(state,internal_energy_j=p.total_internal_energy_j)
    inv = storage.invert(target,InversePolicy(1e-6,1e-6,100))
    assert abs(inv.energy_residual_j)+F(inv.point.energy_error_j) <= F(1e-6)
    assert abs(inv.point.temperature_k-330.) <= inv.temperature_error_bound_k <= 1e-6
    assert inv.point.fluid.mechanical.liquid_inventory_mol == nc
    assert not p.material_qualified and not p.training_eligible
    if nc == 0:
        assert p.excess.mu_ex_j_mol is None and p.excess.activity == 0
        assert p.excess_internal_energy_j != 0
        assert p.gas_volume_m3 == p.available_pore_volume_m3


def test_near_dry_energy_does_not_drop_its_reference_offset(monkeypatch):
    storage, _, gas = setup(monkeypatch)
    dry = storage.evaluate(storage.state(0.,gas,0.),330.)
    nearby = storage.evaluate(storage.state(1e-10,gas,0.),330.)
    assert abs(nearby.total_internal_energy_j-dry.total_internal_energy_j) < 1e-4
    assert dry.excess_internal_energy_j == F(storage.dry_mass_kg)*storage.excess.evaluate(330.,F()).h_ex_j_kg_dry
    assert dry.excess.mu_ex_j_mol is None


def test_new_energy_identity_and_old_model_domain_are_preserved(monkeypatch):
    storage, old, gas = setup(monkeypatch)
    old_state = old.state(.2,gas,0.)
    with pytest.raises(ValueError,match='identity'):
        storage.evaluate(old_state,330.)
    new_state = storage.state(.2,gas,0.)
    with pytest.raises(ValueError,match='identity'):
        old.evaluate(new_state,330.)
    with pytest.raises(ValueError,match='moisture_domain'):
        old.state(0.,gas,0.)
    assert old.model_identity != storage.model_identity


def test_no_unaccounted_energy_source_when_redistributing_the_same_water(monkeypatch):
    storage, _, gas = setup(monkeypatch)
    state = storage.state(.04,gas,0.)
    state = replace(state,internal_energy_j=storage.evaluate(state,330.).total_internal_energy_j)
    shifted = replace(state,liquid_water_mol=.0399,
        gas_amounts_mol=(*gas[:2],gas[2]+.0001))
    inv = storage.invert(shifted,InversePolicy(1e-6,1e-6,100))
    assert inv.point.temperature_k < 330.
    assert inv.target_energy_j == state.internal_energy_j
