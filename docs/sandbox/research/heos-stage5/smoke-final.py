from dataclasses import asdict,replace
from pathlib import Path
import json,hashlib
from sludge_sandbox.water_properties import load_water_properties,WaterSourceError
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential,WaterChemicalError
from sludge_sandbox.deforming_solid_storage import _canonical
from sludge_sandbox.phase_storage import LiquidWaterPhase
repo=Path('/Users/wanggaoying/Desktop/brickmodel-github');case=Path('/private/tmp/brick-heos-stage5')
kw={'backend':'heos','backend_manifest':case/'expected.json'}
w=load_water_properties(repo/'data/sandbox/water',**kw);old=load_water_properties(repo/'data/sandbox/water')
other=load_water_properties(repo/'data/sandbox/water',**kw)
assert w.implementation==other.implementation and w.reference==old.reference
assert _canonical(w)!=_canonical(old) and _canonical(w)==_canonical(other)
s=w.state_tp(300.,1e5,phase='liquid');r=w.state_tp_response(300.,1e5,phase='liquid')
assert r.state==s and s.implementation is w.implementation and s.reference is w.reference
assert w.implementation.sha256==hashlib.sha256(w.implementation.canonical_json.encode()).hexdigest()
assert replace(w.implementation,provider_version='different').sha256!=w.implementation.sha256
assert 'coolprop-8.0.0-heos-water' in LiquidWaterPhase(w).metadata.source_ids
v=IdealWaterVapor(repo/'data/sandbox/water',**kw)
chem=WaterChemicalPotential(repo/"data/sandbox/water",**kw)
# Source-aligned chemical construction/state checks exercised below.
c=chem.liquid_tp(300.,1e5)
assert c.state.implementation==w.implementation
try:chem._liquid(replace(c.state,implementation=None))
except WaterChemicalError:pass
else:raise AssertionError('stripped implementation accepted')
saved=chem.vapor
object.__setattr__(chem,'vapor',IdealWaterVapor(repo/'data/sandbox/water'))
try:
    try:chem.liquid_tp(300.,1e5)
    except WaterChemicalError:pass
    else:raise AssertionError('mixed backend accepted')
finally:object.__setattr__(chem,'vapor',saved)
historical=json.loads((repo/'docs/sandbox/research/water-python-seam/bound-old.json').read_text())
assert _canonical(old)==historical['canonical']
(case/'smoke-result-final.json').write_text(json.dumps({'state':asdict(s),'chemical':asdict(c),'descriptor':json.loads(w.implementation.canonical_json),'default_canonical':_canonical(old),'heos_canonical':_canonical(w)},indent=2)+'\n')
print('factory/state/source/chemical identities passed')
