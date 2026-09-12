"""Actual solid/fluid inverse coupled to programmed reservoir and surface film.

The base is evaluated once per trial. Dynamic gas enthalpy and half-cell heat
are then added to the same outward face ledger without changing stored energy.
"""
from .free_solid_slab import FreeSolidSlab,FreeSolidSlabEvaluation
from .deforming_solid_heat import DeformingSolidHeat,DeformingSolidHeatEvaluation
from dataclasses import dataclass,field
import numpy as np

from .deforming_solid_storage import _digest,DeformingStorageError
from .boundary_program import BoundaryProgram,BoundaryProgramError,BoundaryState
from .gas_transport import GasState,GasTransportError,ideal_gas_reservoir
from .exchanges import BoundaryHeat,ExchangeError
from .surface_balance import solve_surface_balance
from .integration import ConservedState,DomainExit,IntegrationError,Rates
from .programmed_gas_heat import SurfacePolicy,_number,_label
from .solid_fluid_heat import SolidFluidHeat,SolidFluidHeatEvaluation,_failure
from .rigid_fluid_heat import _FAILURES,_sum


class ProgrammedSolidFluidHeatError(IntegrationError):
    """Invalid programmed boundary or unresolved numerical surface balance."""


@dataclass(frozen=True,kw_only=True)
class ProgrammedSolidFluidEvaluation:
    rates: Rates
    base_evaluation: SolidFluidHeatEvaluation | DeformingSolidHeatEvaluation | FreeSolidSlabEvaluation
    boundary: BoundaryState
    reservoir: GasState
    surface_temperature_k: float
    heat: BoundaryHeat
    conductive_into_cell_w: float
    surface_balance_residual_w: float
    surface_balance_limit_w: float
    surface_iterations: int
    surface_status: str
    qualification: str = 'conditional_solid_fluid_inverse_and_numerical_surface_balance_not_full_brick'
    operator_identity: tuple | None = None
    source_ids: tuple[str,...] = ()

    @property
    def storage_states(self):return self.base_evaluation.storage_states
    @property
    def storage_inverses(self):return self.base_evaluation.storage_inverses
    @property
    def gas_states(self):return self.base_evaluation.gas_states


