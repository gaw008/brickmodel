"""Local-only frozen research CLI. No finalize API or automatic second demo."""
import argparse
import json
import sys
from model import ROOT, SCOPE, load_scenario
from scenarios import expand_frozen_manifest, matrix
from paths import new_directory, relative
from resources import Budget, parse_budget
from binding import capture_identity, verify_identity, load_evidence, reference, save_inputs
from solver import integrate
from exports import write_raw, write_json, write_csv
from diagnostics import compute, numerical_label
from audit import audit_exports
import screening
import plots
import report


class SafeParser(argparse.ArgumentParser):
    def error(self,message): raise ValueError('cli_arguments')


def options(argv):
    p=SafeParser(description='B2 synthetic dimensionless research only')
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--suite',choices=['frozen']); group.add_argument('--config')
    p.add_argument('--out',required=True); p.add_argument('--budget-seconds',default='180'); p.add_argument('--verification')
    for flag in ('--out','--budget-seconds','--verification','--suite','--config'):
        if argv.count(flag)>1: raise ValueError('duplicate_argument')
    return p.parse_args(argv)


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    budget=Budget(None,180,'parse'); out=None; results=[]; frozen=True; cases=[]; identity=None
    try:
        # Safe preliminary budget parse ensures failures never report ceiling as active.
        value='180'
        if '--budget-seconds' in argv:
            i=argv.index('--budget-seconds'); value=argv[i+1] if i+1<len(argv) else None
        budget.active=parse_budget(value,180)
        args=options(argv); frozen=args.config is None
        out=new_directory(args.out)
        cases=expand_frozen_manifest() if frozen else [load_scenario(args.config)]
        budget.pending=[s.id for s in cases]; budget.phase='preflight'; budget.check()
        binding=load_evidence(args.verification)
        identity=capture_identity()
        expanded=save_inputs(out/'inputs',cases)
        if binding['binding_status'] in ('mismatch','incomplete','failed'):
            status=binding['binding_status']
            failure={'execution_status':'numerical_failure' if status=='failed' else 'rejected_input',
                     'numerical_validation':numerical_label(frozen,'integrated',None,status),
                     'verification_scope':'frozen_suite' if frozen else 'audit_only',
                     'binding_status':status,'binding_reason':binding['binding_reason'],
                     'screening_status':'unknown_numerical' if status=='failed' else 'unresolved_in_assumption_envelope',
                     'resources':budget.snapshot('evidence_rejected')}
            write_json(out/'failure.json',failure); write_json(out/'resources.json',failure['resources'])
            print(json.dumps(failure,allow_nan=False)); return 1
        budget.phase='integrate'
        for s in cases:
            budget.check(); result=integrate(s,budget); results.append(result)
            budget.completed.append(s.id); budget.pending.remove(s.id)
        budget.phase='raw_export'; write_raw(out,results); budget.check()
        raw_files=[reference(out/name) for name in ('raw_index.json','timeseries.csv','profiles.csv','flux_intervals.csv')]
        budget.phase='current_audit'; current=audit_exports(relative(out)); write_json(out/'audit.json',current)
        if not current['passed']: raise ArithmeticError('current_raw_audit_failed')
        # Recompute identity and re-read the actual focused evidence before promotion.
        budget.check()
        if not verify_identity(identity): raise ValueError('source_changed_during_run')
        fresh=load_evidence(args.verification)
        if fresh['binding_status']!=binding['binding_status'] or fresh.get('focused_evidence')!=binding.get('focused_evidence'):
            raise ValueError('evidence_changed_during_run')
        diagnostics=[]
        for result in results:
            d=compute(result.scenario,result); sid=d['scenario_id']
            d.update(verification_scope='frozen_suite' if frozen else 'audit_only',
                     numerical_validation=numerical_label(frozen,result.execution_status,current['per_case'].get(sid,{}).get('result')=='passed',binding['binding_status']))
            diagnostics.append(d)
        coverage=list(binding.get('coverage',[]))
        current_refs=raw_files+[reference(out/'audit.json')]
        for ent in expanded:
            coverage.append(dict(criterion_id='B2-NUM-002',target_input_sha256=ent['sha256'],executed_input_sha256s=[ent['sha256']],
                                 coverage_kind='per_case',result='passed',evidence_files=current_refs))
        manifest={**identity,'kind':'B2_run_manifest','baseline_commit':'d051c0982835dbe54fc4f509f1819661b85de055',
                  'scope':SCOPE,'command':['python3','-B','run.py',*argv],'expanded_inputs':expanded,
                  'focused_evidence':binding.get('focused_evidence'),'raw_result_files':raw_files,
                  'current_audit':reference(out/'audit.json'),'coverage':coverage,
                  'binding_status':binding['binding_status'],'binding_reason':binding['binding_reason'],
                  'units':matrix()['units'],'provenance':'synthetic_assumption','production_approved':False}
        verification={'kind':'bound_run_verification',**identity,'binding_status':binding['binding_status'],'binding_reason':binding['binding_reason'],
                      'focused_evidence':binding.get('focused_evidence'),'current_audit':reference(out/'audit.json'),'coverage':coverage,
                      'scenarios':[{k:d[k] for k in ('scenario_id','execution_status','verification_scope','numerical_validation')} for d in diagnostics],
                      'independent_safety_approved':False,'production_approved':False}
        summary={'kind':'B2_diagnostics','scope':SCOPE,'binding_status':binding['binding_status'],'scenarios':diagnostics,
                 'independent_safety_approved':False,'production_approved':False}
        budget.phase='report'
        rows=screening.evaluate(matrix(),diagnostics,verification)
        write_json(out/'manifest.json',manifest); write_json(out/'verification.json',verification); write_json(out/'summary.json',summary)
        write_csv(out/'screening.csv',matrix()['screening_output_required_fields'],rows)
        plots.generate(out,binding['binding_status']); plotcheck=plots.verify(out); write_json(out/'svg_checks.json',plotcheck)
        report.generate(out,diagnostics,rows,manifest)
        # Now independently verify final derived summaries as well, without overwriting raw audit identity.
        final_audit=audit_exports(relative(out)); write_json(out/'final_audit.json',final_audit)
        if not final_audit['passed']: raise ArithmeticError('final_derived_audit_failed')
        gate_results=[]
        for criterion in matrix()['criteria']:
            cid=criterion['id']; result='not_run'; reason='Independent or unexecuted gate; not inferred from numerical label'
            evidence=[]
            if cid=='B2-GOV-001':
                result='passed'; reason='Separate Manager G0 accepted B2-BIND-001'; evidence=[reference(ROOT/'MANAGER_G0_DECISION.json')]
            elif cid=='B2-GOV-002': reason='Independent Safety child pending; Engineer cannot approve'
            elif cid=='B2-REP-001': reason='Archive and fresh-copy offline replay are subsequent bounded evidence'
            elif cid in ('B2-NUM-002','B2-NUM-007','B2-OUT-001'):
                result='passed'; reason='Current raw and derived-data checks'; evidence=current_refs+[reference(out/'final_audit.json'),reference(out/'svg_checks.json')]
            elif cid.startswith('B2-NUM-'):
                cs=[c for c in coverage if c['criterion_id']==cid]
                if cs and all(c['result']=='passed' for c in cs): result='passed'; reason='Executed focused numerical evidence'; evidence=cs[0]['evidence_files']
            gate_results.append({'criterion_id':cid,'result':result,'reason':reason,'evidence_files':evidence})
        write_json(out/'test_results.json',{'criteria':gate_results,'exit_code':0,'independent_safety_approved':False})
        budget.check()
        if not verify_identity(identity): raise ValueError('source_changed_during_run')
        budget.phase='complete'; resources=budget.snapshot('integrated'); write_json(out/'resources.json',resources)
        print(json.dumps({'execution_status':'integrated','binding_status':binding['binding_status'],'scenario_count':len(results),'resources':resources},allow_nan=False))
        return 0
    except (ValueError,OSError,ArithmeticError,TimeoutError,RuntimeError) as exc:
        # Fixed safe errors only: never include an untrusted input value or traceback.
        if isinstance(exc,TimeoutError): code,status=3,'partial_timeout'
        elif isinstance(exc,RuntimeError): code,status=3,'resource_limit'
        elif isinstance(exc,ArithmeticError): code,status=1,'numerical_failure'
        else: code,status=2,'rejected_input'
        reason='budget_parse_rejected' if budget.active is None else status
        failure={'execution_status':status,'reason':reason,'verification_scope':'frozen_suite' if frozen else 'audit_only',
                 'numerical_validation':numerical_label(frozen,status,False if code==1 else None,'missing'),
                 'screening_status':'unknown_numerical' if code==1 else 'unresolved_in_assumption_envelope',
                 'resources':budget.snapshot(status,reason),'production_approved':False}
        if out is not None:
            if results and not (out/'raw_index.json').exists(): write_raw(out,results)
            write_json(out/'failure.json',failure); write_json(out/'resources.json',failure['resources'])
        print(json.dumps(failure,allow_nan=False)); return code


if __name__=='__main__': sys.exit(main())
