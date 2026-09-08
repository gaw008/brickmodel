"""Actual liquid/vapor source coupling to current geometry and total energy."""
from dataclasses import replace
from fractions import Fraction
import json
import numpy as np
import pytest
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.phase_storage import IdealGasPhase
from sludge_sandbox.solid_fluid_heat import InventoryLayout
from sludge_sandbox.integration import integrate
from test_water_phase_transfer import ingredients
from test_free_solid_cell import host
from test_integration import policy


def free_transfer(ingredients,**changes):
    water,vapor,chemical=ingredients
    base=host(water);fluid=base.point.template.fluid_template
    fluid=replace(fluid,gas_phases=fluid.gas_phases|{'H2O':IdealGasPhase(vapor,vapor.molar_mass_kg_mol)},
        mechanical=replace(fluid.mechanical,gas_species_ids=('fixture','H2O')),
        envelope=replace(fluid.envelope,gas_u_error_j_mol={'fixture':1e-9,'H2O':1e-9},
                         gas_cv_lower_j_mol_k={'fixture':20.,'H2O':20.}))
    base=replace(base,point=replace(base.point,template=replace(base.point.template,fluid_template=fluid)),
        inventory_layout=InventoryLayout(species_order=('liquid','fixture','H2O','fixture_solid'),
            liquid_column_id='liquid',gas_species_order=('fixture','H2O'),solid_species_order=('fixture_solid',)))
    values=dict(base_model=base,chemical=chemical,coefficients_mol_s_pa=(1e-7,),
        coefficient_set_id='manufactured-free-phase',coefficient_version='1',
        coefficient_classification='manufactured_test_fixture',coefficient_source_ids=('manufactured:kinetic-coefficient',),
        allow_manufactured=True)
    return WaterPhaseTransfer(**(values|changes))


def test_explicit_source_admission_still_requires_manufactured_opt_in(ingredients):
    with pytest.raises(ValueError,match='manufactured_requires'):
        free_transfer(ingredients,allow_manufactured=False)


def test_free_cell_still_rejects_wrong_water_caloric_bridge(ingredients):
    op=free_transfer(ingredients);base=op.base_model;fluid=base.point.template.fluid_template
    wrong_curve=replace(fluid.gas_phases['fixture'].caloric,species_id='H2O')
    wrong=IdealGasPhase(wrong_curve,ingredients[0].reference.molar_mass_kg_mol,0,('manufactured:wrong-water-caloric',))
    fluid=replace(fluid,gas_phases=fluid.gas_phases|{'H2O':wrong})
    changed=replace(base,point=replace(base.point,template=replace(base.point.template,fluid_template=fluid)))
    with pytest.raises(ValueError,match='matching_ideal_water_caloric_bridge'):
        replace(op,base_model=changed)


def test_actual_phase_rate_preserves_free_mechanics_and_external_work(ingredients):
    op=free_transfer(ingredients)
    initial=op.base_model.state_from_temperature([[1.,.01,1e-5,2.]],300.,normal_stretch=1.,tangential_stretch=1.)
    out=op.evaluate(initial,0.);base=out.base_evaluation;phase=out.cell_transfers[0]
    assert phase.rate_mol_s>0 and phase.entropy_production_w_k>=0
    rates=out.rates.reaction_species_mol_s[0]
    assert Fraction(float(rates[0]))+Fraction(float(rates[2]))==0
    assert rates[1]==rates[3]==0
    assert np.array_equal(out.rates.mechanical_rates_per_s,base.rates.mechanical_rates_per_s)
    assert np.array_equal(out.rates.cell_power_w,base.rates.cell_power_w)
    assert set(out.rates.cell_power_components_w)=={'external_traction','body'}
    assert base.storage_inverses[0].state is base.storage_states[0]
    assert set(base.source_ids)<=set(out.source_ids)


def test_actual_free_evaporation_step_conserves_water_and_total_work(ingredients):
    op=free_transfer(ingredients)
    initial=op.base_model.state_from_temperature([[1.,.01,1e-5,2.]],300.,normal_stretch=1.,tangential_stretch=1.)
    numerical=policy(initial_step_s=.001,maximum_step_s=.001,relative_tolerance=1e-7,
        amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-6,
        stretch_absolute_tolerance=1e-9,stretch_scale=1.,maximum_steps=4,maximum_rejections=4,
        maximum_wall_seconds=30.)
    out=integrate(initial,op,start_s=0.,end_s=.001,policy=numerical)
    assert out.status=='completed',out.reason
    final=out.states[-1];row=final.amounts_mol[0]
    assert row[0]<1. and row[2]>1e-5
    assert abs(Fraction(float(row[0]))+Fraction(float(row[2]))-Fraction(1.)-Fraction(1e-5))<Fraction(1e-11)
    point=op.base_model.evaluate(final,.001).inverse.state
    delta_volume=float(point.deformation.current.volumes_m3[0])-op.base_model.point.skeleton.reference_volume_m3
    assert abs(float(final.internal_energy_j[0])-float(initial.internal_energy_j[0])+101325.*delta_volume)<2e-6
    assert point.thermal_state.mechanical.temperature_k<300.
    assert not np.array_equal(final.mechanical_stretches,initial.mechanical_stretches)
    from sludge_sandbox.verification_case import encode
    from sludge_sandbox.checkpoint import audit_integration
    audit_integration(encode(out),numerical,start_s=0.,end_s=.001)
    print(json.dumps(dict(qualification='manufactured_free_cell_active_evaporation_short_interval',
        accepted=len(out.steps),rejected=out.rejected_trials,evaluations=out.evaluations,
        elapsed_s=out.elapsed_seconds,liquid_mol=float(row[0]),water_vapor_mol=float(row[2]),
        temperature_k=point.thermal_state.mechanical.temperature_k,
        pressure_pa=point.thermal_state.mechanical.pressure_pa,stretches=final.mechanical_stretches.tolist(),
        total_work_residual_j=float(final.internal_energy_j[0])-float(initial.internal_energy_j[0])+101325.*delta_volume)))
