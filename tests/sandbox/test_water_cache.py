"""Cache behavior never substitutes for current EOS validation."""
from dataclasses import FrozenInstanceError, replace
import math
from pathlib import Path
from types import SimpleNamespace
import pytest
from sludge_sandbox.water_properties import load_water_properties, WaterNumericalError

DATA=Path(__file__).resolve().parents[2]/'data/sandbox/water'

@pytest.fixture
def water(): return load_water_properties(DATA)

def counting(water,monkeypatch):
    original=water._backend.IAPWS95
    calls=[]
    def wrapped(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(water._backend,'IAPWS95',wrapped)
    return calls

def test_exact_temperature_single_entry_cache(water,monkeypatch):
    calls=counting(water,monkeypatch)
    first=water.saturation_pair(300)
    assert water.saturation_pair(300.)==first
    assert len(calls)==1
    water.saturation_pair(math.nextafter(300.,math.inf))
    water.saturation_pair(300.)
    assert len(calls)==3
    with pytest.raises(FrozenInstanceError): first.pressure_pa=0
    with pytest.raises(FrozenInstanceError): water._saturation_cache.raw.P=0

def test_instances_do_not_share_reference_or_cache(water,monkeypatch):
    other=load_water_properties(DATA)
    calls=counting(water,monkeypatch)
    a=water.saturation_pair(300); b=other.saturation_pair(300)
    assert len(calls)==2
    assert a.liquid.reference is water.reference
    assert b.liquid.reference is other.reference

def test_warm_cache_solver_replacement_still_fails(water,monkeypatch):
    water.saturation_pair(300)
    monkeypatch.setattr(water._backend,'IAPWS95',lambda **kw:SimpleNamespace(status=0,msg='failure'))
    with pytest.raises(WaterNumericalError):water.saturation_pair(300)

@pytest.mark.parametrize('method,field', [('_Helmholtz','h'),('_phir','firtt'),('_phi0','fiott')])
def test_warm_cache_rechecks_current_eos(water,monkeypatch,method,field):
    water.saturation_pair(300)
    original=getattr(water._model,method)
    def corrupt(*a,**k):return original(*a,**k)|{field:math.nan}
    monkeypatch.setattr(water._model,method,corrupt)
    with pytest.raises(WaterNumericalError):water.saturation_pair(300)

def test_policy_change_invalidates_solver_cache(water,monkeypatch):
    calls=counting(water,monkeypatch)
    water.saturation_pair(300)
    object.__setattr__(water,'numerical_limits',replace(water.numerical_limits,temperature_absolute_k=5e-10))
    water.saturation_pair(300)
    assert len(calls)==2

def test_hit_rechecks_eos_but_does_not_resolve_saturation(water,monkeypatch):
    calls=counting(water,monkeypatch)
    original=water._model._Helmholtz
    eos=[]
    def wrapped(*a,**k):eos.append(1);return original(*a,**k)
    monkeypatch.setattr(water._model,'_Helmholtz',wrapped)
    water.saturation_pair(300);water.saturation_pair(300)
    assert len(calls)==1
    assert len(eos)==4

@pytest.mark.parametrize('field', ['reference','source_asset_sha256'])
def test_identity_change_invalidates_cache(water,monkeypatch,field):
    calls=counting(water,monkeypatch)
    water.saturation_pair(300)
    new=(replace(water.reference) if field=='reference'
         else dict(water.source_asset_sha256)|{'test-marker':'changed'})
    object.__setattr__(water,field,new)
    pair=water.saturation_pair(300)
    assert len(calls)==2
    assert pair.liquid.reference is water.reference

def test_failed_miss_is_not_cached(water,monkeypatch):
    original=water._backend.IAPWS95
    calls=[]
    def flaky(**kw):
        calls.append(kw)
        return SimpleNamespace(status=0) if len(calls)==1 else original(**kw)
    monkeypatch.setattr(water._backend,'IAPWS95',flaky)
    with pytest.raises(WaterNumericalError):water.saturation_pair(300)
    assert water._saturation_cache is None
    water.saturation_pair(300);water.saturation_pair(300)
    assert len(calls)==2

def test_warm_cache_warning_is_not_hidden(water,monkeypatch):
    import warnings
    water.saturation_pair(300)
    original=water._backend.IAPWS95
    def warned(**kw):
        warnings.warn('injected warning')
        return original(**kw)
    monkeypatch.setattr(water._backend,'IAPWS95',warned)
    with pytest.raises(WaterNumericalError,match='warning'):water.saturation_pair(300)

@pytest.mark.parametrize('t',[True,float('nan'),float('inf'),292.,501.])
def test_warm_cache_preserves_domain_checks(water,t):
    from sludge_sandbox.water_properties import WaterDomainError
    water.saturation_pair(300)
    with pytest.raises(WaterDomainError):water.saturation_pair(t)

def test_warm_cache_missing_solver_preserves_error_category(water,monkeypatch):
    water.saturation_pair(300)
    monkeypatch.delattr(water._backend,'IAPWS95')
    with pytest.raises(WaterNumericalError,match='iapws_solver_failed'):
        water.saturation_pair(300)
