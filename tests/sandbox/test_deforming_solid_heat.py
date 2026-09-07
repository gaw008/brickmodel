"""No EOS: dry ideal gas + fixed-Cp solids; declared manufactured mechanics."""
from dataclasses import replace
import numpy as np
import math,json,time
from fractions import Fraction as F
import pytest
from test_rigid_storage import water,R
from test_deforming_solid_storage import build
from test_rigid_fluid_heat import operator
from test_integration import policy
from sludge_sandbox.integration import ConservedState,integrate
from sludge_sandbox.solid_fluid_heat import SolidFluidHeat,InventoryLayout
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.deforming_solid_heat import DeformingSolidHeat


def host(water,constant=False,isotropic=False):
    p=build(water)
    motion=p.motion
    if isotropic:motion=replace(motion,tangential_stretches_at_knots=(1.,.9))
    if constant:motion=replace(motion,normal_stretches_at_knots=((1.,),(1.,)))
    p=replace(p,motion=motion,skeleton=replace(p.skeleton,viscosity_pa_s=0.))
    transport=operator(water,liquid_column_id='liquid',storages=(p.template.fluid_template,),face_area_m2=.014,cell_widths_m=(.01,),
        conductivities_w_m_k=(0.,),effective_diffusivities_m2_s={'fixture':(0.,)},
        permeability_m2=(0.,),relative_permeability=(1.,),viscosity_pa_s=(1e-5,),
        temperature_brackets_k=((295.,310.),),inverse_policy=InversePolicy(1e-6,1e-6,100))
    base=SolidFluidHeat(storages=(p.template,),transport=transport,
        inventory_layout=InventoryLayout(species_order=('liquid','fixture','fixture_solid'),
          liquid_column_id='liquid',gas_species_order=('fixture',),solid_species_order=('fixture_solid',)))
    return DeformingSolidHeat(base_model=base,point_storages=(p,),
        mechanical_regime='prescribed_cellwise_quasistatic_incompressible_skeleton',
        transport_regime='manufactured_relative_moving_faces',model_id='fixture-host',version='1',
        source_ids=('fixture-host',),allow_manufactured=True)


def test_dry_compression_analytic_and_actual_accepted_components(water,monkeypatch):
    op=host(water,isotropic=True)
    monkeypatch.setattr(type(water),'state_tp',lambda *a,**k:pytest.fail('dry host called water EOS'))
    initial=op.state_from_temperatures([[0.,.01,2.]],[300.],time_s=0.)
    metrics=[]
    caps=(1/512,1/1024,1/2048)
    for step in caps:
        started=time.monotonic()
        run=integrate(initial,op,start_s=0,end_s=1.,policy=policy(initial_step_s=step,maximum_step_s=step,
            relative_tolerance=1e-6,energy_absolute_tolerance_j=1e-6,
            maximum_wall_seconds=90))
        assert run.status=='completed',run.reason
        errors={'T':0.,'elastic':0.,'interface':0.,'pore':0.}
        sums={k:F() for k in ('elastic','interface','pore')}
        residual_prefix=F()
        for t,state,ledger in zip(run.times_s[1:],run.states[1:],run.steps):
            out=op.evaluate(state,t)
            lam=float(out.motion.normal_stretches[0])
            pore=1.4e-4*lam**3-4e-5
            expected=300*(1e-4/pore)**(.01*R/(10+.01*(30-R)))
            errors['T']=max(errors['T'],abs(out.thermal_evaluation.storage_states[0].mechanical.temperature_k-expected))
            refs={'elastic':.5*1000*1.4e-4*(3*math.log(lam))**2,
                  'interface':.0015*(lam**2-1), 'pore':(10+.01*(30-R))*(expected-300)}
            for k in sums:
                sums[k]+=F(float(ledger.cell_work_components_j[k][0]))
                errors[k]=max(errors[k],abs(float(sums[k])-refs[k]))
            assert state.energy_model_identity==op.energy_model_identity
            assert set(ledger.cell_work_components_j)=={'elastic','interface','dissipation','pore','body'}
            assert ledger.cell_work_components_j['body'][0]==0.
            assert ledger.cell_work_components_j['dissipation'][0]==0.
            residual_prefix+=ledger.component_sum_residual_j[0]
            reconstructed=sum(sums.values(),F())+residual_prefix
            assert abs(F(float(state.internal_energy_j[0]))-F(float(initial.internal_energy_j[0]))-reconstructed)<=F(1e-6)
        durations=np.diff(run.times_s)
        metrics.append({'step_cap':step,'accepted':len(run.steps),'rejected':run.rejected_trials,
            'min_dt':float(min(durations)),'max_dt':float(max(durations)),
            'elapsed_s':time.monotonic()-started,**errors})
    print(json.dumps({'isotropic_dry_components':metrics},sort_keys=True))
    assert metrics[-1]['T']<=2e-5
    for k in ('elastic','interface','pore'):
        assert metrics[-1][k]<=1e-6
        assert metrics[2][k]<metrics[1][k]<metrics[0][k]


