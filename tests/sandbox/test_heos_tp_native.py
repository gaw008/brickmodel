"""Native numerical neighborhood of the preserved TP two-cycle, not material data."""
import math
import pytest
from sludge_sandbox.water_properties import load_water_properties
from test_water_properties import DATA

pytest.importorskip('CoolProp')
T0 = float.fromhex('0x1.2700000000000p+8')
P0 = float.fromhex('0x1.a379187ce8000p+15')


@pytest.fixture(scope='module')
def qualified_heos():
    return load_water_properties(DATA, backend='heos', backend_manifest=DATA/'heos-8.0.0-approved-manifest.json')


@pytest.mark.parametrize('temperature', [T0-.001, T0, T0+.001])
@pytest.mark.parametrize('pressure', [P0-.01, P0, P0+.01])
def test_tp_cycling_point_and_fixed_neighbors_keep_original_gate(qualified_heos, temperature, pressure):
    state = qualified_heos.state_tp(temperature, pressure, phase='liquid')
    rows = qualified_heos._kernel.last_tp
    assert state.temperature_k == temperature and state.pressure_pa == pressure
    assert state.phase == 'liquid'
    assert rows[-1]['rho'] == state.density_kg_m3
    residual = rows[-1]['native_p']-pressure
    assert residual == rows[-1]['residual_pa']
    assert math.isfinite(residual) and abs(residual) <= min(1e-4, state.density_kg_m3*1e-7)
    assert 1 <= len(rows) <= 43
    assert state.implementation == qualified_heos.implementation
