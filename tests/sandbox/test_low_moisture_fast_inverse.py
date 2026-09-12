"""Manufactured caloric callbacks on exact source classes; never real EOS.

These probes validate an explicitly new inverse policy, not thermal material
accuracy or native runtime performance. Counts include actual evaluate calls.
"""
from dataclasses import replace
from fractions import Fraction as F
import json
import math
from pathlib import Path

import pytest

from sludge_sandbox import low_moisture_fast_inverse as fast
from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage
from sludge_sandbox.source_wet_storage import SourceWetStorage, SourceWetInverse
from sludge_sandbox.phase_storage import InversePolicy
from test_low_moisture_storage import setup


METRICS=[]


@pytest.fixture(scope='session',autouse=True)
def save_actual_counts(tmp_path_factory):
    yield
    (tmp_path_factory.mktemp('inverse-counts')/'CALL_COUNTS.json').write_text(json.dumps(METRICS,indent=2)+'\n')


@pytest.fixture
def context(monkeypatch):
    storage,_,gas=setup(monkeypatch)
    original=SourceWetStorage.evaluate
    controls={'mode':'linear','error':0.,'cp_multiplier':1.,'calls':[],
              'pressure':None,'cp':None,'minimum':300.,'reference':F(10**7)}
    def energy(t):
        x=F(t)-F(330.)
        if controls['mode']=='quadratic':
            return controls['reference']+500*x+2*x*x,500+4*x
        return controls['reference']+300*x,F(300)
    def evaluate(self,state,t):
        p=original(self,state,t)
        u,cv=energy(t)
        projected=float(u)
        return replace(p,total_internal_energy_j=projected,
            energy_error_j=float(F(controls['error'])+abs(F(projected)-u)),
            closed_heat_capacity_j_k=float(cv)*controls['cp_multiplier'] if controls['cp'] is None else controls['cp'],
            minimum_heat_capacity_j_k=controls['minimum'])
    monkeypatch.setattr(SourceWetStorage,'evaluate',evaluate)
    original_low=LowMoistureSorptionStorage.evaluate
    def counted(self,state,t):
        controls['calls'].append(t)
        p=original_low(self,state,t)
        return p if controls['pressure'] is None else replace(p,pressure_error_pa=controls['pressure'])
    monkeypatch.setattr(LowMoistureSorptionStorage,'evaluate',counted)
    def target(t,nc=.04):
        state=storage.state(nc,gas,0.)
        p=storage.evaluate(state,t)
        controls['calls'].clear()
        return replace(state,internal_energy_j=p.total_internal_energy_j)
    return storage,controls,target


def accepted(inv,state,policy):
    assert type(inv) is SourceWetInverse
    residual=F(inv.point.total_internal_energy_j)-F(state.internal_energy_j)
    assert inv.target_energy_j==state.internal_energy_j and inv.energy_residual_j==residual
    allowance=abs(residual)+F(inv.point.energy_error_j)
    assert allowance<=F(policy.energy_tolerance_j)
    assert F(inv.temperature_error_bound_k)>=allowance/F(inv.point.minimum_heat_capacity_j_k)
    assert F(inv.temperature_error_bound_k)<=F(policy.temperature_tolerance_k)
    assert inv.final_temperature_bracket_k[0]<=inv.point.temperature_k<=inv.final_temperature_bracket_k[1]


@pytest.mark.parametrize('mode,t,nc', [('linear',342.125,.04),('quadratic',343.12345,.04),
                                     ('linear',330.123456,0.)])
def test_full_U_same_acceptance_and_actual_call_counts(context,mode,t,nc):
    storage,c,target=context
    c['mode']=mode
    state=target(t,nc)
    policy=InversePolicy(1e-5,1e-7,100)
    new=fast.invert_low_moisture_safeguarded(storage,state,policy)
    new_calls=tuple(c['calls'])
    accepted(new,state,policy)
    assert abs(new.point.temperature_k-t)<=new.temperature_error_bound_k+math.ulp(t)
    if nc==0:
        assert new.point.excess_internal_energy_j!=0
        assert new.point.excess.mu_ex_j_mol is None
    c['calls'].clear()
    old=storage.invert(state,policy)
    old_calls=tuple(c['calls'])
    accepted(old,state,policy)
    assert len(new_calls)<len(old_calls)
    METRICS.append({'mode':mode,'target_temperature_k':t,'liquid_mol':nc,
        'new_evaluate_calls':len(new_calls),'old_evaluate_calls':len(old_calls),
        'new_temperatures_k':new_calls,'old_temperatures_k':old_calls,
        'new_iterations':new.iterations,'old_iterations':old.iterations})


