"""Execute only the predeclared bounded validation commands, once per phase."""
import json
from pathlib import Path
import subprocess
import sys
import time
from model import ROOT
from exports import write_json
from resources import Budget

COMMANDS={
 'tests':(['run_tests.py','--out','validation/tests001','--budget-seconds','300'],300),
 'demo':(['run.py','--suite','frozen','--out','validation/demo001','--budget-seconds','180','--verification','validation/tests001/verification.json'],180),
 'audit':(['audit.py','validation/demo001'],30),
 'timeout':(['run.py','--suite','frozen','--out','validation/timeout001','--budget-seconds','0.000001'],10),
 'replay':(['reproduce.py','--run','validation/demo001','--tests','validation/tests001','--out','validation/replay001'],220),
 'package':(['build_repro.py','--run','validation/demo001','--tests','validation/tests001','--out','validation/b2-repro001.tar.gz'],30)}


def main():
    if len(sys.argv)!=2 or sys.argv[1] not in COMMANDS: return 2
    phase=sys.argv[1]; args,cap=COMMANDS[phase]; log=ROOT/'validation'/('command_'+phase+'.json')
    if log.exists(): raise ValueError('command_phase_already_recorded_no_automatic_retry')
    elapsed=sum(json.loads(p.read_text())['elapsed_wall_seconds'] for p in (ROOT/'validation').glob('command_*.json'))
    if elapsed+cap>900: raise RuntimeError('cumulative_budget_preflight_rejected')
    resource_log=ROOT/'validation'/('external_'+phase+'.txt')
    command=[sys.executable,'-B',*args]
    measured=['/usr/bin/time','-f','wall_seconds=%e\npeak_rss_KiB=%M\nexit_code=%x','-o',str(resource_log),*command]
    start=time.monotonic(); p=subprocess.run(measured,cwd=ROOT,capture_output=True,text=True,timeout=cap+3)
    record={'phase':phase,'command':['python3','-B',*args],'exit_code':p.returncode,'elapsed_wall_seconds':time.monotonic()-start,
            'external_resource_log':resource_log.name,'stdout':p.stdout,'stderr':p.stderr,'prior_recorded_verification_wall_seconds':elapsed}
    write_json(log,record)
    print(json.dumps(record,ensure_ascii=False,allow_nan=False))
    return p.returncode


if __name__=='__main__': sys.exit(main())
