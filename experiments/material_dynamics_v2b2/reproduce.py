"""One planned fresh-copy replay of frozen demo using preserved bound tests.

Does not re-run focused solves or silently finalize an unbound report.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from model import ROOT
from paths import new_directory, relative
from exports import write_json
from binding import digest
from build_repro import collect


def main():
    p=argparse.ArgumentParser(); p.add_argument('--run',required=True); p.add_argument('--tests',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    paths,identity,omitted=collect(a.run,a.tests); dest=new_directory(a.out)
    for src in paths:
        target=dest/src.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,target)
    write_json(dest/'SOURCE_SNAPSHOT.json',{'kind':'offline_source_snapshot','identity':identity,'scope':'preserved_byte_identity_not_independent_Safety'})
    commands=[]
    for args in (['-B','-m','unittest','discover','-s','tests','-v'],
                 ['-B','run.py','--suite','frozen','--out','validation/replay_demo','--budget-seconds','180','--verification',a.tests+'/verification.json'],
                 ['-B','audit.py','validation/replay_demo']):
        before=time.monotonic(); p=subprocess.run([sys.executable,*args],cwd=dest,capture_output=True,text=True,timeout=185)
        commands.append({'command':['python3',*args],'exit_code':p.returncode,'elapsed_wall_seconds':time.monotonic()-before,'stdout':p.stdout,'stderr':p.stderr})
        write_json(ROOT/'validation/reproduction_commands.json',commands)
        if p.returncode: raise RuntimeError('offline_replay_failed_no_retry')
    comparisons=[]
    for name in ('raw_index.json','timeseries.csv','profiles.csv','flux_intervals.csv','summary.json','screening.csv','thermal_profiles.svg','conditional_screening.svg','THERMAL_DIAGNOSTIC_REPORT.md','audit.json','final_audit.json'):
        old=ROOT/a.run/name; new=dest/'validation/replay_demo'/name
        comparisons.append({'artifact':name,'original_sha256':digest(old),'replayed_sha256':digest(new),'identical':old.read_bytes()==new.read_bytes()})
    new_resources=json.loads((dest/'validation/replay_demo/resources.json').read_text())
    result={'passed':all(x['identical'] for x in comparisons),'source_commit':identity['source_commit'],'comparisons':comparisons,
            'replay_resources':new_resources,'test_evidence':'Same committed bytes and preserved tests consumed; focused solves are NOT re-run here',
            'independent_safety_approved':False,'omitted_runtime_test_symlinks':len(omitted)}
    write_json(ROOT/'validation/reproduction_result.json',result); print(json.dumps(result,allow_nan=False))
    return 0 if result['passed'] else 1


if __name__=='__main__': sys.exit(main())
