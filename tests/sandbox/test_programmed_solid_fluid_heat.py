from dataclasses import replace
import math
import numpy as np
import pytest
from scipy.optimize import brentq

from sludge_sandbox.boundary_program import BoundaryProgram,ProgramIdentity
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from sludge_sandbox.programmed_solid_fluid_heat import ProgrammedSolidFluidHeat,ProgrammedSolidFluidHeatError
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.integration import DomainExit,IntegrationPolicy,integrate
from test_solid_fluid_heat import ingredients,solid_host


def program(**kw):
    values=dict(identity=ProgramIdentity(program_id='virtual:oven',version='1',classification='virtual_design_choice',
        source_ids=('virtual:oven',)),knot_times_s=(0.,.05,.1,.15),gas_temperature_k=(300.,310.,310.,295.),
        radiation_temperature_k=(300.,)*4,total_pressure_pa=(3e5,)*4,species_order=('fixture','H2O'),
        mole_fractions=((1.,0.),)*4)
    values.update(kw)
    return BoundaryProgram(**values)


def wrapped(ingredients,**kw):
    host=solid_host(ingredients)
    host=replace(host,transport=replace(host.transport,conductivities_w_m_k=(1.,),inverse_policy=InversePolicy(1e-6,1e-6,100)))
    values=dict(base_model=host,program=program(),convection_w_m2_k=20.,emissivity=0.,
        stefan_boltzmann_w_m2_k4=5.670374419e-8,coefficient_set_id='manufactured:film',coefficient_version='1',
        coefficient_classification='manufactured',coefficient_source_ids=('manufactured:film',),allow_manufactured=True,
        surface_policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=200))
    values.update(kw)
    return ProgrammedSolidFluidHeat(**values)


def test_half_cell_film_and_full_inverse_once(ingredients,monkeypatch):
    op=wrapped(ingredients)
    state=op.base_model.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    from sludge_sandbox.solid_fluid_heat import SolidFluidHeat
    original=SolidFluidHeat.decode_inverse
    calls=[]
    def counted(self,s):calls.append(s);return original(self,s)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',counted)
    out=op.evaluate(state,.05)
    expected=(200*300+20*310)/220
    assert out.surface_temperature_k==pytest.approx(expected,rel=0,abs=1e-7)
    assert out.conductive_into_cell_w==pytest.approx(.01*(310-300)/(.005/1+1/20),rel=0,abs=1e-8)
    assert out.rates.face_energy_w[-1]==pytest.approx(-out.conductive_into_cell_w,rel=0,abs=1e-10)
    assert out.storage_inverses is out.base_evaluation.storage_inverses
    assert len(calls)==1


def test_nonlinear_radiation_independent_root(ingredients):
    op=wrapped(ingredients,emissivity=.8,program=program(radiation_temperature_k=(400.,)*4))
    state=op.base_model.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    out=op.evaluate(state,.05)
    expected=brentq(lambda t:200*(t-300)-20*(310-t)-.8*5.670374419e-8*(400**4-t**4),300,400)
    assert out.surface_temperature_k==pytest.approx(expected,rel=0,abs=1e-7)
    assert abs(out.surface_balance_residual_w)<=out.surface_balance_limit_w


def test_real_ramp_hold_cooling_nodes_and_energy_ledger(ingredients):
    op=wrapped(ingredients)
    initial=op.base_model.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    out=integrate(initial,op,start_s=0,end_s=.15,breakpoints_s=op.breakpoints_s(0,.15),
        policy=IntegrationPolicy(initial_step_s=.005,maximum_step_s=.005,minimum_step_s=1e-10,
            relative_tolerance=1e-8,amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-6,
            amount_scale_mol=1.,energy_scale_j=1.,maximum_steps=200,maximum_rejections=20,maximum_wall_seconds=90))
    assert out.status=='completed',(out.status,out.reason)
    capacity=100+.01*(30-8.31446261815324)
    lam=(.01/(.005+1/20))/capacity
    expected=300.
    for a,b,ta,tb in zip((0.,.05,.1),(.05,.1,.15),(300.,310.,310.),(310.,310.,295.)):
        dt=b-a;slope=(tb-ta)/dt
        expected=expected*math.exp(-lam*dt)+ta*(-math.expm1(-lam*dt))+slope*(dt+math.expm1(-lam*dt)/lam)
        index=out.times_s.index(b)
        decoded=op.base_model.decode(out.states[index])[0]
        assert decoded.mechanical.temperature_k==pytest.approx(expected,rel=0,abs=1e-6)
    net=-math.fsum(s.face_energy_j[-1] for s in out.steps)
    assert out.states[-1].internal_energy_j[0]-initial.internal_energy_j[0]==pytest.approx(net,rel=0,abs=1e-7)


