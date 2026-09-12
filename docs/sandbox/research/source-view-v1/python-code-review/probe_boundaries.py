"""Temporary fake-job and bounded DAG probes; no socket or physical operation."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import uuid

from sludge_sandbox import source_run_view as view
from sludge_sandbox.local_app import JobManager

out=Path('/private/tmp/source-view-v1/python-code-review')
with tempfile.TemporaryDirectory(dir=out) as directory:
    root=Path(directory)
    manager=JobManager(case_path=None,water_directory=None,evidence_directory=None,
        storage_directory=root/'storage',maximum_jobs=2,view_source_run=root/'unused-mount')
    identifier=str(uuid.uuid4())
    job=manager.jobs_directory/identifier
    job.mkdir()
    (job/'job.json').write_text(json.dumps({'schema':'sandbox_job_v1','job_id':identifier,'operation':'source-run'}))
    response=manager.cancel_job(identifier)
    cancel={'view_only':not manager.config()['launch_enabled'],'cancel_file_created':(job/'cancel.json').is_file(),
            'request_status':response['request']['status'],'owned_worker_active':response['owned_worker_active']}
    manager.close()

# < 80 KiB input expands to 16 MiB before the declared 1 MiB response bound.
graph={'schema':'source_run_raw_projection_v1','root':{'ref':'root'},'nodes':{
    'root':{'values':[{'ref':'shared'} for _ in range(256)]},
    'shared':{'fields':{'text':'x'*65536}}}}
original_dumps=json.dumps
input_bytes=len(original_dumps(graph).encode())
allocated=[]
def measured_dumps(*args,**kwargs):
    text=original_dumps(*args,**kwargs)
    allocated.append(len(text.encode()))
    return text
try:
    with patch.object(view.json,'dumps',measured_dumps):
        view.project_builder_path(graph,())
except Exception as exc:
    expansion={'input_bytes':input_bytes,'largest_json_allocated_bytes':max(allocated),
               'configured_response_limit':view.MAX_RESPONSE_BYTES,'exception':str(exc)}
result={'scope':'fake_storage_and_16MiB_allocation_only_no_physics_or_socket','read_only_cancel':cancel,
        'projection_expansion':expansion}
with (out/'BOUNDARY_PROBES.json').open('x') as stream:
    json.dump(result,stream,indent=2)
    stream.write('\n')
print(json.dumps(result))
