"""One original source RHS after real reconstruction; no accepted integration step."""
import cProfile
from fractions import Fraction
import io
import json
from pathlib import Path
import pstats
import time

from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.source_run_observer import observer_scope
from sludge_sandbox.source_trajectory import open_source_trajectory
from sludge_sandbox.run_service import runtime_identity

root = Path('/private/tmp/brick-source-performance-v1')
out = root/'rhs01'
out.mkdir(parents=True, exist_ok=False)
parent = Path('/private/tmp/brick-source-dynamic-continuation-v1/native02/parent')
baseline = parent.parent/'continuous'
profiler = cProfile.Profile()
started = time.monotonic()
session = None
before = runtime_identity()

def first_return(directory):
    for path in sorted((directory/'events').glob('*.json')):
        event = json.loads(path.read_bytes())
        if event['event'] == 'rhs_returned':
            return event['payload']
    raise AssertionError('actual RHS return is missing')

try:
    session = open_source_trajectory(parent, out/'segment', end=ExactEventTime(Fraction(1, 16)))
    admission = time.monotonic()-started
    original = dict(session.parent_counts)
    assert session.recorder.counts['rhs_started'] == original['rhs_started']
    rhs_started = time.monotonic()
    with observer_scope(session.recorder):
        session.recorder.phase = 'ordinary_source_segment'
        profiler.enable()
        evaluation = session.adapter.evaluate(session.initial, session.start)
        profiler.disable()
    rhs_elapsed = time.monotonic()-rhs_started
    counts = dict(session.recorder.counts)
    for key in ('heos_started', 'heos_kernel_returned', 'heos_returned'):
        assert counts[key] == original[key]+4
    for key in ('rhs_started', 'rhs_returned'):
        assert counts[key] == original[key]+1
    for key in ('wet_started', 'wet_returned', 'initial_energy_started', 'initial_energy_returned'):
        assert counts[key] == original[key]
    assert first_return(out/'segment') == first_return(baseline)
    assert runtime_identity() == before
    result = dict(status='completed', admission_seconds=admission, rhs_profiled_seconds=rhs_elapsed,
                  elapsed_seconds=time.monotonic()-started, parent_counts=original, counts=counts,
                  full_original_rhs_payload_equal=True, accepted_steps=0, new_rhs=1, new_constructors=4,
                  runtime_before=before, runtime_after=runtime_identity(), material_qualified=False,
                  source_resume_authorized=False, scope='one profiled diagnostic RHS; no integration')
    (out/'RESULT.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not k.startswith('runtime')}, indent=2))
except BaseException as exc:
    (out/'FAILURE.json').write_text(json.dumps(dict(exception=type(exc).__name__, reason=str(exc),
        elapsed_seconds=time.monotonic()-started,
        counts=None if session is None else session.recorder.counts), indent=2)+'\n')
    raise
finally:
    profiler.disable()
    if session is not None:
        session.closed = True
    profiler.dump_stats(out/'profile.pstats')
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative').print_stats(60)
    stats.sort_stats('tottime').print_stats(40)
    (out/'PROFILE.txt').write_text(stream.getvalue())
