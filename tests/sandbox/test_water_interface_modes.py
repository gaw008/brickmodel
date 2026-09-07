from dataclasses import replace,FrozenInstanceError
import numpy as np
import pytest

from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer,WaterPhaseTransferError
from sludge_sandbox.integration import DomainExit,Rates,IntegrationPolicy,integrate
from test_water_phase_transfer import ingredients,transfer
from test_joined_water_host import joined,host


def dry_transfer(ingredients,**kw):
    return transfer(ingredients,interface_modes=('depleted_no_nucleation',),**kw)


def test_default_wet_and_explicit_zero_inventory_switch(ingredients):
    wet=transfer(ingredients)
    assert wet.interfaces==('existing_liquid',)
    assert wet.liquid_index==0 and wet.water_vapor_index==2
    initial=wet.base_model.state_from_temperatures([[2.,.01,1e-5]],[300.])
    assert wet.evaluate(initial,0).cell_transfers[0].rate_mol_s>0
    with pytest.raises(WaterPhaseTransferError):wet.with_depleted_cells(initial,(0,))
    empty=wet.base_model.state_from_temperatures([[0.,.01,1e-5]],[300.])
    with pytest.raises(DomainExit):wet.evaluate(empty,0)
    dry=wet.with_depleted_cells(empty,(0,))
    assert wet.interfaces==('existing_liquid',)
    assert dry.interfaces==('depleted_no_nucleation',)
    assert dry.coefficients_mol_s_pa==wet.coefficients_mol_s_pa
    assert dry.source_ids==wet.source_ids
    result=dry.evaluate(empty,0)
    assert result.cell_transfers[0].rate_mol_s==0
    assert result.cell_transfers[0].equilibrium is None
    assert result.cell_transfers[0].hypothetical_equilibrium is not None
    assert result.interface_modes==dry.interfaces


def test_supersaturated_dry_strict_and_explicit_metastability(ingredients):
    dry=dry_transfer(ingredients)
    initial=dry.base_model.state_from_temperatures([[0.,.01,.001]],[300.])
    with pytest.raises(DomainExit,match='condensation'):dry.evaluate(initial,0)
    out=replace(dry,dry_policy='metastable_no_nucleation').evaluate(initial,0)
    assert out.cell_transfers[0].status=='metastable_no_nucleation_supersaturated'
    assert out.cell_transfers[0].vapor_chemical_potential_j_mol is None
    assert out.cell_transfers[0].entropy_production_w_k is None
    assert np.all(out.rates.reaction_species_mol_s==0)


def test_actual_joined_dry_high_temperature_continues_only_explicit_metastable(ingredients,joined):
    base=host(ingredients,joined,500.)
    values=dict(base_model=base,chemical=ingredients[2],coefficients_mol_s_pa=(1e-7,),
        coefficient_set_id='manufactured:modes',coefficient_version='1',coefficient_classification='manufactured_test_fixture',
        coefficient_source_ids=('manufactured:modes',),allow_manufactured=True,interface_modes=('depleted_no_nucleation',))
    strict=WaterPhaseTransfer(**values)
    initial=base.state_from_temperatures([[2.,.01,0.,0.]],[502.])
    with pytest.raises(DomainExit,match='unknown'):strict.evaluate(initial,0)
    metastable=replace(strict,dry_policy='metastable_no_nucleation')
    diagnostic=metastable.evaluate(initial,0)
    assert diagnostic.cell_transfers[0].status=='metastable_no_nucleation_condensation_drive_unknown'
    assert diagnostic.cell_transfers[0].hypothetical_equilibrium is None
    assert diagnostic.base_evaluation.storage_inverses[0].state is diagnostic.base_evaluation.storage_states[0]
    def powered(state,t):
        result=metastable.evaluate(state,t)
        return Rates(result.rates.face_species_mol_s,result.rates.face_energy_w,result.rates.reaction_species_mol_s,np.array([100.]))
    result=integrate(initial,powered,start_s=0,end_s=.2,policy=IntegrationPolicy(initial_step_s=.1,maximum_step_s=.1,
        minimum_step_s=1e-10,relative_tolerance=1e-8,amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-5,
        amount_scale_mol=.01,energy_scale_j=1.,maximum_steps=10,maximum_rejections=10,maximum_wall_seconds=90))
    assert result.status=='completed',(result.status,result.reason)
    assert np.array_equal(result.states[-1].amounts_mol,initial.amounts_mol)
    assert result.states[-1].internal_energy_j[0]-initial.internal_energy_j[0]==pytest.approx(20.,rel=0,abs=1e-7)
    assert base.decode(result.states[-1])[0].mechanical.temperature_k>502.


def test_dry_base_net_liquid_production_is_not_hidden(ingredients,monkeypatch):
    from sludge_sandbox.rigid_fluid_heat import RigidFluidHeat
    dry=dry_transfer(ingredients,dry_policy='metastable_no_nucleation')
    initial=dry.base_model.state_from_temperatures([[0.,.01,1e-5]],[300.])
    original=RigidFluidHeat.evaluate
    def production(self,state,time):
        result=original(self,state,time)
        source=np.array(result.rates.reaction_species_mol_s);source[0,0]=1e-6
        return replace(result,rates=Rates(result.rates.face_species_mol_s,result.rates.face_energy_w,source,result.rates.cell_power_w))
    monkeypatch.setattr(RigidFluidHeat,'evaluate',production)
    with pytest.raises(DomainExit,match='reappearance'):dry.evaluate(initial,0)


@pytest.mark.parametrize('changes',[{'interface_modes':()},{'interface_modes':('unknown',)},
    {'interface_modes':'existing_liquid'},{'dry_policy':'ignore'}])
def test_invalid_mode_contract(ingredients,changes):
    with pytest.raises(WaterPhaseTransferError):transfer(ingredients,**changes)


def test_dry_cannot_hold_liquid_and_switch_indices_are_strict(ingredients):
    wet=transfer(ingredients)
    initial=wet.base_model.state_from_temperatures([[1.,.01,1e-5]],[300.])
    with pytest.raises(DomainExit,match='dry_interface'):dry_transfer(ingredients).evaluate(initial,0)
    for indices in ((-1,),(1,),(True,),(0,0)):
        with pytest.raises(WaterPhaseTransferError):wet.with_depleted_cells(initial,indices)


def test_modes_are_immutable_and_numerical_failures_are_not_unknown(ingredients,monkeypatch):
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    from sludge_sandbox.water_properties import WaterNumericalError
    dry=dry_transfer(ingredients,dry_policy='metastable_no_nucleation')
    with pytest.raises(FrozenInstanceError):dry.dry_policy='strict'
    initial=dry.base_model.state_from_temperatures([[0.,.01,1e-5]],[300.])
    def fail(*args):raise WaterNumericalError('manufactured_numerical_failure')
    monkeypatch.setattr(WaterChemicalPotential,'equilibrium_at_liquid_tp',fail)
    with pytest.raises(WaterPhaseTransferError,match='manufactured_numerical_failure'):
        dry.evaluate(initial,0)


def test_zero_k_does_not_bypass_explicit_strict_dry_screen(ingredients):
    dry=replace(dry_transfer(ingredients),coefficients_mol_s_pa=(0.,))
    initial=dry.base_model.state_from_temperatures([[0.,.01,.001]],[300.])
    with pytest.raises(DomainExit,match='condensation'):dry.evaluate(initial,0)
