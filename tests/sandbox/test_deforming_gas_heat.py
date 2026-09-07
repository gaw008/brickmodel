"""Manufactured actuated chambers: prescribed motion is not a brick mechanics law."""
from dataclasses import replace
from fractions import Fraction as F
import math
import json
import numpy as np
import pytest
from sludge_sandbox.deforming_gas_heat import DeformingGasHeat,DeformingGasHeatError
from sludge_sandbox.deformation_program import PrescribedSlabMotion
from sludge_sandbox.geometry import ReferenceSlab
from sludge_sandbox.integration import DomainExit,IntegrationError,integrate
from test_gas_heat_model import model,caloric,policy


def chamber(cells=1,*,flow=False):
    return model(thermochemistry=caloric(('A',),cp=30.,formations=(0.,)),species_order=('A',),
        molar_masses_kg_mol={'A':.012},face_area_m2=.1,cell_widths_m=(.1,)*cells,
        gas_volumes_m3=(.1*.1,)*cells,conductivities_w_m_k=((.02 if flow else 0.),)*cells,
        effective_diffusivities_m2_s={'A':((1e-7 if flow else 0.),)*cells},
        permeability_m2=((1e-16 if flow else 0.),)*cells,relative_permeability=(1.,)*cells,viscosity_pa_s=(1e-5,)*cells)


def motion(cells=1,*,constant=False):
    middle=((1.,)*cells if constant else (.8,) if cells==1 else (.9,1.1))
    return PrescribedSlabMotion(reference=ReferenceSlab(.1*cells,.1,cells),knot_times_s=(0.,1.,2.),
        normal_stretches_at_knots=((1.,)*cells,middle,(1.,)*cells),tangential_stretches_at_knots=(1.,1.,1.),
        motion_id='virtual:actuated-reference',version='1',classification='virtual_design_choice',
        source_ids=('virtual:prescribed-c1-motion',),source_asset_sha256=())


def moving(cells=1,*,flow=False,constant=False,**changes):
    values=dict(base_model=chamber(cells,flow=flow),motion=motion(cells,constant=constant),
        mechanical_regime='prescribed_cellwise_quasistatic_gas_chambers',
        work_model_id='declared:pressure-matched-actuators',work_model_version='1',
        work_source_ids=('declared:pressure-matched-pdv',),allow_manufactured=True)
    values.update(changes)
    return DeformingGasHeat(**values)


def imposed_normal(t):
    # Independent expression of the declared reference motion, not candidate.sample.
    if t<=1:return 1-.2*t*t*(3-2*t)
    q=t-1
    return .8+.2*q*q*(3-2*q)


def assert_prefix(result):
    initial=result.states[0];n=np.full(initial.amounts_mol.shape,F(0),dtype=object)
    u=[F(0)]*len(initial.internal_energy_j)
    assert len(result.states)==len(result.times_s)==len(result.steps)+1
    for i,step in enumerate(result.steps):
        after=result.states[i+1]
        assert (step.start_s,step.end_s)==(result.times_s[i],result.times_s[i+1])
        for c in range(len(u)):
            u[c]+=F(float(step.face_energy_j[c]))-F(float(step.face_energy_j[c+1]))+F(float(step.cell_work_j[c]))
            assert abs(F(float(after.internal_energy_j[c]))-F(float(initial.internal_energy_j[c]))-u[c])<=F(1e-8)
            for j in range(initial.amounts_mol.shape[1]):
                n[c,j]+=F(float(step.face_species_mol[c,j]))-F(float(step.face_species_mol[c+1,j]))+F(float(step.reaction_species_mol[c,j]))
                assert abs(F(float(after.amounts_mol[c,j]))-F(float(initial.amounts_mol[c,j]))-n[c,j])<=F(1e-12)
    return u


