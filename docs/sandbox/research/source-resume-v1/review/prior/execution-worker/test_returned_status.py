"""Real worker final-save control, fake numerical session; zero EOS."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from sludge_sandbox import source_execution_worker as worker
from sludge_sandbox import source_run_config as config
from sludge_sandbox import source_trajectory as trajectory
from sludge_sandbox import source_trajectory_record as records
from sludge_sandbox import _heos_rhs_scope as scope
from sludge_sandbox import run_service as runs
from sludge_sandbox.source_run_service import _Recorder
from sludge_sandbox.source_run_observer import observer_scope


def test_exact_accepted_step_resource_status_survives_worker(monkeypatch,tmp_path):
    from dataclasses import replace
    from fractions import Fraction as F
    import test_exact_integration as original
    from sludge_sandbox.exact_integration import integrate_exact_checkpointed
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    execution=integrate_exact_checkpointed(original.initial(),lambda state,t:original.rates(state),
        start_s=T(F()),end_s=T(F(3,2**30)),policy=replace(original.policy(),maximum_steps=1))
    assert execution.result.status=='resource_limit' and execution.result.reason=='accepted_step_limit'
    assert len(execution.result.steps)==1 and len(execution.observations)==8
    clock=[100.]
    monkeypatch.setattr(worker,'time',SimpleNamespace(monotonic=lambda:clock[0]))
    monkeypatch.setattr(worker,'_require_isolated_entry',lambda:None)
    monkeypatch.setattr(worker,'_require_idle_scope',lambda:None)
    monkeypatch.setattr(scope,'_configure_workflow_deadline',lambda t:None)
    monkeypatch.setattr(scope,'_clear_workflow_deadline',lambda:None)
    monkeypatch.setattr(runs,'runtime_identity',lambda:{'pure_seam':True})
    limits=dict(outer_seconds=510.,total_callback_cap=97,wet_pressure_request_cap=16)
    monkeypatch.setattr(config,'load_source_run_config',lambda raw:SimpleNamespace(
        values={'profile':config.RESUME_PROFILE,'resources':limits},sha256='c'*64))
    source=tmp_path/'source';source.mkdir();(source/'case.json').write_text('{}')
    cancel=tmp_path/'cancel'
    counts=dict.fromkeys(worker.COUNTERS,0)
    counts.update(heos_started=8,heos_kernel_returned=8,heos_returned=8,
                  initial_energy_started=3,initial_energy_returned=3,
                  rhs_started=40,rhs_returned=40,wet_started=8,wet_returned=8)
    session=SimpleNamespace(closed=False)

    def opening(parent,out,**kw):
        out.mkdir()
        recorder=_Recorder(out,kw['cancel'],100.);recorder.limits=limits;recorder.counts=dict(counts)
        session.recorder=recorder
        with observer_scope(recorder):
            assert kw['cancel']() is False
        session.advance=lambda **kw:SimpleNamespace(status=execution.result.status,reason=execution.result.reason,counts=tuple(counts.items()),
            parent_study_sha256='p'*64,execution=execution)
        return session

    monkeypatch.setattr(trajectory,'open_source_trajectory',opening)
    request=dict(schema='source_execution_request_v1',operation='source-advance',source=str(source),
        output=str(tmp_path/'output'),cancel_file=str(cancel),end={'numerator':3,'denominator':64},
        step_sizes={'initial_step_s':1/64,'maximum_step_s':1/64,'rationale':'pure lifecycle seam'},pause_after_steps=1,
        shared_budget={'other_counts':dict.fromkeys(worker.COUNTERS,0),'outer_remaining_seconds':1.,
                       'total_callback_cap':97,'wet_pressure_request_cap':16})
    path=tmp_path/'request.json';path.write_text(json.dumps(request))
    error=None
    try:worker._execute_request(path)
    except Exception as exc:error=exc
    output=Path(request['output'])
    observed={'error':None if error is None else repr(error),
              'outcome':json.loads((output/'OUTCOME.json').read_bytes()) if (output/'OUTCOME.json').exists() else None,
              'failure':json.loads((output/'FAILURE.json').read_bytes()) if (output/'FAILURE.json').exists() else None}
    (tmp_path/'OBSERVED.json').write_text(json.dumps(observed,indent=2)+'\n')
    assert error is not None, 'worker failed to stop at actual integrator resource limit'
    assert observed['outcome'] is None
    assert session.recorder.stop_status is None
    assert observed['failure']['status']=='resource_limit'
    assert not (output/'resume-point').exists()
