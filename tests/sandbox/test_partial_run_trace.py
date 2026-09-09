"""Synthetic sealed source graph, actual read_run/query_graph; no EOS."""
import hashlib
import json
import pytest

from sludge_sandbox import run_service as m


def sealed(tmp_path,status,complete):
    def put(name,value):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(value))
        return hashlib.sha256(p.read_bytes()).hexdigest()
    case_sha=put('case.json',{'model_id':'manufactured_reacting_wet_free_slab_v1','parameter':1.})
    put('result.json',{'case_sha256':case_sha,'status':status,'reason':'test_cancel' if status=='cancelled' else 'test_failure',
        'scientific_status':'manufactured','initial_snapshot':{'temperature_k':[999.]},
        'integration':{'states':[{'amounts_mol':[[1.]],'internal_energy_j':[2.],'mechanical_stretches':[1.,1.]}]},
        **({'final_snapshot':{'temperature_k':[300.],'pressure_pa':[1e5],'geometry':{},'free':{}}} if complete else {})})
    for filename,_,_ in m._FREE_EQUATIONS:put('implementation/'+filename,{'fixture':filename})
    catalog_sha=put('equation_catalog.json',{'fixture':'declared'})
    graph={'schema':'sandbox_run_provenance_v1','case_sha256':case_sha,'catalog_sha256':catalog_sha,
        'scope':'test graph','graph_semantics':'declared dependencies',
        'result_roots':{name:'out' for name in m._FREE_QUANTITIES},
        'nodes':[{'id':'param','node_type':'parameter','depends_on':[],'artifact':'case.json','sha256':case_sha},
                 {'id':'out','node_type':'output','depends_on':['param']}]}
    put('provenance.json',graph)
    files={p.relative_to(tmp_path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()}
    put('manifest.json',{'schema':'sandbox_run_manifest_v1','files':files})
    return {p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('quantity',sorted(m._FREE_QUANTITIES))
def test_complete_trace_exact_compatibility(tmp_path,quantity):
    before=sealed(tmp_path,'completed',True)
    expected = {
        'amounts_mol': ([[1.]], '/integration/states/0/amounts_mol'),
        'internal_energy_j': ([2.], '/integration/states/0/internal_energy_j'),
        'mechanical_stretches': ([1., 1.], '/integration/states/0/mechanical_stretches'),
        'temperature_k': ([300.], '/final_snapshot/temperature_k'),
        'pressure_pa': ([1e5], '/final_snapshot/pressure_pa'),
        'geometry': ({}, '/final_snapshot/geometry'),
        'free': ({}, '/final_snapshot/free'),
    }
    trace = m.trace_run(tmp_path, quantity)
    assert (trace['value'], trace['result_pointer']) == expected[quantity]
    assert 'value_availability' not in trace
    assert trace['run_status'] == 'completed'
    assert trace['dependency_graph']['nodes'] and trace['equations']
    assert before=={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


@pytest.mark.parametrize('status',['cancelled','failed'])
@pytest.mark.parametrize('quantity',sorted(m._FREE_QUANTITIES))
def test_missing_final_explicit_unavailable_with_graph(tmp_path,status,quantity):
    before=sealed(tmp_path,status,False)
    trace=m.trace_run(tmp_path,quantity)
    assert trace['value'] is None and trace['result_pointer'] is None
    assert trace['value_availability']['reason']=='final_snapshot_unavailable'
    assert trace['run_status']==status
    assert trace['dependency_graph']['nodes'] and trace['case_parameters'] and trace['equations']
    assert before=={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_unknown_quantity_rejected_before_read(tmp_path):
    with pytest.raises(m.RunError,match='unsupported_quantity'):m.trace_run(tmp_path,'strength_mpa')