def test_closed_cycle_three_steps_independent_adiabatic_oracle_and_work():
    op=moving();initial=op.base_model.state_from_temperatures([[1.]],[500.])
    errors=[];evidence=[]
    for denominator in (128,256,512):
        dt=1/denominator
        # Loose local relative control deliberately exposes the specified step
        # refinement; accuracy is independently checked below, not assumed.
        p=policy(initial_step_s=dt,maximum_step_s=dt,relative_tolerance=1e-3,
            amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-8,
            maximum_steps=2000,maximum_wall_seconds=90.)
        out=integrate(initial,op,start_s=0.,end_s=2.,breakpoints_s=op.breakpoints_s(0.,2.),policy=p)
        assert out.status=='completed',(out.status,out.reason)
        assert len(out.steps)==2*denominator
        assert 1. in out.times_s
        max_t=max_p=max_invariant=max_energy=0.
        for t,state in zip(out.times_s,out.states):
            assert np.array_equal(state.amounts_mol,initial.amounts_mol)
            target=500*imposed_normal(t)**(-8/22)
            decoded=op.evaluate(state,t)
            actual=decoded.gas_evaluation.temperatures_k[0]
            pressure=decoded.gas_evaluation.gas_states[0].pressure_pa
            volume=.1*.1*imposed_normal(t);p0=8*500/(.1*.1)
            max_t=max(max_t,abs(actual-target))
            max_p=max(max_p,abs(pressure/(8*target/volume)-1))
            max_invariant=max(max_invariant,abs((pressure/p0)*imposed_normal(t)**(30/22)-1))
            max_energy=max(max_energy,abs(state.internal_energy_j[0]-initial.internal_energy_j[0]-22*(target-500)))
        errors.append(max_t)
        evidence.append(dict(maximum_step_s=dt,accepted_steps=len(out.steps),
            max_temperature_error_k=max_t,max_relative_pressure_error=max_p,
            max_isentropic_invariant_error=max_invariant,max_energy_oracle_error_j=max_energy,
            temperature_error_reduction_ratio=(errors[-2]/errors[-1] if len(errors)>1 and errors[-1]!=0 else None)))
        print('ADIABATIC_REFINEMENT_PARTIAL '+json.dumps(evidence[-1],sort_keys=True,allow_nan=False),flush=True)
        assert_prefix(out)
        assert all(s.cell_work_j[0]>0 for s in out.steps if s.end_s<=1.)
        assert all(s.cell_work_j[0]<0 for s in out.steps if s.start_s>=1.)
        if denominator==512:
            assert max_t<=2e-4
            assert max_p<=2e-6 and max_invariant<=2e-6
            assert max_energy<=5e-3
            assert abs(out.states[-1].internal_energy_j[0]-initial.internal_energy_j[0])<=5e-3
    print('ADIABATIC_REFINEMENT_EVIDENCE '+json.dumps(evidence,sort_keys=True,allow_nan=False),flush=True)
    assert errors[0]>=3*errors[1] and errors[1]>=3*errors[2],errors


def test_two_chambers_unequal_pressure_actuator_work_and_shared_faces():
    op=moving(2,flow=True)
    initial=op.base_model.state_from_temperatures([[1.],[.5]],[500.,700.])
    sample=op.evaluate(initial,.5)
    # At q=.5: stretch(.95,1.05), dnormal/dt=(-.15,.15).
    volumes=np.array([.0095,.0105]);rates=np.array([-.0015,.0015])
    pressures=np.array([1*8*500/volumes[0],.5*8*700/volumes[1]])
    expected=-pressures*rates
    assert sample.mechanical_power_w==pytest.approx(expected,rel=0,abs=1e-8)
    assert abs(sum(sample.mechanical_power_w))>1.
    assert sum(sample.motion.volume_rates_m3_s)==pytest.approx(0.,rel=0,abs=1e-17)
    assert sample.rates.face_species_mol_s[1,0]!=0 and sample.rates.face_energy_w[1]!=0
    # Equal-pressure state on this same instantaneous geometry: normal internal
    # actuator work cancels, unlike the unequal-pressure state above.
    equal=op.base_model.state_from_temperatures([[.95],[1.05]],[500.,500.])
    assert sum(op.evaluate(equal,.5).mechanical_power_w)==pytest.approx(0.,rel=0,abs=1e-8)
    out=integrate(initial,op,start_s=0,end_s=1/64,policy=policy(initial_step_s=1/1024,maximum_step_s=1/1024,
        amount_absolute_tolerance_mol=1e-12,energy_absolute_tolerance_j=1e-8,maximum_wall_seconds=30.))
    assert out.status=='completed',(out.status,out.reason)
    assert_prefix(out)
    works=math.fsum(float(x) for s in out.steps for x in s.cell_work_j)
    assert math.fsum(out.states[-1].internal_energy_j)-math.fsum(initial.internal_energy_j)==pytest.approx(works,rel=0,abs=1e-8)
    assert out.states[-1].amounts_mol.sum()==pytest.approx(1.5,rel=0,abs=1e-12)


def test_zero_motion_matches_actual_base_including_boundary_and_trajectory():
    base=replace(chamber(2,flow=True),outer_surface_temperature_k=600.,outer_heat_source_ids=('manufactured:wall',))
    op=moving(2,base_model=base,constant=True)
    state=base.state_from_temperatures([[1.],[.5]],[500.,700.])
    a=op.evaluate(state,.4);b=base.evaluate(state,.4)
    assert np.array_equal(a.mechanical_power_w,np.zeros(2))
    for field in ('face_species_mol_s','face_energy_w','reaction_species_mol_s','cell_power_w'):
        assert np.array_equal(getattr(a.rates,field),getattr(b.rates,field))
    p=policy(initial_step_s=1/1024,maximum_step_s=1/1024,maximum_wall_seconds=30.)
    x=integrate(state,op,start_s=0,end_s=1/64,policy=p)
    y=integrate(state,base,start_s=0,end_s=1/64,policy=p)
    assert x.status==y.status=='completed'
    assert np.array_equal(x.states[-1].amounts_mol,y.states[-1].amounts_mol)
    assert np.array_equal(x.states[-1].internal_energy_j,y.states[-1].internal_energy_j)


