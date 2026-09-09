from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import math
import json
import hashlib
import pytest
from sludge_sandbox.mass_storage_bridge import MixedState, MassSolid, MixedStorage, MixedCell, MixedError, integrate_closed
from sludge_sandbox.reaction_reference import Component,Reaction,Anchor,ReactionReferenceNetwork
from sludge_sandbox.phase_storage import IdealGasPhase, InversePolicy
from sludge_sandbox.rigid_storage import DeclaredNumericalEnvelope, RigidStorage
from sludge_sandbox.rigid_water_gas import RigidWaterGas,PressurePolicy
from sludge_sandbox.thermochemistry import ShomateGas,ShomateSegment
from sludge_sandbox.water_properties import load_water_properties

REPOSITORY=Path(__file__).resolve().parents[2]
R=8.31446261815324
MO=.0319988
MN=.0280134

def fixture(monkeypatch):
    water=load_water_properties(REPOSITORY/'data/sandbox/water')
    def forbidden(*args,**kwargs):raise AssertionError('native_water_forbidden')
    for method in ('state_tp','state_tp_response','saturation_at_temperature'):
        if hasattr(type(water),method):monkeypatch.setattr(type(water),method,forbidden)
    # Tracked extracted facts suffice for numerical tests in a clean checkout.
    # Full cached source revalidation is a separate evidence command.
    source_rows=json.loads((REPOSITORY/'data/sandbox/research/mass-storage-bridge-v1/gas_molar_mass_facts.json').read_text())
    sources={row['species_id']:(row['source_id'],row['cache_sha256']) for row in source_rows}
    assert {row['species_id']:row['nominal_molar_mass_kg_mol'] for row in source_rows}=={'O2':MO,'N2':MN}
    phases={}
    for name,cp,mass in (('O2',30.,MO),('N2',29.,MN)):
        curve=ShomateGas(name,(ShomateSegment((250.,600.),(cp,0.,0.,0.,0.,0.,0.,0.),0.,R,('manufactured-constant-cp',)),),'manufactured_test_fixture',('manufactured-constant-cp',))
        phases[name]=IdealGasPhase(curve,mass,0,sources[name])
    mech=RigidWaterGas(water,('O2','N2'),.001,(1e3,1e7),'planar_interface_no_capillary_pressure',PressurePolicy(1e-12,1e-5,100))
    env=DeclaredNumericalEnvelope((290.,500.),(1e3,1e7),0.,0.,0.,{'O2':1e-9,'N2':1e-9},{'O2':20.,'N2':20.},'manufactured-explicit-error-envelope',('manufactured-envelope',))
    fluid=RigidStorage(mech,phases,env,True)
    comps=tuple(Component(name,phase,els,('manufactured-element-composition',)) for name,phase,els in (
        ('A','solid',(1,0,0)),('B','solid',(F(1,2),F(1,2),0)),('O2','gas',(0,1,0)),('N2','gas',(0,0,1))))
    convention='nist_298.15K_element_standard_formation'
    anchors=[Anchor('A',F(),convention,F(300),F(100000),'solid',('manufactured-coordinate-A-zero',))]
    for name in ('O2','N2'):
        h=phases[name].evaluate(300.,100000.).enthalpy_j_mol
        anchors.append(Anchor(name,F(h)/F(phases[name].molar_mass_kg_mol),convention,F(300),F(100000),'gas',('actual-bound-gas-reference',)))
    network=ReactionReferenceNetwork(('C','O','N'),comps,(Reaction('artificial-oxidation',(-1,2,-1,0),-200000,'kg_A_consumed',('manufactured-q',)),),F(300),F(100000),'kg_of_declared_components',convention,'manufactured_test_fixture','exact-defined-nominal-parameters',('manufactured-network',),tuple(anchors))
    storage=MixedStorage(fluid,(MassSolid('A',1000.,.001,('manufactured-solid-A',)),MassSolid('B',1200.,.0005,('manufactured-solid-B',))),network.solve(),(290.,500.),.001)
    cell=MixedCell(storage,InversePolicy(1e-7,1e-7,80),.2,.2,('manufactured-mass-extent-rate',))
    proto=storage.state((.01,0.),(.2,.2),0.)
    initial=replace(proto,internal_energy_j=storage.evaluate(proto,300.).internal_energy_j)
    return cell,initial


