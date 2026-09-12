"""Conservative total-water/full-U transport followed by nominal equilibrium.

Slow rates use the accepted state (first-order explicit transport). A flash is
an algebraic local projection, not a phase rate. A separate fixed-composition
inverse and actual-pv chemical check follow it. Their conditional temperature
certificate is never promoted to an equilibrium-composition certificate.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
import math
import time

from sludge_sandbox.arlabosse_low_moisture_storage import LowMoistureSorptionStorage
from sludge_sandbox.controlled_vapor_column import (
    ControlledVaporColumn, ControlledVaporRates, ControlledVaporFaceIntegral,
)
from sludge_sandbox.deforming_solid_storage import _digest
from sludge_sandbox.integration import DomainExit
from sludge_sandbox.low_moisture_equilibrium import FlashPolicy, FlashFailure, NominalEquilibriumCandidate, flash
from sludge_sandbox.low_moisture_transport import low_moisture_water_point
from sludge_sandbox.mass_storage_bridge import require
from sludge_sandbox.mass_wet_transport import represented
from sludge_sandbox.phase_storage import InversePolicy
from sludge_sandbox.source_wet_column import (
    LowMoistureSorptionColumn, ColumnFaceIntegral, ColumnRoundoff, SourceColumnRun,
    SorptionMoistureColumnFaceIntegral, _advance, _integrals, _liquid_integral,
    _liquid_energy_projection,
)
from sludge_sandbox.source_wet_storage import SourceWetInverse, _binary


POLICY_ID = 'LOW_MOISTURE_TOTAL_WATER_FULL_U_EQUILIBRIUM_PROJECTION_V1'


def numerical_policy() -> dict:
    return {'id': POLICY_ID, 'classification': 'numerical_policy', 'order': 1,
        'sequence': 'accepted slow rates; exact shared-face Nt/U targets; nominal flash; fixed-composition full-U inverse; actual-pv full mu check; same-J single final _advance',
        'phase_coefficients': 'must all be exactly zero; finite-rate phase branch disabled',
        'fixed_composition_temperature_policy_k': 'explicit <=1e-8; actual mu/peq checks still required',
        'equilibrium_certificate': 'not available; fixed-composition inverse excludes flash composition error',
        'budget': 'used final state projection plus each used face readout/decomposition once; previous cumulative costs retained',
        'energy': 'delta sum U = -outer face.energy + signed final U projection; Q-H form additionally subtracts outer decomposition',
        'scope': 'T325-338K, P90-110kPa, W0-.15; fixed carriers, disabled internal gas transfer',
        'counts': 'top-level flash/column/actual-vapor calls, not nested EOS iterations; pure _advance is not an EOS evaluation',
        'wall': 'checked before/after calls; does not preempt an in-flight provider',
        'unknown': ['time truncation', 'LTE timescale separation', 'flash composition error', 'source/material/transport/boundary errors'],
        'material_qualified': False, 'training_eligible': False}


@dataclass(frozen=True)
class EquilibriumCell:
    fixed_composition_inverse: SourceWetInverse
    phase: object
    actual_vapor: object | None
    actual_chemical_residual_j_mol: float | None
    equilibrium_pressure_residual_pa: F
    nominal_flash: NominalEquilibriumCandidate | None
    certified_equilibrium_temperature_bound_k: None = None
    equilibrium_composition_energy_error_j: None = None


@dataclass(frozen=True)
class EquilibriumStepLedger:
    duration_s: F
    origin_rates: ControlledVaporRates | None
    faces: tuple
    exact_total_water_targets: tuple
    exact_energy_targets: tuple
    target_energy_projection_j: tuple
    flashes: tuple
    fixed_composition_rates: ControlledVaporRates
    cells: tuple
    phase_water_mol: tuple
    roundoff: ColumnRoundoff
    step_energy_roundoff_j: F
    step_inventory_roundoff_mol: F
    boundary_water_mol: F
    boundary_heat_j: F
    boundary_enthalpy_j: F
    boundary_energy_decomposition_j: F
    water_balance_residual_mol: F
    energy_balance_residual_j: F


@dataclass(frozen=True)
class EquilibriumTrial:
    stage: str
    old_states: tuple
    faces: tuple = ()
    exact_total_water_targets: tuple = ()
    exact_energy_targets: tuple = ()
    flashes: tuple = ()
    proposed_states: tuple | None = None
    rates: ControlledVaporRates | None = None
    cells: tuple = ()
    phase_water_mol: tuple = ()
    roundoff: ColumnRoundoff | None = None
    candidate_energy_roundoff_j: F | None = None
    candidate_inventory_roundoff_mol: F | None = None
    last_completed_provider_result: object | None = None
    last_completed_provider_context: tuple | None = None
    failure_details: dict | None = None


@dataclass(frozen=True)
class EquilibriumInitialization:
    status: str
    reason: str | None
    raw_states: tuple
    states: tuple
    rates: ControlledVaporRates | None
    cells: tuple
    ledger: EquilibriumStepLedger | None
    failed_trial: EquilibriumTrial | None
    flash_policies: tuple
    model_identity: str
    prior_energy_roundoff_j: F
    prior_inventory_roundoff_mol: F
    energy_roundoff_used_j: F
    inventory_roundoff_used_mol: F
    evaluations_attempted: int
    evaluations_completed: int
    elapsed_seconds: float
    certified_equilibrium_temperature_bound_k: None = None
    material_qualified: bool = False
    training_eligible: bool = False

    @property
    def roundoff(self) -> ColumnRoundoff:
        return self.ledger.roundoff if self.ledger else ColumnRoundoff(
            (F(),)*len(self.states), ((F(),)*3,)*len(self.states), (F(),)*len(self.states))


@dataclass(frozen=True, kw_only=True)
class EquilibriumTransportRun(SourceColumnRun):
    initialization: EquilibriumInitialization
    failed_trial: EquilibriumTrial | None
    numerical_policy: dict
    certified_equilibrium_temperature_bound_k: None = None
    training_eligible: bool = False


def _identity(column, policies) -> str:
    return _digest((POLICY_ID, column.model_identity, policies))


def _config(column, policies) -> str:
    require(type(column) is ControlledVaporColumn and type(column.base) is LowMoistureSorptionColumn,
            'equilibrium_actual_controlled_low_column')
    column._check()
    require(type(policies) is tuple and len(policies)==column.cell_count,
            'equilibrium_one_flash_policy_per_cell')
    require(all(_binary(k)==0 for k in column.base.transfer_coefficients_mol_s_pa),
            'equilibrium_phase_coefficients_must_be_zero')
    require(all(f.diffusivities_m2_s==(0.,)*3 and f.permeability_m2==0 for f in column.base.faces),
            'equilibrium_internal_gas_transport_disabled')
    require(all(mode=='reversible_sorption' for mode in column.interface_modes), 'equilibrium_reversible_interfaces')
    for storage, inverse, policy in zip(column.storages,column.base.inverse_policies,policies):
        require(type(storage) is LowMoistureSorptionStorage and type(policy) is FlashPolicy
                and type(inverse) is InversePolicy, 'equilibrium_actual_storage_and_policies')
        replace(policy); replace(inverse)
        require(inverse.temperature_tolerance_k<=1e-8 and
                inverse.energy_tolerance_j<=policy.inverse_policy.energy_tolerance_j,
                'equilibrium_explicit_tight_fixed_composition_inverse')
        tl,th=storage.temperature_domain_k; pl,ph=storage.pressure_domain_pa
        require(325.<=tl<th<=338. and 90000.<=pl<ph<=110000., 'equilibrium_source_domain')
    return _identity(column,policies)


def _cost(value) -> F:
    require(type(value) in (float,int,F),'explicit_prior_roundoff')
    result=F(value)
    require(result>=0,'nonnegative_prior_roundoff')
    return result


def _step_cost(faces,error) -> tuple[F,F]:
    energy=error.absolute_energy_j+sum((abs(f.energy_decomposition_roundoff_j)+abs(_liquid_energy_projection(f)) for f in faces),F())
    inventory=error.absolute_inventory_mol
    for face in faces:
        if type(face) is SorptionMoistureColumnFaceIntegral: inventory+=abs(face.moisture_molar_projection_mol)
        if type(face) is ControlledVaporFaceIntegral:
            inventory+=abs(face.vapor_molar_projection_mol)
            energy+=abs(face.vapor_enthalpy_projection_j)+abs(face.heat_projection_j)
    return energy,inventory


class _Runner:
    def __init__(self,column,policies,wall,energy_budget,inventory_budget,cancel,used_energy,used_inventory):
        self.column,self.policies=column,policies
        self.wall=_binary(wall,positive=True)
        self.energy_budget=_binary(energy_budget,positive=True)
        self.inventory_budget=_binary(inventory_budget,positive=True)
        self.cancel=cancel; self.used_energy=_cost(used_energy); self.used_inventory=_cost(used_inventory)
        self.started=time.monotonic();self.attempted=self.completed=0
        self.trial=None
        self.last_completed_provider_result=None;self.last_completed_provider_context=None

    def guard(self):
        if self.cancel is not None and self.cancel(): raise InterruptedError('cancel_requested')
        if time.monotonic()-self.started>self.wall: raise TimeoutError('wall_budget_exceeded')

    def call(self,kind,callback,*args):
        self.guard()
        context=(kind,args)
        if kind=='flash':
            context=(kind,{'storage_model_identity':args[0]._identity,
                'chemical_method_id':args[1].method_id,'total_water_mol':args[2],
                'carrier_mol':args[3],'target_energy_j':args[4],'policy':args[5]})
        elif kind=='advance':
            context=(kind,{'column_model_identity':args[0]._identity,
                'old_states':args[1],'faces':args[2],'phase_water_mol':args[3]})
        if kind!='advance': self.attempted+=1
        out=callback(*args)
        if kind!='advance': self.completed+=1
        self.last_completed_provider_result=out;self.last_completed_provider_context=context
        self.trial=replace(self.trial,last_completed_provider_result=out,
            last_completed_provider_context=context)
        self.guard()
        return out

    def states(self,states):
        self.column.base._check_states(states)
        for storage,state in zip(self.column.storages,states):
            w=F(state.liquid_water_mol)*F(storage.wet._mass)/F(storage.dry_mass_kg)
            require(0<=w<=F(.15),'equilibrium_low_water_domain')

    def decode(self,states,flashes=()):
        self.states(states)
        rates=self.call('column',self.column.evaluate,states)
        self.trial=replace(self.trial,rates=rates)
        cells=self.check_rates(states,rates,flashes)
        return rates,cells

    def check_rates(self,states,rates,flashes=()):
        self.states(states)
        require(type(rates) is ControlledVaporRates and rates.model_identity==self.column.model_identity
                and rates.closed_rates.model_identity==self.column.base.model_identity
                and rates.cells==rates.closed_rates.cells and len(rates.cells)==self.column.cell_count,
                'equilibrium_actual_rates_binding')
        cells=[]
        for i,(storage,state,cell,ip,fp) in enumerate(zip(self.column.storages,states,rates.cells,
                self.column.base.inverse_policies,self.policies)):
            inv,phase=cell.inverse,cell.phase
            low_moisture_water_point(storage,self.column.base.chemical,state,inv,phase)
            p=inv.point; residual=F(p.total_internal_energy_j)-F(state.internal_energy_j)
            err=F(_binary(p.energy_error_j));minimum=F(_binary(p.minimum_heat_capacity_j_k,positive=True))
            bound=F(_binary(inv.temperature_error_bound_k))
            require(type(inv) is SourceWetInverse and inv.target_energy_j==state.internal_energy_j
                and inv.energy_residual_j==residual and err>=0 and abs(residual)+err<=F(ip.energy_tolerance_j)
                and (abs(residual)+err)/minimum<=bound<=F(ip.temperature_tolerance_k),
                'equilibrium_fixed_composition_certificate')
            pressure,pe=F(p.pressure_pa),F(p.pressure_error_pa)
            require(pe>=0 and F(storage.pressure_domain_pa[0])<=pressure-pe<=pressure+pe<=F(storage.pressure_domain_pa[1]),
                    'equilibrium_complete_pressure_interval')
            require(fp.temperature_range_k[0]<=p.temperature_k<=fp.temperature_range_k[1], 'equilibrium_temperature_domain')
            require(phase.phase_water_mol_s==0.,'equilibrium_disabled_phase_returned_rate')
            pv=F(_binary(phase.water_partial_pressure_pa));peq=F(_binary(phase.equilibrium.equilibrium_partial_pressure_pa))
            require(pv>=0 and peq>=0 and abs(peq-pv)<=F(fp.equilibrium_pressure_tolerance_pa),
                    'equilibrium_actual_peq_pv_residual')
            total=F(state.liquid_water_mol)+F(state.gas_amounts_mol[2]);mu=None;vapor=None
            if total:
                require(state.liquid_water_mol>0 and state.gas_amounts_mol[2]>0 and pv>0,
                        'equilibrium_positive_total_requires_finite_two_phase_mu')
                vapor=self.call('actual_vapor',self.column.base.chemical.ideal_vapor,p.temperature_k,float(pv))
                mu=_binary(math.fsum((phase.equilibrium.pure_equilibrium.liquid.chemical_potential_j_mol,
                    p.excess.mu_ex_j_mol,-vapor.chemical_potential_j_mol)))
                require(abs(mu)<=fp.chemical_tolerance_j_mol,'equilibrium_actual_mu_residual')
            else:
                require(pv==peq==0,'equilibrium_zero_total_water_limit')
            cells.append(EquilibriumCell(inv,phase,vapor,mu,peq-pv,flashes[i] if flashes else None))
            self.trial=replace(self.trial,cells=tuple(cells))
        return tuple(cells)

    def budgets(self,energy,inventory):
        self.trial=replace(self.trial,candidate_energy_roundoff_j=energy,candidate_inventory_roundoff_mol=inventory)
        require(energy<=F(self.energy_budget),'equilibrium_energy_roundoff_budget_exceeded')
        require(inventory<=F(self.inventory_budget),'equilibrium_inventory_roundoff_budget_exceeded')

    def project(self,old,faces,duration,origin):
        self.states(old)
        self.trial=replace(self.trial,stage='total_water_energy_targets',faces=faces)
        require(len(faces)==self.column.cell_count+1 and all(f.face_id==i for i,f in enumerate(faces)),
                'equilibrium_shared_face_layout')
        require(all(f.gas_mol[:2]==(F(),F()) for f in faces)
            and all(f.gas_mol[2]==0 for f in faces[:-1])
            and _liquid_integral(faces[0])==_liquid_integral(faces[-1])==0 and faces[0].energy_j==0,
            'equilibrium_selective_boundary_and_fixed_carriers')
        totals=tuple(F(s.liquid_water_mol)+F(s.gas_amounts_mol[2])+_liquid_integral(faces[i])
            -_liquid_integral(faces[i+1])+faces[i].gas_mol[2]-faces[i+1].gas_mol[2] for i,s in enumerate(old))
        energies=tuple(F(s.internal_energy_j)+faces[i].energy_j-faces[i+1].energy_j for i,s in enumerate(old))
        self.trial=replace(self.trial,exact_total_water_targets=totals,exact_energy_targets=energies)
        if any(n<0 for n in totals): raise DomainExit('equilibrium_negative_total_water')
        targets=tuple(represented(u) for u in energies)
        delta_u=tuple(F(v)-u for v,u in zip(targets,energies))
        self.trial=replace(self.trial,stage='flash')
        candidates=[]
        for storage,state,n,u,policy in zip(self.column.storages,old,totals,targets,self.policies):
            candidate=self.call('flash',flash,storage,self.column.base.chemical,n,state.gas_amounts_mol[:2],u,policy)
            candidates.append(candidate);self.trial=replace(self.trial,flashes=tuple(candidates))
            require(type(candidate) is NominalEquilibriumCandidate and candidate.policy==policy
                and candidate.exact_liquid_mol+candidate.exact_vapor_mol==n
                and candidate.state.internal_energy_j==u and candidate.state.gas_amounts_mol[:2]==state.gas_amounts_mol[:2],
                'equilibrium_flash_target_correspondence')
        candidates=tuple(candidates);proposed=tuple(c.state for c in candidates)
        self.trial=replace(self.trial,stage='fixed_composition_decode',proposed_states=proposed)
        rates,cells=self.decode(proposed,candidates)
        phase=tuple(F(s.liquid_water_mol)+_liquid_integral(faces[i])-_liquid_integral(faces[i+1])
            -c.exact_liquid_mol for i,(s,c) in enumerate(zip(old,candidates)))
        self.trial=replace(self.trial,stage='single_final_projection',phase_water_mol=phase)
        new,error=self.call('advance',_advance,self.column,old,faces,phase)
        self.trial=replace(self.trial,roundoff=error,proposed_states=new)
        require(new==proposed,'equilibrium_flash_state_correspondence')
        require(error.energy_j==delta_u and all(error.liquid_mol[i]==c.liquid_projection_error_mol
            and error.gas_mol[i][2]==c.vapor_projection_error_mol and error.gas_mol[i][:2]==(F(),F())
            for i,c in enumerate(candidates)), 'equilibrium_projection_fee_correspondence')
        energy,inventory=_step_cost(faces,error)
        self.budgets(self.used_energy+energy,self.used_inventory+inventory)
        water_delta=sum((F(n.liquid_water_mol)+F(n.gas_amounts_mol[2])-F(o.liquid_water_mol)-F(o.gas_amounts_mol[2]) for o,n in zip(old,new)),F())
        energy_delta=sum((F(n.internal_energy_j)-F(o.internal_energy_j) for o,n in zip(old,new)),F())
        water_balance=water_delta+faces[-1].gas_mol[2]-sum(error.liquid_mol,F())-sum((r[2] for r in error.gas_mol),F())
        energy_balance=energy_delta+faces[-1].energy_j-sum(error.energy_j,F())
        require(water_balance==energy_balance==0,'equilibrium_global_shared_face_conservation')
        outer=faces[-1]
        ledger=EquilibriumStepLedger(duration,origin,faces,totals,energies,delta_u,candidates,rates,cells,phase,error,
            energy,inventory,outer.gas_mol[2],-outer.conduction_j,
            sum(outer.diffusive_enthalpy_j,F())+sum(outer.advective_enthalpy_j,F()),
            outer.energy_decomposition_roundoff_j,water_balance,energy_balance)
        return new,rates,cells,ledger

    def failure(self,exc):
        details={'error_type':type(exc).__name__,'reason':str(exc),'cause':repr(exc.__cause__) if exc.__cause__ else None}
        if isinstance(exc,FlashFailure):
            details.update(trials=exc.trials,counts=exc.counts)
            if exc.last_completed_provider_result is not None:
                self.last_completed_provider_result=exc.last_completed_provider_result
                self.last_completed_provider_context=exc.last_completed_provider_context
            self.trial=replace(self.trial,last_completed_provider_result=self.last_completed_provider_result,
                last_completed_provider_context=self.last_completed_provider_context)
        self.trial=replace(self.trial,failure_details=details)
        status=('domain_exit' if isinstance(exc,DomainExit) else 'cancelled' if isinstance(exc,InterruptedError)
            else 'resource_limit' if isinstance(exc,TimeoutError) else 'failed')
        return status,str(exc)

    def finish_status(self,status,reason,states,rates):
        elapsed=time.monotonic()-self.started
        if status=='completed' and elapsed>self.wall:
            self.trial=EquilibriumTrial('terminal_wall_check',states,rates=rates,
                last_completed_provider_result=self.last_completed_provider_result,
                last_completed_provider_context=self.last_completed_provider_context)
            status,reason=self.failure(TimeoutError('wall_budget_exceeded'))
        return status,reason,elapsed


def initialize_equilibrium(column,states,flash_policies,*,project=True,maximum_wall_seconds=30.,
        energy_roundoff_budget_j=1e-8,inventory_roundoff_budget_mol=1e-12,
        prior_energy_roundoff_j=F(),prior_inventory_roundoff_mol=F(),cancel=None) -> EquilibriumInitialization:
    """Separate zero-time projection, or source-bound validation of equilibrated input."""
    identity=_config(column,flash_policies);require(type(project) is bool,'explicit_initial_projection_choice')
    runner=_Runner(column,flash_policies,maximum_wall_seconds,energy_roundoff_budget_j,
        inventory_roundoff_budget_mol,cancel,prior_energy_roundoff_j,prior_inventory_roundoff_mol)
    runner.trial=EquilibriumTrial('initialization',states)
    status,reason='completed',None;new=states;rates=None;cells=();ledger=None
    try:
        runner.guard();runner.states(states);runner.budgets(runner.used_energy,runner.used_inventory)
        if project:
            z=(F(),)*3
            faces=tuple(ColumnFaceIntegral(i,z,F(),F(),z,z,F()) for i in range(column.cell_count+1))
            proposed,rates,cells,ledger=runner.project(states,faces,F(),None)
        else:
            proposed=states;rates,cells=runner.decode(states)
        require(_config(column,flash_policies)==identity,'equilibrium_model_changed')
        runner.guard();new=proposed
        if ledger:
            runner.used_energy+=ledger.step_energy_roundoff_j;runner.used_inventory+=ledger.step_inventory_roundoff_mol
        runner.trial=None
    except Exception as exc: status,reason=runner.failure(exc)
    status,reason,elapsed=runner.finish_status(status,reason,new,rates)
    return EquilibriumInitialization(status,reason,states,new,rates,cells,ledger,runner.trial,flash_policies,identity,
        _cost(prior_energy_roundoff_j),_cost(prior_inventory_roundoff_mol),runner.used_energy,runner.used_inventory,
        runner.attempted,runner.completed,elapsed)


def integrate_equilibrium_transport(column,initialization,*,duration_s,steps,maximum_wall_seconds=30.,
        energy_roundoff_budget_j=1e-8,inventory_roundoff_budget_mol=1e-12,cancel=None) -> EquilibriumTransportRun:
    """Advance only accepted states; each step spends final projection and face fees once."""
    require(type(initialization) is EquilibriumInitialization and initialization.status=='completed',
            'successful_equilibrium_initialization_required')
    policies=initialization.flash_policies;identity=_config(column,policies)
    require(initialization.model_identity==identity,'equilibrium_initialization_model_binding')
    require(type(steps) is int and steps>0,'explicit_equilibrium_steps')
    duration=F(_binary(duration_s,positive=True));h=duration/steps
    runner=_Runner(column,policies,maximum_wall_seconds,energy_roundoff_budget_j,inventory_roundoff_budget_mol,
        cancel,initialization.energy_roundoff_used_j,initialization.inventory_roundoff_used_mol)
    initial=initialization.states;states=[initial];times=[F()];observations=[];ledgers=[]
    runner.trial=EquilibriumTrial('validate_initialization',initial)
    status,reason='completed',None
    try:
        added_energy=added_inventory=F()
        if initialization.ledger is not None:
            row=initialization.ledger
            added_energy,added_inventory=_step_cost(row.faces,row.roundoff)
            require((added_energy,added_inventory)==(row.step_energy_roundoff_j,row.step_inventory_roundoff_mol)
                and row.duration_s==0 and tuple(c.state for c in row.flashes)==initial,
                'equilibrium_initialization_ledger_correspondence')
        require(initialization.energy_roundoff_used_j==_cost(initialization.prior_energy_roundoff_j)+added_energy
            and initialization.inventory_roundoff_used_mol==_cost(initialization.prior_inventory_roundoff_mol)+added_inventory,
            'equilibrium_initialization_accumulated_fee_mismatch')
        runner.guard();runner.budgets(runner.used_energy,runner.used_inventory)
        runner.check_rates(initial,initialization.rates,initialization.ledger.flashes if initialization.ledger else ())
        origin,_=runner.decode(initial)  # Fresh source/rates binding, no state projection or physical fees.
        for i in range(steps):
            runner.trial=EquilibriumTrial('slow_faces',states[-1],rates=origin,
                last_completed_provider_result=runner.last_completed_provider_result,
                last_completed_provider_context=runner.last_completed_provider_context)
            runner.guard()
            faces,disabled=_integrals(origin,h)
            require(all(j==0 for j in disabled),'equilibrium_phase_coefficients_must_be_zero')
            new,rates,cells,ledger=runner.project(states[-1],faces,h,origin)
            require(_config(column,policies)==identity,'equilibrium_model_changed')
            runner.guard()
            states.append(new);times.append((i+1)*h);observations.append(rates);ledgers.append(ledger)
            runner.used_energy+=ledger.step_energy_roundoff_j;runner.used_inventory+=ledger.step_inventory_roundoff_mol
            origin=rates;runner.trial=None
    except Exception as exc: status,reason=runner.failure(exc)
    status,reason,elapsed=runner.finish_status(status,reason,states[-1],observations[-1] if observations else initialization.rates)
    return EquilibriumTransportRun(status,reason,tuple(times),tuple(states),tuple(observations),tuple(ledgers),
        runner.attempted,runner.completed,elapsed,identity,runner.used_energy,runner.used_inventory,
        runner.energy_budget,runner.inventory_budget,initialization=initialization,failed_trial=runner.trial,
        numerical_policy=numerical_policy())
