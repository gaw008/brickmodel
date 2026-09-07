"""Preserve bounded two-cell coupled depletion attempts and independent audits."""
from pathlib import Path
import dataclasses
import hashlib
import json
import sys
from depletion_host_run import encode

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tests/sandbox'))
from test_depletion_coupled_host import run_coupled_host,audit_coupled_host
from test_solid_fluid_heat import ingredients


if __name__=='__main__':
    output=Path(sys.argv[1])
    if output.exists():raise SystemExit('Refusing to overwrite previous evidence')
    paths=[Path(__file__),Path(__file__).with_name('depletion_host_run.py'),
        *sorted((ROOT/'src/sludge_sandbox').glob('*.py')),*sorted((ROOT/'tests/sandbox').glob('*.py'))]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    before=hashes()
    op,result=run_coupled_host(ingredients.__wrapped__())
    data={f.name:encode(getattr(result,f.name)) for f in dataclasses.fields(result) if f.name!='operator'}
    data['qualification']='two_cell_real_water_manufactured_solid_reactions_transport_not_sludge_validation'
    data['interfaces']=result.operator.interfaces
    try:
        data['independent_audit']=audit_coupled_host(op,result)
        data['audit_status']='passed'
    except Exception as exc:
        data['audit_status']='failed'
        data['audit_error']=f'{type(exc).__name__}: {exc}'
    data['sha256_before']=before;data['sha256_after']=hashes()
    data['sources_unchanged']=data['sha256_before']==data['sha256_after']
    output.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:data[k] for k in ('status','reason','audit_status','sources_unchanged','evaluations','attempted_steps','elapsed_seconds')}))
    raise SystemExit(0 if data['audit_status']=='passed' and data['sources_unchanged'] else 1)
