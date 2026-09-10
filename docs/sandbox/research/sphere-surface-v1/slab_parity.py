"""Bounded old/new _surface bit comparison on actual slab host configurations."""
from pathlib import Path
import importlib.util
import json
import sys
from dataclasses import replace

root=Path.cwd()
sys.path.insert(0,str(root/'src'))
sys.path.insert(0,str(root/'tests/sandbox'))
from test_programmed_solid_fluid_heat import wrapped, program
from test_solid_fluid_heat import DATA
from sludge_sandbox.water_properties import load_water_properties
from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
from sludge_sandbox.deforming_solid_storage import _canonical

base=Path('/private/tmp/brick-sphere-surface-v1')
name='sludge_sandbox._previous_programmed_solid_fluid_heat'
spec=importlib.util.spec_from_file_location(name,base/'programmed_solid_fluid_heat.before.py')
old=importlib.util.module_from_spec(spec)
sys.modules[name]=old
spec.loader.exec_module(old)
ingredients=(load_water_properties(DATA),IdealWaterVapor(DATA),WaterChemicalPotential(DATA))
rows=[]
for mode in ('film','radiation','zero_k','adiabatic'):
    op=wrapped(ingredients)
    if mode=='radiation':op=replace(op,emissivity=.8,program=program(radiation_temperature_k=(400.,)*4))
    if mode=='zero_k':op=replace(op,base_model=replace(op.base_model,transport=replace(op.transport,conductivities_w_m_k=(0.,))))
    if mode=='adiabatic':op=replace(op,convection_w_m2_k=0.)
    boundary=op.program.at(.05)
    for temperature in (295.,300.,305.):
        before=old.ProgrammedSolidFluidHeat._surface(op,temperature,boundary)
        after=op._surface(temperature,boundary)
        assert _canonical(before)==_canonical(after),(mode,temperature,before,after)
        rows.append({'mode':mode,'cell_temperature_k':temperature,'same_float_hex_and_all_fields':True,
                     'surface_temperature_hex':after[0].hex(),'surface_iterations':after[-2]})
(base/'slab-parity.json').write_text(json.dumps({'cases':rows,'status':'all_12_bit_identical'},indent=2)+'\n')
print('12 old/new slab _surface results are bit-identical')
