import importlib.util,sys,json,ast
from pathlib import Path
from test_dynamic_solid_storage import water,forbid_water_eos
from sludge_sandbox.verification_case import encode
root=Path('/private/tmp/brick-programmed-free-slab-candidate')
spec=importlib.util.spec_from_file_location('snapshot_candidate_fixture',root/'test_program.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
source=Path(__file__).with_name('test_programmed_free_wet.py')
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='snapshot')
namespace={'encode':encode};exec(compile(ast.Module(body=[node],type_ignores=[]),'snapshot_only','exec'),namespace)

def test_selected_snapshot_dry_candidate(water):
    op=m.wrapped(water);state=m.initial(op.base_model);out=op.evaluate(state,.05)
    saved=namespace['snapshot'](out)
    raw=json.dumps(saved,allow_nan=False)
    assert 'current_host' not in raw and 'current_storage' not in raw
    assert len(saved['geometry']['widths_m'])==2 and len(saved['rates']['mechanical_rates_per_s'])==3
    Path(__file__).with_name('dry-snapshot.json').write_text(raw+'\n')