@pytest.mark.parametrize('changes',[{'mechanical_regime':'free_brick'}, {'work_model_id':''},
    {'work_model_version':''},{'work_source_ids':()},{'allow_manufactured':False}])
def test_explicit_mechanical_source_and_manufactured_gates(changes):
    with pytest.raises(DeformingGasHeatError):moving(**changes)


def test_full_reference_geometry_and_all_gas_chamber_are_required():
    base=chamber()
    for bad in (replace(base,face_area_m2=.2,cell_widths_m=(.05,)),
                replace(base,gas_volumes_m3=(.005,)),chamber(2)):
        with pytest.raises(DeformingGasHeatError):moving(base_model=bad)


def test_caloric_mutation_is_not_erased_by_instantaneous_clone():
    op=moving();state=op.base_model.state_from_temperatures([[1.]],[500.])
    op.base_model.thermochemistry.pack_id='changed-after-construction'
    with pytest.raises(IntegrationError):op.evaluate(state,.5)


def test_domain_cancel_and_resource_keep_accepted_prefix():
    op=moving();state=op.base_model.state_from_temperatures([[1.]],[500.])
    with pytest.raises(IntegrationError):op.evaluate(state,3.)
    from sludge_sandbox.integration import ConservedState
    with pytest.raises(DomainExit):op.evaluate(ConservedState([[1.]],[1e9]),.5)
    p=policy(initial_step_s=.01,maximum_step_s=.01,maximum_steps=1,maximum_wall_seconds=30.)
    cancelled=integrate(state,op,start_s=0,end_s=2,policy=p,cancel=lambda:True)
    assert cancelled.status=='cancelled' and not cancelled.steps and cancelled.states[0] is state
    limited=integrate(state,op,start_s=0,end_s=2,policy=p)
    assert limited.status=='resource_limit' and len(limited.steps)==1
    assert_prefix(limited)


def test_pure_tangential_motion_has_work_and_deep_frozen_diagnostics():
    m=replace(motion(),normal_stretches_at_knots=((1.,),)*3,tangential_stretches_at_knots=(1.,.8,1.))
    op=moving(motion=m)
    state=op.base_model.state_from_temperatures([[1.]],[500.])
    out=op.evaluate(state,.5)
    # lambda_parallel=.9, rate=-.3/s; dx=.1, A0=.1 => Vdot=-.0054.
    expected_volume=.01*.9**2
    assert out.motion.volume_rates_m3_s[0]==pytest.approx(-.0054,rel=0,abs=1e-16)
    assert out.mechanical_power_w[0]==pytest.approx(-(8*500/expected_volume)*(-.0054),rel=0,abs=1e-8)
    for array in (out.mechanical_power_w,out.pressure_for_work_pa,out.motion.current.volumes_m3):
        with pytest.raises(ValueError):array.setflags(write=True)
    assert set(op.work_source_ids)<=set(out.source_ids)
    assert out.work_model_identity==op.work_model_identity
    assert op.material_qualified is False


def test_nonzero_second_order_reaction_uses_current_bulk_not_reference():
    from test_gas_heat_model import gas_reaction
    thermo=caloric();network=gas_reaction(thermo)
    reaction=replace(network.reactions[0],kinetics=replace(network.reactions[0].kinetics,orders={'A':2.}))
    network=replace(network,reactions=(reaction,))
    base=chamber()
    base=replace(base,thermochemistry=thermo,species_order=('A','B'),molar_masses_kg_mol={'A':.012,'B':.012},
        effective_diffusivities_m2_s={'A':(0.,),'B':(0.,)},reaction_network=network)
    op=moving(base_model=base)
    state=base.state_from_temperatures([[.1,0.]],[500.])
    out=op.evaluate(state,.5)
    # rate V*0.2*(N_A/V)^2, normalized to explicit 1 mol/m3.
    expected=.2*.1**2/(.01*.9)
    assert out.rates.reaction_species_mol_s[0]==pytest.approx([-expected,expected],rel=0,abs=1e-12)
    assert np.array_equal(out.rates.cell_power_w,out.mechanical_power_w)


def test_open_flow_uses_donor_enthalpy_once_separate_from_boundary_motion_work():
    from sludge_sandbox.gas_transport import ideal_gas_reservoir
    base=chamber()
    reservoir=ideal_gas_reservoir(pressure_pa=2e5,temperature_k=600.,mole_fractions={'A':1.},
        molar_masses_kg_mol={'A':.012},gas_constant_j_mol_k=8.)
    base=replace(base,permeability_m2=(1e-16,),outer_reservoir=reservoir,outer_reservoir_source_ids=('manufactured:reservoir',))
    op=moving(base_model=base)
    state=base.state_from_temperatures([[1.]],[500.])
    out=op.evaluate(state,.5)
    ndot=out.rates.face_species_mol_s[-1,0]
    assert ndot>0
    assert out.rates.face_energy_w[-1]==pytest.approx(ndot*30*(500-298.15),rel=0,abs=1e-9)
    assert out.rates.cell_power_w[0]==pytest.approx(-(8*500/.009)*(-.003),rel=0,abs=1e-8)
