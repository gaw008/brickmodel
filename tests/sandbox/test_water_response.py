"""Local derivative checks against independent TP finite differences."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import math

import pytest

from sludge_sandbox.water_properties import load_water_properties, WaterDomainError, WaterNumericalError

pytest.importorskip('iapws')
DATA=Path(__file__).resolve().parents[2]/'data/sandbox/water'

@pytest.fixture
def water():return load_water_properties(DATA)

CASES=[(300.,1e5,'liquid'),(350.,1e6,'liquid'),(450.,1e7,'liquid'),(499.,9e7,'liquid'),
       (300.,1e3,'vapor'),(400.,1e5,'vapor'),(499.,1e5,'vapor')]

@pytest.mark.parametrize('t,p,phase',CASES)
def test_response_matches_independent_finite_differences(water,t,p,phase):
    response=water.state_tp_response(t,p,phase=phase)
    state=response.state
    def v(x):return x.molar_mass_kg_mol/x.density_kg_m3
    dt=.01;dp=max(1.,1e-4*p)
    tplus=water.state_tp(t+dt,p,phase=phase);tminus=water.state_tp(t-dt,p,phase=phase)
    pplus=water.state_tp(t,p+dp,phase=phase);pminus=water.state_tp(t,p-dp,phase=phase)
    dvdt=(v(tplus)-v(tminus))/(2*dt)
    dvdp=(v(pplus)-v(pminus))/(2*dp)
    dudp=(pplus.internal_energy_j_mol-pminus.internal_energy_j_mol)/(2*dp)
    assert response.molar_dv_dt_m3_mol_k==pytest.approx(dvdt,rel=2e-5,abs=1e-13)
    assert response.molar_dv_dp_m3_mol_pa==pytest.approx(dvdp,rel=2e-5,abs=1e-17)
    assert response.molar_du_dp_j_mol_pa==pytest.approx(dudp,rel=2e-4,abs=1e-8)
    assert abs(response.cp_cv_identity_residual_j_mol_k)<=1e-7
    assert response.isothermal_compressibility_pa_inverse>0
    assert response.molar_dv_dp_m3_mol_pa<0
    assert response.source_ids==state.source_ids
    assert response.derivative_scope=='local_state_sensitivity_not_interval_bound'
    assert state==water.state_tp(t,p,phase=phase)


def test_response_is_immutable(water):
    response=water.state_tp_response(300,1e5,phase='liquid')
    with pytest.raises(FrozenInstanceError):response.thermal_expansion_k_inverse=0

@pytest.mark.parametrize('t,p,phase',[(292.,1e5,'liquid'),(501.,1e5,'vapor'),(300.,0,'liquid'),(300.,1e8+1,'liquid'),(500.,1e5,'liquid')])
def test_original_domain_remains_enforced(water,t,p,phase):
    with pytest.raises(WaterDomainError):water.state_tp_response(t,p,phase=phase)

@pytest.mark.parametrize('field,value',[('fird',math.nan),('firdd',math.inf),('firdt',math.nan),('firdt',1e300)])
def test_invalid_response_derivatives_rejected(water,monkeypatch,field,value):
    # Isolate the new response gate from the already-tested state gate.
    verified=water.state_tp(300,1e5,phase='liquid')
    monkeypatch.setattr(type(water),'state_tp',lambda *_args,**_kwargs:verified)
    original=water._model._phir
    def corrupt(*args):return original(*args)|{field:value}
    monkeypatch.setattr(water._model,'_phir',corrupt)
    with pytest.raises(WaterNumericalError):water.state_tp_response(300,1e5,phase='liquid')


@pytest.mark.parametrize('field,value',[('temperature_k',301.),('pressure_pa',2e5),('phase','vapor')])
def test_response_rejects_wrong_returned_state_identity(water,monkeypatch,field,value):
    from dataclasses import replace
    state=water.state_tp(300,1e5,phase='liquid')
    monkeypatch.setattr(type(water),'state_tp',lambda *_args,**_kwargs:replace(state,**{field:value}))
    with pytest.raises(WaterNumericalError,match='identity'):water.state_tp_response(300,1e5,phase='liquid')


def test_finite_but_inconsistent_derivative_fails_identity(water,monkeypatch):
    state=water.state_tp(300,1e5,phase='liquid')
    monkeypatch.setattr(type(water),'state_tp',lambda *_args,**_kwargs:state)
    original=water._model._phir
    def corrupt(*args):
        value=original(*args)
        return value|{'firdt':float(value['firdt'])+.1}
    monkeypatch.setattr(water._model,'_phir',corrupt)
    with pytest.raises(WaterNumericalError,match='identity'):water.state_tp_response(300,1e5,phase='liquid')
