"""Real-water host wiring under explicit manufactured liquid transport."""
from dataclasses import replace
import math
import numpy as np
import pytest
from sludge_sandbox.integration import IntegrationPolicy,integrate
from sludge_sandbox.solid_fluid_heat import LiquidTransportConfig
from sludge_sandbox.liquid_transport import SaturationMobilityTable,LiquidConnection
from test_solid_fluid_heat import solid_host,ingredients


def liquid_host(ingredients):
    host=solid_host(ingredients,cells=2,heat=0.)
    host=replace(host,transport=replace(host.transport,
        effective_diffusivities_m2_s={'fixture':(0.,0.),'H2O':(0.,0.)}))
    relation=SaturationMobilityTable(saturation_knots=(0.,1.),permeability_m2=(1e-15,1e-15),
        relative_permeability=(.5,.5),viscosity_pa_s=(.001,.001),
        temperature_range_k=(293.,500.),pressure_range_pa=(1e4,1e7),
        model_id='manufactured:liquid-mobility',version='1',relation_kind='frozen_manufactured',classification='manufactured_test_fixture',
        source_ids=('manufactured:liquid-mobility',),source_asset_sha256=(('fixture','c'*64),))
    connection=LiquidConnection(status='connected',connection_id='manufactured:liquid-link',version='1',
        classification='manufactured_test_fixture',source_ids=('manufactured:liquid-link',))
    return replace(host,liquid_transport=LiquidTransportConfig(relations=(relation,relation),
        connections=(connection,),allow_manufactured=True))


def test_liquid_face_uses_actual_donor_and_complete_layout(ingredients):
    host=liquid_host(ingredients)
    state=host.state_from_temperatures([[2.,1e-5,2.,.02],[2.,1e-5,1.,.01]],[300.,301.])
    out=host.evaluate(state,0)
    face=out.liquid_faces[0]
    assert face.molar_flow_mol_s>0
    assert out.rates.face_species_mol_s[1,2]==face.molar_flow_mol_s
    assert np.all(out.rates.face_species_mol_s[:,[0,1,3]]==0)
    left=out.storage_states[0].mechanical
    water=host.storages[0].fluid_template.mechanical.water
    h=water.state_tp(left.temperature_k,left.liquid_pressure_pa,phase='liquid').enthalpy_j_mol
    assert out.rates.face_energy_w[1]==pytest.approx(face.molar_flow_mol_s*h,rel=0,abs=1e-9)
    assert 'manufactured:liquid-mobility' in host.source_ids


def test_two_wet_cell_prefix_conservation_and_closed_pressure_feedback(ingredients):
    host=liquid_host(ingredients)
    initial=host.state_from_temperatures([[2.,1e-5,2.,.02],[2.,1e-5,1.,.01]],[300.,301.])
    start=host.decode(initial)
    run=integrate(initial,host,start_s=0,end_s=.001,policy=IntegrationPolicy(
        initial_step_s=.001,maximum_step_s=.001,minimum_step_s=1e-10,relative_tolerance=1e-7,
        amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-5,
        amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=10,maximum_rejections=10,maximum_wall_seconds=120))
    assert run.status=='completed',run.reason
    accumulated=np.zeros(2)
    for step,state in zip(run.steps,run.states[1:]):
        accumulated+=step.face_energy_j[:-1]-step.face_energy_j[1:]
        assert state.amounts_mol[:,2].sum()==pytest.approx(3.,rel=0,abs=1e-11)
        assert np.array_equal(state.amounts_mol[:,[0,1,3]],initial.amounts_mol[:,[0,1,3]])
        assert state.internal_energy_j.sum()==pytest.approx(initial.internal_energy_j.sum(),rel=0,abs=1e-6)
        assert state.internal_energy_j-initial.internal_energy_j==pytest.approx(accumulated,rel=0,abs=1e-6)
    end=host.decode(run.states[-1])
    assert end[0].mechanical.pressure_pa<start[0].mechanical.pressure_pa
    assert end[1].mechanical.pressure_pa>start[1].mechanical.pressure_pa
    # Nominal feedback only; no claim that this tiny thermal change exceeds the inverse envelope.
    assert any(a.mechanical.temperature_k!=b.mechanical.temperature_k for a,b in zip(start,end))


