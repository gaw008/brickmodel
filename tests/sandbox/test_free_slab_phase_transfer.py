"""Source-gated water phases in a manufactured compatible two-cell slab."""
from dataclasses import replace
from fractions import Fraction as F
import json
import os
from pathlib import Path
import numpy as np
import pytest
from sludge_sandbox.phase_storage import IdealGasPhase
from sludge_sandbox.solid_fluid_heat import InventoryLayout
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.integration import integrate
from sludge_sandbox.checkpoint import audit_integration
from sludge_sandbox.verification_case import encode
from test_water_phase_transfer import ingredients
from test_free_solid_slab_wet import wet_host
from test_integration import policy


def slab_transfer(ingredients, **changes):
    water,vapor,chemical=ingredients
    base=wet_host(water)
    points=[]
    for point in base.point_storages:
        fluid=point.template.fluid_template
        fluid=replace(fluid,gas_phases=fluid.gas_phases|{'H2O':IdealGasPhase(vapor,vapor.molar_mass_kg_mol)},
            mechanical=replace(fluid.mechanical,gas_species_ids=('fixture','H2O')),
            envelope=replace(fluid.envelope,gas_u_error_j_mol={'fixture':1e-9,'H2O':1e-9},
                gas_cv_lower_j_mol_k={'fixture':20.,'H2O':20.}))
        points.append(replace(point,template=replace(point.template,fluid_template=fluid)))
    points=tuple(points)
    transport=replace(base.base_model.transport,storages=tuple(p.template.fluid_template for p in points),
        gas_species_order=('fixture','H2O'),effective_diffusivities_m2_s={'fixture':(0.,0.),'H2O':(0.,0.)})
    thermal=replace(base.base_model,transport=transport,storages=tuple(p.template for p in points),
        inventory_layout=InventoryLayout(species_order=('liquid','fixture','H2O','fixture_solid'),
            liquid_column_id='liquid',gas_species_order=('fixture','H2O'),solid_species_order=('fixture_solid',)))
    base=replace(base,base_model=thermal,point_storages=points)
    return WaterPhaseTransfer(**(dict(base_model=base,chemical=chemical,
        coefficients_mol_s_pa=(1e-7,1e-7),coefficient_set_id='manufactured-slab-phase',coefficient_version='1',
        coefficient_classification='manufactured_test_fixture',coefficient_source_ids=('manufactured:phase-coefficient',),
        allow_manufactured=True)|changes))


def test_slab_admission_requires_explicit_manufactured_gate(ingredients):
    with pytest.raises(ValueError,match='manufactured_requires'):
        slab_transfer(ingredients,allow_manufactured=False)


def test_second_cell_wrong_caloric_bridge_rejected(ingredients):
    op=slab_transfer(ingredients);base=op.base_model
    points=list(base.point_storages);point=points[1];fluid=point.template.fluid_template
    wrong=IdealGasPhase(replace(fluid.gas_phases['fixture'].caloric,species_id='H2O'),
        ingredients[0].reference.molar_mass_kg_mol,0,('manufactured:wrong-water-caloric',))
    fluid=replace(fluid,gas_phases=fluid.gas_phases|{'H2O':wrong})
    points[1]=replace(point,template=replace(point.template,fluid_template=fluid));points=tuple(points)
    with pytest.raises(ValueError,match='cross_cell_caloric_identity_mismatch'):
        replace(base.base_model.transport,storages=tuple(p.template.fluid_template for p in points))
    # Matching wrong caloric providers clear the shared-face identity gate but
    # must still fail the separate physical water chemical/caloric bridge.
    points=tuple(replace(p,template=replace(p.template,fluid_template=fluid)) for p in points)
    transport=replace(base.base_model.transport,storages=tuple(p.template.fluid_template for p in points))
    thermal=replace(base.base_model,transport=transport,storages=tuple(p.template for p in points))
    with pytest.raises(ValueError,match='matching_ideal_water_caloric_bridge'):
        replace(op,base_model=replace(base,base_model=thermal,point_storages=points))