def oracle(t):
    a=.01;b=MO*.2;c=.2/(MO*.2)
    z=math.exp(-c*(b-a)*t)
    x=a*b*(1-z)/(b-a*z)
    mA=a-x;mB=2*x;n=.2-x/MO
    hB=(-200000+30*300/MO)/2
    U0=a*(-100000*.001)+.2*(30-R)*300+.2*(29-R)*300
    uref=mA*(-100000*.001)+mB*(hB-100000*.0005)+n*(30-R)*300+.2*(29-R)*300
    capacity=mA*1000+mB*1200+n*(30-R)+.2*(29-R)
    T=300+(U0-uref)/capacity
    P=(n+.2)*R*T/(.001-a*.001)
    return x,T,P


def test_coupled_actual_storage_and_closed_trajectory(monkeypatch):
    cell,state=fixture(monkeypatch)
    results=[integrate_closed(cell,state,duration_s=.1,steps=count) for count in (8,16)]
    errors=[]
    for run,count in zip(results,(8,16)):
        assert run.status=='completed',run.reason
        sums_s=[F(),F()];sums_n=[F(),F()]
        for i,(s,obs,ledger) in enumerate(zip(run.states[1:],run.observations,run.ledgers),1):
            x,t,p=oracle(i*.1/count)
            assert abs(s.solid_mass_kg[0]-(.01-x))<1e-8
            assert abs(s.fluid_amounts_mol[0]-(.2-x/MO))<4e-7
            assert abs(obs.inverse.point.temperature_k-t)<1e-3
            assert abs(obs.inverse.point.pressure_pa-p)<1.
            assert s.internal_energy_j==state.internal_energy_j and ledger[3]==0.
            assert obs.inverse.temperature_error_bound_k<=1e-7
            assert obs.chemical_reference_power_w!=0 and obs.external_power_w==0
            for j in range(2):
                sums_s[j]+=F(ledger[1][j]);sums_n[j]+=F(ledger[2][j])
                assert abs(F(s.solid_mass_kg[j])-F(state.solid_mass_kg[j])-sums_s[j])<F(1e-15)
                assert abs(F(s.fluid_amounts_mol[j])-F(state.fluid_amounts_mol[j])-sums_n[j])<F(1e-14)
            assert abs(s.solid_mass_kg[0]+s.solid_mass_kg[1]/2-.01)<1e-15
            assert abs(s.solid_mass_kg[1]/2+s.fluid_amounts_mol[0]*MO-.2*MO)<1e-15
        errors.append(abs(run.states[-1].solid_mass_kg[0]-(.01-oracle(.1)[0])))
    assert errors[1]<errors[0]/3
    assert abs(results[-1].observations[-1].inverse.point.temperature_k-300)>1


def test_zero_oxygen_no_reaction_and_hu_relation(monkeypatch):
    cell,state=fixture(monkeypatch)
    proto=replace(state,fluid_amounts_mol=(0.,.2))
    point=cell.storage.evaluate(proto,310.)
    s=replace(proto,internal_energy_j=point.internal_energy_j)
    out=cell.evaluate(s)
    assert out.extent_kg_s==0 and out.gas_mol_s==(0.,0.)
    assert abs(point.enthalpy_j-point.internal_energy_j-point.pressure_pa*.001)<1e-10
    run=integrate_closed(cell,s,duration_s=.1,steps=2)
    assert run.status=='completed' and run.states[-1]==s


def test_reference_and_shape_and_domain_rejection(monkeypatch):
    cell,state=fixture(monkeypatch)
    with pytest.raises(ValueError):cell.storage.invert(replace(state,internal_energy_j=-1e8),cell.inverse_policy)
    with pytest.raises(ValueError):cell.storage.check(replace(state,solid_mass_kg=(.01,)))
    gas=dict(cell.storage.fluid_template.gas_phases)
    gas['O2']=replace(gas['O2'],molar_mass_kg_mol=.032)
    with pytest.raises(ValueError,match='reference_anchor'):
        replace(cell.storage,fluid_template=replace(cell.storage.fluid_template,gas_phases=gas))
    with pytest.raises(ValueError):MixedState((True,),(.2,),0.,'a'*64)


def test_failed_step_retains_complete_prefix(monkeypatch):
    cell,state=fixture(monkeypatch)
    run=integrate_closed(replace(cell,rate_constant_per_s=1000.),state,duration_s=1.,steps=1)
    assert run.status=='failed' and run.states==(state,) and not run.ledgers


