"""Instrumented dispatch tests, not physical/EOS validation."""
from fractions import Fraction
from types import SimpleNamespace
import pytest
from sludge_sandbox.exact_event_clock import ExactEventTime
from sludge_sandbox.free_solid_slab import FreeSolidSlab
from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
from sludge_sandbox.exact_free_host import ExactFreeWaterTransfer
from sludge_sandbox.integration import IntegrationError


def test_free_shared_body_and_original_time_validation(monkeypatch):
    host=object.__new__(FreeSolidSlab); calls=[]; state=object(); result=object()
    monkeypatch.setattr(FreeSolidSlab,'_check_state',lambda self,s:calls.append(('check',s)))
    monkeypatch.setattr(FreeSolidSlab,'_evaluate_current_state',lambda self,s:(calls.append(('body',s)) or result))
    assert host.evaluate(state,.5) is result
    assert host.evaluate_autonomous(state) is result
    assert calls==[('check',state),('body',state)]*2
    with pytest.raises(ValueError):host.evaluate(state,float('nan'))
    assert calls[-1]==('check',state)


def test_transfer_precheck_precedes_evaluation_and_shared_assembly(monkeypatch):
    host=object.__new__(FreeSolidSlab); op=object.__new__(WaterPhaseTransfer)
    object.__setattr__(op,'base_model',host); calls=[]; state=object(); base=object(); result=object()
    monkeypatch.setattr(WaterPhaseTransfer,'_check_interface_state',lambda self,s:calls.append('precheck'))
    monkeypatch.setattr(FreeSolidSlab,'evaluate_autonomous',lambda self,s:(calls.append('autonomous') or base))
    monkeypatch.setattr(FreeSolidSlab,'evaluate',lambda self,s,t:(calls.append(('legacy',t)) or base))
    monkeypatch.setattr(WaterPhaseTransfer,'_assemble_transfer',lambda self,s,b:(calls.append(('assembly',b)) or result))
    assert op.evaluate(state,.5) is result
    assert op.evaluate_autonomous(state) is result
    assert calls==['precheck',('legacy',.5),('assembly',base),'precheck','autonomous',('assembly',base)]
    def reject(self,s):raise IntegrationError('interface_rejected')
    monkeypatch.setattr(WaterPhaseTransfer,'_check_interface_state',reject)
    with pytest.raises(IntegrationError):op.evaluate_autonomous(state)
    assert len(calls)==6


def test_exact_view_no_float_projection_strict_admission_and_source_checks(monkeypatch):
    host=object.__new__(FreeSolidSlab); op=object.__new__(WaterPhaseTransfer)
    object.__setattr__(op,'base_model',host); checks=[]; calls=[]
    actual_autonomous=WaterPhaseTransfer.evaluate_autonomous
    binding=['original']
    monkeypatch.setattr(ExactFreeWaterTransfer,'_binding',lambda self:(checks.append('bind') or tuple(binding)))
    result=SimpleNamespace(rates=object())
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',lambda self,s:(calls.append(s) or result))
    view=ExactFreeWaterTransfer(op); state=object()
    assert view(state,ExactEventTime(Fraction(10**400))) is result.rates
    assert calls==[state] and len(checks)==3
    for bad in (.5,True,Fraction(1)):
        with pytest.raises(IntegrationError):view(state,bad)
    assert len(calls)==1
    binding[0]='changed'
    with pytest.raises(IntegrationError):view(state,ExactEventTime(Fraction(1)))
    assert len(calls)==1
    with pytest.raises(IntegrationError):ExactFreeWaterTransfer(SimpleNamespace(base_model=host))
    object.__setattr__(op,'base_model',SimpleNamespace())
    with pytest.raises(IntegrationError):actual_autonomous(op,state)


