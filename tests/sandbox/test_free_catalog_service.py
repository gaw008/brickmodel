import json
from pathlib import Path
import pytest
import sludge_sandbox.run_provenance as m
ROOT=Path(__file__).resolve().parents[2]
OLD='manufactured_reacting_wet_prescribed_slab_v1';FREE='manufactured_reacting_wet_free_slab_v1'

def test_explicit_selection():
 assert m.catalog_filename(OLD)=='wet-slab-equations-v1.json'
 assert m.catalog_filename(FREE)=='free-wet-slab-equations-v1.json'

@pytest.mark.parametrize('bad',['../../etc/passwd','unknown',None,[],{}])
def test_unknown_rejected(bad):
 with pytest.raises(m.ProvenanceError):m.catalog_bytes(bad)

def test_default_legacy_bytes_and_explicit_free(monkeypatch,tmp_path):
 # Synthetic catalog fixtures test dispatch only; not a scientific free catalog.
 catalog=tmp_path/'catalogs';catalog.mkdir()
 old=(ROOT/'src/sludge_sandbox/catalogs/wet-slab-equations-v1.json').read_bytes()
 (catalog/'wet-slab-equations-v1.json').write_bytes(old)
 free=json.dumps({'model_id':FREE,'fixture_only':True}).encode()
 (catalog/'free-wet-slab-equations-v1.json').write_bytes(free)
 monkeypatch.setattr(m,'__file__',str(tmp_path/'run_provenance.py'))
 assert m.catalog_bytes()==old and m.catalog_bytes(OLD)==old
 assert m.load_catalog()==json.loads(old)
 assert m.catalog_bytes(FREE)==free and m.load_catalog(FREE)['model_id']==FREE


def test_wrong_payload_model(monkeypatch,tmp_path):
 (tmp_path/'catalogs').mkdir();(tmp_path/'catalogs/free-wet-slab-equations-v1.json').write_text(json.dumps({'model_id':OLD}))
 monkeypatch.setattr(m,'__file__',str(tmp_path/'run_provenance.py'))
 with pytest.raises(m.ProvenanceError,match='catalog_model_mismatch'):m.catalog_bytes(FREE)

@pytest.fixture
def service(monkeypatch):
 import sludge_sandbox.run_service as module
 return module

@pytest.mark.parametrize('model,name',[(OLD,'wet-slab-equations-v1.json'),(FREE,'free-wet-slab-equations-v1.json')])
def test_resume_uses_model_catalog(service,monkeypatch,tmp_path,model,name):
 from types import SimpleNamespace
 import sludge_sandbox.verification_case as case_module
 runtime={'modules':{},'catalogs':{'wet-slab-equations-v1.json':'old','free-wet-slab-equations-v1.json':'free'}}
 result={'runtime_before':runtime,'runtime_after':runtime,'case_sha256':'expected'}
 manifest={'files':{'equation_catalog.json':runtime['catalogs'][name]}}
 monkeypatch.setattr(service,'runtime_identity',lambda:runtime)
 monkeypatch.setattr(service,'read_run',lambda _: (result,manifest))
 monkeypatch.setattr(case_module,'read_case',lambda _:SimpleNamespace(payload={'model_id':model},sha256='different'))
 # Reaching CASE mismatch proves selected catalog passed the actual resume gate.
 with pytest.raises(service.RunError,match='resume_case_binding_mismatch'):service.resume_run(tmp_path,tmp_path/'out')
 manifest['files']['equation_catalog.json']='substituted'
 with pytest.raises(service.RunError,match='resume_catalog_binding_mismatch'):service.resume_run(tmp_path,tmp_path/'out')

@pytest.mark.parametrize('model',[OLD,FREE])
def test_run_dispatches_verified_case_model(service,monkeypatch,tmp_path,model):
 from types import SimpleNamespace
 import sludge_sandbox.verification_case as case_module
 import sludge_sandbox.run_provenance as actual
 source=tmp_path/'input.json';source.write_text('{}');water=tmp_path/'water';water.mkdir();seen=[]
 monkeypatch.setattr(case_module,'read_case',lambda _:SimpleNamespace(payload={'model_id':model,'scope':'mock'},case_id='mock'))
 monkeypatch.setattr(service,'runtime_identity',lambda:{})
 def selected(value):
  seen.append(value)
  raise ValueError('intentional_mock_stop_before_build')
 monkeypatch.setattr(actual,'catalog_bytes',selected)
 result=service.run_case(source,water,tmp_path/'out')
 assert seen==[model] and result['status']!='completed'
 assert (tmp_path/'out/case.json').read_text()=='{}'

@pytest.mark.parametrize('quantity,pointer,value',[('mechanical_stretches','/integration/states/0/mechanical_stretches',[.9,1.1,.98]),('geometry','/final_snapshot/geometry',{'volumes_m3':[.1,.2]}),('free','/final_snapshot/free',{'rates':[1,2,3]})])
def test_saved_free_trace(service,tmp_path,quantity,pointer,value):
 # Seal real artificial artifacts, then invoke actual read_run and trace_run.
 (tmp_path/'implementation').mkdir()
 for filename,_,_ in service._FREE_EQUATIONS:(tmp_path/'implementation'/filename).write_text('# synthetic frozen fixture\n')
 case={'model_id':FREE};raw=json.dumps(case).encode();(tmp_path/'case.json').write_bytes(raw)
 result={'schema':'sandbox_run_v1','case_sha256':service._hash(raw),'status':'completed','scientific_status':'manufactured_verification_only',
  'integration':{'states':[{'mechanical_stretches':[.9,1.1,.98]}]},'final_snapshot':{'geometry':{'volumes_m3':[.1,.2]},'free':{'rates':[1,2,3]}}}
 (tmp_path/'result.json').write_text(json.dumps(result));service._seal(tmp_path)
 trace=service.trace_run(tmp_path,quantity)
 assert trace['value']==value and trace['result_pointer']==pointer
 assert all('Deforming' not in x['symbol'] for x in trace['equations'])
 assert any(x['symbol']=='solve_free_slab_rates' for x in trace['equations'])
 case['model_id']='unknown';(tmp_path/'case.json').write_text(json.dumps(case));result['case_sha256']=service._hash((tmp_path/'case.json').read_bytes());(tmp_path/'result.json').write_text(json.dumps(result));service._seal(tmp_path)
 with pytest.raises(service.RunError,match='unsupported_trace_model'):service.trace_run(tmp_path,quantity)
