from pathlib import Path
import copy,importlib.util,json,sys
from dataclasses import replace
from types import SimpleNamespace
import pytest
from test_depletion_integration import policies
from sludge_sandbox.verification_case import encode
ROOT=Path(__file__).resolve().parents[2]
from sludge_sandbox import verification_case as m

def payload():
    p=json.loads((ROOT/'data/sandbox/cases/reacting-wet-free-slab-v1.json').read_text())
    p['schema']='sludge_sandbox_free_event_case_v1'
    p['numerics']['depletion']={'schema':'sandbox_depletion_policy_v1',**encode(replace(policies()[1],terminal_method='affine_midpoint'))}
    return p

def save(tmp,p):
    path=tmp/'case.json';path.write_text(json.dumps(p,allow_nan=False));return m.read_case(path)

def test_explicit_event_policy_roundtrip_without_eos(tmp_path):
    p=payload();case=save(tmp_path,p)
    expected=p['numerics']['depletion'].copy();expected.pop('schema')
    assert encode(m._build_depletion_policy(case.payload['numerics']['depletion']))==expected
    p['numerics']['depletion']['nested_approach']={'maximum_step_s':1e-4,'reuse_ordinary_spine':True,'strategy_id':'nested_wet_ordinary_spine_v1'}
    assert m._build_depletion_policy(save(tmp_path,p).payload['numerics']['depletion']).nested_approach.reuse_ordinary_spine is True

@pytest.mark.parametrize('mutate',[
    lambda p:p['numerics']['depletion'].pop('roundoff_policy'),
    lambda p:p['numerics']['depletion'].update(terminal_method='euler'),
    lambda p:p['numerics']['depletion'].update(safe_inventory_fraction=.5),
    lambda p:p['numerics']['depletion'].update(maximum_refinements=True),
    lambda p:p['numerics']['depletion'].update(time_absolute_s=0),
    lambda p:p['numerics']['depletion'].update(schema='unknown'),
    lambda p:p['numerics']['depletion'].update(unknown=1),
    lambda p:p['numerics']['depletion']['roundoff_policy'].update(correction_fraction_evaporated=1e-7),
    lambda p:p['numerics']['depletion']['roundoff_policy'].update(molar_mass_kg_mol=True),
    lambda p:p['numerics']['depletion'].update(nested_approach={'maximum_step_s':.001,'reuse_ordinary_spine':1,'strategy_id':'nested_wet_ordinary_spine_v1'}),
    lambda p:p['numerics']['depletion'].update(nested_approach={}),
    lambda p:p.update(schema='sludge_sandbox_verification_case_v1'),
    lambda p:p.update(model_id='manufactured_reacting_wet_prescribed_slab_v1'),
])
def test_invalid_explicit_policy_refused(tmp_path,mutate):
    p=payload();mutate(p)
    with pytest.raises(m.CaseError):save(tmp_path,p)

def test_ordinary_case_unchanged_and_actual_mass_checked_before_forward(tmp_path,monkeypatch):
    p=json.loads((ROOT/'data/sandbox/cases/reacting-wet-free-slab-v1.json').read_text())
    assert save(tmp_path,p).payload==p
    p=payload();case=save(tmp_path,p)
    # Source mass differs; no thermodynamic forward or EOS may be attempted.
    operator=SimpleNamespace(chemical=SimpleNamespace(reference=SimpleNamespace(molar_mass_kg_mol=.02)))
    monkeypatch.setattr(m,'_make_model',lambda *args:(operator,[],[]))
    monkeypatch.setattr(m,'_forward',lambda *args:pytest.fail('mass mismatch must precede forward'))
    with pytest.raises(m.CaseError,match='actual source reference'):m.build_case(case,tmp_path)
