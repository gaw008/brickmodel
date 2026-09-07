"""Prescribed fixed-solid mechanics, total energy, relative moving fluid faces.

No water/depletion wrapper admission or free-sintering prediction is supplied.
"""
from dataclasses import dataclass,field,replace
from fractions import Fraction
import numpy as np
from .integration import ConservedState,Rates,IntegrationError,DomainExit
from .solid_fluid_heat import SolidFluidHeat,_failure
from .deforming_solid_storage import DeformingSolidStorage,DeformingStorageError,SCOPE,_digest
from .deformation_program import DeformationProgramError
from .rigid_fluid_heat import _FAILURES
from .skeleton_energy import SkeletonEnergyError
from .solid_fluid_storage import SolidFluidStorageError


class DeformingSolidHeatError(IntegrationError):pass


def _float(value):
    try:out=float(value)
    except OverflowError as exc:raise DeformingSolidHeatError('unrepresentable_mechanical_power') from exc
    if not np.isfinite(out) or (value and out==0):raise DeformingSolidHeatError('unrepresentable_mechanical_power')
    return out


@dataclass(frozen=True)
class DeformingSolidHeatEvaluation:
    rates: Rates
    motion: object
    total_inverses: tuple
    thermal_evaluation: object
    current_host: object
    pressure_for_work_pa: tuple
    energy_model_identity: tuple
    source_ids: tuple
    qualification: str='prescribed_fixed_solid_total_energy_not_free_sintering_not_wrapper_admitted'


