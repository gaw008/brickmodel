"""Unsupported hosts must not silently replace a dynamic geometry with old geometry."""
from dataclasses import replace
import math
import numpy as np
import pytest
from sludge_sandbox.integration import ConservedState
from test_rigid_storage import water


def test_prescribed_host_rejects_dynamic_geometry_before_inverse(water, monkeypatch):
    from test_deforming_solid_heat import host
    op=host(water)
    monkeypatch.setattr(type(water), 'state_tp', lambda *a,**k: pytest.fail('unexpected EOS'))
    state=ConservedState([[0.,.01,2.]],[1.],op.energy_model_identity,
                         mechanical_stretches=[1.,1.])
    with pytest.raises(ValueError, match='unsupported_mechanical_state'):
        op.evaluate(state,0.)


def test_fixed_geometry_hosts_reject_dynamic_state_before_decode(water, monkeypatch):
    from test_gas_heat_model import model
    from test_deforming_solid_heat import host
    base=host(water).base_model
    monkeypatch.setattr(type(water), 'state_tp', lambda *a,**k: pytest.fail('unexpected EOS'))
    for op,cells in ((model(),2),(base,1),(base.transport,1)):
        state=ConservedState(np.zeros((cells,len(op.species_order))),np.zeros(cells),
                             mechanical_stretches=np.ones(cells+1))
        with pytest.raises(ValueError, match='unsupported_mechanical_state'):
            op.evaluate(state,0.)


def test_depletion_entry_requires_mechanical_scales_before_callback():
    from test_depletion_spine import configured,oracle,initial
    from sludge_sandbox.depletion_integration import integrate_depletion
    p,e=configured();op,counts=oracle(0.)
    state=replace(initial(),mechanical_stretches=[1.,1.])
    with pytest.raises(ValueError,match='finite_depletion_policy_required'):
        integrate_depletion(state,op,start_s=0.,end_s=.2,integration_policy=p,event_policy=e)
    assert counts['calls']==0


def test_inventory_roundoff_writeback_preserves_mechanics():
    from sludge_sandbox.depletion_roundoff import depletion_writeback,DepletionRoundoffTotals
    from test_depletion_roundoff import policy
    p=policy();delta=math.ulp(.01)/2
    old=ConservedState([[delta,.1,7.]],[12.],mechanical_stretches=[.9,1.1])
    state,_,_=depletion_writeback(old,cell_index=0,liquid_index=0,vapor_index=1,
        panel_liquid_start_mol=.01,panel_liquid_terms_mol=(-.01,delta),
        positive_evaporated_mol=.01,policy=p,totals=DepletionRoundoffTotals(p))
    assert state.mechanical_stretches.tobytes()==old.mechanical_stretches.tobytes()
