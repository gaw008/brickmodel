"""Explicit water/enthalpy exchange with a controlled isothermal vapor reservoir."""
from dataclasses import replace
from fractions import Fraction as F

import pytest

from test_low_moisture_column import setup
from sludge_sandbox.controlled_vapor_column import ControlledVaporColumn, VaporBoundaryControl
from sludge_sandbox.source_wet_column import integrate_source_column


def boundary(base,pv=0.,coefficient=1e-9):
    return ControlledVaporColumn(base,VaporBoundaryControl(pv,coefficient,330.,0.,
        ('virtual:controlled_vapor_contact_and_heater',)))


def test_open_boundary_removes_water_with_the_same_shared_enthalpy(monkeypatch):
    base,initial=setup(monkeypatch,(.04,.04))
    column=boundary(base)
    run=integrate_source_column(column,initial,duration_s=1/128,steps=2)
    assert run.status=='completed',run.reason
    for old,new,ledger in zip(run.states,run.states[1:],run.ledgers):
        outer=ledger.faces[-1]
        assert outer.gas_mol[2]>0
        water=lambda row:sum((F(s.liquid_water_mol)+F(s.gas_amounts_mol[2]) for s in row),F())
        assert water(new)-water(old)==-outer.gas_mol[2]+sum(ledger.roundoff.liquid_mol)+sum(r[2] for r in ledger.roundoff.gas_mol)
        assert sum(F(n.internal_energy_j)-F(o.internal_energy_j) for o,n in zip(old,new))==(
            -outer.energy_j+sum(ledger.roundoff.energy_j))
        assert ledger.boundary.vapor_entropy_state=='positive_infinite_vacuum_limit'
        assert ledger.boundary.vapor_entropy_w_k is None


def test_humid_reservoir_adds_vapor_and_can_rewet_exact_dry_inventory(monkeypatch):
    base,initial=setup(monkeypatch,(0.,0.))
    column=boundary(base,1000.)
    run=integrate_source_column(column,initial,duration_s=1/128,steps=2)
    assert run.status=='completed',run.reason
    assert run.states[-1][-1].liquid_water_mol>0
    assert all(l.faces[-1].gas_mol[2]<0 and l.boundary.vapor_entropy_w_k>=0 for l in run.ledgers)


def test_separate_heat_bath_counts_once_and_has_nonnegative_entropy(monkeypatch):
    base,states=setup(monkeypatch,(.04,.04))
    column=ControlledVaporColumn(base,VaporBoundaryControl(0.,0.,350.,.001,('virtual:heater',)))
    rates=column.evaluate(states)
    assert rates.boundary.heat_into_cell_w>0
    assert rates.boundary.heat_entropy_w_k>0
    assert rates.faces[-1].energy_w==-rates.boundary.heat_into_cell_w
    assert rates.faces[-1].gas_mol_s==(0.,0.,0.)


def test_control_inputs_and_content_changes_are_refused(monkeypatch):
    base,states=setup(monkeypatch)
    with pytest.raises(ValueError):
        VaporBoundaryControl(-1.,1e-9,330.,0.,('virtual:bad',))
    column=boundary(base)
    object.__setattr__(column.control,'vapor_pressure_pa',100.)
    with pytest.raises(ValueError,match='changed'):
        column.evaluate(states)
