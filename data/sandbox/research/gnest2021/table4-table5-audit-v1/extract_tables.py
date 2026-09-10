"""Visually transcribed publisher Table4; Decimal balances never normalized."""
from pathlib import Path
from decimal import Decimal as D
import json,csv,hashlib
P=Path(__file__).parent
raw=[('TG1',3,560,'0.6878 0.2984 0.0056 0.0057 0.0010 0.0015 1.0000'),('TG1',3,960,'0.5685 0.2984 0.0637 0.0092 0.0010 0.0094 0.9530'),('TG1',3,'delta','-0.1194 0.0000 0.0582 0.0034 0.0000 0.0079 -0.0498'),('TG2',7,565,'0.6822 0.2941 0.0076 0.0117 0.0027 0.0016 1.0000'),('TG2',7,960,'0.5610 0.2941 0.0692 0.0152 0.0030 0.0085 0.9511'),('TG2',7,'delta','-0.1212 0.0000 0.0616 0.0035 0.0003 0.0068 -0.0489'),('TG3',10,570,'0.6919 0.2917 0.0041 0.0100 0.0016 0.0007 1.0000'),('TG3',10,960,'0.5687 0.2917 0.0588 0.0183 0.0026 0.0106 0.9507'),('TG3',10,'delta','-0.1232 0.0000 0.0547 0.0083 0.0010 0.0099 -0.0493'),('TG4',12,585,'0.6865 0.2939 0.0051 0.0117 0.0022 0.0006 1.0000'),('TG4',12,960,'0.5706 0.2939 0.0522 0.0179 0.0027 0.0099 0.9472'),('TG4',12,'delta','-0.1159 0.0000 0.0471 0.0062 0.0005 0.0093 -0.0528')]
rows=[]
for trial,rate,temp,txt in raw:
 vals=txt.split();r=dict(trial=trial,heating_rate_K_min=rate,temperature_C_or_increment=temp,**dict(zip(['solid','liquid_inferred','CO','CO2','CH4','H2','printed_total'],vals)));r['sum_six_printed_components']=str(sum(map(D,vals[:6])));r['sum_minus_printed_total']=str(D(r['sum_six_printed_components'])-D(vals[6]));rows.append(r)
elements={}
for el,feed,out in [('C','0.2947','0.2517'),('H','0.0391','0.0416'),('O','0.1262','0.1410'),('N','0.0343','0.0220'),('S','0.0338','0.0226')]:elements[el]={'feed_kg_per_kg_dry_feed':feed,'printed_total_products_960C':out,'products_minus_feed':str(D(out)-D(feed))}
r={'doi':'10.30955/gnj.003738','version':'publisher-hosted accepted manuscript,35pages','source_url':'https://journal.gnest.org/sites/default/files/Submissions/gnest_03738/gnest_03738_draft.pdf','source_sha256':hashlib.sha256((P/'source.pdf').read_bytes()).hexdigest(),'locators':{'table4':'printed/PDFpage26,AppendixA','table5':'printed/PDFpage27','inference_methods':'section2.4 printed/PDFpage11','energy':'section3.2 printed/PDFpage19'},'table4':rows,'table5_960C_aggregate_element_audit':elements,'qualified':False,'normalization_applied':False,'fitted':False}
(P/'quantitative-record.json').write_text(json.dumps(r,indent=2)+'\n')
with (P/'table4.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'rows':len(rows),'printed_numeric_yield_values':84,'source_sha256':r['source_sha256'],'row_sum_discrepancies':[(x['trial'],x['temperature_C_or_increment'],x['sum_minus_printed_total']) for x in rows if D(x['sum_minus_printed_total'])!=0],'element_residuals':elements},indent=2))
