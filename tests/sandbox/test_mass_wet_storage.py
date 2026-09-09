"""Manufactured liquid response seam, real dry/ideal source functions; no liquid EOS."""
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import pytest
from test_mass_storage_bridge import fixture,MO,MN,R,REPOSITORY
from sludge_sandbox.mass_wet_storage import WetMixedStorage,WaterElementConvention
from sludge_sandbox.phase_storage import IdealGasPhase,InversePolicy
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.reaction_reference import Component,Anchor
from sludge_sandbox.water_properties import WaterProperties,WaterState,WaterResponse


def setup(monkeypatch):
    dry,_=fixture(monkeypatch);old=dry.storage
    vapor=IdealWaterVapor(REPOSITORY/'data/sandbox/water')
    phases=dict(old.fluid_template.gas_phases);phases['H2O']=IdealGasPhase(vapor,vapor.molar_mass_kg_mol)
    env=replace(old.fluid_template.envelope,temperature_range_k=(293.,400.),gas_u_error_j_mol={'O2':1e-9,'N2':1e-9,'H2O':1e-7},gas_cv_lower_j_mol_k={'O2':20.,'N2':20.,'H2O':20.},liquid_u_error_j_mol=1e-8,liquid_v_error_m3_mol=0.,liquid_abs_du_dp_bound_j_mol_pa=0.)
    mechanical=replace(old.fluid_template.mechanical,gas_species_ids=('O2','N2','H2O'))
    fluid=replace(old.fluid_template,mechanical=mechanical,gas_phases=phases,envelope=env)
    convention=WaterElementConvention.load(REPOSITORY/'data/sandbox/research/water-element-convention-v1/facts.json')
    net=old.reference.network;els=(*net.elements,'H')
    comps=tuple(replace(c,element_mass_fractions=(*c.element_mass_fractions,F())) for c in net.components)
    comps+= (Component('H2O','gas',convention.fractions(els,vapor.molar_mass_kg_mol),('ciaaw-2024-abridged-atomic-weights',)),)
    reactions=tuple(replace(r,mass_change_kg_per_kg_extent=(*r.mass_change_kg_per_kg_extent,F())) for r in net.reactions)
    anchors=net.anchors+(Anchor('H2O',F(phases['H2O'].evaluate(300.,100000.).enthalpy_j_mol)/F(vapor.molar_mass_kg_mol),net.reference_convention,F(300),F(100000),'gas',vapor.source_ids),)
    solution=replace(net,elements=els,components=comps,reactions=reactions,anchors=anchors).solve()
    calls=[]
    def liquid(w,t,p,*,phase):
        assert phase=='liquid';calls.append((t,p))
        # Explicit artificial constant-volume/constant-Cp liquid using the same
        # water reference object. This is not the measured water EOS.
        v=1.8e-5;u=75*t-300000;mass=w.reference.molar_mass_kg_mol;offset=w.reference.energy_offset_j_mol
        return WaterState(t,(u+p*v-offset)/mass,(u-offset)/mass,75/mass,75/mass,w.reference,'manufactured-liquid-seam',p,'liquid',mass/v,0.,0.,0.,implementation=w.implementation)
    def response(w,t,p,*,phase):return WaterResponse(liquid(w,t,p,phase=phase),0.,0.,0.,0.,0.,0.,method_id='manufactured-constant-liquid-response')
    monkeypatch.setattr(WaterProperties,'state_tp',liquid)
    monkeypatch.setattr(WaterProperties,'state_tp_response',response)
    monkeypatch.setattr(WaterProperties,'_solve',lambda *a,**k:(_ for _ in ()).throw(AssertionError('native_EOS_forbidden')))
    st=WetMixedStorage(fluid,old.solids,solution,(294.,350.),.001,convention)
    state=st.state((.01,.002),.2,(.2,.2,.001),0.)
    return st,state,calls


