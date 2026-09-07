from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dataclasses import asdict
import json,traceback
from heos_candidate import HEOSCandidate
from sludge_sandbox.water_properties import WaterNumericalError
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage4')
out={'passed':False}
try:
    w=HEOSCandidate(case/'expected.json',repo/'data/sandbox/water');CP=w._cp
    before=w.state_tp(300.,1e5,phase='liquid');out['before']=asdict(before)
    try:
        CP.set_reference_state('Water','NBP')
        after=w.state_tp(300.,1e5,phase='liquid');out['after']=asdict(after)
        assert before==after
        import CoolProp
        raw=CoolProp.AbstractState('HEOS','Water');raw.update(CP.PT_INPUTS,1e5,300.)
        out['new_native_enthalpy']=raw.hmass()
        assert abs(raw.hmass()-before.h)>1.
        try:HEOSCandidate(case/'expected.json',repo/'data/sandbox/water')
        except WaterNumericalError as e:
            assert str(e)=='heos_ideal_reference_anchor_mismatch'
            out['new_candidate_rejection']=str(e)
        else:raise AssertionError('changed new reference accepted')
    finally:CP.set_reference_state('Water','DEF')
    w=HEOSCandidate(case/'expected.json',repo/'data/sandbox/water')
    cases=[(t,1e7,'liquid') for t in (300.,350.,400.,450.)]*3
    def evaluate(c):return w.state_tp(c[0],c[1],phase=c[2])
    sequential=list(map(evaluate,cases))
    with ThreadPoolExecutor(max_workers=4) as pool:parallel=list(pool.map(evaluate,cases))
    assert sequential==parallel
    out.update(passed=True,thread_cases=cases,workers=4,sequential=[asdict(s) for s in sequential],parallel=[asdict(s) for s in parallel])
except BaseException as e:
    out.update(error=repr(e),traceback=traceback.format_exc())
    raise
finally:(case/'identity-result02.json').write_text(json.dumps(out,indent=2)+'\n')
