from pathlib import Path
from fractions import Fraction as F
import xml.etree.ElementTree as ET
import re,json,hashlib,itertools
import mpmath as mp
root=Path('/Users/wanggaoying/Desktop/brickmodel-github')
obs=json.loads((root/'data/sandbox/research/amadou2006-desorption/observations.json').read_text())
paths=list(ET.parse(root/'.tools/source-cache/amadou2006/sorption-page6.svg').iter('{http://www.w3.org/2000/svg}path'))
mp.mp.dps=100
max_error=mp.mpf(0)
max_residual=mp.mpf(0)
within=0
for t,axis,start in [(30,268,271),(50,250,253)]:
 def box(p):
  nums=[F(x) for x in re.findall(r'-?\d+(?:\.\d+)?',p.attrib['d'])]
  return min(nums[::2]),max(nums[::2]),min(nums[1::2]),max(nums[1::2])
 ax,bx,ay,by=box(paths[axis])
 rows=[r for r in obs['records'] if r['temperature_degC']==t]
 assert [r['svg_path_index_zero_based'] for r in rows]==list(range(start,start+8))
 for j,r in enumerate(rows,1):
  p=paths[start+j-1];x0,x1,y0,y1=box(p)
  assert r['original_path']==p.attrib['d']
  assert r['transform']==p.attrib['transform']==paths[axis].attrib['transform']
  assert tuple(map(F,r['marker_box']))==(x0,x1,y0,y1)
  assert tuple(map(F,r['axis_rectangle']))==(ax,bx,ay,by)
  h=F(p.attrib['stroke-width'])/2
  for lo,hi,a,b,scale,key in [(x0,x1,ax,bx,F(1),'activity_graphic_interval'),(y0,y1,ay,by,F(1,4),'X_graphic_interval')]:
   vals=[(point-origin)/(end-origin)*scale for point,origin,end in itertools.product([lo-h-F(1,2),hi+h+F(1,2)],[a-F(1,2),a+F(1,2)],[b-F(1,2),b+F(1,2)])]
   for v,saved in zip([min(vals),max(vals)],r[key]): assert abs(v-F(saved))<F(1,10**48)
  center=((y0+y1)/2-ay)/(by-ay)/4
  assert abs(center-F(r['digitized_X_kg_water_per_kg_dry']))<F(1,10**48)
  k,n={30:('.112','.416'),50:('.0938','.484')}[t]
  a=mp.mpf(j)/10
  ref=mp.mpf(k)*mp.exp(mp.mpf(n)*mp.log(a/(1-a)))
  max_error=max(max_error,abs(ref-mp.mpf(r['reported_coefficient_fit_X'])))
  residue=ref-mp.mpf(center.numerator)/center.denominator
  max_residual=max(max_residual,abs(residue))
  within+=mp.mpf(r['X_graphic_interval'][0])<=ref<=mp.mpf(r['X_graphic_interval'][1])
assert within==16 and max_error<mp.mpf('1e-48')
files=['src/sludge_sandbox/amadou_desorption.py','tests/sandbox/test_amadou_desorption.py','data/sandbox/research/amadou2006-desorption/digitize.py','data/sandbox/research/amadou2006-desorption/source.json','data/sandbox/research/amadou2006-desorption/observations.json']
result={'rows':16,'inside_graphic_envelope':within,'max_fit_arithmetic_difference':str(max_error),'max_abs_residual':str(max_residual),'hashes':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}}
print(json.dumps(result,indent=2))
