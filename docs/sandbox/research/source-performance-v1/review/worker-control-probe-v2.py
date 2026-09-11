"""Control-flow seams only: no model construction, EOS, or accepted trajectory."""
from contextlib import ExitStack, nullcontext
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import sludge_sandbox.source_managed_worker as worker
import sludge_sandbox.source_run_builder as builder
import sludge_sandbox.source_run_config as configuration
import sludge_sandbox.source_run_service as service
import sludge_sandbox.source_run_observer as observer
import sludge_sandbox.run_service as runservice

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
source = Path(worker.__file__)
(out/'worker-reviewed.py').write_bytes(source.read_bytes())
test = Path('/Users/wanggaoying/Desktop/brickmodel-github/tests/sandbox/test_source_managed_worker.py')
(out/'test-worker-reviewed.py').write_bytes(test.read_bytes())

def request(directory):
    return dict(schema='source_rhs_request_v1', execution_mode='managed_single_rhs_v1',
        case_path=str(directory/'case.json'), assets_root=str(directory/'assets'), output=str(directory/'result'),
        amounts_mol=[[.25, .1, .2, .001], [0., .1, .2, .001], [.25, .1, .2, .001]],
        internal_energy_j=[10., 20., 30.], time={'numerator': 1, 'denominator': 64},
        interface_modes=['existing_liquid', 'depleted_no_nucleation', 'existing_liquid'],
        origin={'kind': 'saved_numerical_query_not_resume', 'sha256': 'a'*64},
        timeout_seconds=120., material_qualified=False)

def plain_rejection():
    value = request(out)
    value['time'] = dict(numerator=2, denominator=128)
    try:
        worker._load_request(json.dumps(value).encode())
    except ValueError as exc:
        return dict(status='rejected', error=str(exc))
    return dict(status='accepted', original_time=value['time'])

def execute_case(name, *, evaluation_failure=False, profile_failure=False, audit_failure=False):
    directory=out/name
    directory.mkdir()
    (directory/'case.json').write_text('{}')
    value=request(directory)
    request_path=directory/'request.json'
    request_path.write_text(json.dumps(value))
    instances=[]
    actual_exception=ValueError('actual control-seam evaluation failed')
    class Journal:
        def append(self, name, payload):
            instances[0].events.append(name)
    class Recorder:
        def __init__(self, *args):
            self.counts={key:0 for key in ('heos_started','heos_kernel_returned','heos_returned',
                'rhs_started','rhs_returned','initial_energy_started','initial_energy_returned',
                'wet_started','wet_returned')}
            self.events=[]
            self.journal=Journal()
            instances.append(self)
        def guard(self): pass
    class Storage:
        def state(self,nl,gas,u): return (nl,gas,u)
    class Adapter:
        interfaces=tuple(value['interface_modes'])
        def pack(self,states): return states
        def with_depleted_cells(self,state,indices):
            assert indices==(1,)
            return self
        def provenance(self): return {'control_seam':True}
        def evaluate(self,state,clock):
            assert tuple(s[2] for s in state)==tuple(value['internal_energy_j'])
            instances[0].counts['rhs_started']+=1
            if evaluation_failure:
                raise actual_exception
            instances[0].counts['rhs_returned']+=1
    def build(*args):
        for key in ('heos_started','heos_kernel_returned','heos_returned'):
            instances[0].counts[key]=4
        return SimpleNamespace(storages=(Storage(),Storage(),Storage()),adapter=Adapter(),check=lambda:None)
    scope=ModuleType('sludge_sandbox._heos_rhs_scope')
    scope._admit_worker=lambda *a,**kw: object()
    scope._close_worker=lambda token: None
    def audit(token):
        if audit_failure:
            raise RuntimeError('control-seam audit serialization failed')
        return {'control_seam':True}
    scope._worker_audit=audit
    publish=worker.publish_record_bytes
    def publisher(path,*args,**kwargs):
        if profile_failure and Path(path).name=='PROFILE.txt':
            raise OSError('control-seam profile publication failed')
        return publish(path,*args,**kwargs)
    failure=None
    with ExitStack() as stack:
        stack.enter_context(patch.dict(sys.modules,{'sludge_sandbox._heos_rhs_scope':scope}))
        stack.enter_context(patch.object(worker,'_require_isolated_entry',lambda:None))
        stack.enter_context(patch.object(configuration,'load_source_run_config',lambda raw:SimpleNamespace(canonical_bytes=b'{}',values={'profile':configuration.RHS_PROFILE,'resources':{'outer_seconds':510.}},sha256='c'*64)))
        stack.enter_context(patch.object(configuration,'validate_source_run_assets',lambda *a,**kw:SimpleNamespace(sha256='d'*64)))
        stack.enter_context(patch.object(service,'_Recorder',Recorder))
        stack.enter_context(patch.object(observer,'observer_scope',lambda recorder:nullcontext()))
        stack.enter_context(patch.object(builder,'build_source_run',build))
        stack.enter_context(patch.object(runservice,'runtime_identity',lambda:{'control_seam':True}))
        stack.enter_context(patch.object(worker,'publish_record_bytes',publisher))
        try:
            worker._execute_request(request_path)
        except BaseException as exc:
            failure=dict(type=type(exc).__name__, message=str(exc), notes=getattr(exc,'__notes__',[]),
                         original_exception_identity=exc is actual_exception)
    files={p.name:json.loads(p.read_bytes()) for p in (directory/'result').glob('*.json')}
    return dict(exception=failure,artifact_names=sorted(p.name for p in (directory/'result').iterdir()),
        terminal_json={k:v for k,v in files.items() if k in ('RESULT.json','FAILURE.json')},
        preserved_U=not evaluation_failure or failure['original_exception_identity'],physics_calls=0)

result=dict(scope='pure worker control-flow seams; no isolation or numerical performance proof',
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    cases={'noncanonical_time':plain_rejection(),
           'profile_publication_failure':execute_case('profile-publication-failure',profile_failure=True),
           'primary_evaluation_and_secondary_audit':execute_case('primary-and-audit-failure',evaluation_failure=True,audit_failure=True),
           'normal_control':execute_case('normal-control')})
(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
