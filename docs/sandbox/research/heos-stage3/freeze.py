import hashlib,json,importlib.metadata
from pathlib import Path
import CoolProp, CoolProp.CoolProp as CP
folder=Path('/private/tmp/brick-heos-stage3')
base=Path(CoolProp.__file__).resolve().parent
raw=CP.get_fluid_param_string('Water','JSON')
(folder/'fluid-runtime.json').write_text(raw)
files={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.rglob('*')) if p.is_file() and p.suffix in ('.py','.so')}
m={'version':importlib.metadata.version('CoolProp'),'git':CP.get_global_param_string('gitrevision'),'files':files,'fluid_sha256':hashlib.sha256(raw.encode()).hexdigest(),'fluid_canonical_sha256':hashlib.sha256(json.dumps(json.loads(raw),sort_keys=True,separators=(',',':')).encode()).hexdigest()}
(folder/'expected.json').write_text(json.dumps(m,indent=2)+'\n')
print(len(files),'files frozen; no EOS solve')
