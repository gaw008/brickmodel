from pathlib import Path
from decimal import Context, localcontext, Inexact, Decimal
import importlib.util
import pytest
from sludge_sandbox.amadou_desorption import AmadouDesorption,DesorptionError
ROOT=Path('/Users/wanggaoying/Desktop/brickmodel-github')
SOURCE=ROOT/'data/sandbox/research/amadou2006-desorption/source.json'
def test_symlink_outside_root(tmp_path):
    dest=tmp_path/'.tools/source-cache/amadou2006/sorption.pdf'
    dest.parent.mkdir(parents=True)
    dest.symlink_to(ROOT/'.tools/source-cache/amadou2006/sorption.pdf')
    with pytest.raises(DesorptionError,match='outside_repository'):
        AmadouDesorption(SOURCE,tmp_path)
def test_ambient_inexact_trap_does_not_leak():
    model=AmadouDesorption(SOURCE,ROOT)
    expected=model.moisture(Decimal('.37'),30,unit='1',temperature_unit='degC')
    with localcontext(Context(prec=2)) as ctx:
        ctx.traps[Inexact]=True
        assert model.moisture(Decimal('.37'),30,unit='1',temperature_unit='degC')==expected
def test_digitizer_changed_source_stops_before_output(tmp_path):
    path=ROOT/'data/sandbox/research/amadou2006-desorption/digitize.py'
    spec=importlib.util.spec_from_file_location('digitizer',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.__file__=str(tmp_path/'digitize.py')
    (tmp_path/'source.json').write_bytes(SOURCE.read_bytes()+b' ')
    with pytest.raises(ValueError,match='metadata differs'):mod.main()
    assert not (tmp_path/'observations.json').exists()
