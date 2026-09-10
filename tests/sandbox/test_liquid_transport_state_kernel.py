"""Decoded-liquid adapter; manufactured liquid seam, no native liquid EOS."""
from dataclasses import replace
import hashlib,importlib,json
from fractions import Fraction as F
import pytest
from test_mass_wet_storage import setup
from test_solid_fluid_heat import ingredients
from test_liquid_solid_fluid_heat import liquid_host
from test_surface_balance_kernel import snapshot
from sludge_sandbox.liquid_transport import LiquidTransportError


def kernel(*args,**kwargs):
    return importlib.import_module('sludge_sandbox.liquid_transport_state').decoded_liquid_state(*args,**kwargs)


def point(monkeypatch,liquid=.2):
    st,s,calls=setup(monkeypatch)
    p=st.evaluate(replace(s,liquid_water_mol=liquid),305.)
    return st,p,calls


def invoke(st,p,**kw):
    options=dict(available_pore_volume_m3=p.available_pore_volume_m3,pressure_error_pa=p.pressure_error_pa)
    options.update(kw)
    return kernel(p.fluid.mechanical,st.water,**options)


def test_frozen_complete_host_observation(monkeypatch):
    setup(monkeypatch)
    host=liquid_host(ingredients.__wrapped__())
    state=host.state_from_temperatures([[2.,1e-5,2.,.02],[2.,1e-5,1.,.01]],[300.,301.])
    out=host.evaluate(state,0)
    assert hashlib.sha256(json.dumps(snapshot(out),sort_keys=True,separators=(',',':')).encode()).hexdigest()=='48e0e20f2a41b919e81dffcbfe2145eb92ffb023e3ac0157ba3af815fea96cd2'
    assert out.liquid_pressure_interval_scope=='fixed_decoded_temperature'
    assert not out.full_inverse_liquid_direction_certified


def test_same_decoded_tp_once_and_analytic_properties(monkeypatch):
    st,p,calls=point(monkeypatch)
    before=len(calls)
    out=invoke(st,p)
    assert calls[before:]==[(p.temperature_k,p.fluid.mechanical.liquid_pressure_pa)]
    assert out.molar_volume_m3_mol==pytest.approx(1.8e-5,rel=1e-15)
    assert out.enthalpy_j_mol==pytest.approx(75*305-300000+p.pressure_pa*1.8e-5,abs=1e-9)
    assert out.saturation==p.fluid.mechanical.liquid_volume_m3/p.available_pore_volume_m3
    assert out.pressure_error_pa==p.pressure_error_pa
    assert out.source_asset_sha256==tuple(sorted(st.water.source_asset_sha256.items()))
    # Explicit caller uncertainty is forwarded, not replaced by bare fluid error.
    expanded=invoke(st,p,pressure_error_pa=p.pressure_error_pa+1.)
    assert expanded.pressure_error_pa==p.pressure_error_pa+1.


def test_dry_no_liquid_query(monkeypatch):
    st,p,calls=point(monkeypatch,liquid=0.)
    def forbidden(*args,**kw):pytest.fail('dry TP called')
    monkeypatch.setattr(type(st.water),'state_tp',forbidden)
    out=invoke(st,p)
    assert out.inventory_mol==out.saturation==0
    assert out.molar_volume_m3_mol is out.enthalpy_j_mol is None


@pytest.mark.parametrize('change',[
    {'source_asset_sha256':{}}, {'gas_constant_j_mol_k':9.},
    {'liquid_native_molar_gas_constant_j_mol_k':9.},
    {'assumption':'capillary'}, {'liquid_pressure_pa':123.},
    {'gas_volume_m3':0.}, {'liquid_inventory_mol':-1.},
])
def test_invalid_mechanical_source_and_domain_before_tp(monkeypatch,change):
    st,p,_=point(monkeypatch)
    def forbidden(*args,**kw):pytest.fail('invalid point reached TP')
    monkeypatch.setattr(type(st.water),'state_tp',forbidden)
    with pytest.raises(LiquidTransportError):
        kernel(replace(p.fluid.mechanical,**change),st.water,
               available_pore_volume_m3=p.available_pore_volume_m3,pressure_error_pa=p.pressure_error_pa)


@pytest.mark.parametrize('change',[
    {'available_pore_volume_m3':0.}, {'available_pore_volume_m3':.02},
    {'available_pore_volume_m3':F(1,1000)}, {'pressure_error_pa':-1.},
    {'pressure_error_pa':True}, {'pressure_error_pa':float('inf')},
    {'pressure_error_pa':1e9},
])
def test_invalid_caller_geometry_and_error(monkeypatch,change):
    st,p,_=point(monkeypatch)
    with pytest.raises(LiquidTransportError):invoke(st,p,**change)


def test_wrong_provider_and_tp_failures_propagate(monkeypatch):
    st,p,_=point(monkeypatch)
    with pytest.raises(LiquidTransportError):
        kernel(p.fluid.mechanical,object(),available_pore_volume_m3=p.available_pore_volume_m3,pressure_error_pa=p.pressure_error_pa)
    def failed(*args,**kwargs):raise RuntimeError('actual_liquid_backend_failure')
    monkeypatch.setattr(type(st.water),'state_tp',failed)
    with pytest.raises(RuntimeError,match='actual_liquid_backend_failure'):invoke(st,p)


def test_legitimate_rounded_volume_sum_above_nominal_is_not_clipped(monkeypatch):
    st,p,_=point(monkeypatch,liquid=.1)
    m=p.fluid.mechanical
    assert F(m.liquid_volume_m3)+F(m.gas_volume_m3)>F(p.available_pore_volume_m3)
    out=invoke(st,p)
    assert out.saturation==m.liquid_volume_m3/p.available_pore_volume_m3


def test_old_host_uses_helper_and_one_inverse(monkeypatch):
    from sludge_sandbox.solid_fluid_heat import SolidFluidHeat
    setup(monkeypatch)
    host=liquid_host(ingredients.__wrapped__())
    state=host.state_from_temperatures([[2.,1e-5,2.,.02],[2.,1e-5,1.,.01]],[300.,301.])
    module=importlib.import_module('sludge_sandbox.liquid_transport_state')
    original=module.decoded_liquid_state; original_decode=SolidFluidHeat.decode_inverse
    calls=[]; decodes=[]
    def observe(*args,**kwargs):
        calls.append(kwargs)
        return original(*args,**kwargs)
    def decode(*args,**kwargs):
        decodes.append(1)
        return original_decode(*args,**kwargs)
    monkeypatch.setattr(module,'decoded_liquid_state',observe)
    monkeypatch.setattr(SolidFluidHeat,'decode_inverse',decode)
    out=host.evaluate(state,0)
    assert len(calls)==2 and decodes==[1]
    for kwargs,closed in zip(calls,out.storage_states):
        assert kwargs==dict(available_pore_volume_m3=closed.available_pore_volume_m3,
                           pressure_error_pa=closed.pressure_error_bound_pa)