def binding_fixture():
    """Actual typed provider shells; real canonicalizer/identity, no EOS construction."""
    from dataclasses import dataclass,fields
    from sludge_sandbox.water_heos import HEOSWaterProperties
    from sludge_sandbox.water_properties import WaterProperties,NumericalLimits
    from sludge_sandbox.water_implementation import WaterImplementation
    from sludge_sandbox.ideal_water_vapor import IdealWaterVapor
    from sludge_sandbox.water_chemical_potential import WaterChemicalPotential
    def shell(cls):
        value=object.__new__(cls)
        for f in fields(cls):object.__setattr__(value,f.name,None)
        return value
    impl=WaterImplementation('water_implementation_v1','instrumented','1',('test',),'{}')
    def water():
        value=shell(HEOSWaterProperties)
        for k,v in dict(reference=('same-test-reference',),source_asset_sha256={'asset':'a'*64},numerical_limits=NumericalLimits(),implementation=impl).items():object.__setattr__(value,k,v)
        return value
    def vapor(provider):
        value=shell(IdealWaterVapor)
        for k,v in dict(reference=provider.reference,source_asset_sha256=provider.source_asset_sha256,gas_constant_j_mol_k=8.31446261815324,_water=provider).items():object.__setattr__(value,k,v)
        return value
    @dataclass(frozen=True)
    class Mechanical:water:object
    @dataclass(frozen=True)
    class Fluid:
        mechanical:object
        gas_phases:object
    @dataclass(frozen=True)
    class Solid:fluid_template:object
    @dataclass(frozen=True)
    class Thermal:storages:tuple
    chemical_water,chemical_ideal,thermal_water,thermal_ideal=[water() for _ in range(4)]
    chemical=shell(WaterChemicalPotential)
    object.__setattr__(chemical,'water',chemical_water);object.__setattr__(chemical,'vapor',vapor(chemical_ideal))
    host=shell(FreeSolidSlab)
    storage=Solid(Fluid(Mechanical(thermal_water),{'H2O':vapor(thermal_ideal)}))
    object.__setattr__(host,'base_model',Thermal((storage,)))
    operator=shell(WaterPhaseTransfer)
    object.__setattr__(operator,'base_model',host);object.__setattr__(operator,'chemical',chemical)
    return operator,(chemical_water,chemical_ideal,thermal_water,thermal_ideal),WaterProperties


@pytest.mark.parametrize('provider_index',[0,1,2,3])
def test_real_binding_detects_last_callback_provider_implementation_change(monkeypatch,provider_index):
    from dataclasses import replace
    from sludge_sandbox.deforming_solid_storage import _digest
    operator,providers,_=binding_fixture();provider=providers[provider_index]
    original=_digest(operator);view=ExactFreeWaterTransfer(operator);calls=[]
    def actual(self,state):
        calls.append(state)
        object.__setattr__(provider,'implementation',replace(provider.implementation,provider_version='2'))
        return SimpleNamespace(rates=object())
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',actual)
    with pytest.raises(IntegrationError,match='source_binding_changed'):
        view.evaluate(object(),ExactEventTime(Fraction(1)))
    assert len(calls)==1 and _digest(operator)==original


def test_real_binding_detects_provider_class_replacement_before_callback(monkeypatch):
    from sludge_sandbox.deforming_solid_storage import _digest
    operator,providers,PythonWater=binding_fixture()
    # Equal None implementation descriptors isolate the concrete-class guard.
    # These are instrumented provider shells, not claimed valid EOS instances.
    object.__setattr__(providers[2],'implementation',None)
    view=ExactFreeWaterTransfer(operator);calls=[]
    mechanical=operator._fluid_storages[0].mechanical;old=_digest(operator)
    replacement=object.__new__(PythonWater)
    for key in ('reference','source_asset_sha256','numerical_limits'):object.__setattr__(replacement,key,getattr(providers[2],key))
    object.__setattr__(mechanical,'water',replacement)
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',lambda self,s:(calls.append(s) or object()))
    assert _digest(operator)==old
    with pytest.raises(IntegrationError,match='source_binding_changed'):view.evaluate(object(),ExactEventTime(Fraction(1)))
    assert calls==[]


def test_real_binding_normal_distinct_providers_control(monkeypatch):
    operator,providers,_=binding_fixture();view=ExactFreeWaterTransfer(operator);calls=[];result=SimpleNamespace(rates=object())
    monkeypatch.setattr(WaterPhaseTransfer,'evaluate_autonomous',lambda self,s:(calls.append(s) or result))
    assert view.evaluate(object(),ExactEventTime(Fraction(10**400))) is result
    assert len(calls)==1 and len({id(w) for w in providers})==4