def test_constant_offset_and_single_inverse(water,monkeypatch):
    op=host(water,constant=True);initial=op.state_from_temperatures([[0.,.01,2.]],[300.],time_s=0.)
    cls=type(op.point_storages[0]);old=cls.temperature_from_total_energy;calls=[]
    def counted(self,*a,**k):calls.append(1);return old(self,*a,**k)
    monkeypatch.setattr(cls,'temperature_from_total_energy',counted)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',lambda *a:pytest.fail('second thermal inverse'))
    out=op.evaluate(initial,.5)
    assert len(calls)==1
    assert out.rates.cell_power_w[0]==0
    assert initial.internal_energy_j[0]-out.thermal_evaluation.storage_states[0].internal_energy_j==pytest.approx(.0015,rel=0,abs=1e-9)
    assert out.thermal_evaluation.storage_inverses[0] is out.total_inverses[0].thermal_inverse


def test_missing_scope_inventory_and_identity_rejected(water):
    op=host(water);state=op.state_from_temperatures([[0.,.01,2.]],[300.],time_s=0.)
    with pytest.raises(ValueError):op.evaluate(ConservedState(state.amounts_mol,state.internal_energy_j),0.)
    with pytest.raises(ValueError):op.evaluate(replace(state,amounts_mol=[[0.,.01,1.]]),0.)
    with pytest.raises(ValueError):replace(op,allow_manufactured=False)


def test_actual_two_cell_geometry_faces_and_no_second_inverse(water,monkeypatch):
    one=host(water);p=one.point_storages[0]
    reference=replace(p.motion.reference,half_thickness_m=.02,cells=2)
    motion=replace(p.motion,reference=reference,normal_stretches_at_knots=((1.,1.),(.9,.95)),
                   tangential_stretches_at_knots=(1.,.9))
    points=tuple(replace(p,motion=motion,skeleton=replace(p.skeleton,reference=reference,cell_index=i)) for i in range(2))
    transport=operator(water,liquid_column_id='liquid',storages=tuple(p.template.fluid_template for p in points),
        face_area_m2=.014,cell_widths_m=(.01,.01),inverse_policy=InversePolicy(1e-6,1e-6,100))
    base=replace(one.base_model,storages=tuple(p.template for p in points),transport=transport)
    op=replace(one,base_model=base,point_storages=points)
    state=op.state_from_temperatures([[0.,.01,2.],[0.,.008,2.]],[300.,301.],time_s=.5)
    cls=type(p);old=cls.temperature_from_total_energy;calls=[]
    def counted(self,*a,**k):calls.append(self.skeleton.cell_index);return old(self,*a,**k)
    monkeypatch.setattr(cls,'temperature_from_total_energy',counted)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',lambda *a:pytest.fail('second inverse'))
    out=op.evaluate(state,.5)
    assert calls==[0,1]
    assert out.rates.face_species_mol_s[1,1]!=0 and out.rates.face_energy_w[1]!=0
    assert out.current_host.transport.face_area_m2==float(out.motion.current.face_areas_m2[0])
    dn,du=out.rates.derivatives(state)
    assert math.fsum(dn[:,1])==0
    assert math.fsum(du)==pytest.approx(math.fsum(out.rates.cell_power_w),rel=0,abs=1e-12)
    assert np.all(out.rates.face_species_mol_s[:,[0,2]]==0)
    for i in range(2):
        assert out.current_host.storages[i] is out.total_inverses[i].state.current_storage
        assert out.thermal_evaluation.storage_inverses[i] is out.total_inverses[i].thermal_inverse


