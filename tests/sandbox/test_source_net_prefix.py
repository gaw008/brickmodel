"""Manufactured saved observations; no constitutive provider or physical path claim."""
from dataclasses import replace
from fractions import Fraction as F
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState, IntegrationPolicy, Rates, IntegrationError
from sludge_sandbox.source_net_panel import build_source_panel
from sludge_sandbox.source_net_prefix import build_source_prefix, audit_source_prefixes
from sludge_sandbox.exact_event_clock import ExactEventTime as T
from test_source_net_panel import sample, panel, OP, ENERGY, MASSES

POLICY = IntegrationPolicy(1.,1.,.001,1e-8,1e-10,1e-10,1.,1.,4,4,5.)


def bound(a, b, upper=F(1)):
    return build_source_panel(a,b,T(upper),operator_identity=OP,energy_identity=ENERGY,fixed_dry_mass_kg=MASSES)


def remap(s, *, faces=None, state=None):
    raw=s.evaluation.source_evaluation
    faces=raw.faces if faces is None else tuple(faces)
    state=s.state if state is None else state
    states=tuple(replace(old,liquid_water_mol=float(state.amounts_mol[i,0]),
                        gas_amounts_mol=tuple(map(float,state.amounts_mol[i,1:])),
                        internal_energy_j=float(state.internal_energy_j[i])) for i,old in enumerate(s.evaluation.source_states))
    rates=Rates(np.array([(f.liquid_mol_s,*f.gas_mol_s) for f in faces]),np.array([f.energy_w for f in faces]),
                s.evaluation.rates.reaction_species_mol_s,np.zeros(3))
    return replace(s,state=state,evaluation=replace(s.evaluation,source_states=states,
        source_evaluation=replace(raw,faces=faces),rates=rates))


def test_nonhalf_affine_shared_incidence_and_exact_residual_identity():
    a=sample(F(),phase=(-.25,0.,0.))
    b=sample(F(1,4),liquid_faces=(0.,.5,.25,0.),phase=(-.125,0.,0.),role='interior')
    p=bound(a,b)
    out=build_source_prefix(p,T(F(3,4)),policy=POLICY)
    h=F(3,4);hm=F(1,4)
    def integ(x,y):return F(float(x))*h+(F(float(y))-F(float(x)))*h*h/(2*hm)
    exact_face=tuple(integ(x,y) for x,y in zip(a.evaluation.rates.face_species_mol_s.flat,b.evaluation.rates.face_species_mol_s.flat))
    assert out.integrals[0][1]==exact_face
    records={name:(values,errors) for name,values,errors in out.integrals}
    for i in range(3):
        for j in range(4):
            k=i*4+j
            nf,ef=records['face_species_mol_s'];nr,er=records['reaction_species_mol_s']
            expected=F(float(a.state.amounts_mol[i,j]))+nf[k]-nf[k+4]+nr[k]
            actual=F(float(out.raw_state.amounts_mol[i,j]))
            assert actual-expected==out.full_residual_mol[k]
            assert out.full_residual_mol[k]==ef[k]-ef[k+4]+er[k]+out.state_roundoff_mol[k]
    assert np.array_equal(out.ledger.reaction_species_mol[:,0],-out.ledger.reaction_species_mol[:,3])
    assert sum(out.full_residual_mol,F())==sum(F(float(x))-F(float(y)) for x,y in zip(out.raw_state.amounts_mol.flat,a.state.amounts_mol.flat))
    assert sum(F(float(x))-F(float(y)) for x,y in zip(out.raw_state.internal_energy_j,a.state.internal_energy_j)) == -3*h+sum(out.full_residual_j,F())
    out.check();audit_source_prefixes((out,)).check()


def test_open_gas_and_total_energy_are_authoritative():
    a=sample(F());b=sample(F(1,2),role='interior')
    def opened(s):
        faces=list(s.evaluation.source_evaluation.faces)
        faces[0]=replace(faces[0],gas_mol_s=(.125,0.,.25),energy_w=2.,conduction_w=2.)
        return remap(s,faces=faces)
    p=bound(opened(a),opened(b))
    out=build_source_prefix(p,T(F(1,2)),policy=POLICY)
    assert sum(F(float(x))-F(float(y)) for x,y in zip(out.raw_state.amounts_mol.flat,p.first.state.amounts_mol.flat)) == F(3,16)
    assert sum(F(float(x))-F(float(y)) for x,y in zip(out.raw_state.internal_energy_j,p.first.state.internal_energy_j)) == -1


