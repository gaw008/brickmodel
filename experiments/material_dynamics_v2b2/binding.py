"""B2-BIND-001: explicit tests-first evidence consumption, not pass inheritance."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from model import ROOT, VERSION, canonical, strict_json
from paths import safe_file, relative
from scenarios import expand_frozen_manifest
from scenarios import matrix
from copy import deepcopy
from paths import checked_path

CONTRACTS={'CONTRACT.md':'40b7d9b71fa8ec1c72d85b7ab7fb9cf3086c4ec9d0c5a2b16ad06c324ba4d506',
           'B2_ACCEPTANCE_MATRIX.json':'90b8b77b1bfd2c36b85a8bc4d38812bfd679f001e6221bdb9b3f0ed287337fda',
           'B2_HANDOFF.md':'f4213eb416b20b8bf736277bda988c84e8f96e6cdedc7e36f39a2e13c6890aa8'}
SOURCE_EXCLUSIONS={'validation','__pycache__','.git'}
SOURCE_SPECIAL={'SOURCE_SNAPSHOT.json'}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reference(p): return {'path':relative(p),'sha256':digest(p)}


def source_files():
    result=[]
    def walk(directory):
        for p in sorted(directory.iterdir()):
            if p.name in SOURCE_EXCLUSIONS or p.name in SOURCE_SPECIAL: continue
            if p.is_symlink(): raise ValueError('source_symlink')
            if p.is_dir(): walk(p)
            elif p.name not in CONTRACTS and (p.suffix in ('.py','.json','.md') or p.name in ('.gitattributes','.gitignore')):
                result.append(reference(p))
    walk(ROOT)
    return sorted(result,key=lambda r:r['path'])


def capture_identity(*,require_commit=True):
    files=source_files(); contracts=[reference(ROOT/p) for p in sorted(CONTRACTS)]
    if any(x['sha256']!=CONTRACTS[x['path']] for x in contracts): raise ValueError('contract_identity')
    offline=ROOT/'SOURCE_SNAPSHOT.json'
    if offline.exists():
        snap=strict_json(offline.read_text(),size_limit=1024*1024,depth_limit=12)
        if snap['kind']!='offline_source_snapshot': raise ValueError('snapshot_schema')
        ident=snap['identity']; commit=ident['source_commit']
        if ident['source_files']!=files or ident['contract_artifacts']!=contracts: raise ValueError('offline_source_mismatch')
    else:
        result=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True)
        commit=result.stdout.strip()
        if require_commit:
            top=Path(subprocess.run(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip())
            for entry in files+contracts:
                name=str((ROOT/entry['path']).relative_to(top))
                blob=subprocess.run(['git','show',f'{commit}:{name}'],cwd=ROOT,capture_output=True)
                if blob.returncode or hashlib.sha256(blob.stdout).hexdigest()!=entry['sha256']:
                    raise ValueError('source_not_committed')
    if not re.fullmatch('[0-9a-f]{40}',commit): raise ValueError('source_commit')
    return dict(contract_version=VERSION,source_commit=commit,source_files=files,contract_artifacts=contracts)


def verify_identity(identity,*,require_commit=True):
    try:
        actual=capture_identity(require_commit=require_commit)
        return all(identity.get(k)==v for k,v in actual.items())
    except (ValueError,OSError,subprocess.SubprocessError): return False


def verify_ref(entry):
    if type(entry) is not dict or set(entry)!={'path','sha256'} or not isinstance(entry['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',entry['sha256']):
        raise ValueError('evidence_reference_schema')
    return digest(safe_file(entry['path']))==entry['sha256']


def save_inputs(out,cases):
    out.mkdir(parents=True,exist_ok=True)
    entries=[]
    for s in cases:
        p=out/(s.id+'.json'); p.write_bytes(s.canonical())
        entries.append({'scenario_id':s.id,**reference(p)})
    return entries


def expected_numeric_inputs():
    """Content identities of the frozen *named* executions, not their labels."""
    cases={s.id:s.to_dict() for s in expand_frozen_manifest()}
    sha=lambda d:hashlib.sha256(canonical(d)).hexdigest()
    required={cid:set() for cid in ('B2-NUM-004','B2-NUM-005','B2-NUM-006')}
    for gamma in (.25,1,2):
        d=deepcopy(cases['C02']); d['reaction']['Gamma']=gamma
        d['temperature']['knots']=deepcopy(matrix()['scenario_manifest']['programs']['P_CYCLE'])
        required['B2-NUM-004'].add(sha(d))
    for program in ('P_EARLY','P_ISO'):
        for n in (7,15,31):
            d=deepcopy(cases['C01']); d['reaction']['theta']=0; d['numerics']['n_cells']=n
            d['temperature']['knots']=deepcopy(matrix()['scenario_manifest']['programs'][program])
            payload={'scenario':d,'test_only_dirichlet':True,'test_initial':{'u':0,'v':1,'f':1},'test_surface':{'u':1,'v':0}}
            required['B2-NUM-005'].add(sha(payload))
    for sid in ('W03','L02','C03'):
        for n,scale in ((7,.25),(15,.25),(31,.25),(31,1),(31,.5)):
            d=deepcopy(cases[sid]); d['numerics']['n_cells']=n; d['numerics']['dt_scale']=scale
            required['B2-NUM-006'].add(sha(d))
    return required


def load_evidence(name):
    if name is None: return {'binding_status':'missing','binding_reason':'verification_not_supplied','coverage':[]}
    p=safe_file(name)
    obj=strict_json(p.read_text(encoding='utf-8'),size_limit=10*1024*1024,depth_limit=20)
    required={'kind','contract_version','source_commit','source_files','contract_artifacts','frozen_inputs','executed_inputs','coverage','command','exit_code','resources_path'}
    if type(obj) is not dict or obj.get('kind')!='executed_focused_evidence' or not required<=obj.keys(): raise ValueError('evidence_schema')
    for k in ('source_files','contract_artifacts','frozen_inputs','executed_inputs','coverage'):
        if type(obj[k]) is not list: raise ValueError('evidence_schema')
    for k in ('source_files','contract_artifacts','frozen_inputs','executed_inputs'):
        for ent in obj[k]:
            if not isinstance(ent,dict) or 'path' not in ent: raise ValueError('evidence_path_schema')
            checked_path(ent['path'])
    checked_path(obj['resources_path'])
    for c in obj['coverage']:
        if not isinstance(c,dict) or not isinstance(c.get('evidence_files'),list): raise ValueError('coverage_schema')
        for ref in c['evidence_files']:
            if not isinstance(ref,dict) or 'path' not in ref: raise ValueError('evidence_path_schema')
            checked_path(ref['path'])
    def result(status,reason):
        return {'binding_status':status,'binding_reason':reason,'coverage':obj['coverage'],'focused_evidence':reference(p),'evidence':obj}
    if not verify_identity(obj): return result('mismatch','source_or_contract_identity')
    frozen=expand_frozen_manifest(); expected={s.id:hashlib.sha256(s.canonical()).hexdigest() for s in frozen}
    if len(obj['frozen_inputs'])!=len(expected): return result('incomplete','frozen_input_coverage')
    got={}; executed=set(); semantic_inputs=set()
    for label in ('frozen_inputs','executed_inputs'):
        seen=set()
        for ent in obj[label]:
            if type(ent) is not dict or set(ent)!={'scenario_id','path','sha256'}: raise ValueError('input_evidence_schema')
            if ent['path'] in seen: raise ValueError('duplicate_evidence_input')
            seen.add(ent['path'])
            if not verify_ref({k:ent[k] for k in ('path','sha256')}): return result('mismatch','input_bytes')
            content=safe_file(ent['path']).read_bytes()
            parsed=strict_json(content.decode(),size_limit=1024*1024,depth_limit=20)
            if canonical(parsed)!=content: return result('mismatch','input_canonical_bytes')
            if label=='frozen_inputs':
                if ent['scenario_id'] in got: raise ValueError('duplicate_frozen_id')
                got[ent['scenario_id']]=ent['sha256']
            else:
                executed.add(ent['sha256'])
                if isinstance(parsed,dict) and parsed.get('kind')=='executed_unit_fixture_inputs':
                    if not parsed.get('fixture_files'): return result('incomplete','unit_fixture_raw_missing')
                    for ref in parsed['fixture_files']:
                        if not verify_ref(ref): return result('mismatch','unit_fixture_bytes')
                    semantic_inputs.add(ent['sha256'])
    if got!=expected: return result('mismatch','frozen_input_identity')
    resources=safe_file(obj['resources_path']); resources_ref=reference(resources)
    resource_bound=False; coverage={}; failed=False
    for c in obj['coverage']:
        if type(c) is not dict or set(c)!={'criterion_id','target_input_sha256','executed_input_sha256s','coverage_kind','result','evidence_files'}: raise ValueError('coverage_schema')
        if c['coverage_kind'] not in ('per_case','representative_frozen_domain','suite_semantics') or c['result'] not in ('passed','failed','not_run'): raise ValueError('coverage_enum')
        if not isinstance(c['executed_input_sha256s'],list) or not isinstance(c['evidence_files'],list): raise ValueError('coverage_schema')
        if c['target_input_sha256'] not in expected.values(): raise ValueError('coverage_target')
        key=(c['criterion_id'],c['target_input_sha256'])
        if key in coverage: raise ValueError('coverage_duplicate')
        coverage[key]=c
        if c['result']=='failed': failed=True
        if not c['evidence_files'] or not c['executed_input_sha256s'] or not set(c['executed_input_sha256s'])<=executed:
            return result('incomplete','unexecuted_or_missing_raw_evidence')
        for ref in c['evidence_files']:
            if not verify_ref(ref): return result('mismatch','raw_evidence_bytes')
            if ref==resources_ref: resource_bound=True
    if failed or obj['exit_code']==1: return result('failed','actual_focused_failure')
    if obj['exit_code']!=0: return result('incomplete','focused_not_successful')
    required_nums=[f'B2-NUM-{i:03}' for i in range(2,9)]
    required_inputs=expected_numeric_inputs()
    for sid,sha in expected.items():
        required_ids=required_nums+(['B2-NUM-001'] if sid.startswith('R') else [])
        for cid in required_ids:
            c=coverage.get((cid,sha))
            if c is None or c['result']!='passed': return result('incomplete','required_numerical_coverage')
            if cid=='B2-NUM-001' and c['coverage_kind']!='per_case': return result('incomplete','regression_not_per_case')
            if cid in ('B2-NUM-004','B2-NUM-005','B2-NUM-006') and c['coverage_kind']!='representative_frozen_domain': return result('incomplete','representative_scope')
            performed=set(c['executed_input_sha256s'])
            if cid in required_inputs and not required_inputs[cid]<=performed: return result('incomplete','named_reference_or_refinement_inputs_missing')
            if cid=='B2-NUM-001' and sha not in performed: return result('incomplete','regression_input_missing')
            if cid=='B2-NUM-007' and not {expected['R03'],expected['R04']}<=performed: return result('incomplete','event_sentinel_inputs_missing')
            if cid in ('B2-NUM-002','B2-NUM-003','B2-NUM-008') and not semantic_inputs.intersection(performed): return result('incomplete','semantic_input_missing')
    if not resource_bound: return result('incomplete','resource_identity_missing')
    return result('bound','matching_source_contract_inputs_executed_coverage')
