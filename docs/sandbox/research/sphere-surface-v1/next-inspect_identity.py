from dataclasses import fields,is_dataclass
from collections.abc import Mapping
from fractions import Fraction
import numpy as np
from test_deforming_solid_heat import host
from test_rigid_storage import DATA
from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.deforming_solid_storage import is_water_provider
root=host(load_water_properties(DATA),isotropic=True)
found=[]
def walk(x,path):
 if x is None or type(x) in (str,bool,int,float,Fraction): return
 if is_water_provider(x): return
 if isinstance(x,Mapping):
  for k,v in sorted(x.items()):walk(v,f'{path}[{k!r}]')
 elif isinstance(x,(tuple,list)):
  for i,v in enumerate(x):walk(v,f'{path}[{i}]')
 elif is_dataclass(x):
  for f in fields(x):walk(getattr(x,f.name),f'{path}.{f.name}')
 else:
  print(path,type(x).__module__,type(x).__qualname__, 'shape='+str(getattr(x,'shape',None)),'dtype='+str(getattr(x,'dtype',None)),'value='+repr(x))
  found.append(path)
walk(root,'base_model')
print('unsupported_count',len(found))
print('first',found[0])
