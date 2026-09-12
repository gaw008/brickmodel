"""Only saved inputs and pure projection; no source model or EOS evaluation."""
import copy
import json
from pathlib import Path
import pytest
from sludge_sandbox import source_trajectory_record as module
from sludge_sandbox.exact_integration_checkpoint_codec import decode_exact_checkpoint
from sludge_sandbox.source_run_journal import raw_projection

PACKET=Path('/private/tmp/brick-source-resume-v1/lifecycle/manufactured-source-first-packet')

def test_actual_journal_array_shape_type_is_bound(tmp_path):
    cp=decode_exact_checkpoint((PACKET/'ordinary-checkpoint.json').read_bytes())
    event=json.loads((PACKET/'events/000002.json').read_bytes())
    graph=event['payload']; nodes=graph['nodes']
    fields=nodes[graph['root']['ref']]['fields']
    adapter=nodes[fields['adapter']['ref']]
    identity=nodes[adapter['identity']['ref']]['values']
    meta=dict(operator_identity=(*identity[:2],tuple(nodes[identity[2]['ref']]['values'])),
              interface_modes=tuple(nodes[adapter['modes']['ref']]['values']))
    obs=cp.observations[0]
    capture=dict(phase=fields['phase'])
    module._event_input(graph,fields,obs.state,obs.time,capture,meta)
    state=nodes[fields['state']['ref']]
    array=nodes[state['fields']['amounts_mol']['ref']]
    before=copy.deepcopy(array['shape'])
    array['shape'][0]=float(array['shape'][0])
    error=None
    try:module._event_input(graph,fields,obs.state,obs.time,capture,meta)
    except Exception as exc:error=exc
    (tmp_path/'RESULT.json').write_text(json.dumps(dict(baseline='accepted',original_shape=before,
        mutated_shape=array['shape'],error=None if error is None else repr(error)),indent=2)+'\n')
    assert error is not None, 'actual raw ndarray shape integer changed to float was accepted'

def test_small_actual_raw_projection_dag_does_not_expand_without_work_bound(monkeypatch,tmp_path):
    value=('leaf',)
    for _ in range(22):value=(value,value)
    graph=raw_projection(value)
    # A review-only ceiling prevents allocating the whole 2**22 expanded tree.
    # It does not alter producer, input graph, or original validation decisions.
    calls=[0];old=module._require
    class ReviewCeiling(Exception):pass
    def guarded(ok,reason):
        calls[0]+=1
        if calls[0]>100000:
            raise ReviewCeiling('review stopped unbounded expansion after 100000 checks')
        return old(ok,reason)
    monkeypatch.setattr(module,'_require',guarded)
    error=None
    try:module._raw_value(graph,graph['root'])
    except Exception as exc:error=exc
    (tmp_path/'RESULT.json').write_text(json.dumps(dict(input_nodes=len(graph['nodes']),
        input_bytes=len(json.dumps(graph).encode()),guard_calls=calls[0],
        error=None if error is None else repr(error),review_ceiling=isinstance(error,ReviewCeiling)),indent=2)+'\n')
    assert not isinstance(error,ReviewCeiling), 'small DAG was expanded without any production work budget'
