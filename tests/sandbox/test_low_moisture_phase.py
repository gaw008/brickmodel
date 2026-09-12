"""Reversible sorption at zero/positive inventory with a manufactured fluid seam."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from test_low_moisture_storage import setup
from sludge_sandbox.low_moisture_phase import evaluate_low_moisture_phase


def test_zero_condensed_inventory_can_rewet_without_an_extra_pool(monkeypatch):
    storage, _, gas = setup(monkeypatch)
    point = storage.evaluate(storage.state(0.,gas,0.),330.)
    phase = evaluate_low_moisture_phase(storage,storage.wet._chemical,point,gas[2],1e-9)
    assert phase.phase_water_mol_s == float(-F(1e-9)*F(phase.water_partial_pressure_pa)) < 0
    assert phase.equilibrium.equilibrium_partial_pressure_pa == 0
    assert phase.chemical_driving_force_j_mol is None
    assert phase.chemical_drive_state == 'minus_infinity_at_zero_inventory'
    assert phase.entropy_production_w_k is None
    assert phase.entropy_state == 'positive_infinite_boundary_limit'
    assert phase.equilibrium.liquid_reference_scope == 'hypothetical_standard_state_at_zero_inventory'
    assert not phase.material_qualified


def test_both_zero_and_disabled_path_have_no_exchange(monkeypatch):
    storage, _, gas = setup(monkeypatch)
    drygas=(*gas[:2],0.)
    point=storage.evaluate(storage.state(0.,drygas,0.),330.)
    phase=evaluate_low_moisture_phase(storage,storage.wet._chemical,point,0.,1e-9)
    assert phase.phase_water_mol_s == 0 and phase.entropy_production_w_k == 0
    assert phase.entropy_state == 'no_exchange'
    assert phase.chemical_driving_force_j_mol is None
    point=storage.evaluate(storage.state(0.,gas,0.),330.)
    phase=evaluate_low_moisture_phase(storage,storage.wet._chemical,point,gas[2],0.)
    assert phase.phase_water_mol_s == 0 and phase.entropy_state == 'no_exchange'


def test_positive_water_uses_full_mu_and_desorption_enthalpy(monkeypatch):
    storage, _, gas = setup(monkeypatch)
    point=storage.evaluate(storage.state(.04,gas,0.),330.)
    phase=evaluate_low_moisture_phase(storage,storage.wet._chemical,point,gas[2],1e-9)
    eq=phase.equilibrium
    assert phase.phase_water_mol_s > 0
    assert phase.entropy_production_w_k > 0 and phase.entropy_state == 'finite'
    assert eq.equilibrium_partial_pressure_pa == float(F(eq.pure_equilibrium.equilibrium_partial_pressure_pa)*F(point.excess.activity))
    assert eq.phase_enthalpy_difference_j_mol == float(F(eq.pure_equilibrium.phase_enthalpy_difference_j_mol)-F(point.excess.partial_h_ex_j_mol))
    assert abs(eq.chemical_potential_residual_j_mol) <= 1e-7


def test_source_or_inventory_mismatch_is_rejected(monkeypatch):
    storage, _, gas = setup(monkeypatch)
    point=storage.evaluate(storage.state(.04,gas,0.),330.)
    with pytest.raises(ValueError,match='inventory'):
        evaluate_low_moisture_phase(storage,storage.wet._chemical,point,gas[2]+.01,1e-9)
    bad=replace(point,excess=replace(point.excess,partial_h_ex_j_mol=point.excess.partial_h_ex_j_mol+1))
    with pytest.raises(ValueError,match='low_sorption_point'):
        evaluate_low_moisture_phase(storage,storage.wet._chemical,bad,gas[2],1e-9)
