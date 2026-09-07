"""Finite-rate interface fixtures coupled to real source-gated water thermodynamics."""
from dataclasses import replace
import math
from pathlib import Path

import numpy as np
import pytest

from sludge_sandbox.integration import DomainExit,IntegrationPolicy,integrate
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer,WaterPhaseTransferError
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.phase_storage import IdealGasPhase,InversePolicy
from sludge_sandbox.rigid_fluid_heat import RigidFluidHeat
from sludge_sandbox.water_properties import load_water_properties
from test_rigid_storage import model as storage_model

pytest.importorskip('iapws')
DATA=Path(__file__).resolve().parents[2]/'data/sandbox/water'


@pytest.fixture(scope='module')
def ingredients():
    return load_water_properties(DATA),IdealWaterVapor(DATA),WaterChemicalPotential(DATA)


def transfer(ingredients,**changes):
    water,vapor,chemical=ingredients
    storage=storage_model(water)
    gases={'fixture':storage.gas_phases['fixture'],'H2O':IdealGasPhase(vapor,vapor.molar_mass_kg_mol)}
    storage=replace(storage,mechanical=replace(storage.mechanical,gas_species_ids=('fixture','H2O')),
        gas_phases=gases,envelope=replace(storage.envelope,
        gas_u_error_j_mol={'fixture':1e-9,'H2O':1e-9},gas_cv_lower_j_mol_k={'fixture':20.,'H2O':20.}))
    base=RigidFluidHeat(storages=(storage,),gas_species_order=('fixture','H2O'),liquid_column_id='H2O_liquid',
        face_area_m2=.01,cell_widths_m=(.01,),conductivities_w_m_k=(0.,),
        effective_diffusivities_m2_s={'fixture':(0.,),'H2O':(0.,)},permeability_m2=(0.,),
        relative_permeability=(1.,),viscosity_pa_s=(1e-5,),temperature_brackets_k=((295.,310.),),
        inverse_policy=InversePolicy(1e-5,1e-4,100),
        coefficient_set_id='manufactured-sealed-phase-cell',coefficient_version='1',
        coefficient_classification='manufactured',coefficient_source_ids=('manufactured:sealed-phase-cell',),allow_manufactured=True)
    values=dict(base_model=base,chemical=chemical,coefficients_mol_s_pa=(1e-7,),
        coefficient_set_id='manufactured-interface-rate',coefficient_version='1',
        coefficient_classification='manufactured_test_fixture',coefficient_source_ids=('manufactured:interface-rate',),
        allow_manufactured=True)
    values.update(changes)
    return WaterPhaseTransfer(**values)


def test_actual_phase_source_is_equimolar_and_no_duplicate_latent_heat(ingredients):
    op=transfer(ingredients)
    state=op.base_model.state_from_temperatures([[2,.01,1e-5]],[300])
    result=op.evaluate(state,0)
    cell=result.cell_transfers[0]
    expected=1e-7*(cell.equilibrium.equilibrium_partial_pressure_pa-cell.vapor_partial_pressure_pa)
    assert cell.rate_mol_s==pytest.approx(expected,rel=1e-12,abs=0)
    assert cell.rate_mol_s>0
    assert result.rates.reaction_species_mol_s[0]==pytest.approx([-expected,0,expected],rel=0,abs=1e-15)
    assert np.array_equal(result.rates.cell_power_w,result.base_evaluation.rates.cell_power_w)
    assert np.all(result.rates.cell_power_w==0)
    assert result.base_evaluation.storage_inverses[0].state is result.base_evaluation.storage_states[0]


@pytest.mark.parametrize('water_vapor,sign',[(1e-5,-1),(.001,1)])
def test_real_adiabatic_phase_transfer_integrates_water_and_energy_with_temperature_feedback(ingredients,water_vapor,sign):
    op=transfer(ingredients)
    initial=op.base_model.state_from_temperatures([[2,.01,water_vapor]],[300])
    result=integrate(initial,op,start_s=0,end_s=.01,
        policy=IntegrationPolicy(initial_step_s=.01,maximum_step_s=.01,minimum_step_s=1e-10,
            relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-5,
            amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=10,maximum_rejections=10,
            maximum_wall_seconds=90))
    assert result.status=='completed',(result.status,result.reason)
    for state in result.states:
        assert math.fsum((state.amounts_mol[0,0],state.amounts_mol[0,2]))==pytest.approx(2+water_vapor,abs=1e-11,rel=0)
        assert state.internal_energy_j[0]==pytest.approx(initial.internal_energy_j[0],abs=1e-7,rel=0)
        assert state.amounts_mol[0,1]==.01
    final=op.base_model.decode(result.states[-1])[0]
    assert sign*(final.mechanical.temperature_k-300)>1e-4
    assert sign*(result.states[-1].amounts_mol[0,0]-2)>0
    for step in result.steps:
        assert step.reaction_species_mol[0,0]==-step.reaction_species_mol[0,2]
        assert np.all(step.cell_work_j==0)


