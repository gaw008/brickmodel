"""Explicit case-family admission and early refusal; no native thermodynamics."""
from fractions import Fraction as F
from types import SimpleNamespace as NS
import pytest
from test_event_case import payload,save
from sludge_sandbox import verification_case as m
from sludge_sandbox import pressure_comparison as pc
from sludge_sandbox.paired_pressure_host import SharedConstantParameterBox


def paired_payload():
    p=payload()
    p['numerics']['depletion'].update(schema='sandbox_depletion_policy_v2',pressure_comparison={
        'schema':pc.SCHEMA,'constant_box_declaration':'all_actual_declared_constant_volume_errors_are_shared'})
    return p


def test_explicit_v2_policy_roundtrip_and_default_v1_unchanged(tmp_path):
    old=payload()
    assert 'pressure_comparison' not in old['numerics']['depletion']
    assert m._build_depletion_policy(save(tmp_path,old).payload['numerics']['depletion']).pressure_comparison is None
    p=paired_payload();case=save(tmp_path,p)
    with pytest.raises(m.CaseError,match='actual operator required'):
        m._build_depletion_policy(case.payload['numerics']['depletion'])
    assert m._build_depletion_policy(case.payload['numerics']['depletion'],validation_only=True).pressure_comparison is None


@pytest.mark.parametrize('change',[
    lambda d:d.update(schema='sandbox_depletion_policy_v1'),
    lambda d:d.update(pressure_comparison=None),
    lambda d:d.update(pressure_comparison=True),
    lambda d:d['pressure_comparison'].update(cell_boxes=[]),
    lambda d:d['pressure_comparison'].update(constant_box_declaration=True),
])
def test_incomplete_or_implicit_family_refused(tmp_path,change):
    p=paired_payload();change(p['numerics']['depletion'])
    with pytest.raises(m.CaseError):save(tmp_path,p)


def test_mismatched_case_boxes_fail_before_forward(tmp_path,monkeypatch):
    p=paired_payload();case=save(tmp_path,p)
    op=NS(base_model=NS(point_storages=(object(),)),chemical=NS(reference=NS(molar_mass_kg_mol=p['numerics']['depletion']['roundoff_policy']['molar_mass_kg_mol'])))
    import sludge_sandbox.paired_pressure_host as host
    monkeypatch.setattr(host,'declare_manufactured_constant_box',lambda point:SharedConstantParameterBox('a'*64,('A',),(F(1),),(F(0),),F(2),F(0)))
    monkeypatch.setattr(m,'_make_model',lambda *args:(op,[],[]))
    monkeypatch.setattr(pc,'pressure_comparison_binding',lambda op:{'boxes':[]})
    monkeypatch.setattr(m,'_forward',lambda *args:pytest.fail('mismatched boxes reached forward'))
    with pytest.raises(m.CaseError,match='boxes differ'):m.build_case(case,tmp_path)


@pytest.mark.parametrize('schema',['sandbox_depletion_result_v1','sandbox_depletion_result_v2'])
def test_resume_shape_admission_allows_both_versions_without_claiming_audit(schema):
    from sludge_sandbox.run_service import _event_cancelled
    _event_cancelled({'integration_kind':'water_depletion_v1','status':'cancelled','integration':{
        'schema':schema,'status':'cancelled','reason':'cancel_requested','steps':[{}]}})
    # This only admits the shape; _run_event must still audit complete records.
