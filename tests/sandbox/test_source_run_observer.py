"""Task-local observation and actual manufactured-host lifecycle, no HEOS."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import pytest
from sludge_sandbox.source_run_observer import observer_scope, emit_source_event, emit_source_failure


def test_scope_restores_nested_and_no_scope_is_noop():
    a,b=[],[]
    emit_source_event('absent')
    with observer_scope(lambda event,**payload:a.append((event,payload))):
        emit_source_event('outer',value=1)
        with observer_scope(lambda event,**payload:b.append(event)):
            emit_source_event('inner')
        emit_source_event('restored')
    emit_source_event('absent')
    assert [e for e,_ in a]==['outer','restored'] and b==['inner']


def test_original_sink_exception_and_context_reset():
    error=OSError('disk')
    def fail(*args,**kwargs):raise error
    with pytest.raises(OSError) as caught:
        with observer_scope(fail):emit_source_event('returned',value=object())
    assert caught.value is error
    emit_source_event('no_failure_outside_scope')


def test_secondary_failure_does_not_replace_primary():
    error=ValueError('primary')
    def fail(*args,**kwargs):raise RuntimeError('secondary')
    with observer_scope(fail):emit_source_failure('failed',error)
    assert error.__notes__==['source observer failure notification failed: RuntimeError']


def test_async_tasks_isolated():
    async def task(name):
        seen=[]
        with observer_scope(lambda event,**payload:seen.append(event)):
            await asyncio.sleep(0)
            emit_source_event(name)
        return seen
    async def run():return await asyncio.gather(task('a'),task('b'))
    assert asyncio.run(run())==[['a'],['b']]


def test_threads_isolated():
    def run(name):
        seen=[]
        with observer_scope(lambda event,**payload:seen.append(event)):emit_source_event(name)
        return seen
    with ThreadPoolExecutor(2) as pool:assert list(pool.map(run,['a','b']))==[['a'],['b']]


def test_bad_sink():
    with pytest.raises(TypeError):
        with observer_scope(None):pass


def test_rhs_actual_return_before_late_validation(monkeypatch):
    from test_source_liquid_column import setup
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    from sludge_sandbox.exact_event_clock import ExactEventTime
    from sludge_sandbox.integration import Rates
    model,initial=setup(monkeypatch,count=1)
    host=ExactSourceColumn(model);state=host.pack(initial);events=[];error=ValueError('late derivative validation')
    def fail(*args,**kwargs):raise error
    monkeypatch.setattr(Rates,'derivatives',fail)
    with observer_scope(lambda event,**payload:events.append((event,payload))):
        with pytest.raises(ValueError) as caught:host.evaluate(state,ExactEventTime(Fraction()))
    assert caught.value is error
    assert [e for e,_ in events]==['rhs_started','rhs_returned','rhs_failed']
    assert events[1][1]['evaluation'] is events[2][1]['evaluation']
    assert events[0][1]['state'] is state


def test_rhs_started_sink_exception_is_not_wrapped(monkeypatch):
    from test_source_liquid_column import setup
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    model,initial=setup(monkeypatch,count=1);host=ExactSourceColumn(model);error=OSError('sink')
    def sink(event,**payload):
        if event=='rhs_started':raise error
    with observer_scope(sink):
        with pytest.raises(OSError) as caught:host.evaluate(host.pack(initial),None)
    assert caught.value is error


def test_heos_start_cancel_before_any_constructor(monkeypatch):
    import sludge_sandbox.water_heos as mod
    error=RuntimeError('stop');calls=[]
    monkeypatch.setattr(mod,'HEOSCandidate',lambda *a:calls.append(a))
    def sink(event,**payload):
        if event=='heos_started':raise error
    with observer_scope(sink):
        with pytest.raises(RuntimeError) as caught:mod.HEOSWaterProperties('missing','missing')
    assert caught.value is error and calls==[]


def test_rhs_callable_preserves_valueerror_from_sink(monkeypatch):
    from test_source_liquid_column import setup
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    model,initial=setup(monkeypatch,count=1);host=ExactSourceColumn(model);error=ValueError('sink')
    def sink(event,**payload):
        if event=='rhs_started':raise error
    with observer_scope(sink):
        with pytest.raises(ValueError) as caught:host(host.pack(initial),None)
    assert caught.value is error


def test_wet_return_kept_before_sink_failure():
    from test_source_wet_shared_pressure import actual_wet_pair
    from sludge_sandbox.source_wet_shared_pressure import collect_source_wet_pressure_pair,declare_source_shared_wet_volume
    gen=actual_wet_pair.__wrapped__();storage,ends,calls=next(gen);events=[];error=ValueError('save failed')
    def sink(event,**payload):
        events.append((event,payload))
        if event=='wet_returned':raise error
    try:
        with observer_scope(sink):
            with pytest.raises(ValueError) as caught:
                collect_source_wet_pressure_pair(*ends,shared_volume=declare_source_shared_wet_volume(storage))
        assert caught.value is error
        assert [e for e,_ in events]==['wet_started','wet_returned','wet_failed']
        assert events[1][1]['state'] is events[2][1]['state']
    finally:gen.close()


@pytest.mark.parametrize('failure_event',['candidate_returned','transition_returned','late_check'])
def test_transition_retains_returns_before_checks(monkeypatch,failure_event):
    from types import SimpleNamespace as NS
    import sludge_sandbox.source_dry_transition as mod
    error=ValueError('observed return then failure');events=[]
    refinement=NS(check=lambda:None,clock=object(),shifted_trial=object(),approach=NS(proposal=NS(original_trial=object(),event_policy=object())))
    monkeypatch.setattr(mod,'SourceRootRefinement',NS)
    monkeypatch.setattr(mod,'_check_shared_volume',lambda *a:None)
    monkeypatch.setattr(mod,'_check_shared_wet_volumes',lambda *a:None)
    candidate=NS(status='executed_dry_candidate',reason=None)
    monkeypatch.setattr(mod,'execute_source_dry_candidate',lambda *a,**k:candidate)
    def late_check():
        if failure_event=='late_check':raise error
    result=NS(check=late_check)
    monkeypatch.setattr(mod,'compare_source_dry_candidates',lambda *a,**k:result)
    def sink(event,**payload):
        events.append((event,payload))
        if event==failure_event:raise error
    with observer_scope(sink):
        with pytest.raises((ValueError,mod.SourceDryTransitionError)) as caught:
            mod.evaluate_source_dry_transition(refinement,end=None,maximum_callbacks_per_path=1)
    if failure_event=='late_check':assert caught.value.__cause__ is error
    else:assert caught.value is error
    assert events[0][1]['candidate'] is candidate
    if failure_event!='candidate_returned':assert events[-1][1]['result'] is result


def test_secondary_sink_failure_preserves_rhs_valueerror(monkeypatch):
    from test_source_liquid_column import setup
    from sludge_sandbox.exact_source_column import ExactSourceColumn
    model,initial=setup(monkeypatch,count=1);host=ExactSourceColumn(model);error=ValueError('primary')
    def sink(event,**payload):
        if event=='rhs_started':raise error
        raise OSError('secondary')
    with observer_scope(sink):
        with pytest.raises(ValueError) as caught:host(host.pack(initial),None)
    assert caught.value is error
