"""Closed single-cell free mechanics and total-energy stage operator.

Fixed phase inventories: no evaporation, reactions, spatial transport or material
admission. Current geometry and pressure are decoded at every actual RK stage.
"""
from dataclasses import dataclass,field
from fractions import Fraction
import numpy as np
from .integration import ConservedState,Rates,IntegrationError,DomainExit
from .dynamic_solid_storage import DynamicSolidStorage,DynamicSolidInverse
from .deforming_solid_storage import DeformingStorageError,_digest,_num,_out,_label
from .skeleton_energy import SkeletonEnergyError
from .phase_storage import InversePolicy
from .solid_fluid_heat import InventoryLayout,_failure
from .solid_fluid_storage import SolidFluidStorageError
from .rigid_fluid_heat import _FAILURES
from .geometry import GeometryError


@dataclass(frozen=True)
class FreeSolidCellEvaluation:
    rates: Rates
    inverse: DynamicSolidInverse
    source_ids: tuple
    qualification: str='manufactured_closed_fixed_phase_single_cell_free_mechanics'


@dataclass(frozen=True,kw_only=True)
class ClosedFreeSolidCell:
    point: DynamicSolidStorage
    inventory_layout: InventoryLayout
    external_pressure_pa: float
    body_power_w: float
    temperature_bracket_k: tuple[float,float]
    inverse_policy: InversePolicy
    source_ids: tuple[str,...]
    model_id: str
    version: str
    _binding: tuple=field(init=False,repr=False)

    def __post_init__(self):
        if type(self.point) is not DynamicSolidStorage or type(self.inventory_layout) is not InventoryLayout:
            raise IntegrationError('explicit_dynamic_point_and_inventory_layout_required')
        if type(self.inverse_policy) is not InversePolicy:
            raise IntegrationError('explicit_inverse_policy_required')
        layout=self.inventory_layout
        if (set(layout.gas_species_order)!=set(self.point.template.fluid_template.gas_phases) or
                set(layout.solid_species_order)!=set(self.point.template.solid_phases)):
            raise IntegrationError('complete_point_inventory_layout_required')
        object.__setattr__(self,'external_pressure_pa',_num(self.external_pressure_pa,'external_pressure',nonnegative=True))
        object.__setattr__(self,'body_power_w',_num(self.body_power_w,'body_power'))
        bracket=self.temperature_bracket_k
        if type(bracket) is not tuple or len(bracket)!=2:
            raise IntegrationError('explicit_temperature_bracket_required')
        low,high=(_num(v,'temperature_bracket') for v in bracket)
        if not 0<low<high:raise IntegrationError('invalid_temperature_bracket')
        object.__setattr__(self,'temperature_bracket_k',(low,high))
        if type(self.source_ids) is not tuple or not self.source_ids:
            raise IntegrationError('explicit_boundary_sources_required')
        for value in self.source_ids+(self.model_id,self.version):_label(value)
        object.__setattr__(self,'_binding',('closed_free_solid_cell_v1',_digest((
            self.point.identity,layout,self.external_pressure_pa,self.body_power_w,
            self.temperature_bracket_k,self.inverse_policy,self.source_ids,self.model_id,self.version))))

    @property
    def energy_model_identity(self):return self._binding

    def _inputs(self,row):
        layout=self.inventory_layout
        return dict(liquid_mol=float(row[layout.liquid_index]),gas_mol=layout.gas_inventory(row),
                    solid_mol=layout.solid_inventory(row),external_pressure_pa=self.external_pressure_pa)

    def _check(self,state,*,binding=True):
        if type(state) is not ConservedState or state.amounts_mol.shape!=(1,len(self.inventory_layout.species_order)):
            raise IntegrationError('complete_single_cell_inventory_required')
        if state.mechanical_stretches is None:
            raise IntegrationError('explicit_dynamic_stretches_required')
        if binding and state.energy_model_identity!=self.energy_model_identity:
            raise IntegrationError('matching_free_cell_energy_binding_required')

    def state_from_temperature(self,amounts_mol,temperature_k,*,normal_stretch,tangential_stretch):
        provisional=ConservedState(amounts_mol,[0.],mechanical_stretches=[normal_stretch,tangential_stretch])
        self._check(provisional,binding=False)
        point=self.point.forward(temperature_k,normal_stretch=float(provisional.mechanical_stretches[0]),
            tangential_stretch=float(provisional.mechanical_stretches[1]),**self._inputs(provisional.amounts_mol[0]))
        return ConservedState(provisional.amounts_mol,[point.total_energy_j],self.energy_model_identity,
                              mechanical_stretches=provisional.mechanical_stretches)

    def evaluate(self,state,time_s):
        self._check(state);_num(time_s,'time')
        n,t=map(float,state.mechanical_stretches)
        try:
            inverse=self.point.temperature_from_total_energy(self.point.target(float(state.internal_energy_j[0]),0.),
                normal_stretch=n,tangential_stretch=t,temperature_bracket_k=self.temperature_bracket_k,
                policy=self.inverse_policy,**self._inputs(state.amounts_mol[0]))
        except (SolidFluidStorageError,)+_FAILURES as exc:
            _failure(exc)
        except (DeformingStorageError,SkeletonEnergyError,GeometryError) as exc:
            if str(exc) in ('stretch_out_of_domain','current_stretch_outside_error_domain','log_rate_out_of_domain'):
                raise DomainExit(str(exc)) from exc
            raise IntegrationError(str(exc)) from exc
        free=inverse.state.free_rates
        if not free.zero_balance_enclosed:
            raise IntegrationError('free_traction_balance_not_enclosed')
        # Total E already contains recoverable storage: add only external work.
        parts={'external_traction':[free.external_power_w],'body':[self.body_power_w]}
        try:
            power=_out(Fraction(free.external_power_w)+Fraction(self.body_power_w))
        except DeformingStorageError as exc:
            raise IntegrationError(str(exc)) from exc
        columns=len(self.inventory_layout.species_order)
        rates=Rates(np.zeros((2,columns)),np.zeros(2),np.zeros((1,columns)),[power],parts,
                    mechanical_rates_per_s=free.rates)
        sources=tuple(sorted(set(self.source_ids+self.point.skeleton.source_ids+
            self.point.error_bounds.source_ids+inverse.state.thermal_state.source_ids)))
        return FreeSolidCellEvaluation(rates,inverse,sources)

    def __call__(self,state,time_s):return self.evaluate(state,time_s).rates
