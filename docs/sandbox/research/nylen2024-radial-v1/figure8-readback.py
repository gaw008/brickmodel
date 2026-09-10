from pathlib import Path
from fractions import Fraction as F
import csv,json,itertools,hashlib
import numpy as np
from scipy.ndimage import binary_erosion,label,find_objects
R=Path('/Users/wanggaoying/Desktop/brickmodel-github');H=R/'data/sandbox/research/nylen2024-drying/figure8'
s=json.loads((H/'selection.json').read_text());meta=json.loads((H.parent/'source.json').read_text());audit=json.loads((H/'extraction_audit.json').read_text());rows=list(csv.DictReader((H/'observations.csv').open()))
a=np.load('/private/tmp/brick-nylen-figure8-review/native.npy').astype(float);r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]
masks={'red':(r>150)&(g<125)&(b<125),'blue':(b>130)&(r<110)&(g<150),'green':(g>100)&(g>r+25)&(g>b+10)&(r<120),'gray':(a.max(axis=2)-a.min(axis=2)<15)&(r<140)}
for color,m in masks.items():
 core=binary_erosion(m,structure=np.ones((5,5),bool),border_value=0);core[:25]=core[840:]=False;core[:,:137]=core[:,1120:]=False
 labs,n=label(core,structure=np.ones((3,3)));components=[]
 for i,sl in enumerate(find_objects(labs),1):
  yy,xx=sl;area=int((labs[sl]==i).sum())
  if area>=5:
   box=[xx.start,yy.start,xx.stop-1,yy.stop-1];components.append({'area':area,'bbox_px':box,'center_px':[(box[0]+box[2])/2,(box[1]+box[3])/2]})
 components.sort(key=lambda x:x['center_px'][0]);assert components==audit['component_audit'][color]['components'],color
 selected=[]
 for anchor in s['series'][color]['reviewed_core_anchors_px']:
  matches=[c for c in components if max(abs(c['center_px'][j]-anchor[j]) for j in [0,1])<=2];assert len(matches)==1;selected.append(matches[0]['center_px'])
 selected.extend(c['center_px'] for c in s['series'][color]['manual_centers']);selected.sort()
 observed=[row for row in rows if row['selection_id'].startswith('figure8-'+color+'-')]
 assert [[float(x['x_px']),float(x['y_px'])] for x in observed]==selected
 for row in observed:
  assert row['source_id']==meta['id'] and row['plotted_sd_degC']=='' and row['role']=='development'
  condition=next(c for c in meta['conditions'] if c['run']==int(row['run']))
  assert str(condition['diameter_cm'])==row['diameter_cm'] and condition['material_id']==row['material_id']
  for pixel,cal,end,scale,keys in [(F(row['x_px']),s['calibration']['time_px'],F(160),F(60),['time_s','time_readout_lower_s','time_readout_upper_s']), (F(row['y_px']),s['calibration']['temperature_px'],F(140),F(1),['value_degC','temperature_readout_lower_degC','temperature_readout_upper_degC'])]:
   half=F(s['series'][color]['center_readout_halfwidth_px']);p0,p1=map(F,cal)
   center=(pixel-p0)*end/(p1-p0)*scale
   vals=[(x-a)*end/(b-a)*scale for x,a,b in itertools.product([pixel-half,pixel+half],[p0-1,p0+1],[p1-1,p1+1])]
   for v,key in zip([center,min(vals),max(vals)],keys):assert abs(v-F(row[key]))<=F(51,10**11),(key,row['selection_id'])
   if keys[0]=='time_s':assert abs(center-F(row['time_min'])*60)<=F(31,10**9)
assert len(rows)==43
print(json.dumps({'rows':len(rows),'counts':{c:sum(row['selection_id'].startswith('figure8-'+c+'-') for row in rows) for c in masks},'independent_component_and_fraction_check':'PASS','hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [H/'extract.py',H/'observations.csv',H/'selection.json',H/'extraction_audit.json',H.parent/'source.json']}},indent=2))
