"""Bounded counterexample for the other metadata-to-runtime container copy."""
import json
from types import MappingProxyType
from sludge_sandbox import source_trajectory_record as module


def test_managed_metadata_copy_retains_shared_dag_without_exponential_walk(monkeypatch,tmp_path):
    item=MappingProxyType({'status':'verified'})
    for _ in range(22):item=(item,item)
    metadata=MappingProxyType({'status':'closed','primary_error':None,'secondary_errors':(),
        'audit':MappingProxyType({'closed':True,'rhs':item})})
    calls=[0];original=module._require
    class ReviewCeiling(Exception):pass
    def guard(ok,reason):
        calls[0]+=1
        if calls[0]>100000:raise ReviewCeiling('stop unchecked metadata expansion')
        return original(ok,reason)
    monkeypatch.setattr(module,'_require',guard)
    error=None
    try:module._owned_audit(metadata)
    except Exception as exc:error=exc
    (tmp_path/'RESULT.json').write_text(json.dumps(dict(guard_calls=calls[0],
        error=None if error is None else repr(error),review_ceiling=isinstance(error,ReviewCeiling)),indent=2)+'\n')
    assert not isinstance(error,ReviewCeiling)
