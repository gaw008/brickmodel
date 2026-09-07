"""Compare exact public outputs in separately launched baseline/candidate processes."""
from dataclasses import asdict
import json
from pathlib import Path
from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.deforming_solid_storage import _canonical
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
w=load_water_properties(root/'data/sandbox/water')
records={'canonical':_canonical(w),'reference':asdict(w.reference),'assets':dict(w.source_asset_sha256),'cases':[]}
for t in (293.,300.,373.15,450.,500.):
    sat=w.saturation_pair(t)
    assert sat.liquid.reference is w.reference and sat.vapor.reference is w.reference
    records['cases'].append(asdict(sat))
    for phase,p in [('vapor',sat.pressure_pa*.5),('liquid',min(1e8,sat.pressure_pa*2))]:
        state=w.state_tp(t,p,phase=phase)
        assert state.reference is w.reference
        records['cases'].append(asdict(state))
        records['cases'].append(asdict(w.state_tp_response(t,p,phase=phase)))
    records['cases'].append(asdict(w.ideal_vapor(t)))
for args in [(292.,1e5,'liquid'),(300.,-1.,'vapor'),(300.,1e8+1.,'liquid'),(300.,1e5,'invalid')]:
    try:w.state_tp(args[0],args[1],phase=args[2])
    except ValueError as e:records['cases'].append({'error_type':type(e).__name__,'message':str(e)})
    else:raise AssertionError('expected rejection')
assert _canonical(w)==records['canonical']
print(json.dumps(records,sort_keys=True,allow_nan=False))
