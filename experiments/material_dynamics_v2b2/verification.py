"""Bounded named numerical evidence. No default pass inferred from names."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from model import ROOT, Scenario, canonical
from scenarios import expand_frozen_manifest, matrix
from solver import integrate
from diagnostics import compute
from exports import write_raw, write_json
from binding import reference
from paths import relative
from reference import oracle


def compare_events(a,b):
    result={}
    for name in a:
        x,y=a[name]['tau'],b[name]['tau']
        status='both_null_not_observed' if x is None and y is None else 'event_convergence_unresolved' if (x is None)!=(y is None) else 'compared'
        err=None if x is None or y is None else abs(x-y)
        result[name]={'status':status,'time_error':err,'left_bracket':a[name]['bracket_tau'],'right_bracket':b[name]['bracket_tau']}
    return result


def refinement_metrics(coarse,middle,fine,kind):
    from diagnostics import row
    fields=('f_mean','f_max','u_core')
    arrays=[[row(r.scenario,t,y) for t,y in r.records] for r in (coarse,middle,fine)]
    result={}; passed=True
    for field in fields:
        a=max(abs(x[field]-y[field]) for x,y in zip(arrays[0],arrays[1])); b=max(abs(x[field]-y[field]) for x,y in zip(arrays[1],arrays[2]))
        limit=(.01 if field=='u_core' else .005) if kind=='space' else (.002 if field=='u_core' else .001)
        good=b<=limit and (b<=1.1*a or max(a,b)<=1e-6)
        result[field]={'coarse_difference':a,'fine_difference':b,'limit':limit,'passed':good}; passed &=good
    ea=compute(middle.scenario,middle)['events']; eb=compute(fine.scenario,fine)['events']; ev=compare_events(ea,eb)
    for item in ev.values():
        if item['status']=='event_convergence_unresolved' or (item['time_error'] is not None and item['time_error']>.1): passed=False
    return {'passed':passed,'metrics':result,'events':ev,'step_counts':[r.steps for r in (coarse,middle,fine)],
            'u_core_granularity':'first cell average changes with N; not an exact center point'}


class NumericalEvidence:
    def __init__(self,out,budget):
        self.out=out; self.budget=budget; self.cases={s.id:s for s in expand_frozen_manifest()}; self.executed=[]; self.gates={}; self.calls=0; self.b1_calls=0
        (out/'executed_inputs').mkdir(); (out/'numeric').mkdir()

    def save_input(self,label,payload):
        p=self.out/'executed_inputs'/(label+'.json'); write_json(p,payload)
        entry={'scenario_id':label,**reference(p)}; self.executed.append(entry); return entry

    def solve(self,label,s,dirichlet=False):
        self.calls+=1
        if self.calls+self.b1_calls>40: raise RuntimeError('invocation_resource_limit')
        self.budget.phase=label; self.budget.check()
        payload=s.to_dict() if not dirichlet else {'scenario':s.to_dict(),'test_only_dirichlet':True,'test_initial':{'u':0,'v':1,'f':1},'test_surface':{'u':1,'v':0}}
        entry=self.save_input(label,payload)
        before=time.monotonic(); result=integrate(s,self.budget,test_only_dirichlet=dirichlet)
        folder=self.out/'numeric'/label; folder.mkdir(); write_raw(folder,[result]); diag=compute(s,result)
        write_json(folder/'diagnostics.json',diag)
        write_json(folder/'execution.json',{'label':label,'execution_status':result.execution_status,'steps':result.steps,'rejected_steps':result.rejected_steps,
                                         'elapsed_wall_seconds':time.monotonic()-before,'input':entry})
        self.budget.completed.append(label)
        return result,entry,folder

    def gate(self,cid,passed,details,entries,files):
        p=self.out/'numeric'/(cid+'.json'); write_json(p,{'criterion_id':cid,'passed':bool(passed),'details':details})
        self.gates[cid]={'result':'passed' if passed else 'failed','executed_input_sha256s':[x['sha256'] for x in entries],
                         'evidence_files':[reference(p)]+[reference(f) for f in files]}
        if not passed: raise ArithmeticError('frozen_numerical_gate_failed')

    def sealed(self):
        details=[]; entries=[]; files=[]; all_ok=True
        for gamma in (.25,1,2):
            d=self.cases['C02'].to_dict(); d['temperature']['knots']=deepcopy(matrix()['scenario_manifest']['programs']['P_CYCLE']); d['reaction']['Gamma']=gamma
            s=Scenario.from_dict(d); label='A_SEALED_'+str(gamma).replace('.','_')
            result,ent,folder=self.solve(label,s); entries.append(ent)
            trajectory=[]; error=0.
            for t,state in result.records:
                H,qtrace=oracle.exposure(d['temperature']['knots'],t,1,6); ref=oracle.sealed_state(gamma,H)
                err=max(abs(x-y) for values,y in zip((state.u,state.v,state.f),ref) for x in values); error=max(error,err)
                trajectory.append({'tau':t,'H':H,'reference_u_v_f':ref,'max_abs_error':err,'quadrature':qtrace})
            p=folder/'independent_reference.json'; write_json(p,trajectory)
            files += [p,folder/'profiles.csv',folder/'flux_intervals.csv',folder/'execution.json']
            good=error<=2e-5; all_ok &=good; details.append({'Gamma':gamma,'max_abs_error':error,'limit':2e-5,'passed':good})
        self.gate('B2-NUM-004',all_ok,details,entries,files)

    def diffusion(self):
        details=[]; entries=[]; files=[]; all_ok=True
        for program in ('P_EARLY','P_ISO'):
            errors=[]
            for n in (7,15,31):
                d=self.cases['C01'].to_dict(); d['reaction']['theta']=0; d['numerics']['n_cells']=n; d['temperature']['knots']=deepcopy(matrix()['scenario_manifest']['programs'][program])
                result,ent,folder=self.solve(f'A_DIFF_{program}_{n}',Scenario.from_dict(d),True); entries.append(ent)
                trajectory=[]; errmax=0.; seriesmax=0.
                for t,state in result.records:
                    if t<.5: continue
                    S=oracle.diffusion_time(d['temperature']['knots'],t)
                    ref=[oracle.diffusion_cell(n,i,S,256) for i in range(n)]
                    small=[oracle.diffusion_cell(n,i,S,128) for i in range(n)]
                    series=max(abs(a-b) for a,b in zip(ref,small)); err=max(abs(a-b) for a,b in zip(state.u,ref)); errmax=max(errmax,err); seriesmax=max(seriesmax,series)
                    trajectory.append({'tau':t,'S_D':S,'reference_cell_u':ref,'series_abs_change':series,'max_abs_error':err})
                p=folder/'independent_reference.json'; write_json(p,trajectory)
                files += [p,folder/'profiles.csv',folder/'execution.json']; errors.append(errmax)
                all_ok &=seriesmax<=1e-9
                details.append({'program':program,'N':n,'max_abs_error':errmax,'series_max_change':seriesmax})
            all_ok &= errors[2]<=5e-4 and errors[2]<errors[1]<errors[0]
        self.gate('B2-NUM-005',all_ok,details,entries,files)

    def regression(self):
        entries=[]; files=[]; details=[]; per={}; results={}
        for sid in ('R01','R02','R03','R04'):
            s=self.cases[sid]; d=s.to_dict(); result,ent,folder=self.solve(sid,s); entries.append(ent); results[sid]=result
            b1name=next(r['b1_scenario'] for r in matrix()['scenario_manifest']['runs'] if r['scenario_id']==sid)
            b1={'schema_version':1,'scope':'dimensionless_reaction_transport_benchmark','scenario_id':b1name,
                'K':d['reaction']['K_ref'],'Gamma':d['reaction']['Gamma'],'Bi':d['transport']['Bi_ref'],
                'boundary_mode':d['boundary']['mode'],'reservoir_ratio':d['boundary']['reservoir_ratio'],
                'n_cells':15,'tau_end':20,'diagnostic_thresholds':[.95,.99]}
            bentry=self.save_input('B1_'+sid,b1); entries.append(bentry); oldout=folder/'b1_fresh.json'; self.b1_calls+=1
            remaining=self.budget.active-(time.monotonic()-self.budget.start); self.budget.check()
            cmd=[sys.executable,'-B',str(ROOT/'reference/b1/sentinel.py'),str(ROOT/bentry['path']),str(oldout),str(remaining)]
            before=time.monotonic(); p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=remaining)
            write_json(folder/'b1_command.json',{'command':['python3','-B','reference/b1/sentinel.py',bentry['path'],relative(oldout),'remaining_focused_budget'],
                                               'exit_code':p.returncode,'elapsed_wall_seconds':time.monotonic()-before,'stderr':p.stderr if p.returncode==0 else 'B1_sentinel_failure'})
            if p.returncode: raise ArithmeticError('b1_sentinel_failed')
            old=json.loads(oldout.read_text()); maxerr=0.
            if len(old['records'])!=len(result.records): raise ArithmeticError('b1_sample_count')
            for oldrow,(t,y) in zip(old['records'],result.records):
                if abs(t-oldrow['tau'])>1e-12: raise ArithmeticError('b1_sample_time')
                os=oldrow['state']
                for field in ('u','v','f'):
                    maxerr=max(maxerr,max(abs(a-b)/max(1,abs(b)) for a,b in zip(getattr(y,field),os[field])))
                for field in ('generated','net_u','net_v','u_res','v_res'):
                    a,b=getattr(y,field),os[field]
                    if a is None or b is None:
                        if a is not b: raise ArithmeticError('b1_null')
                    else: maxerr=max(maxerr,abs(a-b)/max(1,abs(b)))
            from audit import threshold
            times=[r['tau'] for r in old['records']]; events={}
            for name,values in [('mean',[sum(r['state']['f'])/15 for r in old['records']]),('local',[max(r['state']['f']) for r in old['records']])]:
                for pct,q in ((95,.05),(99,.01)): events[name+str(pct)]=threshold(times,values,q,None)
            ev=compare_events(events,compute(s,result)['events']); good=maxerr<=1e-4 and all(x['status']!='event_convergence_unresolved' and (x['time_error'] is None or x['time_error']<=.1) for x in ev.values())
            detail={'scenario_id':sid,'max_scaled_error':maxerr,'events':ev,'passed':good}; details.append(detail)
            evfile=folder/'regression.json'; write_json(evfile,detail)
            fs=[evfile,oldout,folder/'b1_command.json',folder/'profiles.csv',folder/'flux_intervals.csv']; files+=fs
            per[sid]={'result':'passed' if good else 'failed','executed_input_sha256s':[ent['sha256'],bentry['sha256']],'evidence_files':[reference(f) for f in fs]}
        self.gate('B2-NUM-001',all(x['passed'] for x in details),details,entries,files)
        self.gates['B2-NUM-001']['per_case']=per
        # Actual B1 weak-film sentinel proves separate mean/local threshold semantics.
        diag=compute(self.cases['R04'],results['R04'])
        good=diag['events']['mean99']['tau'] is not None and diag['events']['local99']['tau'] is None
        self.gate('B2-NUM-007',good,{'R04':diag['events'],'meaning':'mean99 reached while local99 did not'},entries,files)

    def refinement(self):
        details=[]; entries=[]; files=[]; all_ok=True
        for sid in ('W03','L02','C03'):
            runs={}
            for n,scale in ((7,.25),(15,.25),(31,.25),(31,1),(31,.5)):
                d=self.cases[sid].to_dict(); d['numerics']['n_cells']=n; d['numerics']['dt_scale']=scale
                label=f'{sid}_N{n}_dt'+str(scale).replace('.','_')
                result,ent,folder=self.solve(label,Scenario.from_dict(d)); runs[(n,scale)]=result; entries.append(ent)
                files += [folder/'timeseries.csv',folder/'profiles.csv',folder/'flux_intervals.csv',folder/'diagnostics.json',folder/'execution.json']
            space=refinement_metrics(runs[(7,.25)],runs[(15,.25)],runs[(31,.25)],'space')
            temporal=refinement_metrics(runs[(31,1)],runs[(31,.5)],runs[(31,.25)],'time')
            counts=temporal['step_counts']; temporal['distinct_step_counts']=counts[0]<counts[1]<counts[2]
            temporal['passed'] &= temporal['distinct_step_counts']; all_ok &=space['passed'] and temporal['passed']
            details.append({'scenario_id':sid,'space':space,'time':temporal})
        self.gate('B2-NUM-006',all_ok,details,entries,files)

    def run(self):
        self.sealed(); self.diffusion(); self.regression(); self.refinement()
        return self
