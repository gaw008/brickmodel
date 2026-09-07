"""Dynamic heat boundary and real water phase transfer share one extensive ledger."""
from dataclasses import replace
import math
import pytest
from sludge_sandbox.integration import IntegrationPolicy,integrate
from sludge_sandbox.boundary_program import BoundaryProgram,ProgramIdentity
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeat,ProgrammedSolidFluidEvaluation
from test_solid_fluid_heat import solid_host,ingredients
from test_water_phase_transfer import transfer


def programmed_transfer(ingredients):
    host=solid_host(ingredients)
    host=replace(host,transport=replace(host.transport,conductivities_w_m_k=(.1,)))
    program=BoundaryProgram(identity=ProgramIdentity(program_id='design:wet-heat',version='1',
        classification='virtual_design_choice',source_ids=('design:wet-heat',)),
        knot_times_s=(0.,.0005,.001),gas_temperature_k=(330.,340.,335.),
        radiation_temperature_k=(330.,340.,335.),total_pressure_pa=(4e5,4e5,4e5),
        species_order=('fixture','H2O'),mole_fractions=((.99,.01),)*3)
    programmed=ProgrammedSolidFluidHeat(base_model=host,program=program,
        convection_w_m2_k=10.,emissivity=0.,stefan_boltzmann_w_m2_k4=5.670374419e-8,
        coefficient_set_id='manufactured:wet-film',coefficient_version='1',
        coefficient_classification='manufactured',coefficient_source_ids=('manufactured:wet-film',),
        surface_policy=SurfacePolicy(absolute_residual_w=1e-8,relative_residual=1e-11,maximum_iterations=100),
        allow_manufactured=True)
    return replace(transfer(ingredients),base_model=programmed)


def test_program_diagnostics_and_knots_survive_water_wrapper(ingredients):
    op=programmed_transfer(ingredients)
    initial=op.base_model.base_model.state_from_temperatures([[2.,1e-5,2.,.01]],[300.])
    result=op.evaluate(initial,.0005)
    assert type(result.base_evaluation) is ProgrammedSolidFluidEvaluation
    assert result.base_evaluation.boundary.gas_temperature_k==340.
    assert result.base_evaluation.storage_inverses[0].state is result.base_evaluation.storage_states[0]
    assert op.breakpoints_s(0,.001)==(.0005,)
    assert 'design:wet-heat' in op.source_ids
    assert 'manufactured:wet-film' in op.source_ids
    assert result.rates.face_energy_w[-1]<0
    assert result.cell_transfers[0].rate_mol_s>0


def test_dynamic_heat_plus_phase_integrates_one_energy_and_water_ledger(ingredients):
    op=programmed_transfer(ingredients)
    host=op.base_model.base_model
    initial=host.state_from_temperatures([[2.,1e-5,2.,.01]],[300.])
    run=integrate(initial,op,start_s=0,end_s=.001,breakpoints_s=op.breakpoints_s(0,.001),
        policy=IntegrationPolicy(initial_step_s=.001,maximum_step_s=.001,minimum_step_s=1e-10,
            relative_tolerance=1e-7,amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-5,
            amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=10,maximum_rejections=10,maximum_wall_seconds=120))
    assert run.status=='completed',run.reason
    final=run.states[-1]
    assert final.amounts_mol[0,0]==2.
    assert final.amounts_mol[0,3]==.01
    assert math.fsum(final.amounts_mol[0,[1,2]])==pytest.approx(2.00001,rel=0,abs=1e-12)
    assert final.amounts_mol[0,1]>initial.amounts_mol[0,1]
    incoming=math.fsum(-step.face_energy_j[-1] for step in run.steps)
    assert incoming>0
    assert final.internal_energy_j[0]-initial.internal_energy_j[0]==pytest.approx(incoming,rel=0,abs=1e-7)
    for step in run.steps:
        assert step.reaction_species_mol[0,1]==-step.reaction_species_mol[0,2]
        assert step.cell_work_j[0]==0


def test_static_hosts_expose_no_program_breakpoints(ingredients):
    op=transfer(ingredients)
    assert op.breakpoints_s(0,1)==()
    assert replace(op,base_model=solid_host(ingredients)).breakpoints_s(0,1)==()


def test_program_wrapper_keeps_manufactured_opt_in(ingredients):
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransferError
    op=programmed_transfer(ingredients)
    with pytest.raises(WaterPhaseTransferError,match='manufactured'):
        replace(op,allow_manufactured=False)


def test_program_shaped_duck_object_is_not_an_admitted_host(ingredients):
    from types import SimpleNamespace
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransferError
    op=transfer(ingredients)
    with pytest.raises(WaterPhaseTransferError,match='explicit_fluid'):
        replace(op,base_model=SimpleNamespace(base_model=solid_host(ingredients)))