def test_actual_fluid_closure_and_mass_total_U(monkeypatch):
    st,state,calls=setup(monkeypatch);out=st.evaluate(state,305.)
    assert calls and out.fluid.mechanical.liquid_inventory_mol==.2
    vs=F(.01)*F(.001)+F(.002)*F(.0005);available=F(.001)-vs
    vg=available-F(.2)*F(1.8e-5)
    pressure=sum(map(F,state.gas_amounts_mol))*F(R)*305/vg
    assert abs(F(out.pressure_pa)-pressure)<=F(out.pressure_error_pa)
    assert abs(F(out.gas_volume_m3)-vg)<F(1e-18)
    assert out.available_pore_volume_m3>out.gas_volume_m3
    net=st.reference.network
    solid=sum((F(m)*(h+F(s.cp_j_kg_k)*5-F(100000)*F(s.volume_m3_kg)) for m,s,h in zip(state.solid_mass_kg,st.solids,st.reference.particular_h0_j_kg)),F())
    gas=sum((F(n)*F(st.fluid_template.gas_phases[k]._curve.internal_energy_j_mol(305.)) for k,n in zip(st.gas_ids,state.gas_amounts_mol)),F())
    expected=solid+gas+F(.2)*(75*305-300000)
    assert abs(F(out.total_internal_energy_j)-expected)<=F(out.energy_error_j)
    # The mechanical root has a saved nonzero volume residual. Account for
    # its exact pressure-work contribution rather than claiming an exact root.
    hu=F(out.total_enthalpy_j)-F(out.total_internal_energy_j)-F(out.pressure_pa)*F(.001)
    assert abs(hu-F(out.pressure_pa)*F(out.fluid.mechanical.volume_residual_m3))<F(2e-10)
    target=replace(state,internal_energy_j=float(expected))
    inverse=st.invert(target,InversePolicy(1e-6,1e-6,100))
    assert abs(inverse.point.temperature_k-305)<=inverse.temperature_error_bound_k
    assert abs(inverse.energy_residual_j)<=1e-6


def test_mass_volume_error_chain_and_source_rejection(monkeypatch,tmp_path):
    st,state,_=setup(monkeypatch)
    perturbed=replace(st,bulk_volume_error_m3=1e-12)
    p=perturbed.evaluate(perturbed.state(state.solid_mass_kg,state.liquid_water_mol,state.gas_amounts_mol,0.),305.)
    assert p.pressure_error_pa<=p.global_pressure_error_pa and p.extra_pressure_error_pa>0
    baseline=st.evaluate(state,305.)
    assert p.pressure_error_pa>baseline.pressure_error_pa
    huge=replace(st,bulk_volume_error_m3=1e-3)
    with pytest.raises(ValueError,match='volume_uncertainty'):huge.evaluate(huge.state(state.solid_mass_kg,.2,state.gas_amounts_mol,0.),305.)
    facts=tmp_path/'facts.json';facts.write_text(st.water_element_convention.facts_json)
    copied=WaterElementConvention.load(facts)
    facts.write_text(st.water_element_convention.facts_json+' ')
    with pytest.raises(ValueError,match='source_changed'):copied.fractions(('H','O'),.018)


def test_dry_limit_and_phase_inventory_feedback(monkeypatch):
    st,state,calls=setup(monkeypatch)
    dry=replace(state,liquid_water_mol=0.)
    before=len(calls);d=st.evaluate(dry,305.)
    assert len(calls)==before and d.gas_volume_m3==d.available_pore_volume_m3
    wet=st.evaluate(state,305.)
    assert wet.pressure_pa>d.pressure_pa
    # Internal redistribution of the SAME water, fixed U: no added latent source.
    initial=replace(state,internal_energy_j=wet.total_internal_energy_j)
    shifted=replace(initial,liquid_water_mol=.199,gas_amounts_mol=(.2,.2,.002))
    inv=st.invert(shifted,InversePolicy(1e-6,1e-6,100))
    assert inv.point.temperature_k<305
    assert abs(inv.energy_residual_j)<1e-6
    assert abs((shifted.liquid_water_mol+shifted.gas_amounts_mol[2])-(initial.liquid_water_mol+initial.gas_amounts_mol[2]))<1e-16


