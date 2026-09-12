"""Review-only AST/mock checks. No physical trajectory or water model is imported."""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1]
RUNNER = ROOT/'run_validation.py'
SUPERVISOR = ROOT/'supervise.py'

def extracted(path, names, namespace):
    tree = ast.parse(path.read_text())
    body = [item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in names]
    assert {item.name for item in body} == set(names)
    exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),namespace)
    return namespace

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_checks():
    before = {p.name:sha(p) for p in (RUNNER,SUPERVISOR,ROOT/'PREREGISTRATION.md')}
    ns = extracted(RUNNER, ('write_new','independent_fields','analytic_relaxation','matrix_rhs',
                            'tracked_reference_rhs','run_candidate','summarize'),
        dict(np=np,Decimal=Decimal,localcontext=localcontext,Path=Path,time=time,json=json,asdict=asdict,
             M=1e9,ALPHA=1e-4,C=1e5,TR=300.,V=1e-4,G=1.,GB=2.,TIMES=np.array([0.,10.])))
    # A small isolated root query, not either preregistered trajectory or time grid.
    roots = ns['analytic_relaxation']([0.,0.123456])
    with localcontext() as ctx:
        ctx.prec=100
        r=roots[1];lo=Decimal(r['delta_lower']);hi=Decimal(r['delta_upper'])
        # Independent separation: (C-2 b m)/delta integrates to this expression.
        def integral(delta):
            C=Decimal(100000);b=Decimal(10);m0=Decimal(302);d0=Decimal(2)
            coeff=C-2*b*m0+2*b*b*d0*d0/C
            return coeff*(delta.ln()-d0.ln())-b*b/C*(delta*delta-d0*d0)+Decimal(20000)*Decimal('0.123456')
        assert integral(lo)<0<integral(hi)
        conversion_allowance=Decimal('1e-12')
        bound=(hi-lo)*(1+Decimal('0.0004'))/2+conversion_allowance
        assert Decimal(r['temperature_error_bound_k'])==bound
        assert bound<Decimal('2e-7')
    domain_checks=0
    for external in (False,True):
        for omitted in (False,True):
            tracked,bounds=ns['tracked_reference_rhs'](external,omit_coupling=omitted)
            tracked(.0123,[301.,303.]);tracked(.2345,[300.,304.])
            assert bounds==dict(min_temperature_k=300.,max_temperature_k=304.,
                                min_fixed_strain_heat_capacity_j_m3_k=93920.,rhs_calls=2)
            for invalid in ([289.,300.],[300.,311.],[float('nan'),300.]):
                try:
                    tracked(.3456,invalid)
                except ValueError:
                    domain_checks+=1
                else:
                    raise AssertionError('out-of-domain reference/control accepted')
            assert bounds['rhs_calls']==2
    # 9-component transport wiring checked with a fake integrator and fake model.
    @dataclass(frozen=True)
    class FakeEvaluation:
        temperature_rates_k_s:tuple=(1.,-1.)
        cell_heat_in_w:tuple=(2.,3.)
        cell_mechanical_power_w:tuple=(5.,7.)
        external_heat_in_w:float=11.
        reservoir_entropy_rate_w_k:float=13.
        total_entropy_production_w_k:float=17.
    class FakeModel:
        def evaluate(self,temperatures):
            assert tuple(temperatures)==(301.,302.)
            return FakeEvaluation()
    def fake_solve(fun,span,y0,**policy):
        assert span==(0.,10.) and y0.shape==(9,)
        assert np.array_equal(y0[2:],np.zeros(7))
        assert np.array_equal(fun(0.,y0),[1.,-1.,2.,3.,5.,7.,11.,13.,17.])
        assert policy['method']=='DOP853' and policy['dense_output'] is True
        return SimpleNamespace(success=True,t=np.array([0.,10.]),y=np.tile(y0[:,None],(1,2)),
            sol=lambda times:np.tile(y0[:,None],(1,len(times))),nfev=1,message='FAKE REVIEW STUB; NO INTEGRATION')
    ns['solve_ivp']=fake_solve
    with TemporaryDirectory(dir=DIRECTORY,prefix='fake-only-') as tmp:
        report=ns['run_candidate'](FakeModel(),[301.,302.],dict(rtol=1e-9,atol=1e-11,max_step=.05),Path(tmp),'fake')
        assert len(report['state_columns'])==9 and report['logged_rhs']==1
        assert np.asarray(report['samples']).shape==(2,9)
    # Isolated t=0 reports expose whether stress metrics use actual candidate fields.
    temperatures=[304.,300.]
    point_fields=ns['independent_fields'](temperatures,[0.,0.],False)
    point={'samples':[[*temperatures,*([0.]*7)]],
           'observations':[{'temperature_rates_k_s':ns['matrix_rhs'](temperatures,False).tolist(),
                            'points':[dict(stress_pa=float(st),internal_energy_j_m3=float(u),entropy_j_m3_k=float(en))
                                      for st,u,en in zip(point_fields['stress'],point_fields['u'],point_fields['entropy'])]}]}
    original=ns['summarize'](point,temperatures,[temperatures],False)
    corrupted=deepcopy(point)
    for candidate_point in corrupted['observations'][0]['points']:candidate_point['stress_pa']=1e12
    changed=ns['summarize'](corrupted,temperatures,[temperatures],False)
    stress_output_ignored=(original==changed)
    assert not stress_output_ignored and changed['stress_error_pa']>1e11
    assert changed['reported_stress_consistency_error_pa']>1e11
    other_outputs={}
    for field,metric in [('internal_energy_j_m3','reported_cell_internal_energy_consistency_error_j'),
                         ('entropy_j_m3_k','reported_cell_entropy_consistency_error_j_k')]:
        altered=deepcopy(point);altered['observations'][0]['points'][0][field]+=1e7
        altered_result=ns['summarize'](altered,temperatures,[temperatures],False)
        assert altered_result[metric]>999.
        other_outputs[field]=True
    # All dimensional energy gates are checked without any ODE solver.
    failed={}
    for name,column in [('heat0',2),('heat1',3),('work0',4),('work1',5),('external',6)]:
        altered=deepcopy(point);altered['samples'][0][column]=1e-5
        result=ns['summarize'](altered,temperatures,[temperatures],False)
        required='global_energy' if column==6 else 'local_energy'
        assert result['gates'][required] is False
        failed[name]=required
    supra = extracted(SUPERVISOR,('main',),dict(__file__=str(SUPERVISOR),argparse=argparse,hashlib=hashlib,
        json=json,Path=Path,time=time,subprocess=None))
    results={}
    for outcome in ('success','nonzero','timeout','launch_error'):
        def fake_run(command,**kwargs):
            assert command[1]=='-I' and command[3:5]==['--case','relaxation']
            assert kwargs['cwd']=='/private/tmp' and kwargs['timeout']==10 and kwargs['check'] is False
            if outcome=='timeout':raise subprocess.TimeoutExpired(command,10)
            if outcome=='launch_error':raise FileNotFoundError('FAKE launch error')
            return SimpleNamespace(returncode=0 if outcome=='success' else 7)
        supra['subprocess']=SimpleNamespace(run=fake_run,TimeoutExpired=subprocess.TimeoutExpired)
        with TemporaryDirectory(dir=DIRECTORY,prefix='mock-supervisor-') as tmp:
            out=Path(tmp)/'output'
            with patch.object(sys,'argv',['supervise','--python','/FAKE/python','--case','relaxation','--output',str(out)]):
                exitcode=supra['main']()
            record=json.loads((out/'EXECUTION.json').read_text())
            assert exitcode==(0 if outcome=='success' else 1)
            assert record['timed_out']==(outcome=='timeout') and record['inputs_unchanged']
            assert (out/'START.json').exists()
            results[outcome]={'exitcode':exitcode,'timed_out':record['timed_out'],
                              'child_reaped_claim_from_mock':record['child_reaped']}
    after={p.name:sha(p) for p in (RUNNER,SUPERVISOR,ROOT/'PREREGISTRATION.md')}
    assert before==after
    result={'scope':'Pure functions and manufactured fake objects only; no physical integration, no child process, no water EOS import.',
        'input_sha256':before,'root_query_times_s':[0.,.123456],
        'root_bracket_100_digit_recheck':True,'nine_state_wiring_fake_check':True,
        'reference_and_control_invalid_state_rejections':domain_checks,
        'reference_and_control_domain_records_checked':True,
        'candidate_stress_output_ignored_in_metrics':stress_output_ignored,
        'candidate_u_and_s_output_faults_visible':other_outputs,
        'dimensional_gate_fault_checks':failed,'supervisor_mock_outcomes':results,
        'note':'Mock child_reaped fields only test record branches; actual process termination is not tested here.'}
    (DIRECTORY/'PURE_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    run_checks()