@dataclass(frozen=True,kw_only=True)
class DeformingSolidHeat:
    base_model: SolidFluidHeat
    point_storages: tuple
    mechanical_regime: str
    transport_regime: str
    model_id: str
    version: str
    source_ids: tuple
    allow_manufactured: bool=False
    _binding: tuple=field(init=False,repr=False)
    _base_digest: str=field(init=False,repr=False)

    def __post_init__(self):
        base=self.base_model
        if type(base) is not SolidFluidHeat or not isinstance(self.point_storages,tuple) or not self.point_storages:
            raise DeformingSolidHeatError('explicit_solid_base_and_points_required')
        if len(self.point_storages)!=len(base.storages) or any(type(p) is not DeformingSolidStorage for p in self.point_storages):
            raise DeformingSolidHeatError('complete_point_storages_required')
        if base.solid_reactions is not None:raise DeformingSolidHeatError('solid_reactions_not_admitted')
        if (self.mechanical_regime!='prescribed_cellwise_quasistatic_incompressible_skeleton'
            or self.transport_regime!='manufactured_relative_moving_faces'):
            raise DeformingSolidHeatError('explicit_prescribed_relative_motion_regimes_required')
        if self.allow_manufactured is not True or base.transport.coefficient_classification!='manufactured':
            raise DeformingSolidHeatError('explicit_manufactured_transport_required')
        if not isinstance(self.source_ids,tuple) or not self.source_ids:
            raise DeformingSolidHeatError('explicit_host_sources_required')
        for value in (self.model_id,self.version)+self.source_ids:
            if not isinstance(value,str) or not value or value.strip()!=value:
                raise DeformingSolidHeatError('explicit_host_identity_required')
        motion=self.point_storages[0].motion
        object.__setattr__(self,'source_ids',tuple(sorted(set(self.source_ids+base.source_ids+motion.source_ids+
            tuple(v for p in self.point_storages for v in p.skeleton.source_ids+p.error_bounds.source_ids)))))
        for i,(p,storage) in enumerate(zip(self.point_storages,base.storages)):
            if p.template is not storage or p.skeleton.cell_index!=i or p.motion.identity!=motion.identity:
                raise DeformingSolidHeatError('point_template_cell_motion_mismatch')
        try:
            motion.validate_reference_geometry(cell_count=len(base.storages),face_area_m2=base.transport.face_area_m2,
                cell_widths_m=base.transport.cell_widths_m,gas_volumes_m3=tuple(s.bulk_volume_m3 for s in base.storages))
            digest=_digest(base)
            binding=('deforming_solid_heat_total_v1',SCOPE,_digest((digest,tuple(p.identity for p in self.point_storages),
                self.mechanical_regime,self.transport_regime,self.model_id,self.version,self.source_ids)))
        except (DeformingStorageError,DeformationProgramError) as exc:raise DeformingSolidHeatError(str(exc)) from exc
        object.__setattr__(self,'_base_digest',digest);object.__setattr__(self,'_binding',binding)

    @property
    def energy_model_identity(self):return self._binding
    @property
    def material_qualified(self):return False
    @property
    def motion(self):return self.point_storages[0].motion
    def breakpoints_s(self,start_s,end_s):return self.motion.breakpoints_s(start_s,end_s)

    def _check(self,state,tag=True):
        if type(state) is not ConservedState:raise DeformingSolidHeatError('explicit_conserved_state_required')
        if tag and state.energy_model_identity!=self.energy_model_identity:raise DeformingSolidHeatError('matching_total_energy_binding_required')
        if _digest(self.base_model)!=self._base_digest:raise DeformingSolidHeatError('runtime_base_identity_changed')
        if state.amounts_mol.shape!=(len(self.point_storages),len(self.base_model.species_order)):
            raise DeformingSolidHeatError('complete_inventory_shape_required')
        for row,p in zip(state.amounts_mol,self.point_storages):
            if self.base_model.inventory_layout.solid_inventory(row)!=dict(p.skeleton.fixed_solid_inventory_mol):
                raise DeformingSolidHeatError('fixed_solid_inventory_changed')

    def _inputs(self,row):
        layout=self.base_model.inventory_layout
        return dict(liquid_mol=float(row[layout.liquid_index]),gas_mol=layout.gas_inventory(row),solid_mol=layout.solid_inventory(row))

    def state_from_temperatures(self,amounts_mol,temperatures_k,*,time_s):
        # Forward U is a deterministic represented initial condition. Its provider
        # error is reported by forward storage, not a stochastic trajectory bound.
        rows=ConservedState(amounts_mol,np.zeros(len(self.point_storages)))
        self._check(rows,tag=False)
        if len(temperatures_k)!=len(self.point_storages):raise DeformingSolidHeatError('complete_initial_temperatures_required')
        points=tuple(p.forward(float(t),time_s=time_s,**self._inputs(row)) for p,t,row in
                     zip(self.point_storages,temperatures_k,rows.amounts_mol))
        return ConservedState(rows.amounts_mol,[p.total_energy_j for p in points],energy_model_identity=self.energy_model_identity)

    def evaluate(self,state,time_s):
        self._check(state)
        base=self.base_model;layout=base.inventory_layout
        brackets=tuple(base.dry_temperature_brackets_k[i] if row[layout.liquid_index]==0 and base.dry_temperature_brackets_k is not None
                       else base.transport.temperature_brackets_k[i] for i,row in enumerate(state.amounts_mol))
        try:
            # Represented dynamic total E is the target; current source/storage
            # error is propagated by each point inverse. RK truncation is separate.
            inverses=tuple(p.temperature_from_total_energy(p.target(float(u),0.),time_s=time_s,
                temperature_bracket_k=bracket,policy=base.transport.inverse_policy,**self._inputs(row))
                for p,u,row,bracket in zip(self.point_storages,state.internal_energy_j,state.amounts_mol,brackets))
            snap=inverses[0].state.motion
            storages=tuple(inv.state.current_storage for inv in inverses)
            transport=replace(base.transport,storages=tuple(s.fluid_template for s in storages),
                face_area_m2=float(snap.current.face_areas_m2[0]),cell_widths_m=tuple(float(x) for x in snap.current.widths_m))
            current=replace(base,storages=storages,transport=transport)
            thermal=current._assemble_decoded(state.amounts_mol,tuple(inv.thermal_inverse for inv in inverses),brackets)
            components={key:[] for key in ('elastic','interface','dissipation','pore','body')}
            pressures=[]
            for i,inv in enumerate(inverses):
                sk=inv.state.skeleton_state;p=inv.state.thermal_state.mechanical.pressure_pa;pressures.append(p)
                components['elastic'].append(sk.elastic_rate_w);components['interface'].append(sk.interface_rate_w)
                components['dissipation'].append(sk.dissipation_w)
                components['pore'].append(_float(-Fraction(p)*Fraction(float(snap.volume_rates_m3_s[i]))))
                components['body'].append(float(thermal.rates.cell_power_w[i]))
            total=[_float(sum((Fraction(values[i]) for values in components.values()),Fraction())) for i in range(len(inverses))]
            rates=Rates(thermal.rates.face_species_mol_s,thermal.rates.face_energy_w,
                thermal.rates.reaction_species_mol_s,total,components)
        except (SolidFluidStorageError,)+_FAILURES as exc:_failure(exc)
        except (DeformingStorageError,DeformationProgramError,SkeletonEnergyError) as exc:raise DeformingSolidHeatError(str(exc)) from exc
        sources=tuple(sorted(set(self.source_ids+base.source_ids+self.motion.source_ids+tuple(
            v for p in self.point_storages for v in p.skeleton.source_ids+p.error_bounds.source_ids))))
        return DeformingSolidHeatEvaluation(rates,snap,inverses,thermal,current,tuple(pressures),self.energy_model_identity,sources)

    def __call__(self,state,time_s):return self.evaluate(state,time_s).rates
