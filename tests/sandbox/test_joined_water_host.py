"""Actual fixed-solid/full-water-vapor host, not only phase point samples."""
from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path
import math
import numpy as np
import pytest
from scipy.optimize import brentq

from sludge_sandbox.joined_water_vapor import JoinedWaterVapor
from sludge_sandbox.phase_storage import IdealGasPhase,InversePolicy
from sludge_sandbox.integration import Rates,IntegrationPolicy,integrate,DomainExit
from test_solid_fluid_heat import ingredients,solid_host

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def joined():
    return JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
        low_enthalpy_error_j_mol=1e-3,numerical_error_source_ids=('manufactured:declared-low-water-error',))


def host(ingredients,joined,center):
    base=solid_host(ingredients)
    s=base.storages[0];fluid=s.fluid_template
    vapor=IdealGasPhase(joined,joined.molar_mass_kg_mol)
    fluid=replace(fluid,gas_phases={'fixture':fluid.gas_phases['fixture'],'H2O':vapor},
        mechanical=replace(fluid.mechanical,pressure_bracket_pa=(1e4,1e7)),
        envelope=replace(fluid.envelope,temperature_range_k=(max(293.,center-10),center+10),pressure_range_pa=(1e4,1e7),
            gas_u_error_j_mol={'fixture':1e-9,'H2O':.002},gas_cv_lower_j_mol_k={'fixture':20.,'H2O':20.}))
    solid=s.solid_phases['fixture_solid']
    solid=replace(solid,caloric=replace(solid.caloric,temperature_range_k=(290.,2000.)))
    s=replace(s,fluid_template=fluid,solid_phases={'fixture_solid':solid})
    transport=replace(base.transport,storages=(fluid,),temperature_brackets_k=((max(293.,center-10),center+10),),
        inverse_policy=InversePolicy(5e-5,1e-6,100))
    return replace(base,storages=(s,),transport=transport)


def independent_u(joined,t):
    # High branch independent source-coefficient Decimal integral from the exact
    # real 500 K low anchor. Low branch remains the separately tested water EOS.
    if t<=500:h=joined.low_model.enthalpy_j_mol(t)
    else:
        with localcontext() as ctx:
            ctx.prec=60
            h=Decimal.from_float(joined.low_model.enthalpy_j_mol(500.))
            start=500.
            for segment in joined.source_gas.segments:
                a,b=segment.temperature_range_k
                if t<=a:break
                end=min(t,b)
                aa,bb,cc,dd,ee,*_=map(Decimal.from_float,segment.coefficients)
                def primitive(temp):
                    x=Decimal.from_float(temp)/1000
                    return 1000*(aa*x+bb*x*x/2+cc*x**3/3+dd*x**4/4-ee/x)
                if end>start:h+=primitive(end)-primitive(start)
                start=end
                if t<=b:break
            h=float(h)
    return 2*(-100000+50*t-1e5*1e-6)+.01*(h-joined.gas_constant_j_mol_k*t)


@pytest.mark.parametrize('center,start,sign',[(500.,498.,1),(500.,502.,-1),(1700.,1698.,1),(1700.,1702.,-1)])
def test_actual_host_power_crosses_caloric_seam_with_water_inventory(ingredients,joined,center,start,sign):
    op=host(ingredients,joined,center)
    initial=op.state_from_temperatures([[2.,.01,0.,0.]],[start])
    trials=[]
    def powered(state,t):
        base=op.evaluate(state,t)
        trials.append(base.storage_states[0].mechanical.temperature_k)
        return Rates(base.rates.face_species_mol_s,base.rates.face_energy_w,base.rates.reaction_species_mol_s,np.array([sign*100.]))
    result=integrate(initial,powered,start_s=0,end_s=4.,policy=IntegrationPolicy(initial_step_s=.25,maximum_step_s=.25,
        minimum_step_s=1e-10,relative_tolerance=1e-8,amount_absolute_tolerance_mol=1e-11,energy_absolute_tolerance_j=1e-5,
        amount_scale_mol=.01,energy_scale_j=1.,maximum_steps=100,maximum_rejections=20,maximum_wall_seconds=90))
    assert result.status=='completed',(result.status,result.reason)
    expected=brentq(lambda t:independent_u(joined,t)-independent_u(joined,start)-sign*400.,center-9,center+9,xtol=1e-9)
    final=op.decode(result.states[-1])[0]
    assert final.mechanical.temperature_k==pytest.approx(expected,rel=0,abs=2e-5)
    assert min(trials)<center<max(trials)
    for i,(time,state) in enumerate(zip(result.times_s,result.states)):
        assert np.array_equal(state.amounts_mol,initial.amounts_mol)
        assert state.internal_energy_j[0]-initial.internal_energy_j[0]==pytest.approx(sign*100*time,rel=0,abs=1e-7)
    assert math.fsum(step.cell_work_j[0] for step in result.steps)==pytest.approx(sign*400,rel=0,abs=1e-7)


