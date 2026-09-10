from pathlib import Path
import ast,hashlib,json
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github');audit=Path('/private/tmp/brick-nylen-integration-audit');out=Path('/private/tmp/brick-radial-host-review')
class Normalize(ast.NodeTransformer):
 def visit_FunctionDef(self,n):
  n.returns=None
  for a in n.args.posonlyargs+n.args.args+n.args.kwonlyargs:a.annotation=None
  return self.generic_visit(n)
 def visit_ImportFrom(self,n):
  if n.module=='exchanges' and [a.name for a in n.names]==['conduction_rate_w']:return None
  return n
results=[]
for p in (audit/'before-annotations').iterdir():
 q=ROOT/'src/sludge_sandbox'/p.name
 a=Normalize().visit(ast.parse(p.read_text()));b=Normalize().visit(ast.parse(q.read_text()))
 assert ast.dump(a)==ast.dump(b),p.name
 compile(q.read_text(),str(q),'exec');results.append(p.name)
f=json.loads((audit/'FREEZE.json').read_text())
for item in f['files']:assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()==item['sha256']
result={'annotation_only_comparison':'PASS','files_compared':results,'exception':'Removed unused conduction_rate_w import in solid_fluid_heat; same dependency still imported by rigid_fluid_heat','all7_final_freeze_hashes_match':True,'files':f['files'],'numerical_tests':'21submitted +4independent passed on exact preannotationfreeze; not rerun after annotations'}
(out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print('Annotation-normalized AST parity and final7hashes PASS')
