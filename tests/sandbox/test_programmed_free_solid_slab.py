from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from test_dynamic_solid_storage import water,forbid_water_eos
from test_free_solid_slab import host,initial
from test_programmed_solid_fluid_heat import program
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.integration import integrate
from sludge_sandbox.checkpoint import audit_integration
from sludge_sandbox.verification_case import encode
from test_integration import policy
import sludge_sandbox.programmed_solid_fluid_heat as m


def wrapped(water):
    return m.ProgrammedSolidFluidHeat(base_model=host(water),program=program(species_order=('fixture',),mole_fractions=((1.,),)*4),
        convection_w_m2_k=20.,emissivity=0.,stefan_boltzmann_w_m2_k4=5.670374419e-8,
        coefficient_set_id='manufactured:film',coefficient_version='1',coefficient_classification='manufactured',
        coefficient_source_ids=('manufactured:film',),allow_manufactured=True,
        surface_policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=200))


def test_actual_current_surface_and_mechanics_forwarding(water):
    op=wrapped(water);state=initial(op.base_model);out=op.evaluate(state,.05)
    base=out.base_evaluation;transport=base.current_host.transport;temperature=base.storage_states[-1].mechanical.temperature_k
    area=F(transport.face_area_m2);distance=F(transport.cell_widths_m[-1])/2
    expected=(F(310.)-F(temperature))/(1/(F(20.)*area)+distance/(F(.2)*area))
    assert abs(F(out.conductive_into_cell_w)-expected)<F(2e-10)
    np.testing.assert_array_equal(out.rates.mechanical_rates_per_s,base.rates.mechanical_rates_per_s)
    for key in ('external_traction','mechanical_constraint','body'):
        np.testing.assert_array_equal(out.rates.cell_power_components_w[key],base.rates.cell_power_components_w[key])
    assert op.base_model.external_pressure_pa!=out.boundary.total_pressure_pa
    assert state.energy_model_identity==op.base_model.energy_model_identity
    assert out.operator_identity==op.operator_identity
    assert set(op.source_ids)<=set(out.source_ids)
    assert set(base.source_ids)<=set(out.source_ids)
    assert out.rates.face_energy_w[-1]==-out.conductive_into_cell_w
    assert op.breakpoints_s(0.,.15)==(.05,.1)


def test_waveform_knots_energy_and_checkpoint(water):
    op=wrapped(water);state=initial(op.base_model)
    p=policy(initial_step_s=.007,maximum_step_s=.007,relative_tolerance=1e-8,
        energy_absolute_tolerance_j=1e-6,stretch_absolute_tolerance=1e-9,stretch_scale=1.,maximum_wall_seconds=20.)
    run=integrate(state,op,start_s=0.,end_s=.15,policy=p,breakpoints_s=op.breakpoints_s(0.,.15))
    assert run.status=='completed',run.reason
    assert .05 in run.times_s and .1 in run.times_s
    assert all(not a<k<b for a,b in zip(run.times_s,run.times_s[1:]) for k in (.05,.1))
    audit_integration(encode(run),p,start_s=0.,end_s=.15)
    exchange=F();pe=F(op.base_model.external_pressure_pa);v0=F(.00014)
    a,b,c=map(F,map(float,state.mechanical_stretches));initial_j_sum=(a+b)*c*c
    for step,after in zip(run.steps,run.states[1:],strict=True):
        exchange+=F(float(step.face_energy_j[0]))-F(float(step.face_energy_j[-1]))
        delta=sum((F(float(a))-F(float(b)) for a,b in zip(after.internal_energy_j,state.internal_energy_j)),F())
        n0,n1,t=map(F,map(float,after.mechanical_stretches))
        assert abs(delta+pe*v0*((n0+n1)*t*t-initial_j_sum)-exchange)<F(4e-6)


def test_order_source_and_duplicate_boundary_guards(water):
    op=wrapped(water)
    with pytest.raises(ValueError):replace(op,allow_manufactured=False)
    with pytest.raises(ValueError):replace(op,program=program())
    base=op.base_model
    transport=replace(base.base_model.transport,outer_surface_temperature_k=305.,outer_heat_source_ids=('virtual:duplicate',))
    changed=replace(base,base_model=replace(base.base_model,transport=transport))
    with pytest.raises(ValueError,match='duplicated'):replace(op,base_model=changed)
    assert 'virtual:oven' in op.source_ids and set(base.source_ids)<=set(op.source_ids)


def test_program_content_identity_separate_from_energy(water):
    op=wrapped(water);state=initial(op.base_model)
    identity=op.operator_identity
    changed=replace(op,program=replace(op.program,gas_temperature_k=(300.,309.,310.,295.)))
    assert changed.program.identity==op.program.identity
    assert changed.operator_identity!=identity
    assert state.energy_model_identity==changed.base_model.energy_model_identity
    assert changed.evaluate(state,.05).base_evaluation.model_identity==state.energy_model_identity
    assert op.operator_identity==identity


@pytest.mark.parametrize('target',['program','coefficient','base'])
def test_runtime_content_mutation_rejected_by_all_entrypoints(water,target):
    op=wrapped(water);state=initial(op.base_model)
    if target=='program':object.__setattr__(op.program,'gas_temperature_k',(300.,309.,310.,295.))
    elif target=='coefficient':object.__setattr__(op,'emissivity',.5)
    else:object.__setattr__(op.base_model.base_model.transport,'conductivities_w_m_k',(.3,.3))
    for call in (lambda:op.operator_identity,lambda:op._check_state(state),lambda:op.evaluate(state,.05)):
        with pytest.raises(ValueError,match='runtime_programmed_operator_content_changed'):call()


@pytest.mark.parametrize('value',[float('nan'),object()])
def test_invalid_digest_maps_to_integration_error(water,value):
    from sludge_sandbox.integration import IntegrationError
    op=wrapped(water);state=initial(op.base_model)
    object.__setattr__(op,'convection_w_m2_k',value)
    for call in (lambda:op.operator_identity,lambda:op._check_state(state),lambda:op.evaluate(state,.05)):
        with pytest.raises(IntegrationError,match='invalid_runtime_programmed_operator_content') as caught:call()
        assert caught.value.__cause__ is not None


@pytest.mark.parametrize('value',[float('nan'),object()])
def test_invalid_digest_after_acceptance_preserves_complete_prefix(water,value):
    op=wrapped(water);state=initial(op.base_model);mutations=[]
    def callback(stage,time):
        if time>.001 and not mutations:
            object.__setattr__(op,'convection_w_m2_k',value);mutations.append(time)
        return op(stage,time)
    p=policy(initial_step_s=.001,maximum_step_s=.001,relative_tolerance=1e-8,
        energy_absolute_tolerance_j=1e-6,stretch_absolute_tolerance=1e-9,stretch_scale=1.,maximum_wall_seconds=20.)
    run=integrate(state,callback,start_s=0.,end_s=.003,policy=p)
    assert mutations and run.status=='numerical_failure'
    assert run.reason=='invalid_runtime_programmed_operator_content'
    assert len(run.steps)==1 and run.times_s==(0.,.001)
    assert len(run.states)==2 and run.steps[0].end_s==run.times_s[-1]
    assert run.states[0] is state and run.states[-1].energy_model_identity==state.energy_model_identity
    audit_integration(encode(run),p,start_s=0.,end_s=.003)
