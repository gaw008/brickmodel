import json
from capture_slab import HERE,cases,serial
records=json.loads((HERE/'SLAB_GOLDEN.json').read_text())['records'];checked=0
for label,prior,current,state in cases():
 for row in records:
  if row['case']==label:
   actual=serial(current.evaluate(state,row['time_s']))
   assert actual==row['expected'],(label,row['time_s'],actual,row['expected'])
   checked+=1
assert checked==28
print(json.dumps({'checked':checked,'all_hex_fields_match':True,'scope':'actual current slab full evaluation matches saved priorHEAD outputs; no old numerical recomputation'}))
