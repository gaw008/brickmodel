"""One passive installed read, profiled without allowing any live physics."""
from contextlib import ExitStack
import cProfile
import io
import json
from pathlib import Path
import pstats
import time
from unittest.mock import patch

from sludge_sandbox.exact_source_column import ExactSourceColumn
from sludge_sandbox.source_wet_storage import SourceWetStorage
from sludge_sandbox.water_properties import WaterProperties
from sludge_sandbox.water_heos import HEOSWaterProperties
from sludge_sandbox.run_service import read_run_with_source_record, runtime_identity

out = Path('/private/tmp/brick-source-performance-v1/passive01')
out.mkdir(parents=True, exist_ok=False)
parent = Path('/private/tmp/brick-source-dynamic-continuation-v1/native02/parent')
count = 0

def forbidden(*args, **kwargs):
    global count
    count += 1
    raise AssertionError('passive profiling attempted live physics')

before = runtime_identity()
profiler = cProfile.Profile()
started = time.monotonic()
try:
    with ExitStack() as stack:
        for cls in (ExactSourceColumn, SourceWetStorage, WaterProperties, HEOSWaterProperties):
            stack.enter_context(patch.object(cls, '__init__', forbidden))
        for cls in (ExactSourceColumn, SourceWetStorage):
            stack.enter_context(patch.object(cls, 'evaluate', forbidden))
        for cls in (WaterProperties, HEOSWaterProperties):
            stack.enter_context(patch.object(cls, 'state_tp', forbidden))
        profiler.enable()
        summary, manifest, record = read_run_with_source_record(parent)
        profiler.disable()
    elapsed = time.monotonic()-started
    assert count == 0 and record.roots['transition'].numerical_event_accepted
    assert runtime_identity() == before
    result = dict(status='completed', elapsed_seconds=elapsed, forbidden_live_calls=count,
                  parent_study_sha256=record.sha256, parent_status=summary['status'],
                  profile_scope='single full passive installed parent read; profiler overhead included',
                  runtime_before=before, runtime_after=runtime_identity())
    (out/'RESULT.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not k.startswith('runtime')}, indent=2))
finally:
    profiler.disable()
    profiler.dump_stats(out/'profile.pstats')
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative').print_stats(45)
    stats.sort_stats('tottime').print_stats(30)
    (out/'PROFILE.txt').write_text(stream.getvalue())