def classification_control_host(host):
    """Only gate logic: relabel synthetic records; never material admission."""
    storages=[];templates=[]
    for storage in host.storages:
        fluid=storage.fluid_template
        gas=fluid.gas_phases['fixture']
        gas=replace(gas,caloric=replace(gas.caloric,classification='literature_constitutive_model'))
        fluid=replace(fluid,gas_phases=dict(fluid.gas_phases)|{'fixture':gas})
        solid=storage.solid_phases['fixture_solid']
        solid=replace(solid,caloric=replace(solid.caloric,classification='literature_constitutive_model'),
            volume_classification='literature_constitutive_model',error_classification='derived_from_evidence')
        storages.append(replace(storage,fluid_template=fluid,solid_phases={'fixture_solid':solid},
            geometry_classification='virtual_design_choice'))
        templates.append(fluid)
    return replace(host,storages=tuple(storages),transport=replace(host.transport,storages=tuple(templates),
        coefficient_classification='literature_candidate'))


def test_only_liquid_manufactured_classification_reaches_both_wrappers(ingredients):
    from test_programmed_water_phase_transfer import programmed_transfer
    from test_water_phase_transfer import transfer
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransferError
    from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeatError
    host=classification_control_host(liquid_host(ingredients))
    program=programmed_transfer(ingredients).base_model
    with pytest.raises(ProgrammedSolidFluidHeatError,match='manufactured'):
        replace(program,base_model=host,coefficient_classification='literature_candidate',allow_manufactured=False)
    with pytest.raises(WaterPhaseTransferError,match='manufactured'):
        replace(transfer(ingredients),base_model=host,coefficients_mol_s_pa=(0.,0.),
            coefficient_classification='literature_constitutive_model',allow_manufactured=False)
    # Negative control: remove only liquid config; no unrelated classification blocks either wrapper.
    clean=replace(host,liquid_transport=None)
    replace(program,base_model=clean,coefficient_classification='literature_candidate',allow_manufactured=False)
    replace(transfer(ingredients),base_model=clean,coefficients_mol_s_pa=(0.,0.),
        coefficient_classification='literature_constitutive_model',allow_manufactured=False)


def test_liquid_diagnostics_survive_program_and_phase_chain(ingredients):
    from test_programmed_water_phase_transfer import programmed_transfer
    host=liquid_host(ingredients)
    op=programmed_transfer(ingredients)
    program=replace(op.base_model,base_model=host)
    op=replace(op,base_model=program,coefficients_mol_s_pa=(1e-7,1e-7))
    state=host.state_from_temperatures([[2.,1e-5,2.,.02],[2.,1e-5,1.,.01]],[300.,301.])
    result=op.evaluate(state,.0005)
    face=result.base_evaluation.base_evaluation.liquid_faces[0]
    assert face.molar_flow_mol_s!=0
    assert result.rates.face_species_mol_s[1,2]==face.molar_flow_mol_s
    assert result.base_evaluation.boundary.gas_temperature_k==340.
    assert op.breakpoints_s(0,.001)==(.0005,)


def test_liquid_host_decodes_once_and_marks_pressure_scope(ingredients,monkeypatch):
    from sludge_sandbox.solid_fluid_heat import SolidFluidHeat
    host=liquid_host(ingredients)
    state=host.state_from_temperatures([[2.,1e-5,2.,.02],[2.,1e-5,1.,.01]],[300.,301.])
    original=SolidFluidHeat.decode_inverse
    calls=[]
    def count(self,state):calls.append(1);return original(self,state)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',count)
    out=host.evaluate(state,0)
    assert len(calls)==1
    assert out.liquid_pressure_interval_scope=='fixed_decoded_temperature'
    assert out.full_inverse_liquid_direction_certified is False
    assert out.liquid_faces[0].full_inverse_direction_certified is False


def test_disabled_dry_face_does_not_request_liquid_state(ingredients,monkeypatch):
    host=liquid_host(ingredients)
    disabled=replace(host.liquid_transport.connections[0],status='disabled')
    host=replace(host,liquid_transport=replace(host.liquid_transport,connections=(disabled,)))
    state=host.state_from_temperatures([[2.,1e-5,0.,.02],[2.,1e-5,0.,.01]],[300.,301.])
    water=host.storages[0].fluid_template.mechanical.water
    def forbidden(*a,**k):raise AssertionError('dry cells must not query liquid water TP')
    monkeypatch.setattr(type(water),'state_tp',forbidden)
    result=host.evaluate(state,0)
    assert result.liquid_faces[0].molar_flow_mol_s==0
