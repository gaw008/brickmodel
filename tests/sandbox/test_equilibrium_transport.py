"""Manufactured API responses for host bookkeeping; no EOS/material admission."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace as NS

import pytest

import sludge_sandbox.equilibrium_transport as module
from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage, LowMoistureSorptionPoint
from sludge_sandbox.controlled_vapor_column import ControlledVaporColumn, ControlledVaporRates, ControlledVaporFaceRate
from sludge_sandbox.low_moisture_equilibrium import FlashPolicy, FlashFailure, NominalEquilibriumCandidate
from sludge_sandbox.mass_wet_storage import WetMixedState
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_wet_storage import SourceWetInverse
from sludge_sandbox.source_wet_column import (
    LowMoistureSorptionColumn, SourceColumnCell, SourceColumnRates,
    ColumnFaceRate, SorptionMoistureColumnFaceRate, _integrals, _advance,
)
from sludge_sandbox.water_chemical_potential import WaterChemicalPotential


@pytest.fixture
def setup(monkeypatch):
    controls = NS(flash_calls=[], decode_calls=[], advances=[], outlet=.008,
        full_mu_bias=0., fail_flash_number=None, fail_decode_number=None, changed=False)
    chemical = object.__new__(WaterChemicalPotential)
    object.__setattr__(chemical, 'vapor', NS(source_ids=('manufactured:chemical',)))
    monkeypatch.setattr(WaterChemicalPotential, 'ideal_vapor', lambda *args:
        NS(chemical_potential_j_mol=0.))
    storages=[]
    for i in range(2):
        st=object.__new__(LowMoistureSorptionStorage)
        object.__setattr__(st,'base',NS(dry_mass_kg=.01,temperature_domain_k=(325.,338.),
            gas_ids=('O2','N2','H2O')))
        object.__setattr__(st,'wet',NS(_mass=.02))
        object.__setattr__(st,'pressure_domain_pa',(90000.,110000.))
        object.__setattr__(st,'_identity',str(i+1)*64)
        storages.append(st)
    def storage_state(self,nc,gas,u):
        assert nc>=0 and all(n>=0 for n in gas)
        return WetMixedState((.01,),float(nc),tuple(map(float,gas)),float(u),self._identity)
    monkeypatch.setattr(LowMoistureSorptionStorage,'state',storage_state)
    monkeypatch.setattr(LowMoistureSorptionStorage,'_check',lambda self:None)
    monkeypatch.setattr(LowMoistureSorptionStorage,'source_ids',property(lambda self:('manufactured:storage',)))
    base=object.__new__(LowMoistureSorptionColumn)
    for key,value in dict(storages=tuple(storages),chemical=chemical,
        inverse_policies=(InversePolicy(1e-5,1e-8,100),)*2,
        transfer_coefficients_mol_s_pa=(0.,0.),
        faces=(NS(diffusivities_m2_s=(0.,)*3,permeability_m2=0.),),
        interface_modes=('reversible_sorption',)*2,
        inverse_strategy='LOW_MOISTURE_FULL_U_SAFEGUARDED_NEWTON_BISECTION_V1',
        _identity='b'*64).items():
        object.__setattr__(base,key,value)
    monkeypatch.setattr(LowMoistureSorptionColumn,'_check',lambda self:None)
    monkeypatch.setattr(LowMoistureSorptionColumn,'_check_states',lambda self,s:
        None if len(s)==2 else (_ for _ in ()).throw(ValueError('manufactured_shape')))
    column=object.__new__(ControlledVaporColumn)
    object.__setattr__(column,'base',base)
    object.__setattr__(column,'_identity','c'*64)
    def check(self):
        if controls.changed: raise ValueError('manufactured_source_changed')
    monkeypatch.setattr(ControlledVaporColumn,'_check',check)
    monkeypatch.setattr(module,'low_moisture_water_point',lambda *args:None)

    def point(storage,state):
        nc,nv=state.liquid_water_mol,state.gas_amounts_mol[2]
        mechanical=NS(temperature_k=330.,pressure_pa=100000.,gas_volume_m3=1e-5,
            liquid_inventory_mol=nc,gas_inventory_mol=dict(zip(column.gas_ids,state.gas_amounts_mol)))
        return LowMoistureSorptionPoint(fluid=NS(mechanical=mechanical),
            total_internal_energy_j=state.internal_energy_j,solid_internal_energy_j=F(),
            available_pore_volume_m3=1e-5,available_volume_error_m3=0.,
            global_pressure_error_pa=0.,extra_pressure_error_pa=0.,pressure_error_pa=0.,
            energy_error_j=0.,closed_heat_capacity_j_k=100.,minimum_heat_capacity_j_k=100.,
            model_identity=storage._identity,source_ids=('manufactured:point',),
            excess=NS(mu_ex_j_mol=0.),excess_internal_energy_j=F(),
            excess_entropy_j_k=F(),excess_helmholtz_energy_j=F())

    def evaluate(self,states):
        controls.decode_calls.append(states)
        if len(controls.decode_calls)==controls.fail_decode_number:
            raise ValueError('manufactured_decode_failure')
        cells=[]
        for storage,state in zip(storages,states):
            p=point(storage,state)
            inverse=SourceWetInverse(p,state.internal_energy_j,F(),0.,(325.,338.),1)
            drive=1e5*float(F(state.liquid_water_mol)-F(3,4)*(F(state.liquid_water_mol)+F(state.gas_amounts_mol[2])))
            pure=NS(liquid=NS(chemical_potential_j_mol=drive+controls.full_mu_bias))
            eq=NS(equilibrium_partial_pressure_pa=1.+drive,pure_equilibrium=pure,source_ids=('manufactured:eq',))
            phase=NS(phase_water_mol_s=0.,water_partial_pressure_pa=1.,equilibrium=eq,
                chemical_driving_force_j_mol=drive)
            cells.append(SourceColumnCell(inverse,phase,None))
        z=(0.,)*3
        left=ColumnFaceRate(0,None,0,z,0.,0.,z,z,None)
        exchange=NS(molar_flow_mol_s=.001,carried_energy_w=-1.,
            exact_molar_flow_mol_s=F(.001)+F(1,2**65),exact_carried_energy_w=F(-1)+F(1,2**52))
        middle=SorptionMoistureColumnFaceRate(face_id=1,left_cell=0,right_cell=1,
            gas_mol_s=z,energy_w=-.7+2**-43,conduction_w=.3,
            diffusive_enthalpy_w=z,advective_enthalpy_w=z,shared_evaluation=None,
            conductivity_witness=NS(classification='manufactured_test_fixture'),
            moisture_witness=NS(exchange=exchange))
        n=controls.outlet; carried=-1000.*n; heat=.25
        boundary=NS(outward_water_mol_s=n,common_vapor_enthalpy_j_mol=-1000.,
            outward_carried_energy_w=carried,heat_into_cell_w=heat)
        outer=ControlledVaporFaceRate(face_id=2,left_cell=1,right_cell=None,
            gas_mol_s=(0.,0.,n),energy_w=carried-heat+2**-40,conduction_w=-heat,
            diffusive_enthalpy_w=(0.,0.,carried),advective_enthalpy_w=z,
            shared_evaluation=boundary,exact_water_mol_s=F(n)+F(1,2**65),
            exact_carried_energy_w=(F(n)+F(1,2**65))*F(-1000),
            exact_heat_into_cell_w=F(heat)+F(1,2**54),boundary=boundary)
        closed=SourceColumnRates(tuple(cells),(),(left,middle,left),base._identity,('manufactured:rates',))
        return ControlledVaporRates(cells=closed.cells,gas_states=(),faces=(left,middle,outer),
            model_identity=self._identity,source_ids=closed.source_ids,closed_rates=closed,boundary=boundary)
    monkeypatch.setattr(ControlledVaporColumn,'evaluate',evaluate)

    def fake_flash(storage,chemical,total,carrier,target,policy):
        controls.flash_calls.append((total,carrier,target))
        if len(controls.flash_calls)==controls.fail_flash_number:
            raise FlashFailure('manufactured_flash_failure',last_completed_provider_result=NS(raw='kept'))
        x,n=total*F(3,4),total*F(1,4)
        state=storage.state(float(x),(*carrier,float(n)),target)
        dx,dn=F(state.liquid_water_mol)-x,F(state.gas_amounts_mol[2])-n
        return NominalEquilibriumCandidate(state,point(storage,state),x,n,dx,dn,dx+dn,F(),
            (330.,330.),(F(state.liquid_water_mol),)*2,1.,1.,F(),0.,'finite_nominal_chemical_potential',
            ('manufactured:flash',),policy,(),{},)
    monkeypatch.setattr(module,'flash',fake_flash)
    def advance(*args):
        controls.advances.append(args)
        return _advance(*args)
    monkeypatch.setattr(module,'_advance',advance)
    policy=FlashPolicy(InversePolicy(1e-5,1e-6,60),(325.,338.),1.,1e-11,1e-12,1e-5,1e-5,4,40,500,50.)
    states=tuple(s.state(nc,(.001,.003,nv),u) for s,nc,nv,u in
        zip(storages,(0.,.02),(.04,0.),(1.,2.)))
    return NS(column=column,states=states,policies=(policy,policy),controls=controls)


def initialize(a,**kwargs):
    return module.initialize_equilibrium(a.column,a.states,a.policies,**kwargs)


def test_initialization_keeps_raw_states_and_projection_with_two_certificates(setup):
    a=setup; init=initialize(a)
    assert init.status=='completed',init.reason
    assert init.raw_states is a.states and len(a.controls.advances)==1
    assert init.states[0].liquid_water_mol>0
    assert init.certified_equilibrium_temperature_bound_k is None
    for cell in init.cells:
        assert cell.fixed_composition_inverse.temperature_error_bound_k<=1e-8
        assert cell.certified_equilibrium_temperature_bound_k is None
        assert cell.actual_vapor.chemical_potential_j_mol==0.
        assert cell.actual_chemical_residual_j_mol==pytest.approx(
            cell.phase.equilibrium.pure_equilibrium.liquid.chemical_potential_j_mol
            +cell.fixed_composition_inverse.point.excess.mu_ex_j_mol
            -cell.actual_vapor.chemical_potential_j_mol)
    for old,new in zip(a.states,init.states):
        assert old.internal_energy_j==new.internal_energy_j
        assert old.gas_amounts_mol[:2]==new.gas_amounts_mol[:2]


def test_total_water_update_can_remove_more_than_initial_vapor_without_negative_state(setup):
    a=setup;init=initialize(a)
    assert a.controls.outlet>init.states[-1].gas_amounts_mol[2]
    run=module.integrate_equilibrium_transport(a.column,init,duration_s=1.,steps=1)
    assert run.status=='completed',run.reason
    assert len(a.controls.advances)==2
    ledger=run.ledgers[0]
    old,new=run.states
    for i,(s,t,candidate) in enumerate(zip(old,new,ledger.flashes)):
        assert t==candidate.state
        assert t.gas_amounts_mol[:2]==s.gas_amounts_mol[:2]
        assert F(t.internal_energy_j)-F(s.internal_energy_j)==ledger.faces[i].energy_j-ledger.faces[i+1].energy_j+ledger.roundoff.energy_j[i]
        assert ledger.roundoff.liquid_mol[i]==candidate.liquid_projection_error_mol
        assert ledger.roundoff.gas_mol[i][2]==candidate.vapor_projection_error_mol
        assert ledger.roundoff.energy_j[i]==ledger.target_energy_projection_j[i]
    assert ledger.water_balance_residual_mol==ledger.energy_balance_residual_j==0
    assert ledger.boundary_energy_decomposition_j!=0
    delta_u=sum((F(n.internal_energy_j)-F(o.internal_energy_j) for o,n in zip(old,new)),F())
    assert delta_u==ledger.boundary_heat_j-ledger.boundary_enthalpy_j-ledger.boundary_energy_decomposition_j+sum(ledger.roundoff.energy_j,F())
    assert run.energy_roundoff_used_j==init.energy_roundoff_used_j+ledger.step_energy_roundoff_j
    assert run.inventory_roundoff_used_mol==init.inventory_roundoff_used_mol+ledger.step_inventory_roundoff_mol
    assert not run.material_qualified


def test_each_face_projection_and_prior_cost_is_counted_once(setup):
    init=initialize(setup,prior_energy_roundoff_j=F(1,10**12),prior_inventory_roundoff_mol=F(1,10**14))
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=.1,steps=1)
    assert run.status=='completed',run.reason
    row=run.ledgers[0]
    internal,boundary=row.faces[1:]
    expected_e=row.roundoff.absolute_energy_j+sum(abs(f.energy_decomposition_roundoff_j) for f in row.faces)
    expected_e+=abs(internal.moisture_enthalpy_projection_j)+abs(boundary.vapor_enthalpy_projection_j)+abs(boundary.heat_projection_j)
    expected_n=row.roundoff.absolute_inventory_mol+abs(internal.moisture_molar_projection_mol)+abs(boundary.vapor_molar_projection_mol)
    assert row.step_energy_roundoff_j==expected_e
    assert row.step_inventory_roundoff_mol==expected_n
    assert run.energy_roundoff_used_j==init.energy_roundoff_used_j+expected_e
    assert run.inventory_roundoff_used_mol==init.inventory_roundoff_used_mol+expected_n


def test_nonzero_kinetics_and_loose_inverse_are_rejected_before_callbacks(setup):
    object.__setattr__(setup.column.base,'transfer_coefficients_mol_s_pa',(0.,1e-10))
    with pytest.raises(ValueError,match='phase.*zero'):
        initialize(setup)
    assert not setup.controls.flash_calls and not setup.controls.decode_calls
    object.__setattr__(setup.column.base,'transfer_coefficients_mol_s_pa',(0.,0.))
    object.__setattr__(setup.column.base,'inverse_policies',(InversePolicy(1e-5,1e-6,100),)*2)
    with pytest.raises(ValueError,match='tight_fixed'):
        initialize(setup)


def test_project_false_checks_actual_full_mu_not_only_phase_log_drive(setup):
    first=initialize(setup)
    n=len(setup.controls.flash_calls)
    accepted=module.initialize_equilibrium(setup.column,first.states,setup.policies,project=False)
    assert accepted.status=='completed' and len(setup.controls.flash_calls)==n
    setup.controls.full_mu_bias=2e-5
    failed=module.initialize_equilibrium(setup.column,first.states,setup.policies,project=False)
    assert failed.status=='failed' and 'actual_mu' in failed.reason


def test_negative_total_fails_before_any_new_flash_or_advance(setup):
    init=initialize(setup)
    setup.controls.outlet=100.
    init=module.initialize_equilibrium(setup.column,init.states,setup.policies,project=False)
    before=len(setup.controls.flash_calls),len(setup.controls.advances)
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=1.,steps=1)
    assert run.status=='domain_exit' and 'negative_total_water' in run.reason
    assert run.states==(init.states,) and not run.ledgers
    assert before==(len(setup.controls.flash_calls),len(setup.controls.advances))


def test_second_cell_flash_failure_preserves_accepted_prefix_and_completed_provider(setup):
    init=initialize(setup)
    setup.controls.fail_flash_number=len(setup.controls.flash_calls)+4
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=.2,steps=2)
    assert run.status=='failed' and len(run.states)==2 and len(run.ledgers)==1
    assert len(run.failed_trial.flashes)==1
    assert run.failed_trial.last_completed_provider_result.raw=='kept'


def test_cancel_after_decode_preserves_returned_rates_and_no_commit(setup):
    init=initialize(setup)
    before=len(setup.controls.decode_calls)
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=.1,steps=1,
        cancel=lambda:len(setup.controls.decode_calls)>before+1)
    assert run.status=='cancelled' and run.states==(init.states,)
    assert run.failed_trial.last_completed_provider_result is not None
    assert len(setup.controls.advances)==1


def test_advance_correspondence_is_enforced(setup,monkeypatch):
    init=initialize(setup)
    def bad(*args):
        states,error=_advance(*args)
        return (replace(states[0],internal_energy_j=states[0].internal_energy_j+1.),states[1]),error
    monkeypatch.setattr(module,'_advance',bad)
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=.1,steps=1)
    assert run.status=='failed' and 'flash_state_correspondence' in run.reason
    assert run.states==(init.states,)


def test_cancel_between_accepted_steps_preserves_prefix(setup):
    init=initialize(setup)
    guards_after_first_advance=[0]
    def cancel():
        if len(setup.controls.advances)==2:
            guards_after_first_advance[0]+=1
            return guards_after_first_advance[0]>=3
        return False
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=.2,steps=2,cancel=cancel)
    assert run.status=='cancelled' and len(run.ledgers)==1 and len(run.states)==2
    assert run.failed_trial.old_states==run.states[-1]
    assert run.failed_trial.rates is run.observations[-1]
    assert run.failed_trial.last_completed_provider_result is not None


def test_rejected_step_does_not_commit_new_cost_or_states(setup):
    init=initialize(setup)
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=.1,steps=1,
        energy_roundoff_budget_j=1e-30)
    assert run.status=='failed' and 'energy_roundoff_budget' in run.reason
    assert run.states==(init.states,) and not run.ledgers
    assert run.energy_roundoff_used_j==init.energy_roundoff_used_j
    assert run.inventory_roundoff_used_mol==init.inventory_roundoff_used_mol
    assert run.failed_trial.roundoff is not None
    assert run.failed_trial.candidate_energy_roundoff_j>F(1e-30)


def test_post_decode_wall_exit_keeps_actual_rates_object(setup,monkeypatch):
    init=initialize(setup)
    clock=[0.];returned=[]
    original=ControlledVaporColumn.evaluate
    def evaluate(self,states):
        out=original(self,states)
        returned.append(out);clock[0]=2.
        return out
    monkeypatch.setattr(module,'time',NS(monotonic=lambda:clock[0]))
    monkeypatch.setattr(ControlledVaporColumn,'evaluate',evaluate)
    run=module.integrate_equilibrium_transport(setup.column,init,duration_s=.1,steps=1,
        maximum_wall_seconds=1.)
    assert run.status=='resource_limit' and run.states==(init.states,)
    assert run.failed_trial.last_completed_provider_result is returned[-1]
