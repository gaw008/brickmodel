"""Stage2: one-time50C observation unlock after externally pinned training freeze."""
import argparse
import json
from pathlib import Path
import time
import traceback
from wang_d1 import Parameters,mean_curve
from independent_check import checked_curve
from study_io import check_binding,load_curves,metrics,save,sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--training',required=True);parser.add_argument('--parameters-sha256',required=True);parser.add_argument('--csv',required=True);parser.add_argument('--output',required=True)
    a=parser.parse_args();parent=Path(a.training);out=Path(a.output);out.mkdir(exist_ok=False)
    report={'status':'started','holdout_values_parsed':False, 'holdout_access_started':False, 'holdout_parse_complete':False};start=time.monotonic()
    try:
        params=parent/'parameters.json'
        if sha(params)!=a.parameters_sha256:raise ValueError('external training freeze digest mismatch')
        frozen=json.loads(params.read_bytes())
        if frozen['schema']!='wang_d1_training_parameters_v1' or frozen['training_temperatures']!=[40,60] or frozen['holdout_temperature']!=50:raise ValueError('explicit original split/schema required')
        check_binding(frozen['binding'])
        if sha(parent/'training.json')!=frozen['training_report_sha256'] or sha(parent/'training-metrics.json')!=frozen['training_metrics_sha256']:raise ValueError('training outputs changed')
        csvpath=str(Path(a.csv).resolve())
        if csvpath not in frozen['binding']['files'] or sha(csvpath)!=frozen['binding']['files'][csvpath]:raise ValueError('unbound holdout data')
        # Single token lives with training, so changing output directory cannot rerun.
        with (parent/'HOLDOUT_UNLOCKED.json').open('x') as token:
            json.dump({'parameters_sha256':a.parameters_sha256,'output':str(out.resolve())},token)
        def guard():
            if time.monotonic()-start>=120:raise TimeoutError('single holdout evaluation wall exhausted')
        guard()
        # Mark access before parsing: an exception may follow already-read MR.
        # Legacy null means unknown/possibly partial access until parsing completes.
        report.update(holdout_access_started=True, holdout_values_parsed=None)
        save(out/'report.json',report)
        curves=load_curves(a.csv,(50,))
        report.update(holdout_parse_complete=True, holdout_values_parsed=True)
        if sum(map(len,curves.values()))!=57:raise ValueError('original57 holdout observations required')
        p=Parameters(**frozen['parameters'])
        values=metrics(curves,lambda t,h,times:checked_curve(p,t,h,times,mean_curve,guard=guard))
        save(out/'holdout-metrics.json',values);guard();check_binding(frozen['binding'])
        if sha(params)!=a.parameters_sha256:raise ValueError('training parameters changed during evaluation')
        report.update(status='evaluated',parameters_sha256=a.parameters_sha256,parameters=frozen['parameters'],qualification=values['qualification'])
    except Exception as exc:
        report.update(status='failed',reason=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
    report['elapsed_seconds']=time.monotonic()-start;save(out/'report.json',report)
    return 0 if report['status']=='evaluated' else 1

if __name__=='__main__':raise SystemExit(main())
