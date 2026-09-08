from pathlib import Path
import importlib.util,json,sys,shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]
from sludge_sandbox import run_provenance as m
HERE=Path(m.__file__).parent/'catalogs'
EVENT='sludge_sandbox_free_event_case_v1'
FREE='manufactured_reacting_wet_free_slab_v1'

def test_fixed_schema_selection():
 assert m.catalog_filename()== 'wet-slab-equations-v1.json'
 assert m.catalog_filename(FREE)=='free-wet-slab-equations-v1.json'
 assert m.catalog_filename(FREE,case_schema=EVENT)=='free-wet-event-slab-equations-v1.json'
 for model,schema in [(m.LEGACY_MODEL_ID,EVENT),(FREE,'../evil'),([],EVENT)]:
  with pytest.raises(m.ProvenanceError):m.catalog_filename(model,case_schema=schema)

def test_event_graph_binds_real_code_and_policy(tmp_path):
 p=json.loads((ROOT/'data/sandbox/cases/reacting-wet-free-slab-v1.json').read_text())
 p['schema']=EVENT;p['numerics']['depletion']={'schema':'sandbox_depletion_policy_v1','terminal_method':'affine_midpoint'}
 (tmp_path/'case.json').write_text(json.dumps(p))
 shutil.copytree(ROOT/'src/sludge_sandbox',tmp_path/'implementation')
 c=json.loads((HERE/'free-wet-event-slab-equations-v1.json').read_text())
 g=m.build_graph(tmp_path,c)
 for quantity in c['result_roots']:
  trace=m.query_graph(g,quantity)
  ids={n['id'] for n in trace['nodes']}
  assert {'equation:depletion-writeback','equation:depletion-record-audit','parameter:/numerics/depletion'}<=ids
  assert trace['scientific_validation']=='not_established_by_graph'
 old=json.loads((ROOT/'src/sludge_sandbox/catalogs/free-wet-slab-equations-v1.json').read_text())
 with pytest.raises(m.ProvenanceError,match='catalog_case_schema_mismatch'):m.build_graph(tmp_path,old)
 p['schema']='sludge_sandbox_verification_case_v1';(tmp_path/'case.json').write_text(json.dumps(p))
 with pytest.raises(m.ProvenanceError,match='catalog_case_schema_mismatch'):m.build_graph(tmp_path,c)
