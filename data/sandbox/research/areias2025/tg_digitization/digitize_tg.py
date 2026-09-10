"""Fixed-grid Figure3 TG readout; manual curve choice, rational pixel envelope."""
from pathlib import Path
from fractions import Fraction as F
from itertools import product
import json,csv,hashlib
from PIL import Image,ImageDraw
P=Path(__file__).parent
source=Path('/Users/wanggaoying/Desktop/brickmodel-github/runs/sandbox/source-cache/areias2025-20260907/page-08-figure3.png')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='f5d76f00a1ef2144f795b97055822e8184fa135e96356059d4618cb675b0f01d'
# Raw figure/page coordinates, not values inferred from printed mass-loss labels.
picks={'A':[None,307,314,320,None,338,348,None,365,392.5,436,None,465,482.5,529,578,582.5,584,584.5,585.5,587,None], 'B':[796,809.5,820.5,None,833,860.5,880.5,None,905,938.5,990,None,1019.5,1036.5,1065,1069.5,1069.5,1070,1070.5,1070.5,1071.5,None]}
cal={'A':{'x':(F('237.5'),F('785.5'),F(200),F(1000)),'y':(F('303.5'),F('636.5'),F(100),F(84)),'ticks_x':[(374.5,400),(511.5,600),(649,800)],'ticks_y':[(346,98),(388.5,96),(428.5,94),(470.5,92),(512.5,90),(553.5,88),(594.5,86)]},'B':{'x':(F('240.5'),F('789.5'),F(200),F(1000)),'y':(F('793.5'),F('1106.5'),F(100),F(86)),'ticks_x':[(377.5,400),(514.5,600),(652.5,800)],'ticks_y':[(838.5,98),(883.5,96),(927.5,94),(973.5,92),(1018.5,90),(1063.5,88)]}}
def linear(p,a,b,v,w):return v+(p-a)*(w-v)/(b-a)
def interval(p,c,residual):
 a,b,v,w=c
 q=[linear(F(p)+dp,a+da,b+db,v,w) for dp,da,db in product((-2,2),(-1,1),(-1,1))]
 return min(q)-residual,max(q)+residual
def outward(x,upper):
 n=x*100
 return (-((-n.numerator)//n.denominator) if upper else n.numerator//n.denominator)/100
im=Image.open(source).convert('RGB');draw=ImageDraw.Draw(im);rows=[]
for panel,ys in picks.items():
 c=cal[panel];xr=max(abs(linear(F(x),*c['x'])-v) for x,v in c['ticks_x']);yr=max(abs(linear(F(y),*c['y'])-v) for y,v in c['ticks_y'])
 for t,y in zip(range(50,1101,50),ys):
  a,b,v,w=c['x'];x=round(a+(F(t)-v)*(b-a)/(w-v));xi=interval(x,c['x'],xr)
  row={'panel':panel,'sample':'MIA1' if panel=='A' else 'MIA3','target_temperature_c':t,'pixel_x':x,'pixel_y':y,'temperature_c':float(linear(F(x),*c['x'])),'temperature_lower_c':outward(xi[0],False),'temperature_upper_c':outward(xi[1],True),'tg_percent':None,'tg_lower_percent':None,'tg_upper_percent':None,'status':'unknown' if y is None else 'readable','reason':'curve overlaps baseline/arrow or final vertical axis; no interpolated substitute' if y is None else 'manually assigned TG branch; pixel envelope includes stroke thickness'}
  if y is not None:
   yi=interval(y,c['y'],yr);row.update(tg_percent=float(linear(F(y),*c['y'])),tg_lower_percent=outward(yi[0],False),tg_upper_percent=outward(yi[1],True));draw.ellipse((x-4,y-4,x+4,y+4),outline='red',width=1)
  rows.append(row)
record={'source_id':'areias-maciel-holanda2025-minerals15-879','source_doi':'10.3390/min15080879','figure':3,'pdf_page_one_based':8,'original_pdf_sha256':'9c59141a717cb3b062aed6f28b48ed6005c5564aa3ce5a86de1c083bb6eae8a6','read_image_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'read_image_size':[990,1400],'coordinate_origin':'top-left; x right,y down','calibration':cal,'point_pixel_error':2,'axis_endpoint_pixel_error':1,'method':'all exact Fraction endpoint corners plus maximum internal tick residual, outward 0.01; not experiment confidence limits','raw_tg_basis':'reported TG percent; initial normalization not independently known','runtime_material_qualified':False,'kinetics_fitted':False,'rows':rows}
def enc(x):
 if isinstance(x,F):return {'numerator':x.numerator,'denominator':x.denominator}
 raise TypeError(type(x))
(P/'tg-observations.json').write_text(json.dumps(record,default=enc,indent=2)+'\n')
with (P/'tg-observations.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
im.save(P/'tg-read-overlay.png')
print(json.dumps({'targets':len(rows),'readable':sum(r['status']=='readable' for r in rows),'unknown':sum(r['status']=='unknown' for r in rows),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}))