@pytest.mark.parametrize('endpoint',['low','high'])
def test_near_domain_endpoints_keep_the_original_inward_support_gate(context,endpoint):
    storage,c,target=context
    bound=storage.temperature_domain_k[0 if endpoint=='low' else 1]
    t=bound+(1e-5 if endpoint=='low' else -1e-5)
    state=target(t)
    policy=InversePolicy(1e-5,1e-7,100)
    result=fast.invert_low_moisture_safeguarded(storage,state,policy)
    accepted(result,state,policy)
    assert len(c['calls'])<=5
    endpoint_state=target(bound)
    endpoint_point=storage.evaluate(endpoint_state,bound)
    assert endpoint_point.energy_error_j>0  # Full-U projection includes excess.
    c['calls'].clear()
    with pytest.raises(ValueError,match='outside_domain_or_resolution'):
        fast.invert_low_moisture_safeguarded(storage,endpoint_state,policy)
    assert len(c['calls'])==2


def test_large_error_cannot_pass_zero_nominal_residual(context):
    storage,c,target=context
    state=target(342.)
    c['error']=1e-3
    policy=InversePolicy(1e-6,1e-7,100)
    with pytest.raises(ValueError,match='unresolved'):
        fast.invert_low_moisture_safeguarded(storage,state,policy)
    with pytest.raises(ValueError,match='unresolved|unresolvable'):
        storage.invert(state,policy)


@pytest.mark.parametrize('field,value', [('error',None),('error',math.nan),
                                       ('cp',math.nan),('cp',0.),('minimum',None),
                                       ('minimum',0.),('pressure',20000.)])
def test_unknown_or_invalid_bounds_are_rejected_without_defaults(context,field,value):
    storage,c,target=context
    state=target(342.)
    if field=='error':
        # Replace only the declared result error to exercise unknown metadata;
        # production caloric source and stored U are not modified.
        original=storage.__class__.evaluate
        def invalid(self,state,t):
            return replace(original(self,state,t),energy_error_j=value)
        c['invalid_callback']=invalid
        from unittest.mock import patch
        with patch.object(LowMoistureSorptionStorage,'evaluate',invalid):
            with pytest.raises(ValueError):
                fast.invert_low_moisture_safeguarded(storage,state,InversePolicy(1e-5,1e-7,100))
    else:
        c[field]=value
        with pytest.raises(ValueError):
            fast.invert_low_moisture_safeguarded(storage,state,InversePolicy(1e-5,1e-7,100))


def test_candidate_overflow_or_endpoint_rounding_requests_bisection():
    lo,hi=330.,331.
    assert fast._interior_float(F(10**1000),lo,hi) is None
    assert fast._interior_float(F(lo)-1,lo,hi) is None
    assert fast._interior_float(F(lo)+F(1,10**100),lo,hi) is None
    assert fast._interior_float(F(661,2),lo,hi)==330.5


def test_fallback_for_outside_newton_and_forced_bracket_shrink(context):
    storage,c,target=context
    c['mode']='quadratic'
    state=target(344.321)
    # An inexact large Newton derivative can stagnate. The conservative lower
    # bound remains valid; forced bisection must still contract the bracket.
    c['cp_multiplier']=1e12
    result=fast.invert_low_moisture_safeguarded(storage,state,InversePolicy(1e-5,1e-7,120))
    accepted(result,state,InversePolicy(1e-5,1e-7,120))
    calls=tuple(c['calls'])
    assert len(calls)<=122
    lo,hi=storage.temperature_domain_k
    for iteration,t in enumerate(calls[2:],1):
        if iteration%3==0:
            assert t==float((F(lo)+F(hi))/2)
        p=storage.evaluate(state,t)
        if F(p.total_internal_energy_j)>F(state.internal_energy_j):
            hi=t
        else:
            lo=t
        if t==result.point.temperature_k:
            break


def test_type_and_iteration_limit_are_explicit(context):
    storage,c,target=context
    state=target(344.321)
    with pytest.raises(ValueError,match='actual_low_moisture_storage'):
        fast.invert_low_moisture_safeguarded(storage.base,state,InversePolicy(1e-5,1e-7,100))
    with pytest.raises(ValueError,match='explicit_inverse_policy'):
        fast.invert_low_moisture_safeguarded(storage,state,object())
    c['mode']='quadratic'
    state=target(344.321)
    with pytest.raises(ValueError,match='iteration_limit'):
        fast.invert_low_moisture_safeguarded(storage,state,InversePolicy(1e-12,1e-12,1))