def test_negative_control_oxygen_source_and_duplicate_heat_detected(monkeypatch):
    cell,state=fixture(monkeypatch)
    original=MixedCell.evaluate
    def missing_oxygen(self,s):
        return replace(original(self,s),gas_mol_s=(0.,0.))
    with monkeypatch.context() as patch:
        patch.setattr(MixedCell,'evaluate',missing_oxygen)
        wrong=integrate_closed(cell,state,duration_s=.1,steps=8)
    assert wrong.status=='completed'
    s=wrong.states[-1]
    assert abs(s.solid_mass_kg[1]/2+s.fluid_amounts_mol[0]*MO-.2*MO)>1e-5
    def duplicate_heat(self,s):
        value=original(self,s)
        return replace(value,external_power_w=-value.chemical_reference_power_w)
    with monkeypatch.context() as patch:
        patch.setattr(MixedCell,'evaluate',duplicate_heat)
        heated=integrate_closed(cell,state,duration_s=.1,steps=8)
    assert heated.status=='completed'
    assert abs(heated.states[-1].internal_energy_j-state.internal_energy_j)>1.
    assert abs(heated.observations[-1].inverse.point.temperature_k-oracle(.1)[1])>.1


def test_missing_offset_and_mutated_provider_rejected(monkeypatch):
    cell,state=fixture(monkeypatch)
    solution=cell.storage.reference
    bad=replace(solution,particular_h0_j_kg=(F(),)*4)
    with pytest.raises(ValueError,match='not_recomputed'):
        replace(cell.storage,reference=bad)
    phase=cell.storage.fluid_template.gas_phases['O2']
    object.__setattr__(phase,'molar_mass_kg_mol',.032)
    with pytest.raises(ValueError,match='content_changed'):
        cell.evaluate(state)


def test_named_gas_elements_follow_labels_not_column_positions(monkeypatch):
    cell,state=fixture(monkeypatch)
    net=cell.storage.reference.network
    components=tuple(replace(c,element_mass_fractions=(c.element_mass_fractions[1],c.element_mass_fractions[0],c.element_mass_fractions[2])) for c in net.components)
    permuted=replace(net,elements=('O','C','N'),components=components).solve()
    moved=replace(cell.storage,reference=permuted)
    state=moved.state(state.solid_mass_kg,state.fluid_amounts_mol,state.internal_energy_j)
    assert abs(moved.invert(state,cell.inverse_policy).point.temperature_k-300)<1e-7


def test_named_oxygen_must_not_be_carbon_in_reference(monkeypatch):
    cell,state=fixture(monkeypatch)
    net=cell.storage.reference.network
    # Swap C/O compositions throughout: AB stays exactly conserved, but named O2 becomes carbon.
    components=tuple(replace(c,element_mass_fractions=(c.element_mass_fractions[1],c.element_mass_fractions[0],c.element_mass_fractions[2])) for c in net.components)
    altered=replace(net,components=components).solve()
    with pytest.raises(MixedError,match='element|composition'):
        replace(cell.storage,reference=altered)


def test_energy_acceptance_uses_unrounded_difference(monkeypatch):
    cell,state=fixture(monkeypatch)
    sample=cell.storage.evaluate(state,300.)
    # An exact affine energy path centered at the first bisection midpoint.
    # Test the inverse's numerical acceptance, not a physical provider claim.
    def affine(self,state,t):
        e=100*(t-395)+1
        return replace(sample,temperature_k=t,internal_energy_j=e,
                       energy_error_j=0.,minimum_heat_capacity_j_k=100.,closed_heat_capacity_j_k=100.)
    monkeypatch.setattr(MixedStorage,'evaluate',affine)
    state=replace(state,internal_energy_j=-2**-54)
    out=cell.storage.invert(state,InversePolicy(1.,1.,80))
    assert abs(F(out.point.internal_energy_j)-F(state.internal_energy_j))+F(out.point.energy_error_j)<=F(1.)


def test_heat_identified_by_anchors_is_used_or_refused_at_construction(monkeypatch):
    cell,state=fixture(monkeypatch)
    old=cell.storage.reference;net=old.network
    b=Anchor('B',old.particular_h0_j_kg[1],net.reference_convention,net.reference_temperature_k,net.reference_pressure_pa,'solid',('manufactured:equivalent-anchor',))
    net=replace(net,anchors=net.anchors+(b,),reactions=(replace(net.reactions[0],enthalpy_j_per_kg_extent=None),))
    solution=net.solve(required_outputs=((-1,2,-1,0),))
    assert solution.identified_value((-1,2,-1,0))==F(-200000)
    storage=replace(cell.storage,reference=solution)
    cell=replace(cell,storage=storage)
    state=storage.state(state.solid_mass_kg,state.fluid_amounts_mol,state.internal_energy_j)
    # Either constructor should explicitly reject the unsupported heat form,
    # or evaluate must use the identified heat instead of float(None).
    out=cell.evaluate(state)
    assert out.chemical_reference_power_w!=0
