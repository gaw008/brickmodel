"""Independent exact printed-cell arithmetic; no PDF redistribution or physics."""
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import re

ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github')
DATA=ROOT/'data/sandbox/research/gnest2021/appendix-b-check-v1'
DOC=ROOT/'docs/sandbox/research/gnest2021-appendix-b-check-v1'
OUT=Path(__file__).parent
tables=json.loads((DATA/'tables.json').read_bytes())
published=json.loads((DOC/'PRINTED_ARITHMETIC.json').read_bytes())
delivery=json.loads((DOC/'DELIVERY.json').read_bytes())
files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
       for p in (*DATA.iterdir(),*DOC.iterdir()) if p.is_file()}
assert all(files[k]==v for k,v in delivery['files'].items())
assert tables['qualifications']==dict(same_GNEST2021_batch=None,material_qualified=False,
    reaction_heat_identified=False,raw_lost_species_identified=False)
experiments=[f'HRN{i}' for i in range(1,6)]
count=0
for table,nrows,ncols in [('B1',15,5),('B2',14,5),('B3',9,6)]:
    t=tables[table]
    assert len(t['rows'])==nrows
    assert t['columns']==(experiments if table!='B3' else ['HRN1',"HRN1'",*experiments[1:]])
    for row in t['rows'].values():
        assert len(row)==ncols and all(type(v)is str and re.fullmatch(r'\d+\.\d+',v) for v in row)
        count+=len(row)
assert tables['B4']['columns']==['C','H','N','O']
assert list(tables['B4']['experiments'])==experiments
for table in tables['B4']['experiments'].values():
    assert set(table)=={'S','G','K','H2O','Total'}
    for row in table.values():
        assert len(row)==4 and all(type(v)is str and re.fullmatch(r'\d+\.\d+',v) for v in row)
        count+=len(row)
assert count==299==delivery['numeric_cells']
rows=[]
def add(table,experiment,quantity,parts,total):
    total=F(total);summed=sum(map(F,parts),F())
    rows.append(dict(table=table,experiment=experiment,quantity=quantity,
        sum_printed_parts=str(summed),printed_total=str(total),
        sum_minus_printed_total=str(summed-total),printed_total_minus_one=str(total-1)))
for i,experiment in enumerate(tables['B3']['columns']):
    for quantity,components in [('mass',['S','G','K','H2O']),('energy',['S','G','K'])]:
        values=tables['B3']['rows']
        add('B3',experiment,quantity,[values[quantity+'_'+c][i] for c in components],values[quantity+'_Total'][i])
for experiment,values in tables['B4']['experiments'].items():
    for i,element in enumerate(tables['B4']['columns']):
        add('B4',experiment,element,[values[c][i] for c in ['S','G','K','H2O']],values['Total'][i])
assert len(rows)==32==delivery['exact_arithmetic_rows']
assert rows==published['rows']
large=[(r['experiment'],r['quantity'],r['sum_minus_printed_total']) for r in rows if abs(F(r['sum_minus_printed_total']))>F(1,100)]
assert large==[("HRN1'",'mass','-7/500'),('HRN2','mass','11/200'),('HRN2','energy','-29/1000')]
(OUT/'RESULT.json').write_text(json.dumps(dict(status='passed',numeric_cells=count,
    exact_rows_recomputed=len(rows),large_printed_differences=large,files=files,
    eos_calls=0,material_qualified=False,reaction_heat_identified=False),indent=2)+'\n')
print('PASS: 299 printed cells, 32 independent Fraction rows; all three large original differences retained.')