@pytest.mark.parametrize('phase',[0.,-.25])
def test_drainage_and_drainage_exceeding_condensation(phase):
    p=bound(sample(F(),phase=(phase,0.,0.)),sample(F(1,2),phase=(phase,0.,0.),role='interior'))
    out=build_source_prefix(p,T(F(1,2)),policy=POLICY)
    assert out.raw_state.amounts_mol[0,0]==2.+(-1.-phase)/2
    assert out.status=='strictly_positive_numerical_prefix'
    assert 'no_stage_event' in out.qualification


def test_liquid_donor_projection_and_direction_reversal_are_diagnostics():
    def changed(s):
        faces=[]
        for f in s.evaluation.source_evaluation.faces:
            enthalpy=2*f.liquid_mol_s
            faces.append(replace(f,liquid_enthalpy_w=enthalpy,
                                 liquid_enthalpy_projection_w=F(1,2**45),energy_w=f.conduction_w+enthalpy))
        return remap(s,faces=faces)
    a=changed(sample(F()))
    b=changed(sample(F(1,2),liquid_faces=(0.,-1.,-.5,0.),role='interior'))
    out=build_source_prefix(bound(a,b),T(F(3,4)),policy=POLICY)
    assert out.liquid_direction_reversal_faces==(1,2)
    assert out.face_diagnostics[1].liquid_enthalpy_j==2*out.face_diagnostics[1].liquid_mol
    assert out.face_diagnostics[1].liquid_enthalpy_projection_j==F(3,2**47)
    assert all(f.energy_decomposition_roundoff_j==0 for f in out.face_diagnostics)


@pytest.mark.parametrize('liquid,phase0,phasem,match',[
    (0.,0.,0.,'zero_initial'),
    (1.,12.,-12.,'negative_inventory_minimum'),
])
def test_whole_prefix_and_zero_initial_rejections(liquid,phase0,phasem,match):
    a=sample(F(),liquid_faces=(0.,0.,0.,0.),phase=(phase0,0.,0.),liquid=liquid)
    b=sample(F(1,2),liquid_faces=(0.,0.,0.,0.),phase=(phasem,0.,0.),liquid=liquid,role='interior')
    with pytest.raises(ValueError,match=match):build_source_prefix(bound(a,b),T(F(1)),policy=POLICY)


def test_tangent_and_endpoint_are_only_numerical_boundaries():
    for first,mid in ((4.,0.),(1.,1.)):
        a=sample(F(),liquid_faces=(0.,0.,0.,0.),phase=(first,0.,0.),liquid=1.)
        b=sample(F(1,2),liquid_faces=(0.,0.,0.,0.),phase=(mid,0.,0.),liquid=1.,role='interior')
        out=build_source_prefix(bound(a,b),T(F(1)),policy=POLICY)
        assert out.status=='numerical_boundary'
        out.check()


def test_zero_gas_is_not_silently_omitted():
    a=sample(F());amounts=a.state.amounts_mol.copy();amounts[1,1]=0.
    a=remap(a,state=ConservedState(amounts,a.state.internal_energy_j,ENERGY))
    with pytest.raises(ValueError,match='zero_initial'):
        build_source_prefix(bound(a,sample(F(1,2),role='interior')),T(F(1,4)),policy=POLICY)


def test_exact_origin_and_prefix_before_interior():
    origin=F(2**80)+F(1,3)
    a=build_source_prefix(panel(),T(F(1,4)),policy=POLICY)
    b=build_source_prefix(panel(origin=origin),T(origin+F(1,4)),policy=POLICY)
    assert a.integrals==b.integrals
    np.testing.assert_array_equal(a.raw_state.amounts_mol,b.raw_state.amounts_mol)


def test_tampering_full_arrays_diagnostics_and_missing_derived_records():
    out=build_source_prefix(panel(),T(F(1,4)),policy=POLICY)
    for bad in (replace(out,integrals=()),replace(out,minima=()),replace(out,status='accepted'),
                replace(out,full_residual_j=(F(1),)*3),replace(out,face_diagnostics=()),
                replace(out,raw_state=ConservedState(out.raw_state.amounts_mol+1,out.raw_state.internal_energy_j,ENERGY)),
                replace(out,ledger=replace(out.ledger,face_energy_j=out.ledger.face_energy_j+1))):
        with pytest.raises(ValueError,match='derived_content'):bad.check()
    object.__setattr__(out.panel.first.evaluation.source_evaluation,'source_ids',('forged',))
    with pytest.raises(ValueError,match='content_changed'):out.check()


