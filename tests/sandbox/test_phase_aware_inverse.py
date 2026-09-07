from dataclasses import replace,FrozenInstanceError
import numpy as np
import pytest
from sludge_sandbox.solid_fluid_heat import SolidFluidHeatError
from sludge_sandbox.integration import DomainExit,IntegrationError
from test_joined_water_host import ingredients,joined,host


def phase_host(ingredients,joined):
    base=host(ingredients,joined,500.)
    fluid=base.storages[0].fluid_template
    fluid=replace(fluid,envelope=replace(fluid.envelope,temperature_range_k=(295.,510.)))
    storage=replace(base.storages[0],fluid_template=fluid)
    return replace(base,storages=(storage,),transport=replace(base.transport,storages=(fluid,),temperature_brackets_k=((295.,310.),)))


def policy_host(ingredients,joined):
    return replace(phase_host(ingredients,joined),dry_temperature_brackets_k=((295.,510.),),
        inverse_bracket_policy_id='test:phase-selection',inverse_bracket_policy_version='1',
        inverse_bracket_policy_reason='Select broad dry bracket without probing liquid EOS above its domain.')


def test_actual_wet_and_dry_inverse_share_one_host_without_energy_changes(ingredients,joined):
    base=phase_host(ingredients,joined)
    dry=base.state_from_temperatures([[2.,.01,0.,0.]],[502.])
    with pytest.raises(DomainExit):base.decode(dry)
    op=policy_host(ingredients,joined)
    wet=op.state_from_temperatures([[2.,1e-5,1.,.01]],[300.])
    for state,expected,bracket in ((wet,300.,(295.,310.)),(dry,502.,(295.,510.))):
        before=np.array(state.internal_energy_j)
        result=op.evaluate(state,0.)
        assert result.storage_states[0].mechanical.temperature_k==pytest.approx(expected,rel=0,abs=2e-5)
        assert result.temperature_brackets_k==(bracket,)
        assert result.inverse_bracket_policy_id=='test:phase-selection'
        assert np.array_equal(before,state.internal_energy_j)
    assert op.temperature_brackets_for(wet)==((295.,310.),)
    with pytest.raises(FrozenInstanceError):op.dry_temperature_brackets_k=None


@pytest.mark.parametrize('changes',[{'dry_temperature_brackets_k':()},
    {'dry_temperature_brackets_k':((510.,295.),)}, {'dry_temperature_brackets_k':((295.,float('inf')),)},
    {'inverse_bracket_policy_id':''},{'inverse_bracket_policy_version':''},{'inverse_bracket_policy_reason':''}])
def test_explicit_numerical_policy_contract(ingredients,joined,changes):
    with pytest.raises(SolidFluidHeatError):replace(policy_host(ingredients,joined),**changes)


def test_nonzero_liquid_never_selects_dry_and_domains_remain_checked(ingredients,joined):
    op=policy_host(ingredients,joined)
    state=op.state_from_temperatures([[2.,1e-5,1e-12,.01]],[300.])
    assert op.temperature_brackets_for(state)==op.transport.temperature_brackets_k
    dry=op.state_from_temperatures([[2.,.01,0.,0.]],[502.])
    outside=replace(op,dry_temperature_brackets_k=((295.,2100.),))
    with pytest.raises(DomainExit):outside.decode(dry)


def test_mixed_cells_select_independently_and_default_replace_stays_implicit(ingredients):
    from test_solid_fluid_heat import solid_host
    from sludge_sandbox.integration import ConservedState
    single=solid_host(ingredients)
    two=solid_host(ingredients,cells=2)
    default=replace(single,storages=two.storages,transport=two.transport)
    assert default.dry_temperature_brackets_k is None
    op=replace(default,dry_temperature_brackets_k=((296.,309.),(297.,308.)),
        inverse_bracket_policy_id='test:mixed',inverse_bracket_policy_version='1',inverse_bracket_policy_reason='Selection test.')
    state=ConservedState([[2.,1e-5,1e-100,.01],[2.,1e-5,0.,.01]],[0.,0.])
    assert op.temperature_brackets_for(state)==((295.,310.),(297.,308.))
    with pytest.raises(SolidFluidHeatError):replace(op,storages=single.storages,transport=single.transport)
