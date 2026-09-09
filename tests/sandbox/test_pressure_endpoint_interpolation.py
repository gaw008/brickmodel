"""Explicit analytic liquid provider, no native EOS."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from sludge_sandbox import rigid_water_gas as m
from sludge_sandbox.verification_case import encode


class Liquid:
    source_ids=('analytic-liquid',)
    source_asset_sha256={}
    reference=SimpleNamespace(native_molar_gas_constant_j_mol_k=m._R)
    def __init__(self,slope=0.,fail=None):self.calls=[];self.slope=slope;self.fail=fail
    def state_tp(self,t,p,*,phase):
        self.calls.append(p)
        if len(self.calls)==self.fail:raise m.WaterNumericalError('injected')
        return SimpleNamespace(molar_mass_kg_mol=1.,density_kg_m3=1./(1e-5-self.slope*p))


def model(monkeypatch,water, strategy=None, maximum=100):
    monkeypatch.setattr(m,'is_water_provider',lambda value:value is water)
    return m.RigidWaterGas(water,('gas',),1e-3,(1e4,1e6),m._ASSUMPTION,
        m.PressurePolicy(1e-13,1e-5,maximum,strategy=strategy))


def test_default_codec_unchanged(monkeypatch):
    p=m.PressurePolicy(1e-13,1e-5,100)
    assert 'strategy' not in encode(p)


def test_constant_liquid_accelerates_with_real_bracket_gate(monkeypatch):
    old=Liquid();baseline=model(monkeypatch,old).evaluate_at_temperature(300.,1.,{'gas':.01})
    water=Liquid();result=model(monkeypatch,water,'guarded_liquid_endpoint_interpolation_v1').evaluate_at_temperature(300.,1.,{'gas':.01})
    root=.01*m._R*300/(1e-3-1e-5)
    lo,hi=result.final_numerical_pressure_bracket_pa
    assert lo<=root<=hi and hi-lo<=1e-5
    assert abs(result.pressure_pa-root)<=1e-5
    assert len(water.calls)<len(old.calls)
    assert len(result.pressure_trial_ledger)==len(water.calls)
    assert result.iterations<=100
    assert baseline.pressure_trial_ledger is None


def test_failed_actual_call_retains_attempted_ledger(monkeypatch):
    water=Liquid(fail=3)
    with pytest.raises(m.RigidClosureNumericalError) as caught:
        model(monkeypatch,water,'guarded_liquid_endpoint_interpolation_v1').evaluate_at_temperature(300.,1.,{'gas':.01})
    assert len(caught.value.pressure_trial_ledger)==3
    assert caught.value.pressure_trial_ledger[-1].status=='failed'


def test_budget_counts_trials(monkeypatch):
    water=Liquid(slope=1e-12)
    with pytest.raises(m.RigidClosureNumericalError):
        model(monkeypatch,water,'guarded_liquid_endpoint_interpolation_v1',maximum=1).evaluate_at_temperature(300.,1.,{'gas':.01})
    assert len(water.calls)<=3


@pytest.mark.parametrize('slope',[0.,1e-13,5e-12])
def test_monotone_analytic_root_and_complete_bracket_ledger(monkeypatch,slope):
    from decimal import Decimal,localcontext
    water=Liquid(slope=slope)
    result=model(monkeypatch,water,'guarded_liquid_endpoint_interpolation_v1').evaluate_at_temperature(300.,1.,{'gas':.01})
    # Independent quadratic: slope*p^2 + (V-v0)*p - NgRT = 0.
    with localcontext() as ctx:
        ctx.prec=60
        c=Decimal.from_float(.01*m._R*300.)
        b=Decimal.from_float(1e-3)-Decimal.from_float(1e-5)
        a=Decimal.from_float(slope)
        root=c/b if not a else 2*c/(b+(b*b+4*a*c).sqrt())
    assert abs(result.pressure_pa-float(root))<=1e-5
    assert len(water.calls)==result.iterations+2
    previous=(1e4,1e6)
    for index,row in enumerate(result.pressure_trial_ledger):
        assert row.bracket_before_pa==previous
        if index>=2:
            lo,hi=row.bracket_before_pa
            assert lo<row.pressure_pa<hi
            flo,fhi=row.residuals_before_m3
            assert flo>=row.residual_m3>=fhi
            if row.status=='bracket_updated':
                expected=(row.pressure_pa,hi) if row.residual_m3>0 else (lo,row.pressure_pa)
                assert row.bracket_after_pa==expected
                previous=expected
            else:
                assert row.status=='finished' and hi-lo<=1e-5
        assert row.liquid_volume_m3>0
    with pytest.raises(Exception):result.pressure_trial_ledger[0].status='altered'


@pytest.mark.parametrize('value',['bisection','brent',True,{},1])
def test_unknown_strategy_refused(value):
    with pytest.raises(m.RigidClosureDomainError,match='strategy'):
        m.PressurePolicy(1e-13,1e-5,100,strategy=value)


def test_pure_gas_does_not_call_liquid(monkeypatch):
    water=Liquid(fail=1)
    result=model(monkeypatch,water,'guarded_liquid_endpoint_interpolation_v1').evaluate_at_temperature(300.,0.,{'gas':.01})
    assert water.calls==[] and result.pressure_trial_ledger==()
    assert result.pressure_solution_path=='pure_gas_analytic_rounded'


def test_nonmonotone_trial_not_silently_retried(monkeypatch):
    class Bad(Liquid):
        def state_tp(self,t,p,*,phase):
            result=super().state_tp(t,p,phase=phase)
            if len(self.calls)==3:result.density_kg_m3=1.
            return result
    water=Bad()
    with pytest.raises(m.RigidClosureNumericalError,match='nonmonotonic') as caught:
        model(monkeypatch,water,'guarded_liquid_endpoint_interpolation_v1').evaluate_at_temperature(300.,1.,{'gas':.01})
    assert len(water.calls)==3
    assert caught.value.pressure_trial_ledger[-1].status=='failed'


def test_default_matches_original_module_outputs_and_calls(monkeypatch):
    # Saved original source is not needed: default recorded midpoint sequence
    # independently obeys original bisection regardless of interpolation API.
    water=Liquid();out=model(monkeypatch,water).evaluate_at_temperature(300.,1.,{'gas':.01})
    lo,hi=1e4,1e6
    for index,p in enumerate(water.calls[2:]):
        assert p==lo+(hi-lo)/2
        residual=__import__('math').fsum((1e-5,.01*m._R*300/p,-1e-3))
        if index==len(water.calls)-3:break
        if residual>0:lo=p
        else:hi=p
    assert out.final_numerical_pressure_bracket_pa==(lo,hi)
    assert 'pressure_trial_ledger' not in encode(out)