def test_false_water_elements_and_reference_refused(monkeypatch):
    st,state,_=setup(monkeypatch);net=st.reference.network
    comps=list(net.components);comps[-1]=replace(comps[-1],element_mass_fractions=(F(),F(1),F(),F()))
    wrong=replace(net,components=tuple(comps)).solve()
    with pytest.raises(ValueError,match='water_element_composition'):replace(st,reference=wrong)
    anchors=list(net.anchors);anchors[-1]=replace(anchors[-1],h0_j_kg=anchors[-1].h0_j_kg+1)
    with pytest.raises(ValueError,match='actual_gas_reference_anchor'):replace(st,reference=replace(net,anchors=tuple(anchors)).solve())
    for value in (True,float('nan'),-1.):
        with pytest.raises(ValueError):replace(state,liquid_water_mol=value)
    with pytest.raises(ValueError,match='wet_inventory_shape'):st.evaluate(replace(state,gas_amounts_mol=(.2,.2)),305.)


def test_extra_liquid_pressure_energy_error_not_dropped(monkeypatch):
    st,state,_=setup(monkeypatch)
    env=replace(st.fluid_template.envelope,liquid_abs_du_dp_bound_j_mol_pa=1e-6)
    st=replace(st,fluid_template=replace(st.fluid_template,envelope=env),bulk_volume_error_m3=1e-12)
    state=st.state(state.solid_mass_kg,state.liquid_water_mol,state.gas_amounts_mol,0.)
    out=st.evaluate(state,305.)
    added=F(state.liquid_water_mol)*F(env.liquid_abs_du_dp_bound_j_mol_pa)*F(out.extra_pressure_error_pa)
    assert F(out.energy_error_j)>=F(out.fluid.energy_error_bound_j)+added
    assert out.extra_pressure_error_pa>0 and added>0


def test_balanced_water_chemical_channel_explicitly_refused(monkeypatch):
    from sludge_sandbox.reaction_reference import Reaction
    st,state,_=setup(monkeypatch);net=st.reference.network;comps=list(net.components)
    comps[0]=replace(comps[0],element_mass_fractions=comps[-1].element_mass_fractions)
    h=st.reference.particular_h0_j_kg
    reaction=Reaction('artificial-water-production',(-1,0,0,0,1),h[-1]-h[0],'kg_A',('manufactured-negative-control',))
    extra=Anchor('B',h[1],net.reference_convention,F(300),F(100000),'solid',('manufactured-extra-anchor',))
    reference=replace(net,components=tuple(comps),reactions=(reaction,),anchors=(*net.anchors,extra)).solve()
    assert not reference.nullspace_h0_j_kg
    with pytest.raises(ValueError,match='water_chemical_reactions_not_admitted'):replace(st,reference=reference)


def test_actual_backend_type_drift_and_global_domain_guard(monkeypatch):
    st,state,_=setup(monkeypatch)
    class DifferentWater(WaterProperties):pass
    object.__setattr__(st.fluid_template.gas_phases['H2O'].caloric._water,'__class__',DifferentWater)
    with pytest.raises(ValueError):st.evaluate(state,305.)
    st,state,_=setup(monkeypatch)
    # Positive pore uncertainty can still be too large to certify either root
    # inside the original source pressure domain; reject before local tightening.
    large=replace(st,bulk_volume_error_m3=1e-4)
    with pytest.raises(ValueError,match='global_pressure_uncertainty_outside_domain'):
        large.evaluate(large.state(state.solid_mass_kg,.2,state.gas_amounts_mol,0.),305.)


def test_aggregated_sources_include_numerical_envelope_and_constants(monkeypatch):
    st,_,_=setup(monkeypatch)
    assert set(st.fluid_template.envelope.source_ids).issubset(st.source_ids)
    assert set(st.fluid_template.mechanical.constant_source_ids).issubset(st.source_ids)


@pytest.mark.parametrize('sign',(-1,1))
@pytest.mark.parametrize('field',('solid_mass_kg','liquid_water_mol','gas_amounts_mol'))
def test_nonzero_inventory_cannot_underflow_to_zero(field,sign):
    from sludge_sandbox.mass_wet_storage import WetMixedState
    values=dict(solid_mass_kg=(0.,),liquid_water_mol=0.,gas_amounts_mol=(0.,),internal_energy_j=0.,energy_model_identity='a'*64)
    value=F(sign,10**400)
    values[field]=value if field=='liquid_water_mol' else (value,)
    with pytest.raises(ValueError):WetMixedState(**values)
