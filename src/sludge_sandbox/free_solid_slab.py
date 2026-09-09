"""Manufactured reduced common-tangent slab with actual current transport."""
from dataclasses import dataclass,field,replace
from fractions import Fraction
import math
import numpy as np
from .integration import ConservedState,Rates,IntegrationError,DomainExit
from .solid_fluid_heat import SolidFluidHeat,SolidFluidHeatEvaluation,InventoryLayout,_failure
from .solid_fluid_storage import SolidFluidStorageError,SolidFluidStorage
from .current_solid_storage import CurrentSolidStorage,CurrentSolidInverse
from .deforming_solid_storage import DeformingStorageError,_digest,_num,_label,_out,SCOPE
from .free_slab_rates import FreeSlabRates,solve_free_slab_rates
from .free_skeleton_rates import FreeSkeletonRatesError
from .skeleton_energy import SkeletonEnergyError
from .geometry import GeometryError,CurrentSlab
from .rigid_fluid_heat import _FAILURES,_column


@dataclass(frozen=True)
class FreeSolidSlabEvaluation:
    rates: Rates
    geometry: CurrentSlab
    total_inverses: tuple[CurrentSolidInverse,...]
    thermal_evaluation: SolidFluidHeatEvaluation
    current_host: SolidFluidHeat
    free: FreeSlabRates
    model_identity: tuple
    source_ids: tuple[str,...]
    qualification: str='manufactured_fixed_solid_reduced_common_tangent_relative_transport_not_material_admission'

    @property
    def storage_states(self) -> tuple:return self.thermal_evaluation.storage_states
    @property
    def storage_inverses(self) -> tuple:return self.thermal_evaluation.storage_inverses
    @property
    def gas_states(self) -> tuple:return self.thermal_evaluation.gas_states


