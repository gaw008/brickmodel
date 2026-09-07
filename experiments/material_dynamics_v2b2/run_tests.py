"""Tests-first producer for B2-BIND-001. Full evidence only after real execution."""
import argparse
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest
from unittest.mock import patch
import solver
from model import ROOT, canonical
from paths import new_directory, relative
from resources import Budget, parse_budget
from binding import capture_identity, verify_identity, save_inputs, reference, load_evidence
from scenarios import expand_frozen_manifest, matrix
from exports import write_json
from verification import NumericalEvidence
from coefficient_checks import record as coefficient_record
from mutations import audit_controls, binding_controls
from run import SafeParser


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv); budget=Budget(None,300,'parse'); out=None; runner=None
    try:
        value='300'
        if '--budget-seconds' in argv:
            i=argv.index('--budget-seconds'); value=argv[i+1] if i+1<len(argv) else None
        budget.active=parse_budget(value,300)
        parser=SafeParser(); parser.add_argument('--out',required=True); parser.add_argument('--budget-seconds',default='300'); args=parser.parse_args(argv)
        out=new_directory(args.out); budget.check(); identity=capture_identity()
        cases=expand_frozen_manifest(); frozen=save_inputs(out/'frozen_inputs',cases)
        write_json(out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'machine':platform.machine(),
                                          'encoding':'UTF-8','cwd':relative(ROOT) or '.', 'workers':1,'threads':1,'dependencies':'stdlib_only'})
        budget.phase='focused_unit'; os.environ['B2_TEST_OUT']=relative(out/'unit_fixtures')
        stream=io.StringIO(); tests=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_*.py')
        with patch('solver.integrate', wraps=solver.integrate) as unit_integrations:
            actual=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
        log=out/'unit_tests.log'; log.write_text(stream.getvalue(),encoding='utf-8')
        unit={'tests_run':actual.testsRun,'failures':len(actual.failures),'errors':len(actual.errors),'skipped':len(actual.skipped),
              'B2_solver_invocations':unit_integrations.call_count,'exit_code':0 if actual.wasSuccessful() else 1}
        write_json(out/'unit_test_results.json',unit)
        if not actual.wasSuccessful() or actual.skipped: raise ArithmeticError('focused_tests_failed')
        coeff=coefficient_record(out)
        runner=NumericalEvidence(out,budget)
        # The two historical-ramp regressions are real solves and count toward
        # the same 40-invocation ceiling as the named numerical evidence.
        runner.calls=unit['B2_solver_invocations']
        unit_entry=runner.save_input('executed_unit_semantics',{'kind':'executed_unit_fixture_inputs','test_command':['python3','-B','-m','unittest','discover','-s','tests','-v'],
                                                             'tests_run':actual.testsRun,'frozen_inputs':frozen,
                                                             'fixture_files':[reference(p) for p in sorted((out/'unit_fixtures').rglob('*')) if p.is_file() and not p.is_symlink() and not any(x.is_symlink() for x in p.parents if x!=ROOT)]})
        runner.run()
        budget.phase='adversarial_audit'; audit_log=audit_controls(out,budget)
        numeric=runner.gates
        unit_files=[reference(coeff),reference(log),reference(out/'unit_test_results.json')]
        numeric['B2-NUM-002']={'result':'passed','executed_input_sha256s':[unit_entry['sha256']],'evidence_files':unit_files,
                               'note':'Only signed single-step control here; current demo must audit every actual case'}
        numeric['B2-NUM-003']={'result':'passed','executed_input_sha256s':[unit_entry['sha256']],'evidence_files':unit_files}
        numeric['B2-NUM-008']={'result':'not_run','executed_input_sha256s':[unit_entry['sha256']],'evidence_files':unit_files}
        budget.phase='binding_controls'; write_json(out/'resources.json',budget.snapshot('binding_preflight'))
        def evidence():
            coverage=[]; resource_ref=reference(out/'resources.json')
            for ent in frozen:
                for cid,g in numeric.items():
                    if cid=='B2-NUM-001':
                        if ent['scenario_id'] not in g.get('per_case',{}): continue
                        g=g['per_case'][ent['scenario_id']]
                    kind='per_case' if cid=='B2-NUM-001' else 'representative_frozen_domain' if cid in ('B2-NUM-004','B2-NUM-005','B2-NUM-006') else 'suite_semantics'
                    coverage.append({'criterion_id':cid,'target_input_sha256':ent['sha256'],'executed_input_sha256s':g['executed_input_sha256s'],
                                     'coverage_kind':kind,'result':g['result'],'evidence_files':g['evidence_files']+[resource_ref]})
            return {**identity,'kind':'executed_focused_evidence','frozen_inputs':frozen,'executed_inputs':runner.executed,
                    'coverage':coverage,'command':['python3','-B','run_tests.py',*argv],'exit_code':0,
                    'resources_path':relative(out/'resources.json')}
        provisional=evidence(); controls=binding_controls(out,provisional,budget)
        numeric['B2-NUM-008']['result']='passed'; numeric['B2-NUM-008']['evidence_files']+= [reference(controls),reference(audit_log)]
        if not verify_identity(identity): raise ArithmeticError('source_changed_during_tests')
        budget.check(); budget.phase='complete'
        resources=budget.snapshot('integrated'); resources.update(additional_solver_invocations=runner.calls+runner.b1_calls,B2_solver_invocations=runner.calls,B1_sentinel_invocations=runner.b1_calls)
        write_json(out/'resources.json',resources)
        verification=evidence(); write_json(out/'verification.json',verification)
        bound=load_evidence(relative(out/'verification.json'))
        write_json(out/'binding_readback.json',{'binding_status':bound['binding_status'],'binding_reason':bound['binding_reason'],
                                              'verification_identity':reference(out/'verification.json')})
        if bound['binding_status']!='bound': raise ArithmeticError('final_binding_readback_failed')
        criteria=[]
        for c in matrix()['criteria']:
            cid=c['id']; result='not_run'; reason='Requires current demo, manual scientific review, archive, or independent Safety'; files=[]
            if cid in numeric: result=numeric[cid]['result']; files=numeric[cid]['evidence_files']; reason='Actual focused numerical/semantic execution (representative scope where declared)'
            elif cid in ('B2-AUD-001','B2-AUD-002'): result='passed'; files=[reference(audit_log)]; reason='Fresh raw controls and defined mutations'
            elif cid in ('B2-IO-001','B2-IO-002','B2-RES-002'): result='passed'; files=unit_files; reason='Focused real input/path/short budget and harness-injected inventory-failure tests'
            elif cid=='B2-RES-001': result='passed'; files=[reference(out/'resources.json')]; reason='Focused phase only; demo and Safety have separate resource evidence'
            criteria.append({'criterion_id':cid,'result':result,'reason':reason,'evidence_files':files})
        write_json(out/'test_results.json',{'unit_tests':unit,'criteria':criteria,'exit_code':0,'production_approved':False,'independent_safety_approved':False})
        budget.check()
        print(json.dumps({'exit_code':0,'unit_tests':unit,'numeric_gate_results':{k:v['result'] for k,v in numeric.items()},'binding_status':bound['binding_status'],'resources':resources},allow_nan=False))
        return 0
    except (ValueError,OSError,ArithmeticError,TimeoutError,RuntimeError) as exc:
        if isinstance(exc,TimeoutError): code,status=3,'partial_timeout'
        elif isinstance(exc,RuntimeError): code,status=3,'resource_limit'
        elif isinstance(exc,ArithmeticError): code,status=1,'numerical_failure'
        else: code,status=2,'rejected_input'
        failure={'exit_code':code,'execution_status':status,'reason':'budget_parse_rejected' if budget.active is None else status,
                 'resources':budget.snapshot(status),'completed_gates':runner.gates if runner else {},'numerical_validation':'failed' if code==1 else 'not_run'}
        if out is not None:
            write_json(out/'failure.json',failure); write_json(out/'resources.json',failure['resources'])
        print(json.dumps(failure,allow_nan=False)); return code


if __name__=='__main__': sys.exit(main())
