"""Independent read-only arithmetic audit. Does not run the extractor."""
from pathlib import Path
from fractions import Fraction as F
import ast
import csv
import hashlib
import json
import time
P=Path('/private/tmp/brick-source-run-service-v1/material')
O=Path(__file__).parent
start=time.monotonic(); checks=0
def require(value):
 global checks
 checks+=1
 assert value
j=json.loads((P/'quantitative-record.json').read_text())
require(j['source_sha256']==hashlib.sha256((P/'source.pdf').read_bytes()).hexdigest())
require(j['source_sha256']=='3b49eae9d37fb2fab1c9097b2c5b2606e9ecbfe60e52f639f6e9ae637b78d536')
require(len(j['table4'])==12)
require(j['qualified'] is False and j['normalization_applied'] is False and j['fitted'] is False)
fields=('solid','liquid_inferred','CO','CO2','CH4','H2','printed_total')
node=ast.parse((P/'extract_tables.py').read_text())
raw=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='raw' for t in n.targets))
require(len(raw)==12)
with (P/'table4.csv').open() as f: csv_rows=list(csv.DictReader(f))
require(len(csv_rows)==12)
discrepancies=[]
for row, literal, c in zip(j['table4'],raw,csv_rows):
 require((row['trial'],row['heating_rate_K_min'],row['temperature_C_or_increment'])==literal[:3])
 tokens=literal[3].split();require(len(tokens)==7)
 for field,token in zip(fields,tokens):
  require(row[field]==token)
 for key,value in row.items():require(c[key]==str(value))
 total=sum((F(row[key]) for key in fields[:6]),F())
 require(total==F(row['sum_six_printed_components']))
 residual=total-F(row['printed_total'])
 require(residual==F(row['sum_minus_printed_total']))
 if residual:discrepancies.append({'trial':row['trial'],'temperature':row['temperature_C_or_increment'],'exact_sum_minus_printed_total':str(residual)})
 require(0<=row['heating_rate_K_min']<=12)
for base,rate,temperature in zip(range(0,12,3),(3,7,10,12),(560,565,570,585)):
 lo,hi,delta=j['table4'][base:base+3]
 require(lo['heating_rate_K_min']==rate and lo['temperature_C_or_increment']==temperature)
 require(hi['temperature_C_or_increment']==960 and delta['temperature_C_or_increment']=='delta')
 require(lo['liquid_inferred']==hi['liquid_inferred'] and delta['liquid_inferred']=='0.0000')
delta_discrepancies=[]
for base in range(0,12,3):
 lo,hi,delta=j['table4'][base:base+3]
 for key in fields:
  exact=F(hi[key])-F(lo[key]); printed=F(delta[key])
  if exact!=printed:delta_discrepancies.append({'trial':lo['trial'],'column':key,'printed_delta':str(printed),'endpoint_difference':str(exact),'printed_minus_endpoint_difference':str(printed-exact)})
# Independent transcription of only feed and printed totals from viewed Table 5.
expected={'C':('0.2947','0.2517'),'H':('0.0391','0.0416'),'O':('0.1262','0.1410'),'N':('0.0343','0.0220'),'S':('0.0338','0.0226')}
require(set(expected)==set(j['table5_960C_aggregate_element_audit']))
for element,(feed,products) in expected.items():
 row=j['table5_960C_aggregate_element_audit'][element]
 require(row['feed_kg_per_kg_dry_feed']==feed and row['printed_total_products_960C']==products)
 require(F(row['products_minus_feed'])==F(products)-F(feed))
text=(P/'source.txt').read_text()
require('All values are in dry basis' in text)
require('water +' in text and 'organic liquid' in text and 'calculated by difference' in text)
require('at 10 K/min until 570' in text)
result={'status':'passed','checks':checks,'elapsed_seconds':time.monotonic()-start,
 'scope':'12 printed Table4 rows, 84 literal yields, CSV parity, exact six-component sums and residuals; Table5 only 10 feed/printed-total values and five differences. No uncertainty, fitting or physical closure qualification.',
 'visual_review':'Both supplied page images actually viewed; Table4 all 84 yield values and Table5 selected feed/960C printed totals matched.',
 'table4_nonzero_sum_residuals':discrepancies,'additional_printed_delta_vs_endpoint_discrepancies':delta_discrepancies,
 'additional_delta_check_scope':'Reviewer-only arithmetic; does not change the source transcription or assert the printed delta is recomputed.',
 'sha256':{name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ('quantitative-record.json','extract_tables.py','table4.csv','source.pdf','source.txt','table4.png','table5.png')},
 'source_pdf_publication_allowed':False,'license_scope':'undetermined: private cache only per parent instruction',
 'EOS_calls':0,'extractor_executed':False}
(O/'MATERIAL_TABLES_ARITHMETIC.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
