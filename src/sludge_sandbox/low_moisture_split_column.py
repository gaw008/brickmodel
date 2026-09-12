"""Explicit first-order local-BE / internal-transport split for low moisture.

Each suboperator advances h; the accepted physical clock advances h, not 2h.
Actual full-U inverses check both substep results. The old midpoint integrator
is untouched. Frozen coefficients and time truncation have no claimed error
certificate; projection budgets retain their original arithmetic-only scope.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
import time

from .arlabosse_wet_thermo import W_MIN
from .controlled_vapor_column import ControlledVaporColumn, ControlledVaporRates
from .deforming_solid_storage import _digest
from .implicit_local_moisture import (
    FrozenLocalMoistureCoefficients, backward_euler_local_moisture, numerical_policy,
)
from .integration import DomainExit
from .low_moisture_transport import low_moisture_water_point
from .mass_storage_bridge import require
from .source_wet_column import (
    ColumnFaceIntegral, ColumnRoundoff, SourceColumnRun,
    SorptionMoistureColumnFaceIntegral, _advance, _integrals, _liquid_energy_projection,
)
from .source_wet_storage import _binary


NUMERICAL_POLICY_ID='LOW_MOISTURE_LOCAL_BE_THEN_TRANSPORT_LIE_V1'


def split_policy():
    return {'id':NUMERICAL_POLICY_ID,'classification':'numerical_policy',
        'local':numerical_policy(),'order':1,
        'sequence':'local phase plus selective vapor BE(h); actual full-U decode; internal k/D plus bath Euler(h); actual full-U decode',
        'clock':'one accepted macrostep advances h; intermediate state is a split stage, not a midpoint or accepted endpoint',
        'source_domain':'exact inventory W between zero and original W_MIN at every substep',
        'gas_transport':'disabled internal gas diffusion and Darcy; existing apparent condensed-water path only',
        'local_coefficients':'freeze actual T/P/Vg and source join activity; readout residuals are not full-step error bounds',
        'budget':'two actual state projections, used internal face decomposition and moisture projections, used bath projection; excludes truncation, inverse propagation, source/model uncertainty',
        'failure':'fixed steps; stop and retain accepted prefix and incomplete trial, no clipping or hidden retries',
        'qualification':'conditional numerical method; no full-step entropy or material qualification'}


@dataclass(frozen=True)
class BoundLocalCoefficients:
    cell_index: int
    state: object
    inverse: object
    phase: object
    join_point: object
    coefficients: FrozenLocalMoistureCoefficients
    peq_per_condensed_mol_pa: F
    pv_per_vapor_mol_pa: F
    equilibrium_pressure_readout_residual_pa: F
    vapor_pressure_readout_residual_pa: F
    phase_rate_readout_residual_mol_s: F
    outlet_rate_readout_residual_mol_s: F
    outlet_enthalpy_readout_residual_w: F
    origin_rates_identity: str
    origin_classifications: tuple[tuple[str,str], ...]
    source_state_binding_verified: bool=True
    full_step_freezing_error_bound: None=None
    material_qualified: bool=False
    training_eligible: bool=False


def _check_low_states(column,states):
    column.base._check_states(states)
    for storage,state in zip(column.storages,states):
        w=F(state.liquid_water_mol)*F(storage.wet._mass)/F(storage.dry_mass_kg)
        require(0<=w<=F(W_MIN),'low_moisture_split_domain_exit')


def freeze_local_coefficients(column,states,rates):
    """Bind actual decoded source points; no fresh equilibrium or EOS solve."""
    require(type(column) is ControlledVaporColumn and type(rates) is ControlledVaporRates,
            'actual_controlled_low_moisture_rates_required')
    _check_low_states(column,states)
    base=column.base
    require(rates.model_identity==column.model_identity and
        rates.closed_rates.model_identity==base.model_identity and
        rates.cells==rates.closed_rates.cells and len(rates.cells)==column.cell_count,
        'split_origin_rates_correspondence')
    result=[]
    for i,(storage,state,cell,policy) in enumerate(zip(column.storages,states,rates.cells,base.inverse_policies)):
        water=low_moisture_water_point(storage,base.chemical,state,cell.inverse,cell.phase)
        inv=cell.inverse; p=inv.point
        error=F(_binary(p.energy_error_j)); minimum=F(_binary(p.minimum_heat_capacity_j_k,positive=True))
        allowance=abs(inv.energy_residual_j)+error
        require(error>=0 and allowance<=F(policy.energy_tolerance_j) and
            allowance/minimum<=F(inv.temperature_error_bound_k)<=F(policy.temperature_tolerance_k),
            'split_origin_inverse_certificate')
        require(F(storage.pressure_domain_pa[0])<=F(p.pressure_pa)-F(p.pressure_error_pa) and
            F(p.pressure_pa)+F(p.pressure_error_pa)<=F(storage.pressure_domain_pa[1]),
            'split_origin_pressure_domain')
        join=storage.excess.evaluate(p.temperature_k,F(W_MIN))
        pure=cell.phase.equilibrium.pure_equilibrium
        alpha=F(pure.equilibrium_partial_pressure_pa)*F(join.activity)*water.water_molar_mass_kg_mol/(F(storage.dry_mass_kg)*F(W_MIN))
        beta=water.gas_constant_j_mol_k*water.temperature_k/F(p.gas_volume_m3)
        require(alpha>0 and beta>0,'positive_split_pressure_coefficients')
        kp=F(base.transfer_coefficients_mol_s_pa[i])
        outer=i==column.cell_count-1
        kv=F(column.control.transfer_coefficient_mol_s_pa) if outer else F()
        pe=F(column.control.vapor_pressure_pa) if outer else F()
        hv=F(pure.vapor.enthalpy_j_mol)
        if outer:
            require(F(rates.boundary.common_vapor_enthalpy_j_mol)==hv and
                rates.boundary.cell_temperature_k==p.temperature_k and
                rates.boundary.cell_vapor_pressure_pa==cell.phase.water_partial_pressure_pa,
                'split_boundary_reference_correspondence')
        coefficients=FrozenLocalMoistureCoefficients(kp*alpha,kp*beta,kv*beta,kv*pe,hv,
            water.energy_reference_id,tuple(sorted(set(water.source_ids+base.coefficient_source_ids+
                (column.control.source_ids if outer else ())+(NUMERICAL_POLICY_ID,)))), 'manufactured_test_fixture')
        nc,nv=F(state.liquid_water_mol),F(state.gas_amounts_mol[2])
        outlet=kv*(beta*nv-pe)
        result.append(BoundLocalCoefficients(i,state,inv,cell.phase,join,coefficients,alpha,beta,
            alpha*nc-F(cell.phase.equilibrium.equilibrium_partial_pressure_pa),
            beta*nv-F(cell.phase.water_partial_pressure_pa),
            kp*(alpha*nc-beta*nv)-F(cell.phase.phase_water_mol_s),
            outlet-(F(rates.boundary.outward_water_mol_s) if outer else F()),
            hv*outlet-(F(rates.boundary.outward_carried_energy_w) if outer else F()),rates.model_identity,
            (('pressure_activity_enthalpy','derived_from_evidence'),
             ('local_phase_coefficient','manufactured_test_fixture'),
             ('reservoir_control_or_disconnected_topology','virtual_design_choice'),
             ('freezing_and_integration','numerical_policy'))))
    return tuple(result)


def _face(face_id,*,water=F(),enthalpy=F(),conduction=F()):
    zeros=(F(),)*3
    return ColumnFaceIntegral(face_id,(*zeros[:2],water),enthalpy+conduction,conduction,
        (*zeros[:2],enthalpy),zeros,F())


@dataclass(frozen=True)
class LowMoistureSplitLedger:
    duration_s: F
    origin_rates: ControlledVaporRates
    coefficients: tuple
    local_steps: tuple
    local_faces: tuple
    phase_water_mol: tuple
    local_states: tuple
    local_roundoff: ColumnRoundoff
    slow_rates: ControlledVaporRates
    slow_faces: tuple
    heat_projection_j: F
    slow_roundoff: ColumnRoundoff
    step_energy_roundoff_j: F
    step_inventory_roundoff_mol: F


@dataclass(frozen=True)
class IncompleteSplitTrial:
    duration_s: F
    stage: str='origin_decode'
    coefficients: tuple | None=None
    local_steps: tuple | None=None
    local_faces: tuple | None=None
    phase_water_mol: tuple | None=None
    local_states: tuple | None=None
    local_roundoff: ColumnRoundoff | None=None
    slow_rates: ControlledVaporRates | None=None
    slow_faces: tuple | None=None
    heat_projection_j: F | None=None
    proposed_states: tuple | None=None
    slow_roundoff: ColumnRoundoff | None=None
    candidate_energy_roundoff_j: F | None=None
    candidate_inventory_roundoff_mol: F | None=None
    last_completed_states: tuple | None=None
    last_completed_rates: ControlledVaporRates | None=None


@dataclass(frozen=True,kw_only=True)
class LowMoistureSplitRun(SourceColumnRun):
    numerical_policy: dict
    failed_trial: IncompleteSplitTrial | None


def integrate_low_moisture_split(column,initial,*,duration_s,steps,maximum_wall_seconds=30.,
                                energy_roundoff_budget_j=1e-8,inventory_roundoff_budget_mol=1e-12,cancel=None):
    """Fixed-step Lie integration with one atomic acceptance after both stages."""
    require(type(column) is ControlledVaporColumn,'explicit_controlled_low_moisture_column')
    require(type(steps) is int and steps>0,'explicit_split_steps')
    require(all(f.diffusivities_m2_s==(0.,)*3 and f.permeability_m2==0. for f in column.base.faces),
            'split_internal_gas_transport_must_be_disabled')
    duration=F(_binary(duration_s,positive=True));h=duration/steps
    wall=_binary(maximum_wall_seconds,positive=True)
    energy_budget=_binary(energy_roundoff_budget_j,positive=True)
    inventory_budget=_binary(inventory_roundoff_budget_mol,positive=True)
    policy=split_policy();identity=_digest((column.model_identity,policy))
    start=time.monotonic();attempted=completed=0
    states=[initial];times=[F()];ledgers=[];observations=[]
    used_energy=used_inventory=F();trial=None
    status,reason='completed',None
    def guard():
        if cancel is not None and cancel():raise InterruptedError('cancel_requested')
        if time.monotonic()-start>wall:raise TimeoutError('wall_budget_exceeded')
    def evaluate(state):
        nonlocal attempted,completed,trial
        guard();_check_low_states(column,state)
        attempted+=1;out=column.evaluate(state);completed+=1
        # Keep a completed physical evaluation even if cancellation arrives now.
        trial=replace(trial,last_completed_states=state,last_completed_rates=out)
        guard()
        return out
    try:
        trial=IncompleteSplitTrial(h)
        origin=evaluate(initial)
        for step_index in range(steps):
            guard()
            # Reuse only the actual last accepted decode, with fresh source/state binding below.
            trial=IncompleteSplitTrial(h,stage='freeze_local',
                last_completed_states=states[-1],last_completed_rates=origin)
            contexts=freeze_local_coefficients(column,states[-1],origin)
            local=tuple(backward_euler_local_moisture(s.liquid_water_mol,s.gas_amounts_mol[2],h,w.coefficients)
                        for s,w in zip(states[-1],contexts))
            phase=tuple(v.phase_transfer_mol for v in local)
            faces=tuple(_face(i) for i in range(column.cell_count))+(
                _face(column.cell_count,water=local[-1].outlet_transfer_mol,enthalpy=local[-1].outlet_enthalpy_j),)
            require(all(v.outlet_transfer_mol==0 for v in local[:-1]),'split_internal_reservoir_forbidden')
            trial=replace(trial,stage='local_projection',coefficients=contexts,local_steps=local,local_faces=faces,phase_water_mol=phase)
            after_local,local_error=_advance(column,states[-1],faces,phase)
            trial=replace(trial,stage='local_decode',local_states=after_local,local_roundoff=local_error)
            slow=evaluate(after_local)
            internal,_unused_phase=_integrals(slow.closed_rates,h)
            bath=h*F(slow.boundary.heat_into_cell_w)
            bath_error=bath-h*slow.faces[-1].exact_heat_into_cell_w
            slow_faces=(*internal[:-1],_face(column.cell_count,conduction=-bath))
            trial=replace(trial,stage='slow_projection',slow_rates=slow,slow_faces=slow_faces,heat_projection_j=bath_error)
            new,slow_error=_advance(column,after_local,slow_faces,(F(),)*column.cell_count)
            candidate_energy=used_energy+local_error.absolute_energy_j+slow_error.absolute_energy_j+abs(bath_error)
            candidate_energy+=sum((abs(f.energy_decomposition_roundoff_j)+abs(_liquid_energy_projection(f)) for f in slow_faces),F())
            candidate_inventory=used_inventory+local_error.absolute_inventory_mol+slow_error.absolute_inventory_mol
            candidate_inventory+=sum((abs(f.moisture_molar_projection_mol) for f in slow_faces
                if type(f) is SorptionMoistureColumnFaceIntegral),F())
            trial=replace(trial,stage='budget',proposed_states=new,slow_roundoff=slow_error,
                candidate_energy_roundoff_j=candidate_energy,candidate_inventory_roundoff_mol=candidate_inventory)
            require(candidate_energy<=F(energy_budget),'split_energy_roundoff_budget_exceeded')
            require(candidate_inventory<=F(inventory_budget),'split_inventory_roundoff_budget_exceeded')
            trial=replace(trial,stage='final_decode')
            last=evaluate(new)
            require(_digest((column.model_identity,split_policy()))==identity,'split_model_changed')
            guard()
            ledger=LowMoistureSplitLedger(h,origin,contexts,local,faces,phase,after_local,local_error,
                slow,slow_faces,bath_error,slow_error,candidate_energy-used_energy,candidate_inventory-used_inventory)
            states.append(new);times.append((step_index+1)*h);ledgers.append(ledger);observations.append(last)
            used_energy,used_inventory=candidate_energy,candidate_inventory
            origin=last;trial=None
        guard()
    except DomainExit as exc:status,reason='domain_exit',str(exc)
    except InterruptedError as exc:status,reason='cancelled',str(exc)
    except TimeoutError as exc:status,reason='resource_limit',str(exc)
    except (ValueError,OverflowError) as exc:status,reason='failed',str(exc)
    return LowMoistureSplitRun(status,reason,tuple(times),tuple(states),tuple(observations),tuple(ledgers),
        attempted,completed,time.monotonic()-start,identity,used_energy,used_inventory,energy_budget,inventory_budget,
        numerical_policy=policy,failed_trial=trial)
