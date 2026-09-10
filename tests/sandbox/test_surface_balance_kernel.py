"""Independent thermal roots and frozen complete legacy host observations."""
from collections.abc import Mapping
from dataclasses import fields,is_dataclass
import hashlib,importlib,json,math
import numpy as np
import pytest
from scipy.optimize import brentq
from sludge_sandbox.deforming_solid_storage import _canonical
from sludge_sandbox.programmed_gas_heat import SurfacePolicy
from test_solid_fluid_heat import ingredients
from test_programmed_solid_fluid_heat import wrapped,program


def snapshot(x):
    # Explicit test serializer includes all numeric arrays; no physics identity
    # serializer changes. Captured using this format before extracting solver.
    if isinstance(x,np.ndarray):return ['ndarray',str(x.dtype),list(x.shape),snapshot(x.tolist())]
    if is_dataclass(x):return [type(x).__module__,type(x).__qualname__,[[f.name,snapshot(getattr(x,f.name))] for f in fields(x)]]
    if isinstance(x,Mapping):return {k:snapshot(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [snapshot(v) for v in x]
    return _canonical(x)


@pytest.mark.parametrize('radiation,identity,golden', [
    (False,'ca28eebb6222ae0c2f00a57292f769a34d412870de69e8a6bc4750286191ca83','72177aa4f90ea31828ec7ac11da7290325892be134fe32d255660410f806d07d'),
    (True,'53fc8336c60293e3eac7d92c3d4331249ca8dc4c82518735f5d5f598a6682df4','539c53b47cffd316657de14515bfad6db2c4fef5d466d59cfc5a24da5819653e'),
])
def test_whole_legacy_observation_and_identity(ingredients,radiation,identity,golden):
    options=dict(emissivity=.8,program=program(radiation_temperature_k=(400.,)*4)) if radiation else {}
    op=wrapped(ingredients,**options)
    state=op.base_model.state_from_temperatures([[2.,0.,0.,.01]],[300.])
    out=op.evaluate(state,.05)
    assert op.operator_identity==('programmed_solid_fluid_operator_v1',identity)
    assert hashlib.sha256(json.dumps(snapshot(out),sort_keys=True,separators=(',',':')).encode()).hexdigest()==golden


class SurfaceProbeError(ValueError):pass


def solve(**changes):
    values=dict(cell_temperature_k=300.,gas_temperature_k=400.,radiation_temperature_k=450.,
                area_m2=.02,convection_w_m2_k=20.,emissivity=0.,stefan_boltzmann_w_m2_k4=5.670374419e-8,
                policy=SurfacePolicy(absolute_residual_w=1e-10,relative_residual=1e-12,maximum_iterations=200),
                conductive_into_cell=lambda t:2.*(t-300.),zero_conductivity=False,error_type=SurfaceProbeError)
    values.update(changes)
    return importlib.import_module('sludge_sandbox.surface_balance').solve_surface_balance(**values)


def test_linear_series_resistance_and_radiation_root():
    surface,heat,into,residual,limit,iterations,status=solve()
    assert surface==pytest.approx((2*300+.4*400)/2.4,abs=1e-9)
    assert into==pytest.approx((400-300)/(1/2+1/.4),abs=1e-9)
    assert abs(residual)<=limit and status=='balanced' and iterations>0
    root=brentq(lambda t:2*(t-300)-.02*(20*(400-t)+.8*5.670374419e-8*(450**4-t**4)),300,450)
    assert solve(emissivity=.8)[0]==pytest.approx(root,abs=1e-8)


@pytest.mark.parametrize('zero_k,status',[(False,'adiabatic'),(True,'insulated_surface_undetermined')])
def test_zero_film_coefficients(zero_k,status):
    out=solve(convection_w_m2_k=0.,emissivity=0.,zero_conductivity=zero_k,
              conductive_into_cell=(lambda t:0.) if zero_k else (lambda t:2*(t-300.)))
    assert out[0]==300. and out[2]==0. and out[5]==0 and out[6]==status


def test_zero_conductivity_still_solves_film_and_zero_h_radiation():
    out=solve(zero_conductivity=True,conductive_into_cell=lambda t:0.,radiation_temperature_k=400.)
    assert out[0]==400. and out[2]==0.
    out=solve(convection_w_m2_k=0.,emissivity=.8)
    assert 300.<out[0]<450. and abs(out[3])<=out[4]


def test_failure_types_and_callback_propagation():
    with pytest.raises(SurfaceProbeError,match='nonfinite_surface_balance'):
        solve(conductive_into_cell=lambda t:math.nan)
    with pytest.raises(SurfaceProbeError,match='surface_iteration_limit'):
        solve(policy=SurfacePolicy(absolute_residual_w=1e-20,relative_residual=1e-20,maximum_iterations=1))
    with pytest.raises(SurfaceProbeError,match='surface_root_unresolvable_in_float'):
        solve(gas_temperature_k=math.nextafter(300.,math.inf),radiation_temperature_k=300.,
              conductive_into_cell=lambda t:-1. if t==300. else 1.,
              policy=SurfacePolicy(absolute_residual_w=1e-20,relative_residual=1e-20,maximum_iterations=10))
    def failed(t):raise RuntimeError('bound_conduction_failed')
    with pytest.raises(RuntimeError,match='bound_conduction_failed'):solve(conductive_into_cell=failed)