def test_old_host_rejects_tag_and_private_assembly_rejects_inventory_geometry(water):
    op=host(water);state=op.state_from_temperatures([[0.,.01,2.]],[300.],time_s=0.)
    with pytest.raises(ValueError):op.base_model.evaluate(state,0.)
    out=op.evaluate(state,.2);inv=out.total_inverses[0].thermal_inverse
    with pytest.raises(ValueError,match='inventory'):
        out.current_host._assemble_decoded([[0.,.02,2.]],(inv,),((295.,310.),))
    with pytest.raises(ValueError,match='geometry'):
        op.base_model._assemble_decoded(state.amounts_mol,(inv,),((295.,310.),))


def test_dissipation_point_and_full_reference_guard(water):
    op=host(water);p=op.point_storages[0]
    viscous=replace(op,point_storages=(replace(p,skeleton=replace(p.skeleton,viscosity_pa_s=3.)),))
    state=viscous.state_from_temperatures([[0.,.01,2.]],[300.],time_s=.5)
    out=viscous.evaluate(state,.5)
    rate=float(out.motion.normal_rates_per_s[0])/float(out.motion.normal_stretches[0])
    assert out.rates.cell_power_components_w['dissipation'][0]==pytest.approx(3*1.4e-4*rate**2,rel=0,abs=1e-18)
    mismatched=replace(op.base_model,transport=replace(op.base_model.transport,face_area_m2=.028,cell_widths_m=(.005,)))
    with pytest.raises(ValueError,match='reference_area'):
        replace(op,base_model=mismatched)


def test_point_state_original_positional_qualification_is_compatible(water):
    from dataclasses import fields
    point=host(water).point_storages[0]
    s=point.forward(300.,liquid_mol=0.,gas_mol={'fixture':.01},solid_mol={'fixture_solid':2.},time_s=0.)
    old_args=[getattr(s,f.name) for f in fields(s) if f.name!='current_storage']
    old_args[-1]='legacy-qualified-string'
    restored=type(s)(*old_args)
    assert restored.qualification=='legacy-qualified-string'
    assert restored.current_storage is None


@pytest.mark.parametrize('temperatures',[['300.'],[True],300.,[float('nan')],{'temperature':300.},[]])
def test_initializer_strict_temperature_input(water,temperatures):
    from sludge_sandbox.integration import IntegrationError
    with pytest.raises(IntegrationError):
        host(water).state_from_temperatures([[0.,.01,2.]],temperatures,time_s=0.)


def test_initializer_valid_input_matches_actual_attempt06_source(water):
    import ast
    from pathlib import Path
    import sludge_sandbox.deforming_solid_heat as module
    old=Path(__file__).resolve().parents[2]/'docs/sandbox/research/deforming-solid-host-attempt06.py'
    tree=ast.parse(old.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DeformingSolidHeat')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='state_from_temperatures')
    namespace=dict(vars(module));exec(compile(ast.Module(body=[method],type_ignores=[]),str(old),'exec'),namespace)
    op=host(water,isotropic=True);inputs=[[0.,.01,2.]]
    before=namespace['state_from_temperatures'](op,inputs,[300.],time_s=0.)
    after=op.state_from_temperatures(inputs,[300.],time_s=0.)
    assert np.array_equal(before.amounts_mol,after.amounts_mol)
    assert np.array_equal(before.internal_energy_j,after.internal_energy_j)
    assert before.energy_model_identity==after.energy_model_identity
