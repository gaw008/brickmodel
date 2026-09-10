from pathlib import Path
from fractions import Fraction as F
import json,hashlib,ast,math
p=Path('/private/tmp/brick-sphere-surface-v1');out=Path('/private/tmp/brick-sphere-surface-review')
r=json.loads((p/'RESULT.json').read_text());lines=(p/'author-tests02.log').read_text().splitlines();saved=[json.loads(s) for s in (p/'pytest01/test_multicell_sphere_robin_mo0/robin-grids.jsonl').read_text().splitlines()]
rows=[x for x in saved if x.get('metric_status')=='evaluated'];assert rows==r['Robin_rows'] and len(saved)==8
summary=ast.literal_eval(next(s for s in lines if s.startswith("{'sphere_Robin_midpoint_RMS_K'")))
assert [x['RMS_error_K'] for x in rows]==summary['sphere_Robin_midpoint_RMS_K']
assert r['finest_time_halving_max_delta_K']==summary['finest_temporal_halving_max_delta_K']
for row,(n,dt) in zip(rows,[(4,.001),(8,.001),(16,.001),(16,.0005)]):
 assert row['cells']==n and row['dt']==dt and row['status']=='completed' and row['reason'] is None
 assert row['last_time_s']==row['required_end_s'] and 0<row['elapsed_s']<row['wall_budget_s']==90
 assert row['rejected']==0 and row['accepted']==(107 if dt==.001 else 214)
end=.05*.02**2/(.5/(100*(30-8.31446261815324)+10*50));assert abs(end-rows[0]['required_end_s'])<1e-15
errors=[F(x['RMS_error_K']) for x in rows];delta=F(r['finest_time_halving_max_delta_K'])
assert errors[1]<errors[0]/3 and errors[2]<errors[1]/3 and errors[2]<F('.005') and delta<errors[2]/20
f=json.loads((p/'FREEZE.json').read_text())
for x in f['files']:assert hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256']
result={'saved_rows_log_summary_agree':True,'all_numeric_and_resource_gates_pass':True,'spatial_error_ratios':[float(errors[0]/errors[1]),float(errors[1]/errors[2])],'temporal_delta_K':float(delta),'temporal_delta_gate_K':float(errors[2]/20),'author_terminal_summary':lines[-1],'final_freeze_match':True,'limitation':'saved metric consistency checked; raw final temperature vectors not present, so RMS and temporal max not independently recomputed; no grid rerun'}
(out/'ROBIN_SAVED_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
