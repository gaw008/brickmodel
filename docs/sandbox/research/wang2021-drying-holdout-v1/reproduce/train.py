"""Stage1: only40/60 observations; freeze parameters before holdout access."""
import argparse
from pathlib import Path
import math
import time
import traceback
import numpy as np
from scipy.optimize import least_squares
from wang_d1 import Parameters, mean_curve
from independent_check import checked_curve
from study_io import binding, check_binding, load_curves, metrics, save

STARTS=tuple((d,k,40000.) for d in (1e-10,1e-9,1e-8) for k in (1e-7,1e-6,1e-5))
LOWER=np.array([math.log(1e-12),math.log(1e-10),0.])
UPPER=np.array([math.log(1e-7),math.log(1e-4),1.5])


def parameters(x):
    physical=[]
    for i,(lo,hi) in enumerate(((1e-12,1e-7),(1e-10,1e-4))):
        value=float(x[i])
        physical.append(lo if value==LOWER[i] else hi if value==UPPER[i] else math.exp(value))
    return Parameters(*physical,float(x[2])*100000)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--csv',required=True);parser.add_argument('--prereg',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output);out.mkdir(exist_ok=False)
    began=time.monotonic();bound=binding(args.csv,args.prereg);save(out/'binding.json',bound)
    result={'status':'started','starts':[],'policy':{'maximum_total_wall_s':120,'max_nfev_per_start':200,'xtol':1e-9,'ftol':1e-9,'gtol':1e-9,'near_best_objective_absolute':1e-8,'bound_scaled_distance':1e-6},'holdout_values_parsed':False}
    def guard():
        if time.monotonic()-began>=120:raise TimeoutError('original training total wall exhausted')
    try:
        curves=load_curves(args.csv,(40,60))
        if sum(map(len,curves.values()))!=117:raise ValueError('original117 selected observations required')
        winners=[]
        for index,start in enumerate(STARTS):
            record={'index':index,'initial':start,'residual_calls_attempted':0,'residual_calls_completed':0,'status':'started'}
            result['starts'].append(record);save(out/'training.json',result);tic=time.monotonic()
            def residual(x):
                guard();record['residual_calls_attempted']+=1
                p=parameters(x);parts=[]
                for (t,h), rows in sorted(curves.items()):
                    values,_=mean_curve(p,t,h/100,[r['time_s'] for r in rows],guard=guard)
                    parts.extend((values-np.array([r['observed'] for r in rows]))/math.sqrt(8*len(rows)))
                record['residual_calls_completed']+=1
                return np.array(parts)
            try:
                guard();fit=least_squares(residual,[math.log(start[0]),math.log(start[1]),start[2]/100000],bounds=(LOWER,UPPER),max_nfev=200,xtol=1e-9,ftol=1e-9,gtol=1e-9)
                guard();objective=float(np.dot(fit.fun,fit.fun));p=parameters(fit.x)
                record.update(status='converged' if fit.success else 'not_converged',parameters=vars(p),objective=objective,nfev=fit.nfev,njev=fit.njev,optimality=fit.optimality,termination=fit.message,active_mask=fit.active_mask.tolist(),near_search_boundary=bool(np.any(np.minimum(fit.x-LOWER,UPPER-fit.x)<=1e-6)),jacobian_singular_values=np.linalg.svd(fit.jac,compute_uv=False).tolist())
                if fit.success:winners.append((objective,index,p))
            except Exception as exc:
                record.update(status='failed',reason=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
                if isinstance(exc,TimeoutError):raise
            finally:
                record['elapsed_seconds']=time.monotonic()-tic;save(out/'training.json',result)
        if not winners:raise ValueError('no converged training start; holdout remains locked')
        best=min(winners,key=lambda x:(x[0],x[1]));guard()
        training_metrics=metrics(curves,lambda t,h,times:checked_curve(best[2],t,h,times,mean_curve,guard=guard))
        save(out/'training-metrics.json',training_metrics);guard();check_binding(bound)
        result.update(status='training_complete',selected_start=best[1],near_best=[r for r in result['starts'] if r.get('status')=='converged' and r['objective']<=best[0]+1e-8],elapsed_seconds=time.monotonic()-began)
        save(out/'training.json',result)
        frozen={'schema':'wang_d1_training_parameters_v1','parameters':vars(best[2]),'objective':best[0],'selected_start':best[1],'binding':bound,'training_temperatures':[40,60],'holdout_temperature':50,'qualification':'numerical search box not material prior; no unique material coefficient claim'}
        from study_io import sha
        frozen['training_report_sha256']=sha(out/'training.json');frozen['training_metrics_sha256']=sha(out/'training-metrics.json')
        save(out/'parameters.json',frozen)
    except Exception as exc:
        result.update(status='failed_no_parameter_freeze',reason=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),elapsed_seconds=time.monotonic()-began)
        save(out/'training.json',result);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
