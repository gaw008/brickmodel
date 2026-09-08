from pathlib import Path
import json,copy
from fractions import Fraction as F
import pytest
from test_dynamic_solid_storage import water,forbid_water_eos
import sludge_sandbox.verification_case as m
ROOT=Path(__file__).resolve().parents[2]

def payload():return json.loads((ROOT/'data/sandbox/cases/reacting-wet-free-slab-v1.json').read_text())
def save(tmp,p,name='case.json'):
    f=tmp/name;f.write_text(json.dumps(p));return m.read_case(f)


def test_dry_build_two_eight_extensive_q_and_mechanics(tmp_path,monkeypatch,water):
    import sludge_sandbox.water_properties as wp
    import sludge_sandbox.ideal_water_vapor as iv
    import sludge_sandbox.water_chemical_potential as wc
    for module in (wp,iv,wc):monkeypatch.setattr(module,'load_water_properties',lambda *a,**k:water)
    # Test-only manufactured caloric substitute for zero-inventory gas water;
    # no water/source qualification is asserted by this builder wiring test.
    monkeypatch.setattr(iv.IdealWaterVapor,'_caloric',lambda self,t:(30*t,(30-self.gas_constant_j_mol_k)*t,30.,30-self.gas_constant_j_mol_k,t))
    p=payload()
    for row in p['initial']['parent_amounts_mol']:row[2]=row[3]=0.
    p['transport']['phase_coefficient_density_mol_s_pa_m3']=0.
    p['mechanics']['initial_parent_normal_stretches']=[.98,1.02]
    p['mechanics']['parent_additional_bulk_volume_error_m3']=1e-18
    p['mechanics']['parent_additional_mechanical_energy_error_j']=1e-10
    coarse=m.build_case(save(tmp_path,p,'two.json'),tmp_path)
    p['grid']['cells']=8
    fine=m.build_case(save(tmp_path,p,'eight.json'),tmp_path)
    assert tuple(coarse.initial.mechanical_stretches)==(.98,1.02,1.)
    assert tuple(fine.initial.mechanical_stretches)==(.98,.98,.98,.98,1.02,1.02,1.02,1.02,1.)
    for i in range(2):
        for j in range(5):assert F(float(coarse.initial.amounts_mol[i,j]))==sum((F(float(fine.initial.amounts_mol[k,j])) for k in range(4*i,4*i+4)),F())
        assert F(float(coarse.initial.internal_energy_j[i]))==sum((F(float(fine.initial.internal_energy_j[k])) for k in range(4*i,4*i+4)),F())
        a=coarse.operator.base_model.point_storages[i];b=fine.operator.base_model.point_storages[4*i]
        assert b.skeleton.reference_model.reference_interface_area_m2*4==a.skeleton.reference_model.reference_interface_area_m2
        assert b.error_bounds.additional_mechanical_energy_error_j*4==a.error_bounds.additional_mechanical_energy_error_j
        for (_,wa),(_,wb) in zip(a.skeleton.composition_weights_per_mol,b.skeleton.composition_weights_per_mol):assert wb==4*wa
    assert fine.policy==coarse.policy
    reference=fine.operator.base_model.point_storages[0].skeleton.reference
    geometry=reference.deform(tuple(fine.initial.mechanical_stretches[:-1]),tangential_stretch=float(fine.initial.mechanical_stretches[-1]))
    expected_widths=[(.02/8)*n for n in [.98]*4+[1.02]*4]
    assert list(geometry.widths_m)==expected_widths
    assert len(geometry.faces_m)==9
    for i in range(9):
        assert abs(F(float(geometry.faces_m[i]))-sum(map(F,expected_widths[:i]),F()))<=F(1e-17)
    assert fine.policy.stretch_absolute_tolerance==1e-9



