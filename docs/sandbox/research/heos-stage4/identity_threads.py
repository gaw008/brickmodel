from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
from heos_candidate import HEOSCandidate
from sludge_sandbox.water_properties import WaterSourceError
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage4')
w=HEOSCandidate(case/'expected.json',repo/'data/sandbox/water');CP=w._cp
out={'source_rejections':[]}
try:
    CP.set_reference_state('Water','NBP')
    for name,f in [('existing',lambda:w.saturation_pair(300.)),('new',lambda:HEOSCandidate(case/'expected.json',repo/'data/sandbox/water'))]:
        try:f()
        except WaterSourceError as e:out['source_rejections'].append({'case':name,'error':str(e)})
        else:raise AssertionError('changed reference accepted:'+name)
finally:
    CP.set_reference_state('Water','DEF')
assert len(out['source_rejections'])==2
# Restoration is validated by the ordinary source-gated constructor, not assumed.
w=HEOSCandidate(case/'expected.json',repo/'data/sandbox/water')
cases=[(t,1e7,'liquid') for t in (300.,350.,400.,450.)]*3
def evaluate(c):return w.state_tp(c[0],c[1],phase=c[2])
sequential=list(map(evaluate,cases))
with ThreadPoolExecutor(max_workers=4) as pool:parallel=list(pool.map(evaluate,cases))
assert sequential==parallel
out.update({'passed':True,'thread_cases':cases,'thread_workers':4,'identical_snapshots':len(parallel),'implementation':w.identity})
(case/'identity-result.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