def test_contiguous_audit_uses_actual_initial_and_represented_exchange():
    first=build_source_prefix(panel(),T(F(1,4)),policy=POLICY)
    a=remap(sample(F(1,4)),state=first.raw_state)
    b=remap(sample(F(1,2),role='interior'),state=first.raw_state)
    second=build_source_prefix(bound(a,b,upper=F(3,4)),T(F(3,4)),policy=POLICY)
    audit=audit_source_prefixes((first,second));audit.check()
    assert audit.inventory_residual_mol==(F(),)*12
    assert audit.energy_residual_j==(F(),)*3
    with pytest.raises(ValueError,match='contiguity'):audit_source_prefixes((first,first))
    with pytest.raises(ValueError,match='audit_changed'):
        replace(audit,cumulative_energy_exchange_j=(F(),)*3).check()


def test_integral_projection_cannot_hide_behind_exact_final_aggregation():
    # Exact J integral 2**54+1 rounds to 2**54; state projection alone is zero.
    a=sample(F(),liquid_faces=(0.,float(2**54),0.,0.),liquid=float(2**54+4))
    b=sample(F(1,2),liquid_faces=(0.,float(2**54),0.,0.),liquid=float(2**54+4),role='interior')
    h=F(2**54+1,2**54)
    p=bound(a,b,upper=h)
    with pytest.raises(ValueError,match='integral_roundoff_budget'):
        build_source_prefix(p,T(h),policy=POLICY)


def energy_only_sample(at, powers, *, state=None, role='first'):
    s=sample(at,liquid_faces=(0.,0.,0.,0.),role=role)
    faces=tuple(replace(f,gas_mol_s=(0.,0.,0.),energy_w=float(q),conduction_w=float(q))
                for f,q in zip(s.evaluation.source_evaluation.faces,powers))
    return remap(s,faces=faces,state=state)


def test_final_state_roundoff_gate_is_independent_of_integral_projection():
    delta=3*2.**-48
    a=energy_only_sample(F(),(delta,0.,0.,0.))
    b=energy_only_sample(F(1,2),(delta,0.,0.,0.),role='interior')
    policy=replace(POLICY,energy_absolute_tolerance_j=2.**-49)
    with pytest.raises(ValueError,match='affine_state_roundoff_budget'):
        build_source_prefix(bound(a,b),T(F(1)),policy=policy)


def test_full_incidence_gate_exceeds_each_integral_and_state_error():
    # At h=1/3, rounding both face terms and the state all matter.
    h=F(1,3);x,y=F(1,3),F(2,3)
    ex,ey=F(float(x))-x,F(float(y))-y
    total=F(100)+F(float(x))-F(float(y))
    es=F(float(total))-total
    full=ex-ey+es
    tolerance=float((max(abs(ex),abs(ey),abs(es))+abs(full))/2)
    assert max(abs(ex),abs(ey),abs(es))<F(tolerance)<abs(full)
    a=energy_only_sample(F(),(1.,2.,2.,2.))
    b=energy_only_sample(F(1,4),(1.,2.,2.,2.),role='interior')
    with pytest.raises(ValueError,match='full_energy_budget'):
        build_source_prefix(bound(a,b),T(h),policy=replace(POLICY,energy_absolute_tolerance_j=tolerance))


def test_two_individually_valid_prefixes_fail_original_cumulative_gate():
    delta=2.**-48
    policy=replace(POLICY,energy_absolute_tolerance_j=3*2.**-49)
    powers=(delta,0.,0.,0.)
    a=energy_only_sample(F(),powers)
    b=energy_only_sample(F(1,2),powers,role='interior')
    first=build_source_prefix(bound(a,b),T(F(1)),policy=policy)
    a2=energy_only_sample(F(1),powers,state=first.raw_state)
    b2=energy_only_sample(F(3,2),powers,state=first.raw_state,role='interior')
    second=build_source_prefix(bound(a2,b2,F(2)),T(F(2)),policy=policy)
    assert first.full_residual_j[0]==second.full_residual_j[0]==-F(delta)
    assert abs(F(delta))<F(policy.energy_absolute_tolerance_j)<2*F(delta)
    with pytest.raises(ValueError,match='cumulative_energy_budget'):
        audit_source_prefixes((first,second))