def test_nonzero_b_q_viscosity_interface_and_uniform_refinement(tmp_path,monkeypatch,water):
    import sludge_sandbox.water_properties as wp
    import sludge_sandbox.ideal_water_vapor as iv
    import sludge_sandbox.water_chemical_potential as wc
    for module in (wp,iv,wc):monkeypatch.setattr(module,'load_water_properties',lambda *a,**k:water)
    monkeypatch.setattr(iv.IdealWaterVapor,'_caloric',lambda self,t:(30*t,(30-self.gas_constant_j_mol_k)*t,30.,30-self.gas_constant_j_mol_k,t))
    p=payload();p['profile']='uniform'
    for row in p['initial']['parent_amounts_mol']:row[:4]=[2.,0.,0.,0.]
    p['mechanics']['initial_parent_normal_stretches']=[.98,1.02]
    p['mechanics']['initial_tangential_stretch']=.99
    p['mechanics']['parent_additional_bulk_volume_error_m3']=1e-18
    p['mechanics']['parent_additional_mechanical_energy_error_j']=1e-10
    p['transport']['phase_coefficient_density_mol_s_pa_m3']=0.
    two=m.build_case(save(tmp_path,p,'nonzero-two.json'),tmp_path)
    p['grid']['cells']=8
    fine=m.build_case(save(tmp_path,p,'nonzero-eight.json'),tmp_path)
    assert tuple(two.initial.mechanical_stretches)==(.98,.98,.99)
    assert tuple(fine.initial.mechanical_stretches)==(.98,.98,.98,.98,.98,.98,.98,.98,.99)
    for i in range(2):
        a=two.operator.base_model.point_storages[i];b=fine.operator.base_model.point_storages[4*i]
        def current_q(point,row):
            weights=dict(point.skeleton.composition_weights_per_mol)
            return F(point.skeleton.composition_offset)+F(weights['A'])*F(float(row[0]))+F(weights['B'])*F(float(row[1]))
        # Later reaction extent is evaluated at current inventory; initial B stays zero.
        parent_row=[1.5,.5,0.,0.,.001];child_row=[value/4 for value in parent_row]
        qa=current_q(a,parent_row);qb=current_q(b,child_row)
        assert qa==qb and qa>1
        assert qa*F(a.skeleton.reference_model.viscosity_pa_s)==qb*F(b.skeleton.reference_model.viscosity_pa_s)
        for point,row,qvalue in [(a,parent_row,qa),(b,child_row,qb)]:
            state=point.skeleton.evaluate(normal_stretch=.98,tangential_stretch=.99,normal_rate_per_s=0.,tangential_rate_per_s=0.,solid_inventory_mol={'A':float(row[0]),'B':float(row[1])})
            ref=point.skeleton.reference_model
            expected=qvalue*F(ref.interface_energy_j_m2)*F(ref.reference_interface_area_m2)*F(.99)**2
            assert abs(F(state.interface_energy_j)-expected)<=F(state.numerical_error_bounds['interface_energy_j'])
        assert F(a.error_bounds.additional_bulk_volume_error_m3)==4*F(b.error_bounds.additional_bulk_volume_error_m3)
        assert F(a.template.bulk_volume_error_m3)==4*F(b.template.bulk_volume_error_m3)
        assert F(float(two.initial.internal_energy_j[i]))==sum((F(float(fine.initial.internal_energy_j[k])) for k in range(4*i,4*i+4)),F())
        for column in range(5):assert F(float(two.initial.amounts_mol[i,column]))==sum((F(float(fine.initial.amounts_mol[k,column])) for k in range(4*i,4*i+4)),F())


def test_only_free_eight_admission(tmp_path):
    p=payload();p['grid']['cells']=8
    assert save(tmp_path,p).payload['grid']['cells']==8
    p['grid']['cells']=6
    with pytest.raises(m.CaseError):save(tmp_path,p)
    p=json.loads((ROOT/'data/sandbox/cases/reacting-wet-slab-v1.json').read_text());p['grid']['cells']=8
    with pytest.raises(m.CaseError):save(tmp_path,p)
