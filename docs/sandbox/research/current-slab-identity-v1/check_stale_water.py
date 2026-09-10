import ast,json,hashlib,subprocess
from pathlib import Path
r=Path('/Users/wanggaoying/Desktop/brickmodel-github');old=r/'docs/sandbox/research/deforming-wet-admission/baseline/water_phase_transfer.py';new=r/'src/sludge_sandbox/water_phase_transfer.py'
def methods(p):
 c=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='WaterPhaseTransfer');return {n.name:n for n in c.body if isinstance(n,ast.FunctionDef)}
a,b=methods(old),methods(new)
def dump(x):return ast.dump(x,include_attributes=False)
def same(xs,ys):return [dump(x) for x in xs]==[dump(x) for x in ys]
checks={'old_evaluate_whole_same':dump(a['evaluate'])==dump(b['evaluate']), 'old_first2_checks_equal_extracted_interface_body':same(a['evaluate'].body[:2],b['_check_interface_state'].body),'old_assignments_and_chemical_loop_equal_new_assembly_prefix':same(a['evaluate'].body[3:7],b['_assemble_transfer'].body[:4]),'dry_diagnostic_identical':dump(a['_dry_diagnostic'])==dump(b['_dry_diagnostic']),'with_depleted_cells_identical':dump(a['with_depleted_cells'])==dump(b['with_depleted_cells'])}
for key,value in checks.items():assert value==(key!='old_evaluate_whole_same'),key
for m in [a,b]:
 loop=next(x for x in m['__post_init__'].body if isinstance(x,ast.For) and isinstance(x.target,ast.Tuple) and [t.id for t in x.target.elts]==['storage','k','mode'])
 m['_match']=loop
assert dump(a['_match'])==dump(b['_match'])
checks['source_matching_constructor_loop_identical']=True
head=subprocess.check_output(['git','rev-parse','HEAD:src/sludge_sandbox/water_phase_transfer.py'],cwd=r,text=True).strip();work=subprocess.check_output(['git','hash-object','src/sludge_sandbox/water_phase_transfer.py'],cwd=r,text=True).strip();assert head==work
result={'checks':checks,'HEAD_and_worktree_git_blob':head,'current_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'baseline_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'scope':'read-only structural analysis; not a new active water physical experiment'}
Path('/private/tmp/brick-current-slab-identity-review/STALE_WATER_AST.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