def test_zero_vapor_is_finite_evaporation_not_finite_chemical_potential(ingredients):
    op=transfer(ingredients)
    state=op.base_model.state_from_temperatures([[2,.01,0]],[300])
    cell=op.evaluate(state,0).cell_transfers[0]
    assert cell.vapor_partial_pressure_pa==0
    assert math.isfinite(cell.rate_mol_s) and cell.rate_mol_s>0
    assert cell.vapor_chemical_potential_j_mol is None
    assert cell.entropy_production_w_k is None
    assert cell.status=='zero_vapor_limit'


def test_liquid_absent_exits_active_interface_but_disabled_rate_preserves_base(ingredients):
    op=transfer(ingredients)
    state=op.base_model.state_from_temperatures([[0,.01,.001]],[300])
    with pytest.raises(DomainExit,match='liquid_interface'):
        op(state,0)
    disabled=replace(op,coefficients_mol_s_pa=(0.,))
    result=disabled.evaluate(state,0)
    assert result.cell_transfers[0].status=='disabled'
    assert np.all(result.rates.reaction_species_mol_s==0)


@pytest.mark.parametrize('changes',[dict(coefficients_mol_s_pa=(-1.,)),dict(coefficients_mol_s_pa=(math.nan,)),
    dict(coefficients_mol_s_pa=()),dict(coefficient_source_ids=()),dict(coefficient_version=''),
    dict(coefficient_classification='unknown'),dict(allow_manufactured=False)])
def test_invalid_rate_contract(ingredients,changes):
    with pytest.raises(WaterPhaseTransferError):transfer(ingredients,**changes)


def test_finite_inventory_overstep_rejects_without_clipping_or_claiming_depletion(ingredients):
    op=transfer(ingredients,coefficients_mol_s_pa=(1.,))
    initial=op.base_model.state_from_temperatures([[2,.01,1e-5]],[300])
    result=integrate(initial,op,start_s=0,end_s=.01,
        policy=IntegrationPolicy(initial_step_s=.01,maximum_step_s=.01,minimum_step_s=1e-10,
            relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-5,
            amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=2,maximum_rejections=1,
            maximum_wall_seconds=90))
    assert result.status=='resource_limit'
    assert result.reason=='rejected_trial_limit'
    assert result.rejected_trials==1
    assert result.times_s==(0.,)
    assert np.array_equal(result.states[0].amounts_mol,initial.amounts_mol)
    assert result.states[0].internal_energy_j[0]==initial.internal_energy_j[0]


def test_disabled_interface_allows_high_temperature_base_pure_carrier(ingredients,monkeypatch):
    op=transfer(ingredients,coefficients_mol_s_pa=(0.,))
    storage=op.base_model.storages[0]
    storage=replace(storage,envelope=replace(storage.envelope,temperature_range_k=(600.,1000.)))
    op=replace(op,base_model=replace(op.base_model,storages=(storage,),temperature_brackets_k=((700.,900.),)))
    def forbidden(*args,**kwargs):raise AssertionError('disabled interface queried chemical model')
    monkeypatch.setattr(WaterChemicalPotential,'equilibrium_at_liquid_tp',forbidden)
    initial=op.base_model.state_from_temperatures([[0,.01,0]],[800])
    result=op.evaluate(initial,0)
    assert result.cell_transfers[0].status=='disabled'
    assert result.base_evaluation.storage_states[0].mechanical.temperature_k==pytest.approx(800,abs=1e-6,rel=0)


def test_incompatible_water_caloric_provider_cannot_drive_chemical_transfer(ingredients):
    op=transfer(ingredients)
    storage=op.base_model.storages[0]
    wrong_curve=replace(storage.gas_phases['fixture'].caloric,species_id='H2O')
    wrong_phase=IdealGasPhase(wrong_curve,ingredients[0].reference.molar_mass_kg_mol,0,('manufactured:wrong-water-caloric',))
    bad_storage=replace(storage,gas_phases={'fixture':storage.gas_phases['fixture'],'H2O':wrong_phase})
    with pytest.raises(WaterPhaseTransferError,match='matching_ideal_water_caloric_bridge'):
        replace(op,base_model=replace(op.base_model,storages=(bad_storage,)))


def test_nonzero_tiny_rate_is_not_silently_called_equilibrium(ingredients):
    op=transfer(ingredients)
    initial=op.base_model.state_from_temperatures([[2,.01,1e-5]],[300])
    baseline=op.evaluate(initial,0)
    mechanical=baseline.base_evaluation.storage_states[0].mechanical
    peq=baseline.cell_transfers[0].equilibrium.equilibrium_partial_pressure_pa
    approximate_vapor=peq*mechanical.gas_volume_m3/(ingredients[2].gas_constant_j_mol_k*mechanical.temperature_k)
    near=op.base_model.state_from_temperatures([[2,.01,approximate_vapor+1e-9]],[300])
    tiny=replace(op,coefficients_mol_s_pa=(math.ulp(0.),))
    with pytest.raises(WaterPhaseTransferError,match='unrepresentable_phase_transfer_rate'):
        tiny(near,0)
