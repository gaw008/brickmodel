"""Read-only source/boundary preflight; output only in validation."""
import ast
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from model import ROOT
from binding import source_files, reference, CONTRACTS
from scenarios import matrix, expand_frozen_manifest
from exports import write_json


def main():
    files=source_files(); checks=[]; imports=set()
    for ent in files:
        p=ROOT/ent['path']
        if p.suffix!='.py': continue
        tree=ast.parse(p.read_text(),filename=ent['path']); compile(tree,ent['path'],'exec')
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): imports.update(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom) and node.module: imports.add(node.module)
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Name) and node.func.id in ('eval','exec'): raise ValueError('dynamic_execution')
                if any(k.arg=='shell' and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords): raise ValueError('shell_execution')
    checks.append({'name':'all_module_python_AST_compile_no_eval_exec_shell_true','passed':True})
    decision=json.loads((ROOT/'MANAGER_G0_DECISION.json').read_text()); artifacts={}
    for name,ident in decision['artifact_identity'].items():
        local=ROOT/('CONTRACT.md' if name=='B2_CONTRACT.md' else name)
        good=hashlib.sha256(local.read_bytes()).hexdigest()==ident['sha256']; artifacts[name]=good
    if not all(artifacts.values()): raise ValueError('frozen_bytes')
    checks.append({'name':'five_frozen_hashes','passed':True,'files':artifacts})
    for name in ('model.py','solver.py'):
        if (ROOT/'reference/b1'/name).read_bytes()!=(ROOT.parent/'material_dynamics_v2b1'/name).read_bytes(): raise ValueError('B1_copy_changed')
    checks.append({'name':'B1_reference_copy_byte_identity','passed':True})
    cases=expand_frozen_manifest(); assert len(cases)==22 and len(matrix()['criteria'])==24
    changes=subprocess.run(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT.parents[1],text=True,capture_output=True,check=True).stdout.splitlines()
    if any(not line[3:].startswith('experiments/material_dynamics_v2b2/') for line in changes): raise ValueError('changed_path_boundary')
    checks.append({'name':'all_changes_only_B2','passed':True,'changed_paths':len(changes)})
    result={'checks':checks,'source_file_count':len(files),'imports':sorted(imports),'python':platform.python_version(),
            'scenarios':len(cases),'criteria':len(matrix()['criteria']),'production_approved':False,'independent_safety_approved':False}
    write_json(ROOT/'validation/preflight.json',result); print(json.dumps(result,ensure_ascii=False)); return 0


if __name__=='__main__': raise SystemExit(main())
