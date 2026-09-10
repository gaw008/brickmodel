import importlib.util,sys,traceback
from pathlib import Path
from sludge_sandbox.water_properties import load_water_properties
from test_rigid_storage import DATA
import test_deforming_wet_admission as tests
p=Path('/private/tmp/brick-sphere-surface-review/prior_programmed_solid_fluid_heat.py');s=importlib.util.spec_from_file_location('sludge_sandbox._review_prior_deforming',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
tests.ProgrammedSolidFluidHeat=m.ProgrammedSolidFluidHeat
try:tests.wrapped(load_water_properties(DATA))
except Exception as e:
 traceback.print_exc()
 assert str(e)=='unsupported_identity_type:ndarray'
 print('Confirmed same preexisting construction failure with frozen priorHEAD wrapper.')
else:raise AssertionError('Prior unexpectedly accepted')