@pytest.mark.parametrize('bad_end',[T(F()),T(F(2)),1.])
def test_invalid_prefix_time(bad_end):
    with pytest.raises(ValueError,match='exact_interval'):
        build_source_prefix(panel(),bad_end,policy=POLICY)


def test_cumulative_integral_error_cannot_hide_behind_zero_represented_residual():
    h=F(2**54+1,2**54)
    policy=replace(POLICY,amount_absolute_tolerance_mol=1.5)
    def build(start,state=None):
        a=sample(start,liquid_faces=(0.,float(2**54),0.,0.),liquid=float(2**56))
        b=sample(start+h/2,liquid_faces=(0.,float(2**54),0.,0.),liquid=float(2**56),role='interior')
        if state is not None:
            a=remap(a,state=state);b=remap(b,state=state)
        return build_source_prefix(bound(a,b,upper=start+h),T(start+h),policy=policy)
    first=build(F());second=build(h,first.raw_state)
    assert first.full_residual_mol[0]==second.full_residual_mol[0]==1
    assert first.state_roundoff_mol[0]==second.state_roundoff_mol[0]==0
    with pytest.raises(ValueError,match='cumulative_full_inventory_budget'):
        audit_source_prefixes((first,second))


@pytest.mark.parametrize('field,value,reason',[
    ('conduction_w',999.,'energy_decomposition_budget'),
    ('liquid_enthalpy_projection_w',F(1),'liquid_enthalpy_projection_budget'),
    ('diffusive_enthalpy_w',(0.,0.),'diagnostic_shape'),
])
def test_original_face_diagnostics_cannot_be_omitted_or_silently_absorbed(field,value,reason):
    def changed(s):
        faces=list(s.evaluation.source_evaluation.faces)
        faces[1]=replace(faces[1],**{field:value})
        return remap(s,faces=faces)
    a=changed(sample(F()));b=changed(sample(F(1,2),role='interior'))
    with pytest.raises(ValueError,match=reason):
        build_source_prefix(bound(a,b),T(F(1,4)),policy=POLICY)


def test_budget_policy_mutation_is_revalidated():
    policy=replace(POLICY)
    object.__setattr__(policy,'energy_absolute_tolerance_j',float('inf'))
    with pytest.raises(ValueError):build_source_prefix(panel(),T(F(1,4)),policy=policy)


def test_valid_policy_loosening_after_build_does_not_reauthorize_record():
    policy=replace(POLICY)
    out=build_source_prefix(panel(),T(F(1,4)),policy=policy)
    object.__setattr__(policy,'amount_absolute_tolerance_mol',1.)
    with pytest.raises(ValueError,match='policy_binding'):
        out.check()
    with pytest.raises(ValueError,match='policy_binding'):
        audit_source_prefixes((out,))


def test_saved_policy_replacement_and_typed_binding_tamper_are_rejected():
    out=build_source_prefix(panel(),T(F(1,4)),policy=POLICY)
    for bad in (replace(out,policy=replace(POLICY,energy_absolute_tolerance_j=1.)),
                replace(out,policy_binding=list(out.policy_binding)),
                replace(out,policy_binding=(('initial_step_s',True),*out.policy_binding[1:]))):
        with pytest.raises(ValueError,match='policy_binding'):bad.check()


def test_unknown_face_subclass_is_not_treated_as_gas_only_diagnostic():
    from sludge_sandbox.source_wet_column import LiquidColumnFaceRate
    from dataclasses import fields
    class UnknownFace(LiquidColumnFaceRate):
        pass
    def changed(s):
        faces=list(s.evaluation.source_evaluation.faces)
        old=faces[1]
        faces[1]=UnknownFace(**{f.name:getattr(old,f.name) for f in fields(old)})
        return remap(s,faces=faces)
    a=changed(sample(F()));b=changed(sample(F(1,2),role='interior'))
    with pytest.raises(ValueError,match='diagnostic_schema_changed'):
        build_source_prefix(bound(a,b),T(F(1,4)),policy=POLICY)