def test_actual_opposite_phase_directions_current_geometry_and_work(ingredients):
    op=slab_transfer(ingredients)
    state=op.base_model.state_from_temperatures([[1.,.01,1e-5,2.],[.5,.008,.001,2.]],
        [300.,301.],normal_stretches=(.95,1.03),tangential_stretch=.99)
    out=op.evaluate(state,0.);base=out.base_evaluation
    assert out.cell_transfers[0].rate_mol_s>0>out.cell_transfers[1].rate_mol_s
    for i,phase in enumerate(out.cell_transfers):
        current=base.storage_states[i].mechanical
        pressure=F(float(state.amounts_mol[i,2]))*F(op.chemical.gas_constant_j_mol_k)*F(current.temperature_k)/F(current.gas_volume_m3)
        assert phase.vapor_partial_pressure_pa==float(pressure)
        assert phase.entropy_production_w_k>0
        assert F(float(out.rates.reaction_species_mol_s[i,0]))+F(float(out.rates.reaction_species_mol_s[i,2]))==0
        assert base.total_inverses[i].thermal_inverse.state is base.storage_states[i]
    np.testing.assert_array_equal(out.rates.mechanical_rates_per_s,base.rates.mechanical_rates_per_s)
    np.testing.assert_array_equal(out.rates.face_energy_w,base.rates.face_energy_w)
    assert out.rates.face_energy_w[1]!=0
    for name in ('external_traction','mechanical_constraint','body'):
        np.testing.assert_array_equal(out.rates.cell_power_components_w[name],base.rates.cell_power_components_w[name])
    assert set(base.source_ids)<=set(out.source_ids)


def test_actual_two_cell_phase_trajectory_refinement(ingredients):
    op=slab_transfer(ingredients)
    initial=op.base_model.state_from_temperatures([[1.,.01,1e-5,2.],[.5,.008,.001,2.]],
        [300.,301.],normal_stretches=(1.,1.),tangential_stretch=1.)
    runs=[];final_temperatures=[];payload=[];max_water=0.;max_work=0.
    for cap in (1e-4,5e-5):
        numerical=policy(initial_step_s=cap,maximum_step_s=cap,relative_tolerance=1e-7,
            amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-6,
            stretch_absolute_tolerance=1e-9,stretch_scale=1.,maximum_steps=4,
            maximum_rejections=4,maximum_wall_seconds=60.)
        out=integrate(initial,op,start_s=0.,end_s=1e-4,policy=numerical)
        payload.append({'policy':encode(numerical),'result':encode(out)})
        artifact=os.environ.get('BRICK_FREE_SLAB_PHASE_ARTIFACT')
        if artifact:Path(artifact).write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
        assert out.status=='completed',out.reason
        for state in out.states:
            np.testing.assert_array_equal(state.amounts_mol[:,[1,3]],initial.amounts_mol[:,[1,3]])
            for row,start in zip(state.amounts_mol,initial.amounts_mol,strict=True):
                residual=abs(F(float(row[0]))+F(float(row[2]))-F(float(start[0]))-F(float(start[2])))
                assert residual<F(1e-11);max_water=max(max_water,float(residual))
            n0,n1,t=map(float,state.mechanical_stretches)
            delta=sum((F(float(a))-F(float(b)) for a,b in zip(state.internal_energy_j,initial.internal_energy_j,strict=True)),F())
            work=abs(delta+F(101325.)*F(.00014)*((F(n0)+F(n1))*F(t)**2-2))
            assert work<F(4e-6);max_work=max(max_work,float(work))
        audit_integration(encode(out),numerical,start_s=0.,end_s=1e-4)
        assert out.states[-1].amounts_mol[0,0]<initial.amounts_mol[0,0]
        assert out.states[-1].amounts_mol[1,0]>initial.amounts_mol[1,0]
        final=op.base_model.evaluate(out.states[-1],1e-4)
        final_temperatures.append([s.mechanical.temperature_k for s in final.storage_states]);runs.append(out)
    coarse,fine=(r.states[-1] for r in runs)
    assert np.max(np.abs(coarse.amounts_mol-fine.amounts_mol))<1e-11
    assert np.max(np.abs(coarse.internal_energy_j-fine.internal_energy_j))<2e-6
    assert np.max(np.abs(coarse.mechanical_stretches-fine.mechanical_stretches))<2e-7
    assert np.max(np.abs(np.array(final_temperatures[0])-final_temperatures[1]))<2e-6
    print(json.dumps(dict(qualification='real_water_manufactured_two_cell_phase_short_trajectory',
        accepted=[len(r.steps) for r in runs],evaluations=[r.evaluations for r in runs],
        elapsed_s=[r.elapsed_seconds for r in runs],temperatures_k=final_temperatures,
        maximum_prefix_water_residual_mol=max_water,maximum_prefix_external_work_residual_j=max_work)))
