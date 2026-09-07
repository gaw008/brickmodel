"""Real water phase transfer with explicit solid columns and heat capacity."""
from dataclasses import replace
import math
import numpy as np
import pytest
from sludge_sandbox.integration import IntegrationPolicy,integrate
from test_solid_fluid_heat import solid_host,ingredients
from test_water_phase_transfer import transfer


def test_real_solid_water_phase_transfer_conserves_and_responds_to_solid_cp(ingredients):
    intervals=[]
    for cp in (10.,100.):
        host=solid_host(ingredients,cp=cp)
        op=replace(transfer(ingredients),base_model=host)
        initial=host.state_from_temperatures([[2.,1e-5,2.,.01]],[300.])
        rates=op.evaluate(initial,0).rates
        assert rates.reaction_species_mol_s[0,0]==0
        assert rates.reaction_species_mol_s[0,1]>0
        assert rates.reaction_species_mol_s[0,2]==-rates.reaction_species_mol_s[0,1]
        run=integrate(initial,op,start_s=0,end_s=.001,policy=IntegrationPolicy(
            initial_step_s=.001,maximum_step_s=.001,minimum_step_s=1e-10,relative_tolerance=1e-7,
            amount_absolute_tolerance_mol=1e-10,energy_absolute_tolerance_j=1e-5,
            amount_scale_mol=.001,energy_scale_j=1.,maximum_steps=10,maximum_rejections=10,maximum_wall_seconds=90))
        assert run.status=='completed',run.reason
        for state in run.states:
            assert state.amounts_mol[0,0]==2.
            assert state.amounts_mol[0,3]==.01
            assert math.fsum(state.amounts_mol[0,[1,2]])==pytest.approx(2.00001,rel=0,abs=1e-12)
            assert state.internal_energy_j[0]==pytest.approx(initial.internal_energy_j[0],rel=0,abs=1e-7)
        inverse=host.decode_inverse(run.states[-1])[0]
        temperature=inverse.state.mechanical.temperature_k
        error=inverse.temperature_error_bound_k
        intervals.append((temperature-error,temperature+error))
    assert intervals[0][1]<intervals[1][0]
    assert intervals[1][1]<300.


def test_explicit_liquid_index_rejects_missing_interface_before_decode(ingredients):
    from sludge_sandbox.integration import ConservedState,DomainExit
    host=solid_host(ingredients)
    op=replace(transfer(ingredients),base_model=host)
    with pytest.raises(DomainExit,match='liquid_interface'):
        op(ConservedState([[2.,1e-5,0.,.01]],[0.]),0)


def test_manufactured_host_requires_wrapper_opt_in(ingredients):
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransferError
    host=solid_host(ingredients)
    with pytest.raises(WaterPhaseTransferError,match='manufactured'):
        replace(transfer(ingredients),base_model=host,allow_manufactured=False)