@dataclass(frozen=True,kw_only=True)
class ProgrammedSolidFluidHeat:
    base_model: SolidFluidHeat | DeformingSolidHeat | FreeSolidSlab
    program: BoundaryProgram
    convection_w_m2_k: float
    emissivity: float
    stefan_boltzmann_w_m2_k4: float
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    coefficient_source_ids: tuple[str,...]
    surface_policy: SurfacePolicy
    allow_manufactured: bool = False
    _content_digest: str = field(init=False,repr=False)

    def __post_init__(self):
        if type(self.base_model) not in (SolidFluidHeat,DeformingSolidHeat,FreeSolidSlab) or type(self.program) is not BoundaryProgram:
            raise ProgrammedSolidFluidHeatError('explicit_solid_fluid_and_program_required')
        if type(self.surface_policy) is not SurfacePolicy:raise ProgrammedSolidFluidHeatError('explicit_surface_policy_required')
        base=self._configuration_host;transport=base.transport
        if transport.outer_reservoir is not None or transport.outer_surface_temperature_k is not None:
            raise ProgrammedSolidFluidHeatError('existing_outer_boundary_would_be_duplicated')
        if base.gas_species_order!=self.program.species_order:
            raise ProgrammedSolidFluidHeatError('complete_ordered_boundary_species_must_match_model')
        if type(self.allow_manufactured) is not bool:raise ProgrammedSolidFluidHeatError('invalid_manufactured_gate')
        if self.coefficient_classification not in ('manufactured','literature_candidate'):
            raise ProgrammedSolidFluidHeatError('invalid_coefficient_classification')
        manufactured=(type(self.base_model) in (DeformingSolidHeat,FreeSolidSlab) or base.has_manufactured_reactions or base.has_manufactured_liquid_transport or self.coefficient_classification=='manufactured' or transport.coefficient_classification=='manufactured'
            or any(s.geometry_classification=='manufactured_test_fixture' or
                any(p.metadata.classification=='manufactured_test_fixture' for p in (*s.solid_phases.values(),*s.fluid_template.gas_phases.values()))
                for s in base.storages))
        if manufactured and not self.allow_manufactured:raise ProgrammedSolidFluidHeatError('manufactured_requires_explicit_test_mode')
        if not _label(self.coefficient_set_id) or not _label(self.coefficient_version):raise ProgrammedSolidFluidHeatError('coefficient_identity_required')
        sources=self.coefficient_source_ids
        if (not isinstance(sources,(tuple,list)) or not sources or any(not _label(v) for v in sources)
                or len(set(sources))!=len(sources)):raise ProgrammedSolidFluidHeatError('unique_coefficient_sources_required')
        object.__setattr__(self,'coefficient_source_ids',tuple(sources))
        for name in ('convection_w_m2_k','emissivity','stefan_boltzmann_w_m2_k4'):
            try:value=_number(getattr(self,name),name,positive=name=='stefan_boltzmann_w_m2_k4')
            except IntegrationError as exc:raise ProgrammedSolidFluidHeatError(str(exc)) from exc
            object.__setattr__(self,name,value)
        if self.emissivity>1:raise ProgrammedSolidFluidHeatError('emissivity_exceeds_one')
        object.__setattr__(self,'_content_digest',self._current_content_digest())

    def _current_content_digest(self) -> str:
        return _digest((self.base_model,self.program,self.convection_w_m2_k,self.emissivity,
            self.stefan_boltzmann_w_m2_k4,self.coefficient_set_id,self.coefficient_version,
            self.coefficient_classification,self.coefficient_source_ids,self.surface_policy,self.allow_manufactured))

    def _check_content(self) -> None:
        try:
            current=self._current_content_digest()
        except (DeformingStorageError,TypeError,AttributeError,OverflowError) as exc:
            raise ProgrammedSolidFluidHeatError('invalid_runtime_programmed_operator_content') from exc
        if current!=self._content_digest:
            raise ProgrammedSolidFluidHeatError('runtime_programmed_operator_content_changed')

    @property
    def operator_identity(self) -> tuple:
        self._check_content()
        return ('programmed_solid_fluid_operator_v1',self._content_digest)

    @property
    def _configuration_host(self):
        return self.base_model.base_model if type(self.base_model) in (DeformingSolidHeat,FreeSolidSlab) else self.base_model
    @property
    def transport(self):return self._configuration_host.transport
    @property
    def inventory_layout(self):return self.base_model.inventory_layout
    @property
    def species_order(self):return self.base_model.species_order
    @property
    def gas_species_order(self):return self.base_model.gas_species_order
    @property
    def material_qualified(self):return False
    @property
    def source_ids(self):return tuple(sorted(set(self.base_model.source_ids+self.program.identity.source_ids+self.coefficient_source_ids)))

    def _check_state(self,state):
        self._check_content()
        return self.base_model._check_state(state)
    def breakpoints_s(self,start_s,end_s):
        boundary=self.program.breakpoints_s(start_s,end_s)
        if type(self.base_model) is DeformingSolidHeat:
            return tuple(sorted(set(boundary+self.base_model.breakpoints_s(start_s,end_s))))
        return boundary

    def _surface(self, cell_temperature, boundary, *, transport=None):
        base = self.transport if transport is None else transport
        last = len(base.storages) - 1
        area = base._face_metric(last, None)[0]
        return solve_surface_balance(
            cell_temperature_k=cell_temperature,
            gas_temperature_k=boundary.gas_temperature_k,
            radiation_temperature_k=boundary.radiation_temperature_k,
            area_m2=area, convection_w_m2_k=self.convection_w_m2_k,
            emissivity=self.emissivity,
            stefan_boltzmann_w_m2_k4=self.stefan_boltzmann_w_m2_k4,
            policy=self.surface_policy,
            conductive_into_cell=lambda surface: base._conduction(surface, cell_temperature, last, None),
            zero_conductivity=base.conductivities_w_m_k[-1] == 0,
            error_type=ProgrammedSolidFluidHeatError)

    def evaluate(self,state:ConservedState,time_s:float)->ProgrammedSolidFluidEvaluation:
        self._check_content()
        try:boundary=self.program.at(time_s)
        except BoundaryProgramError as exc:
            if str(exc)=='time_outside_program_domain':raise DomainExit(str(exc)) from exc
            raise ProgrammedSolidFluidHeatError(str(exc)) from exc
        base=self.base_model.evaluate(state,time_s)
        current=base.current_host if type(self.base_model) in (DeformingSolidHeat,FreeSolidSlab) else self.base_model
        transport=current.transport
        template=current.storages[0].fluid_template
        masses={n:template.gas_phases[n].metadata.molar_mass_kg_mol for n in self.gas_species_order}
        try:
            reservoir=ideal_gas_reservoir(pressure_pa=boundary.total_pressure_pa,temperature_k=boundary.gas_temperature_k,
                mole_fractions=boundary.mole_fractions,molar_masses_kg_mol=masses,
                gas_constant_j_mol_k=template.mechanical.gas_constant_j_mol_k)
            surface,heat,into,residual,limit,iterations,status=(
                self._surface(base.gas_states[-1].temperature_k,boundary,transport=transport)
                if type(self.base_model) in (DeformingSolidHeat,FreeSolidSlab) else self._surface(base.gas_states[-1].temperature_k,boundary))
            exchange=transport._face(base.gas_states[-1],reservoir,len(base.gas_states)-1,None)
            enthalpy=transport._enthalpy(exchange)
            fn=np.array(base.rates.face_species_mol_s);fe=np.array(base.rates.face_energy_w)
            for n in self.gas_species_order:
                index=self.species_order.index(n)
                fn[-1,index]=_sum((float(fn[-1,index]),exchange.net_mol_s[n]))
            fe[-1]=_sum((float(fe[-1]),enthalpy,-into))
            rates=Rates(fn,fe,base.rates.reaction_species_mol_s,base.rates.cell_power_w,
                        cell_power_components_w=base.rates.cell_power_components_w,
                        mechanical_rates_per_s=base.rates.mechanical_rates_per_s)
        except _FAILURES as exc:_failure(exc)
        except OverflowError as exc:raise ProgrammedSolidFluidHeatError('nonfinite_programmed_boundary') from exc
        return ProgrammedSolidFluidEvaluation(rates=rates,base_evaluation=base,boundary=boundary,reservoir=reservoir,
            surface_temperature_k=surface,heat=heat,conductive_into_cell_w=into,surface_balance_residual_w=residual,
            surface_balance_limit_w=limit,surface_iterations=iterations,surface_status=status,
            operator_identity=self.operator_identity,
            source_ids=tuple(sorted(set(self.source_ids+getattr(base,'source_ids',())))),
            qualification=('manufactured_reduced_free_slab_furnace_gas_pressure_separate_from_constant_mechanical_traction'
                if type(self.base_model) is FreeSolidSlab else 'conditional_prescribed_deforming_total_inverse_and_surface_balance_not_full_brick'
                if type(self.base_model) is DeformingSolidHeat else
                'conditional_solid_fluid_inverse_and_numerical_surface_balance_not_full_brick'))

    def __call__(self,state,time_s):return self.evaluate(state,time_s).rates
