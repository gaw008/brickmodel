"""Loopback HTTP boundary and shared-service dispatch; no EOS in these tests."""
import http.client
import json
from pathlib import Path
import threading
import time
import uuid

import pytest

from sludge_sandbox import local_app as app

CASE = Path(__file__).resolve().parents[2]/'data/sandbox/cases/reacting-wet-slab-v1.json'


@pytest.fixture
def server(tmp_path):
    srv = app.make_server(case_path=CASE, water_directory=tmp_path/'water',
                          storage_directory=tmp_path/'storage', maximum_jobs=2)
    thread = threading.Thread(target=srv.serve_forever)
    thread.start()
    yield srv
    srv.close()
    thread.join(timeout=3)
    assert not thread.is_alive()


def request(server, path, body=None, *, headers=None, raw=None):
    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    fields = {'X-Sandbox-Token':server.token}
    if body is not None or raw is not None: fields['Content-Type']='application/json'
    fields.update(headers or {})
    conn.request('POST' if body is not None or raw is not None else 'GET',path,
                 body=raw if raw is not None else (json.dumps(body).encode() if body is not None else None),
                 headers=fields)
    response=conn.getresponse(); data=response.read(); status=response.status
    content_type=response.getheader('Content-Type'); conn.close()
    return status,json.loads(data) if 'application/json' in content_type else data.decode()


def test_page_and_same_case_schema(server):
    code,page=request(server,'/')
    assert code==200 and '__APP_TOKEN__' not in page and server.token in page
    code,config=request(server,'/api/config')
    assert config['material_qualified'] is False and config['case']['grid']['cells']==2
    assert request(server,'/api/validate',{'case':config['case']})[0]==200
    assert list(server.manager.cases_directory.iterdir())==[]
    for path in ('/app.js','/app.css'): assert request(server,path)[0]==200


@pytest.mark.parametrize('headers',[{'X-Sandbox-Token':'wrong'}, {'Origin':'https://evil.example'}, {'Host':'evil.example'}, {'Origin':'null'}])
def test_cross_origin_and_token_rejected(server,headers):
    assert request(server,'/api/config',headers=headers)[0]==403


@pytest.mark.parametrize('raw',[b'{"case":NaN}', b'{"case":1e999}', b'{"case":{},"case":{}}',b'[]',b'{'])
def test_invalid_json_rejected(server,raw):
    assert request(server,'/api/validate',raw=raw)[0]==400


def test_bad_content_type_and_large_body(server):
    assert request(server,'/api/validate',raw=b'{}',headers={'Content-Type':'text/plain'})[0]==415
    assert request(server,'/api/validate',raw=b'{}',headers={'Content-Length':str(1024*1024+1)})[0]==413


def test_invalid_material_and_unknown_parameters_not_queued(server):
    case=json.loads(CASE.read_bytes());case['material_qualified']=True
    code,value=request(server,'/api/jobs',{'case':case,'wall_seconds':1,'grace_seconds':1})
    assert code==400 and value['code']=='evidence_incomplete'
    assert request(server,'/api/jobs')[1]['jobs']==[]


@pytest.mark.parametrize('wall,grace',[(121,1),(1,6),(True,1),(0,1),(1,0)])
def test_resource_caps(server,wall,grace):
    assert request(server,'/api/jobs',{'case':json.loads(CASE.read_bytes()),'wall_seconds':wall,'grace_seconds':grace})[0]==400


def test_worker_dispatch_busy_cancel_and_shutdown(server,monkeypatch):
    entered=threading.Event(); stopped=threading.Event(); captured={}

    def supervisor(operation,source,directory,policy,**kwargs):
        captured.update(operation=operation,source=source,policy=policy,kwargs=kwargs)
        entered.set()
        while not kwargs['cancel'](): time.sleep(.005)
        stopped.set()

    monkeypatch.setattr(app,'supervise',supervisor)
    payload={'case':json.loads(CASE.read_bytes()),'wall_seconds':1,'grace_seconds':.1}
    code,value=request(server,'/api/jobs',payload);assert code==200 and entered.wait(1)
    identifier=value['id']; uuid.UUID(identifier)
    assert request(server,'/api/jobs/'+identifier)[1]['owned_worker_active']
    assert request(server,'/api/jobs',payload)[0]==409
    assert captured['operation']=='run' and captured['policy'].maximum_wall_seconds==1
    assert captured['kwargs']['water_directory']==server.manager.water_directory
    assert request(server,'/api/jobs/'+identifier+'/cancel',{})[0]==200
    assert stopped.wait(1)
    server.manager.close()
    assert not request(server,'/api/jobs/'+identifier)[1]['owned_worker_active']
    assert request(server,'/api/jobs',payload)[0]==503


def test_shutdown_requests_owned_cancel(server,monkeypatch):
    entered=threading.Event();stopped=threading.Event()
    def supervisor(*args,**kwargs):
        entered.set()
        while not kwargs['cancel'](): time.sleep(.005)
        stopped.set()
    monkeypatch.setattr(app,'supervise',supervisor)
    request(server,'/api/jobs',{'case':json.loads(CASE.read_bytes()),'wall_seconds':1,'grace_seconds':.1})
    assert entered.wait(1)
    server.manager.close()
    assert stopped.is_set()


def saved_run(server):
    import hashlib
    identifier=str(uuid.uuid4());directory=server.manager.jobs_directory/identifier
    run=directory/'run';run.mkdir(parents=True)
    case=b'{}';(run/'case.json').write_bytes(case)
    (run/'result.json').write_text(json.dumps({'status':'completed','case_sha256':hashlib.sha256(case).hexdigest()}))
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}
    (run/'manifest.json').write_text(json.dumps({'schema':'sandbox_run_manifest_v1','files':files}))
    return identifier,run


def test_export_sources_and_tamper_rejection(server):
    identifier,run=saved_run(server)
    assert request(server,f'/api/jobs/{identifier}/export')[0]==200
    code,source=request(server,f'/api/jobs/{identifier}/artifact?path=case.json')
    assert code==200 and source['text']=='{}'
    for path in ('../job.json','%2Fetc%2Fpasswd','water%2F..%2Fcase.json'):
        assert request(server,f'/api/jobs/{identifier}/artifact?path={path}')[0]==404
    (run/'result.json').write_text('{}')
    assert request(server,f'/api/jobs/{identifier}/export')[0]==400
    detail=request(server,f'/api/jobs/{identifier}')[1]
    assert detail['result'] is None and detail['error']=='artifact_hash_mismatch:result.json'


def test_persisted_directory_not_live_thread_and_job_cap(server):
    for _ in range(2): saved_run(server)
    items=request(server,'/api/jobs')[1]['jobs']
    assert len(items)==2 and all(not item['owned_worker_active'] for item in items)
    code,result=request(server,'/api/jobs',{'case':json.loads(CASE.read_bytes()),'wall_seconds':1,'grace_seconds':1})
    assert code==409 and result['reason']=='maximum_jobs_reached'


def test_no_arbitrary_request_paths(server):
    for path in ('/../../etc/passwd','/api/jobs/nope','/api/jobs/'+str(uuid.uuid4())):
        assert request(server,path)[0]==404