@pytest.mark.parametrize('center,temperature',[(300.,298.),(500.,502.),(1700.,1702.)])
def test_runtime_joined_error_contract_rejects_insufficient_gas_budget(ingredients,joined,center,temperature):
    from sludge_sandbox.rigid_storage import RigidStorageError
    op=host(ingredients,joined,center)
    storage=op.storages[0].fluid_template
    bad=replace(storage,envelope=replace(storage.envelope,gas_u_error_j_mol={'fixture':1e-9,'H2O':1e-9}))
    with pytest.raises(RigidStorageError,match='joined_water_numerical_error'):
        bad.evaluate_at_temperature(temperature,0.,{'fixture':0.,'H2O':.01})


def test_joined_low_phase_transfer_matches_and_high_dry_gate_is_unchanged(ingredients,joined):
    from sludge_sandbox.water_phase_transfer import WaterPhaseTransfer
    def transfer(base,k):
        return WaterPhaseTransfer(base_model=base,chemical=ingredients[2],coefficients_mol_s_pa=(k,),
            coefficient_set_id='manufactured:joined-phase',coefficient_version='1',
            coefficient_classification='manufactured_test_fixture',coefficient_source_ids=('manufactured:joined-phase',),allow_manufactured=True)
    low=host(ingredients,joined,300.)
    state=low.state_from_temperatures([[2.,1e-5,1.,.01]],[300.])
    out=transfer(low,1e-7).evaluate(state,0.)
    assert out.cell_transfers[0].rate_mol_s>0
    assert out.cell_transfers[0].equilibrium.liquid.state.temperature_k==pytest.approx(300.,rel=0,abs=1e-6)
    high=host(ingredients,joined,1700.)
    dry=high.state_from_temperatures([[2.,.01,0.,0.]],[1702.])
    with pytest.raises(DomainExit,match='liquid_interface'):transfer(high,1e-7).evaluate(dry,0.)
    disabled=transfer(high,0.).evaluate(dry,0.)
    assert disabled.cell_transfers[0].status=='disabled'
    # Positive liquid still cannot use high joined gas range as liquid EOS range.
    with pytest.raises(DomainExit):high.state_from_temperatures([[2.,.01,1.,0.]],[1702.])


def test_joined_mass_segment_and_full_reaction_identity(ingredients,joined):
    from sludge_sandbox.phase_storage import PhaseStorageError,LiquidWaterPhase
    from sludge_sandbox.reactions import ReactionNetwork,ReactionDefinition,SpeciesDefinition
    from sludge_sandbox.solid_reactions import SolidReactionConfig,ReactionSpeciesBinding,SolidReactionError
    from test_reactions import kinetics
    with pytest.raises(PhaseStorageError):IdealGasPhase(joined,joined.molar_mass_kg_mol*1.01)
    with pytest.raises(PhaseStorageError):IdealGasPhase(joined,joined.molar_mass_kg_mol,0)
    op=host(ingredients,joined,300.);storage=op.storages[0]
    mass=joined.molar_mass_kg_mol
    definitions=tuple(SpeciesDefinition(n,p,{'H':2,'O':1},mass,('manufactured:joined-alias',),'manufactured')
        for n,p in [('liquid_alias','liquid'),('gas_alias','gas')])
    law=kinetics({'liquid_alias':1},gas_constant_j_mol_k=joined.gas_constant_j_mol_k,temperature_range_k=(293.,500.))
    net=ReactionNetwork(definitions,(ReactionDefinition('phase','1',{'liquid_alias':-1,'gas_alias':1},law,'other',('manufactured:joined-alias',)),),True)
    bindings=(ReactionSpeciesBinding('liquid_alias','H2O_liquid',LiquidWaterPhase(storage.fluid_template.mechanical.water)),
        ReactionSpeciesBinding('gas_alias','H2O',storage.fluid_template.gas_phases['H2O']))
    cfg=SolidReactionConfig(network=net,bindings=bindings,storages=(storage,),inventory_layout=op.inventory_layout,
        allow_manufactured=True,binding_id='manufactured:joined',version='1',source_ids=('manufactured:joined',))
    another=JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
        low_enthalpy_error_j_mol=1e-3,numerical_error_source_ids=('manufactured:declared-low-water-error',))
    replace(cfg,bindings=(bindings[0],replace(bindings[1],provider=IdealGasPhase(another,mass))))
    changed=JoinedWaterVapor(ROOT/'data/sandbox/water',ROOT/'data/sandbox/thermochemistry',
        low_enthalpy_error_j_mol=.002,numerical_error_source_ids=('manufactured:changed-water-error',))
    with pytest.raises(SolidReactionError,match='provider_identity'):
        replace(cfg,bindings=(bindings[0],replace(bindings[1],provider=IdealGasPhase(changed,mass))))
