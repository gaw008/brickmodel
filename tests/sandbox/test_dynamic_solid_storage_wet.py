"""Bounded native-water point validation, independent coupled P/E construction."""
from dataclasses import replace
from decimal import Decimal as D,localcontext
import math
import pytest
from scipy.optimize import brentq
from sludge_sandbox.dynamic_solid_storage import DynamicSolidStorage,DynamicStorageErrorBounds
from sludge_sandbox.phase_storage import InversePolicy
from test_deforming_solid_storage import build,exact_volume_wet_model
from test_rigid_storage import water,R


@pytest.mark.parametrize('normal,tangent',[(.97,.99),(.9,.95)])
def test_native_wet_inverse_against_independent_pressure_and_energy(water,normal,tangent):
    # Existing exact-rational manufactured volume fixture; the original broader
    # solid-volume uncertainty remains covered by the explicit refusal test below.
    original=exact_volume_wet_model(water)
    point=DynamicSolidStorage(template=original.template,
        skeleton=replace(original.skeleton,viscosity_pa_s=1e6),
        error_bounds=DynamicStorageErrorBounds((.5,2.),(.5,2.),0.,0.,
          ('manufactured-numerical-envelope',),'manufactured-not-material-data'),
        model_id='wet-dynamic-point',version='1',allow_manufactured=True)
    with localcontext() as context:
        context.prec=100
        n,t=D.from_float(normal),D.from_float(tangent)
        bulk=float(D.from_float(.01)*D.from_float(.014)*n*t*t)
        theta=n.ln()+2*t.ln()
        elastic=D.from_float(point.skeleton.reference_volume_m3)*(500*theta**2+
            400*((n.ln()-theta/3)**2+2*(t.ln()-theta/3)**2))
        surface=D.from_float(.5)*D.from_float(.003)*t*t
        recoverable=float(elastic+surface)
    def volume_residual(pressure):
        liquid=water.state_tp(300.,pressure,phase='liquid')
        return water.reference.molar_mass_kg_mol/liquid.density_kg_m3+.01*R*300./pressure+4e-5-bulk
    pressure=brentq(volume_residual,1e4,1e6,xtol=1e-7,rtol=8*math.ulp(1.))
    assert abs(volume_residual(pressure))<1e-12
    liquid=water.state_tp(300.,pressure,phase='liquid')
    target=liquid.internal_energy_j_mol+.01*(30.-R)*300.+2*(-100000+5*300.-2)+recoverable
    result=point.temperature_from_total_energy(point.target(target,1e-8),
        normal_stretch=normal,tangential_stretch=tangent,liquid_mol=1.,
        gas_mol={'fixture':.01},solid_mol={'fixture_solid':2.},external_pressure_pa=101325.,
        temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100))
    state=result.state;mechanical=state.thermal_state.mechanical
    assert abs(mechanical.temperature_k-300.)<=result.temperature_error_bound_k
    assert result.temperature_error_bound_k<=1e-6
    assert abs(mechanical.pressure_pa-pressure)<.2
    assert abs(result.total_energy_residual_j)<1e-6
    assert state.free_rates.pore_pressure_pa==mechanical.pressure_pa
    assert state.free_rates.zero_balance_enclosed
    assert state.skeleton_state.normal_rate_per_s==0.
    assert state.skeleton_state.tangential_rate_per_s==0.
    assert any(rate!=0. for rate in state.free_rates.rates)


def test_original_solid_volume_uncertainty_still_refuses_precision(water):
    original=build(water)
    point=DynamicSolidStorage(template=original.template,
        skeleton=replace(original.skeleton,viscosity_pa_s=1e6),
        error_bounds=DynamicStorageErrorBounds((.5,2.),(.5,2.),0.,0.,('original-envelope',),
          'manufactured-not-material-data'),model_id='broad-envelope',version='1',allow_manufactured=True)
    values=dict(normal_stretch=.97,tangential_stretch=.99,liquid_mol=1.,gas_mol={'fixture':.01},
                solid_mol={'fixture_solid':2.},external_pressure_pa=101325.)
    forward=point.forward(300.,**values)
    assert forward.energy_error_bound_j>1e-6
    with pytest.raises(ValueError,match='exceeds_inverse_tolerance'):
        point.temperature_from_total_energy(point.target(forward.total_energy_j,0.),**values,
            temperature_bracket_k=(295.,310.),policy=InversePolicy(1e-6,1e-6,100))