@dataclass(frozen=True,kw_only=True)
class FreeSolidSlab:
    base_model: SolidFluidHeat
    point_storages: tuple[CurrentSolidStorage,...]
    external_pressure_pa: float
    model_id: str
    version: str
    source_ids: tuple[str,...]
    allow_manufactured: bool
    mechanical_regime: str='reduced_common_tangent_quasistatic_fixed_solid'
    transport_regime: str='manufactured_relative_moving_faces'
    solid_inventory_regime: str='fixed_solid'
    _base_digest: str=field(init=False,repr=False)
    _binding: tuple=field(init=False,repr=False)

    def __post_init__(self) -> None:
        base=self.base_model;points=self.point_storages
        if (type(base) is not SolidFluidHeat or type(points) is not tuple or not points
                or len(points)!=len(base.storages) or any(type(p) is not CurrentSolidStorage for p in points)):
            raise IntegrationError('explicit_complete_current_solid_points_required')
        if self.solid_inventory_regime not in ('fixed_solid','reacting_manufactured'):
            raise IntegrationError('explicit_solid_inventory_regime_required')
        reacting=self.solid_inventory_regime=='reacting_manufactured'
        if not reacting and any(p.solid_inventory_regime != 'fixed_solid' for p in points):
            raise IntegrationError('reacting_current_points_not_admitted_by_fixed_free_slab')
        if any(p.solid_inventory_regime!=self.solid_inventory_regime for p in points):
            raise IntegrationError('skeleton_inventory_regime_mismatch')
        if not reacting and base.solid_reactions is not None:raise IntegrationError('fixed_solid_reactions_not_admitted')
        if self.allow_manufactured is not True or base.transport.coefficient_classification!='manufactured':
            raise IntegrationError('explicit_manufactured_transport_required')
        expected_mechanics=('reduced_common_tangent_quasistatic_reacting_manufactured' if reacting
                            else 'reduced_common_tangent_quasistatic_fixed_solid')
        if (self.mechanical_regime!=expected_mechanics
                or self.transport_regime!='manufactured_relative_moving_faces'):
            raise IntegrationError('explicit_reduced_relative_regimes_required')
        if type(self.source_ids) is not tuple or not self.source_ids:raise IntegrationError('explicit_host_sources_required')
        for value in (self.model_id,self.version)+self.source_ids:_label(value)
        object.__setattr__(self,'external_pressure_pa',_num(self.external_pressure_pa,'external_pressure',nonnegative=True))
        reference=points[0].skeleton.reference
        if reference.cells!=len(points):raise IntegrationError('complete_reference_required')
        def same(a,b):return abs(a-b)<=2*max(math.ulp(a),math.ulp(b))
        if not same(base.transport.face_area_m2,reference.reference_area_m2):raise IntegrationError('reference_area_mismatch')
        for i,(p,storage,width) in enumerate(zip(points,base.storages,base.transport.cell_widths_m,strict=True)):
            if p.template is not storage or p.skeleton.cell_index!=i or p.skeleton.reference!=reference:
                raise IntegrationError('point_template_reference_cell_mismatch')
            reference_model=p.skeleton.reference_model if reacting else p.skeleton
            if reference_model.viscosity_pa_s<=0:raise IntegrationError('positive_viscosity_required')
            if not same(width,reference.half_thickness_m/reference.cells) or not same(storage.bulk_volume_m3,p.skeleton.reference_volume_m3):
                raise IntegrationError('reference_geometry_mismatch')
        sources=tuple(sorted(set(self.source_ids+base.source_ids+tuple(v for p in points for v in p.skeleton.source_ids+p.error_bounds.source_ids))))
        object.__setattr__(self,'source_ids',sources)
        digest=_digest(base);object.__setattr__(self,'_base_digest',digest)
        object.__setattr__(self,'_binding',('reacting_free_solid_slab_total_v1' if reacting else 'free_solid_slab_total_v1',SCOPE,_digest((digest,tuple(p.identity for p in points),
            self.external_pressure_pa,self.mechanical_regime,self.transport_regime,self.model_id,self.version,sources))))

    @property
    def energy_model_identity(self) -> tuple:return self._binding
    @property
    def material_qualified(self) -> bool:return False
    @property
    def species_order(self) -> tuple[str,...]:return self.base_model.species_order
    @property
    def gas_species_order(self) -> tuple[str,...]:return self.base_model.gas_species_order
    @property
    def inventory_layout(self) -> InventoryLayout:return self.base_model.inventory_layout
    @property
    def coefficient_classification(self) -> str:return 'manufactured'
    @property
    def storages(self) -> tuple[SolidFluidStorage,...]:return self.base_model.storages

    def _check_state(self,state: ConservedState,*,binding: bool=True) -> None:
        if type(state) is not ConservedState or state.amounts_mol.shape!=(len(self.point_storages),len(self.species_order)):
            raise IntegrationError('complete_slab_inventory_required')
        if state.mechanical_stretches is None:raise IntegrationError('explicit_dynamic_stretches_required')
        if binding and state.energy_model_identity!=self.energy_model_identity:raise IntegrationError('matching_free_slab_energy_binding_required')
        if _digest(self.base_model)!=self._base_digest:raise IntegrationError('runtime_base_identity_changed')
        if self.solid_inventory_regime=='fixed_solid':
            for row,p in zip(state.amounts_mol,self.point_storages,strict=True):
                if self.inventory_layout.solid_inventory(row)!=dict(p.skeleton.fixed_solid_inventory_mol):
                    raise IntegrationError('fixed_solid_inventory_changed')

    def _inputs(self,row) -> dict:
        layout=self.inventory_layout
        return dict(liquid_mol=float(row[layout.liquid_index]),gas_mol=layout.gas_inventory(row),solid_mol=layout.solid_inventory(row))

    def state_from_temperatures(self,amounts_mol,temperatures_k,*,normal_stretches,tangential_stretch) -> ConservedState:
        reference=self.point_storages[0].skeleton.reference
        reference.deform(normal_stretches,tangential_stretch=tangential_stretch)
        stretches=tuple(normal_stretches)+(tangential_stretch,)
        rows=ConservedState(amounts_mol,np.zeros(len(self.point_storages)),mechanical_stretches=stretches)
        self._check_state(rows,binding=False)
        temperatures=_column(temperatures_k,len(self.point_storages),'initial_temperature',positive=True)
        points=tuple(p.forward(float(t),normal_stretches=tuple(map(float,rows.mechanical_stretches[:-1])),
            tangential_stretch=float(rows.mechanical_stretches[-1]),**self._inputs(row))
            for p,t,row in zip(self.point_storages,temperatures,rows.amounts_mol,strict=True))
        return ConservedState(rows.amounts_mol,[p.total_energy_j for p in points],self.energy_model_identity,mechanical_stretches=rows.mechanical_stretches)

    def evaluate(self,state: ConservedState,time_s: float) -> FreeSolidSlabEvaluation:
        self._check_state(state);_num(time_s,'time')
        return self._evaluate_current_state(state)

    def evaluate_autonomous(self,state: ConservedState) -> FreeSolidSlabEvaluation:
        """State-only evaluation for the explicitly autonomous direct slab."""
        if type(self) is not FreeSolidSlab:
            raise IntegrationError('explicit_direct_free_slab_required')
        self._check_state(state)
        return self._evaluate_current_state(state)

    def _evaluate_current_state(self,state: ConservedState) -> FreeSolidSlabEvaluation:
        base=self.base_model;layout=self.inventory_layout
        normals=tuple(map(float,state.mechanical_stretches[:-1]));tangent=float(state.mechanical_stretches[-1])
        brackets=tuple(base.dry_temperature_brackets_k[i] if row[layout.liquid_index]==0 and base.dry_temperature_brackets_k is not None
            else base.transport.temperature_brackets_k[i] for i,row in enumerate(state.amounts_mol))
        try:
            inverses=tuple(p.temperature_from_total_energy(p.target(float(u),0.),normal_stretches=normals,tangential_stretch=tangent,
                temperature_bracket_k=bracket,policy=base.transport.inverse_policy,**self._inputs(row))
                for p,u,row,bracket in zip(self.point_storages,state.internal_energy_j,state.amounts_mol,brackets,strict=True))
            geometry=inverses[0].state.deformation.current
            storages=tuple(inv.state.current_storage for inv in inverses)
            transport=replace(base.transport,storages=tuple(s.fluid_template for s in storages),
                face_area_m2=float(geometry.face_areas_m2[0]),cell_widths_m=tuple(map(float,geometry.widths_m)))
            reactions=replace(base.solid_reactions,storages=storages) if base.solid_reactions is not None else None
            current=replace(base,storages=storages,transport=transport,solid_reactions=reactions)
            thermal=current._assemble_decoded(state.amounts_mol,tuple(inv.thermal_inverse for inv in inverses),brackets)
            free=solve_free_slab_rates(tuple(p.skeleton for p in self.point_storages),normal_stretches=normals,tangential_stretch=tangent,
                pore_pressures_pa=tuple(s.mechanical.pressure_pa for s in thermal.storage_states),external_pressure_pa=self.external_pressure_pa,
                solid_inventories_mol=tuple(layout.solid_inventory(row) for row in state.amounts_mol),
                solid_inventory_regime=self.solid_inventory_regime)
            if not free.zero_balance_enclosed:raise IntegrationError('free_slab_balance_not_enclosed')
            components={'external_traction':free.external_powers_w,'mechanical_constraint':free.constraint_powers_w,
                        'body':thermal.rates.cell_power_w}
            powers=[_out(sum((Fraction(float(values[i])) for values in components.values()),Fraction())) for i in range(len(inverses))]
            rates=Rates(thermal.rates.face_species_mol_s,thermal.rates.face_energy_w,thermal.rates.reaction_species_mol_s,
                powers,components,mechanical_rates_per_s=free.rates)
        except (SolidFluidStorageError,)+_FAILURES as exc:_failure(exc)
        except (DeformingStorageError,SkeletonEnergyError,FreeSkeletonRatesError,GeometryError) as exc:
            if str(exc) in ('stretch_out_of_domain','current_stretch_outside_error_domain','log_rate_out_of_domain'):
                raise DomainExit(str(exc)) from exc
            raise IntegrationError(str(exc)) from exc
        sources=tuple(sorted(set(self.source_ids+current.source_ids+free.source_ids)))
        result=FreeSolidSlabEvaluation(rates,geometry,inverses,thermal,current,free,self.energy_model_identity,sources)
        if self.solid_inventory_regime=='reacting_manufactured':
            return replace(result,qualification='manufactured_reacting_reduced_common_tangent_total_energy_not_material_admission')
        return result

    def __call__(self,state: ConservedState,time_s: float) -> Rates:return self.evaluate(state,time_s).rates
