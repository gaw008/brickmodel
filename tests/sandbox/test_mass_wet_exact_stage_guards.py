from dataclasses import replace
from fractions import Fraction as F
import pytest
from test_mass_wet_exact_stage import setup,run,policy
from sludge_sandbox.mass_wet_transport import WetPair


def test_wet_without_global_temperature_volume_contract_is_unavailable(monkeypatch):
    pair,states=setup(monkeypatch)
    from sludge_sandbox.mass_wet_exact_stage import try_step_doubling
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    result=try_step_doubling(pair,states,start=T(F()),end=T(F(1,1000)),policy=policy())
    assert result.status=='failed' and result.reason=='pressure_temperature_envelope_unavailable'


@pytest.mark.parametrize('failure_at',[3,9])
def test_failed_endpoint_keeps_prepared_state_and_ledger(monkeypatch,failure_at):
    pair,states=setup(monkeypatch);old=WetPair.evaluate;calls=[0]
    def fail(self,state):
        calls[0]+=1
        if calls[0]==failure_at:raise ValueError('endpoint_failure')
        return old(self,state)
    monkeypatch.setattr(WetPair,'evaluate',fail)
    r=run(pair,states)
    assert r.status=='failed' and r.evaluations_attempted==failure_at
    assert r.endpoint_attempts[-1].endpoint_state and r.endpoint_attempts[-1].ledger
    assert len(r.steps)==failure_at//3-1 and r.candidate_state is None


def test_temperature_pressure_interval_contains_exact_analytic_corners(monkeypatch):
    from test_mass_wet_exact_stage import fixture
    from sludge_sandbox.mass_wet_exact_stage import pressure_radius
    pair,states=setup(monkeypatch);inverse=pair.evaluate(states).cells[0].inverse
    inverse=replace(inverse,temperature_error_bound_k=.01)
    radius=pressure_radius(pair,states[0],inverse,0,fixture(pair))
    st=pair.storages[0];s=states[0];p=F(inverse.point.pressure_pa)
    volume=F(st.bulk_volume_m3)-sum((F(m)*F(v.volume_m3_kg) for m,v in zip(s.solid_mass_kg,st.solids)),F())-F(s.liquid_water_mol)*F(1.8e-5)
    nr=sum(map(F,s.gas_amounts_mol),F())*F(st.fluid_template.mechanical.gas_constant_j_mol_k)
    for sign in (-1,1):
        true_p=nr*(F(inverse.point.temperature_k)+sign*F(.01))/volume
        assert abs(true_p-p)<=radius
    assert radius>F(inverse.point.pressure_error_pa)*100


def test_native_method_cannot_be_declared_constant_fixture(monkeypatch):
    from test_mass_wet_exact_stage import fixture
    pair,states=setup(monkeypatch)
    fn=pair.storages[0].water.state_tp.__func__
    monkeypatch.setattr(fn,'__module__','sludge_sandbox.water_properties')
    with pytest.raises(ValueError,match='native_liquid'):fixture(pair)


def test_fixture_declaration_drift_refuses_before_callbacks(monkeypatch):
    from test_mass_wet_exact_stage import fixture
    from sludge_sandbox.mass_wet_exact_stage import try_step_doubling
    from sludge_sandbox.exact_event_clock import ExactEventTime as T
    pair,states=setup(monkeypatch);contract=fixture(pair)
    monkeypatch.setattr(pair.storages[0].water.state_tp.__func__,'constant_volume_m3_mol',F(2e-5))
    r=try_step_doubling(pair,states,start=T(F()),end=T(F(1,1000)),policy=policy(),constant_liquid_fixture=contract)
    assert r.status=='failed' and r.evaluations_attempted==0 and r.candidate_state is None
