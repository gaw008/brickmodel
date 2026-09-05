"""Bounded hostile-copy checks. Original results and frozen snapshots untouched."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
from model import ROOT, canonical
from exports import write_json
from paths import relative
from binding import load_evidence, reference


def copy_raw(source,dest):
    dest.mkdir()
    shutil.copytree(source/'inputs',dest/'inputs')
    for name in ('raw_index.json','timeseries.csv','profiles.csv','flux_intervals.csv','summary.json'):
        if (source/name).is_file(): shutil.copyfile(source/name,dest/name)


def change_csv(p,fn):
    with p.open(newline='') as f:
        reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
    fn(rows)
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows)


def audit_controls(out,budget):
    root=out/'audit_controls'; root.mkdir(); cases=[]
    # Use fresh actual finite and weak-film B1-degenerate B2 trajectories.
    for sid in ('R03','R04'):
        src=out/'numeric'/sid
        diag=json.loads((src/'diagnostics.json').read_text()); diag.update(verification_scope='frozen_suite',numerical_validation='not_run')
        dest=root/('positive_'+sid); copy_raw(src,dest); write_json(dest/'summary.json',{'scenarios':[diag]})
        cases.append((dest,0,'positive_without_prewritten_audit_or_verification'))
    source=root/'positive_R03'; weak=root/'positive_R04'
    attacks=['inventory','reservoir_reset','flux_sign','missing_flux_interval','missing_profile','duplicate_profile',
             'nan_inventory','negative_inventory','null_event_to_zero','mean_as_local','fake_energy','fake_pressure',
             'top_tolerance_inventory','nested_tolerance_inventory','exposure','surface_oxygen']
    for name in attacks:
        dest=root/name; copy_raw(weak if name=='mean_as_local' else source,dest)
        if name in ('inventory','nan_inventory','negative_inventory','top_tolerance_inventory','nested_tolerance_inventory'):
            val='nan' if name=='nan_inventory' else '-0.1' if name=='negative_inventory' else '0.9'
            change_csv(dest/'profiles.csv',lambda rs:rs[-1].update(f=val))
        if name=='reservoir_reset': change_csv(dest/'timeseries.csv',lambda rs:rs[-1].update(u_res='1',v_res='0'))
        if name=='flux_sign': change_csv(dest/'flux_intervals.csv',lambda rs:[r.update(integral_J_u=str(-float(r['integral_J_u']))) for r in rs])
        if name=='missing_flux_interval': change_csv(dest/'flux_intervals.csv',lambda rs:rs.pop())
        if name=='missing_profile': change_csv(dest/'profiles.csv',lambda rs:rs.pop())
        if name=='duplicate_profile': change_csv(dest/'profiles.csv',lambda rs:rs.append(rs[-1].copy()))
        if name=='exposure': change_csv(dest/'timeseries.csv',lambda rs:rs[-1].update(H='123'))
        if name=='surface_oxygen': change_csv(dest/'timeseries.csv',lambda rs:rs[-1].update(u_surface='123'))
        if name in ('null_event_to_zero','mean_as_local','fake_energy','fake_pressure','top_tolerance_inventory','nested_tolerance_inventory'):
            p=dest/'summary.json'; sm=json.loads(p.read_text()); d=sm['scenarios'][0]
            if name=='null_event_to_zero': d['events']['local99']['tau']=0
            if name=='mean_as_local': d['events']['local99']=deepcopy(d['events']['mean99'])
            if name=='fake_energy': d['not_modelled']['energy']={'status':'passed','value':0}
            if name=='fake_pressure': d['not_modelled']['pressure']={'status':'passed','value':0}
            if name=='top_tolerance_inventory': sm['tolerance']=100
            if name=='nested_tolerance_inventory': d['verification']={'nested':{'tolerance':100}}
            write_json(p,sm)
        cases.append((dest,1,name))
    logs=[]
    for dest,expected,name in cases:
        budget.check(); p=subprocess.run([sys.executable,'-B','audit.py',relative(dest)],cwd=ROOT,capture_output=True,text=True,timeout=30)
        log={'control':name,'command':['python3','-B','audit.py',relative(dest)],'exit_code':p.returncode,'expected_exit_code':expected,
             'passed':p.returncode==expected,'stdout':json.loads(p.stdout),'stderr':p.stderr}
        write_json(dest/'command_result.json',log); logs.append(log)
    path=root/'results.json'; write_json(path,logs)
    if not all(r['passed'] for r in logs): raise ArithmeticError('audit_control_failed')
    return path


def binding_controls(out,provisional,budget):
    root=out/'binding_controls'; root.mkdir(); logs=[]
    def check(name,value,expected):
        budget.check()
        if value is None: actual=load_evidence(None)['binding_status']; ref=None
        else:
            p=root/(name+'.json'); write_json(p,value); ref=reference(p)
            try: actual=load_evidence(relative(p))['binding_status']
            except ValueError: actual='rejected_schema'
        logs.append({'control':name,'expected':expected,'actual':actual,'passed':actual==expected,'input_evidence':ref})
    check('missing',None,'missing')
    check('actual_evidence_coverage_incomplete',provisional,'incomplete')
    for field in ('source_commit','source_files','contract_artifacts'):
        obj=deepcopy(provisional)
        if field=='source_commit': obj[field]='d051c0982835dbe54fc4f509f1819661b85de055'
        else: obj[field][0]['sha256']='0'*64
        check('stale_'+field,obj,'mismatch')
    obj=deepcopy(provisional); obj['frozen_inputs'][0]['sha256']='0'*64; check('stale_complete_input',obj,'mismatch')
    obj=deepcopy(provisional); obj['coverage'][0]['evidence_files'][0]['sha256']='0'*64; check('raw_evidence_mutated',obj,'mismatch')
    schema=json.loads((ROOT/'B2_VALIDATION_STATUS_FIXTURES.json').read_text()); check('schema_example',schema,'rejected_schema')
    obj=deepcopy(provisional); obj['source_files'][0]['path']='../escape'; check('traversal',obj,'rejected_schema')
    obj=deepcopy(provisional)
    for c in obj['coverage']:
        if c['criterion_id']=='B2-NUM-006': c['executed_input_sha256s']=c['executed_input_sha256s'][:1]
    check('missing_named_refinement_execution',obj,'incomplete')
    # Exact custom input bytes differ even when the identifier remains W03.
    from scenarios import expand_frozen_manifest
    from model import Scenario
    from diagnostics import numerical_label
    s=next(s for s in expand_frozen_manifest() if s.id=='W03'); d=s.to_dict(); d['reaction']['Gamma']=3; custom=Scenario.from_dict(d)
    write_json(root/'same_name_custom_input.json',d)
    actual=numerical_label(False,'integrated',True,'bound')
    logs.append({'control':'same_name_custom_cannot_inherit_bound_pass','same_id':s.id==custom.id,'different_input_bytes':s.canonical()!=custom.canonical(),
                 'actual':actual,'passed':s.canonical()!=custom.canonical() and actual=='not_verified_for_custom_case',
                 'solver_execution':'not_run; schema/status control only, no added solve'})
    p=root/'results.json'; write_json(p,logs)
    if not all(x['passed'] for x in logs): raise ArithmeticError('binding_control_failed')
    return p
