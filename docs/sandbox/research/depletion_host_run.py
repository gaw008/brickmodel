"""Run the preregistered real-water host; preserve failures as well as success."""
import dataclasses
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests/sandbox'))
from test_depletion_host import run_wet_dry_host,assert_wet_dry_host
from test_solid_fluid_heat import ingredients


def encode(value):
    if isinstance(value,Fraction):return str(value)
    if dataclasses.is_dataclass(value):
        return {f.name:encode(getattr(value,f.name)) for f in dataclasses.fields(value)}
    if hasattr(value,'tolist'):return value.tolist()
    if isinstance(value,(list,tuple)):return [encode(v) for v in value]
    if isinstance(value,dict):return {str(k):encode(v) for k,v in value.items()}
    return value


if __name__=='__main__':
    destination=Path(sys.argv[1])
    if destination.exists():raise SystemExit('Refusing to overwrite prior evidence')
    paths=[Path(__file__),*sorted((ROOT/'tests/sandbox').glob('*.py')),
           *sorted((ROOT/'src/sludge_sandbox').glob('*.py'))]
    def hashes():
        return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    before_hashes=hashes()
    op,result=run_wet_dry_host(ingredients.__wrapped__())
    data={f.name:encode(getattr(result,f.name)) for f in dataclasses.fields(result) if f.name!='operator'}
    data['interfaces']=result.operator.interfaces
    data['qualification']='manufactured_solid_and_kinetics_real_water_provider_not_sludge_validation'
    try:
        assert_wet_dry_host(op,result)
        data['host_assertions']='passed'
    except Exception as exc:
        data['host_assertions']='failed'
        data['assertion_error']=f'{type(exc).__name__}: {exc}'
    data['sha256_before']=before_hashes
    data['sha256_after']=hashes()
    data['sources_unchanged_during_run']=data['sha256_before']==data['sha256_after']
    destination.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:data[k] for k in ('status','reason','host_assertions','evaluations','attempted_steps','elapsed_seconds')}))
    raise SystemExit(0 if data['host_assertions']=='passed' and data['sources_unchanged_during_run'] else 1)