def test_actual_pressure_composition_and_inflow_donor_enthalpy(ingredients):
    op=wrapped(ingredients,convection_w_m2_k=0.)
    host=op.base_model
    host=replace(host,transport=replace(host.transport,permeability_m2=(1e-15,)))
    op=replace(op,base_model=host,program=program(total_pressure_pa=(1e5,4e5,4e5,1e5),
        mole_fractions=((1.,0.),(.5,.5),(0.,1.),(1.,0.))))
    state=host.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    incoming=op.evaluate(state,.05);outgoing=op.evaluate(state,0.)
    assert sum(incoming.rates.face_species_mol_s[-1])<0
    assert sum(outgoing.rates.face_species_mol_s[-1])>0
    indices=[op.species_order.index(n) for n in op.gas_species_order]
    phases=host.storages[0].fluid_template.gas_phases
    expected=sum(incoming.rates.face_species_mol_s[-1,i]*phases[n]._curve.enthalpy_j_mol(310.) for n,i in zip(op.gas_species_order,indices))
    assert incoming.rates.face_energy_w[-1]==pytest.approx(expected,rel=2e-12,abs=1e-12)
    assert np.all(incoming.rates.face_species_mol_s[:,[0,2]]==0)
    assert op.evaluate(state,.1).rates.face_species_mol_s[-1,op.species_order.index('fixture')]==0


def test_domain_duplicate_and_manufactured_configuration(ingredients):
    op=wrapped(ingredients)
    state=op.base_model.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    with pytest.raises(DomainExit):op(state,.2)
    with pytest.raises(ProgrammedSolidFluidHeatError,match='manufactured'):replace(op,allow_manufactured=False)
    host=replace(op.base_model,transport=replace(op.transport,outer_surface_temperature_k=305.,outer_heat_source_ids=('virtual:other',)))
    with pytest.raises(ProgrammedSolidFluidHeatError,match='duplicated'):replace(op,base_model=host)


def test_zero_conductivity_blocks_film_but_not_inflow_enthalpy(ingredients):
    op=wrapped(ingredients)
    host=replace(op.base_model,transport=replace(op.transport,conductivities_w_m_k=(0.,),permeability_m2=(1e-15,)))
    op=replace(op,base_model=host,program=program(total_pressure_pa=(4e5,)*4))
    state=host.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    out=op.evaluate(state,.05)
    assert out.conductive_into_cell_w==0
    assert out.surface_temperature_k==pytest.approx(310.,rel=0,abs=1e-7)
    assert out.rates.face_energy_w[-1]<0
    assert out.rates.face_species_mol_s[-1,op.species_order.index('fixture')]<0


def test_gas_program_order_must_match_and_sources_remain_explicit(ingredients):
    op=wrapped(ingredients)
    with pytest.raises(ProgrammedSolidFluidHeatError,match='ordered_boundary_species'):
        replace(op,program=program(species_order=('H2O','fixture')))
    for kw in ({'coefficient_source_ids':()}, {'coefficient_version':''}, {'emissivity':1.01}, {'stefan_boltzmann_w_m2_k4':0}):
        with pytest.raises(ProgrammedSolidFluidHeatError):replace(op,**kw)
    assert 'virtual:oven' in op.source_ids
    assert 'manufactured:film' in op.source_ids
    assert not op.material_qualified


def test_actual_inflow_atmosphere_program_integrates_species_and_energy(ingredients):
    op=wrapped(ingredients,convection_w_m2_k=0.)
    host=replace(op.base_model,transport=replace(op.transport,permeability_m2=(1e-15,)))
    op=replace(op,base_model=host,program=program(knot_times_s=(0.,.001,.002),
        gas_temperature_k=(300.,304.,300.),radiation_temperature_k=(300.,)*3,
        total_pressure_pa=(4e5,)*3,mole_fractions=((1.,0.),(.5,.5),(0.,1.))))
    initial=host.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    out=integrate(initial,op,start_s=0,end_s=.002,breakpoints_s=op.breakpoints_s(0,.002),
        policy=IntegrationPolicy(initial_step_s=.0005,maximum_step_s=.0005,minimum_step_s=1e-10,
            relative_tolerance=1e-8,amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-6,
            amount_scale_mol=.01,energy_scale_j=1.,maximum_steps=100,maximum_rejections=20,maximum_wall_seconds=90))
    assert out.status=='completed',(out.status,out.reason)
    assert .001 in out.times_s
    for before,after,step in zip(out.states,out.states[1:],out.steps):
        assert after.amounts_mol[0]-before.amounts_mol[0]==pytest.approx(-step.face_species_mol[-1],rel=0,abs=1e-12)
        assert after.internal_energy_j[0]-before.internal_energy_j[0]==pytest.approx(-step.face_energy_j[-1],rel=0,abs=1e-7)
    assert out.states[-1].amounts_mol[0,1]>0
    assert np.array_equal(out.states[-1].amounts_mol[:,[0,2]],initial.amounts_mol[:,[0,2]])
    final=host.decode(out.states[-1])[0]
    assert final.mechanical.gas_inventory_mol['H2O']>0
    assert final.mechanical.pressure_pa!=host.decode(initial)[0].mechanical.pressure_pa
