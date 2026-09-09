"""Pure preflight guards; actual source boxes remain checked after model build."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_depletion_integration import policies
from sludge_sandbox import run_service as m
from sludge_sandbox.verification_case import encode
from sludge_sandbox.pressure_comparison import PressureComparisonPolicy,SCHEMA
from sludge_sandbox.paired_pressure_host import SharedConstantParameterBox


def fixture():
    scalar=encode(replace(policies()[1],terminal_method='affine_midpoint'))
    declaration={'schema':SCHEMA,'constant_box_declaration':'all_actual_declared_constant_volume_errors_are_shared'}
    case={'schema':'sandbox_depletion_policy_v2',**scalar,'pressure_comparison':declaration}
    box=SharedConstantParameterBox('a'*64,('A',),(F(1),),(F(0),),F(2),F(0))
    saved={**scalar,'pressure_comparison':PressureComparisonPolicy((box,)).to_record()}
    return case,saved


def test_v2_preflight_does_not_need_unbuilt_operator():
    case,saved=fixture()
    m._validate_event_resume_policy(case,saved)
    assert saved==fixture()[1]  # no destructive pop of parent policy


@pytest.mark.parametrize('change',[
    lambda s:s.update(pressure_absolute_pa=1.),
    lambda s:s.pop('pressure_comparison'),
    lambda s:s.update(pressure_comparison=None),
    lambda s:s['pressure_comparison'].update(schema='unknown'),
    lambda s:s['pressure_comparison'].update(cell_boxes=[]),
    lambda s:s['pressure_comparison']['cell_boxes'][0].update(reference_volume_m3={'numerator':True,'denominator':1}),
])
def test_v2_rejects_changed_budget_missing_or_invalid_typed_policy(change):
    case,saved=fixture();change(saved)
    with pytest.raises(ValueError):m._validate_event_resume_policy(case,saved)


def test_legacy_preflight_exact_policy_and_rejects_injected_family():
    case,saved=fixture();case.pop('pressure_comparison');case['schema']='sandbox_depletion_policy_v1'
    old=deepcopy(saved);old.pop('pressure_comparison')
    m._validate_event_resume_policy(case,old)
    with pytest.raises(ValueError):m._validate_event_resume_policy(case,saved)


def test_v2_still_requires_explicit_case_declaration():
    case,saved=fixture();case['pressure_comparison']['constant_box_declaration']='inferred'
    with pytest.raises(ValueError):m._validate_event_resume_policy(case,saved)


def test_changed_valid_box_still_fails_fresh_model_check_before_integration(tmp_path,monkeypatch):
    from types import SimpleNamespace as NS
    from sludge_sandbox.pressure_comparison import restore_pressure_comparison_policy
    from sludge_sandbox.integration import ConservedState
    case,saved=fixture();p,e=policies()
    actual=replace(e,terminal_method='affine_midpoint',pressure_comparison=restore_pressure_comparison_policy(saved['pressure_comparison']))
    changed=deepcopy(saved);changed['pressure_comparison']['cell_boxes'][0]['reference_volume_m3']['numerator']=3
    m._validate_event_resume_policy(case,changed)  # structure is valid, identity is not yet certified
    built=NS(depletion_policy=actual,policy=p,initial=ConservedState([[1.,0.]],[0.]),start_s=0.,operator=NS(interfaces=('existing_liquid',)))
    parent={'integration_kind':'water_depletion_v1','status':'cancelled','policy':encode(p),'depletion_policy':changed,
            'integration':{'schema':'sandbox_depletion_result_v2','status':'cancelled','reason':'cancel_requested','steps':[{}]}}
    import sludge_sandbox.depletion_integration as core
    monkeypatch.setattr(core,'integrate_depletion',lambda *a,**k:pytest.fail('changed box reached integrator'))
    with pytest.raises(m.RunError,match='resume_event_original_policy_mismatch'):
        m._run_event(built,{},parent,tmp_path,None)
