"""Fixed solid inventories with actual solid/fluid storage and shared gas faces."""
from dataclasses import dataclass
import math
import numpy as np
from .integration import ConservedState,DomainExit,IntegrationError,Rates
from .rigid_fluid_heat import RigidFluidHeat,_num,_column,_FAILURES,_raise_failure,_sum
from .gas_transport import ideal_gas_state
from .exchanges import conduction_rate_w


class SolidFluidHeatError(IntegrationError):
    """Invalid explicit solid/fluid host contract."""


def _failure(exc):
    if str(exc) in ('solid_temperature_out_of_domain','solid_pressure_out_of_domain',
                    'no_positive_fluid_available_volume'):
        raise DomainExit(str(exc)) from exc
    _raise_failure(exc)


@dataclass(frozen=True,kw_only=True)
class InventoryLayout:
    species_order: tuple[str,...]
    liquid_column_id: str
    gas_species_order: tuple[str,...]
    solid_species_order: tuple[str,...]

    def __post_init__(self):
        for field in ('species_order','gas_species_order','solid_species_order'):
            values=getattr(self,field)
            if (not isinstance(values,(tuple,list)) or not values
                    or any(not isinstance(v,str) or not v or v!=v.strip() for v in values)
                    or len(set(values))!=len(values)):
                raise SolidFluidHeatError('explicit_unique_inventory_names_required')
            object.__setattr__(self,field,tuple(values))
        if (not isinstance(self.liquid_column_id,str) or not self.liquid_column_id
                or self.liquid_column_id!=self.liquid_column_id.strip()):
            raise SolidFluidHeatError('explicit_liquid_column_identity_required')
        expected=(self.liquid_column_id,)+self.gas_species_order+self.solid_species_order
        if len(set(expected))!=len(expected) or set(expected)!=set(self.species_order):
            raise SolidFluidHeatError('complete_disjoint_inventory_layout_required')

    @property
    def liquid_index(self):return self.species_order.index(self.liquid_column_id)

    def gas_inventory(self,row):return {n:float(row[self.species_order.index(n)]) for n in self.gas_species_order}

    def solid_inventory(self,row):return {n:float(row[self.species_order.index(n)]) for n in self.solid_species_order}


@dataclass(frozen=True)
class SolidFluidHeatEvaluation:
    rates: Rates
    storage_states: tuple
    gas_states: tuple
    storage_inverses: tuple
    qualification: str = 'conditional_fixed_solid_inventory_fluid_transport_not_brick'


@dataclass(frozen=True,kw_only=True)
class SolidFluidHeat:
    storages: tuple
    inventory_layout: InventoryLayout
    transport: RigidFluidHeat

    def __post_init__(self):
        from .solid_fluid_storage import SolidFluidStorage
        if (type(self.inventory_layout) is not InventoryLayout or type(self.transport) is not RigidFluidHeat
                or not isinstance(self.storages,(tuple,list)) or not self.storages
                or any(type(s) is not SolidFluidStorage for s in self.storages)):
            raise SolidFluidHeatError('explicit_solid_storage_layout_transport_required')
        object.__setattr__(self,'storages',tuple(self.storages))
        if (len(self.storages)!=len(self.transport.storages)
                or self.gas_species_order!=self.transport.gas_species_order
                or self.inventory_layout.liquid_column_id!=self.transport.liquid_column_id):
            raise SolidFluidHeatError('transport_inventory_identity_mismatch')
        for storage,template,width in zip(self.storages,self.transport.storages,self.transport.cell_widths_m):
            # Exact object binding retains all template caloric, water, source,
            # pressure policy and numerical envelope settings without shallow name checks.
            if storage.fluid_template is not template:
                raise SolidFluidHeatError('transport_fluid_template_identity_mismatch')
            if set(storage.solid_phases)!=set(self.inventory_layout.solid_species_order):
                raise SolidFluidHeatError('complete_solid_inventory_identity_mismatch')
            volume=self.transport.face_area_m2*width
            if not math.isclose(volume,storage.bulk_volume_m3,rel_tol=0,
                                abs_tol=2*max(math.ulp(volume),math.ulp(storage.bulk_volume_m3))):
                raise SolidFluidHeatError('transport_bulk_geometry_mismatch')
            if not self.transport.allow_manufactured and storage.allow_manufactured:
                raise SolidFluidHeatError('manufactured_requires_explicit_test_mode')

    @property
    def species_order(self):return self.inventory_layout.species_order
    @property
    def gas_species_order(self):return self.inventory_layout.gas_species_order
    @property
    def coefficient_classification(self):return self.transport.coefficient_classification
    @property
    def material_qualified(self):return False
    @property
    def source_ids(self):
        sources=set(self.transport.source_ids)
        for storage in self.storages:
            sources.update(storage.source_ids)
        return tuple(sorted(sources))

    def _check_state(self,state):
        if type(state) is not ConservedState or state.amounts_mol.shape!=(len(self.storages),len(self.species_order)):
            raise SolidFluidHeatError('state_shape_mismatch')

    def _inputs(self,row):
        return (float(row[self.inventory_layout.liquid_index]),self.inventory_layout.gas_inventory(row),
                self.inventory_layout.solid_inventory(row))

    def state_from_temperatures(self,amounts_mol,temperatures_k):
        state=ConservedState(amounts_mol,np.zeros(len(self.storages)))
        self._check_state(state)
        temperatures=_column(temperatures_k,len(self.storages),'temperatures',positive=True)
        from .solid_fluid_storage import SolidFluidStorageError
        try:
            energies=[s.evaluate_at_temperature(t,*self._inputs(row)).internal_energy_j
                      for s,t,row in zip(self.storages,temperatures,state.amounts_mol)]
        except (SolidFluidStorageError,)+_FAILURES as exc:_failure(exc)
        return ConservedState(state.amounts_mol,energies)

    def decode_inverse(self,state):
        self._check_state(state)
        from .solid_fluid_storage import SolidFluidStorageError
        try:
            return tuple(s.temperature_from_energy(float(u),*self._inputs(row),bracket,self.transport.inverse_policy)
                for s,row,u,bracket in zip(self.storages,state.amounts_mol,state.internal_energy_j,
                                           self.transport.temperature_brackets_k))
        except (SolidFluidStorageError,)+_FAILURES as exc:_failure(exc)

    def decode(self,state):return tuple(v.state for v in self.decode_inverse(state))

    def evaluate(self,state,time_s):
        _num(time_s,'time')
        inverses=self.decode_inverse(state)
        decoded=tuple(v.state for v in inverses)
        transport=self.transport
        first=transport.storages[0]
        names=self.gas_species_order
        masses={n:first.gas_phases[n].metadata.molar_mass_kg_mol for n in names}
        count=len(self.storages)
        fn=np.zeros((count+1,len(self.species_order)));fe=np.zeros(count+1)
        indices=[self.species_order.index(n) for n in names]
        try:
            gases=tuple(ideal_gas_state(self.inventory_layout.gas_inventory(row),
                temperature_k=s.mechanical.temperature_k,gas_volume_m3=s.mechanical.gas_volume_m3,
                molar_masses_kg_mol=masses,gas_constant_j_mol_k=first.mechanical.gas_constant_j_mol_k)
                for row,s in zip(state.amounts_mol,decoded))
            for face in range(1,count):
                left,right=face-1,face
                exchange=transport._face(gases[left],gases[right],left,right)
                fn[face,indices]=[exchange.net_mol_s[n] for n in names]
                heat=conduction_rate_w(gases[left].temperature_k,gases[right].temperature_k,
                    area_m2=transport.face_area_m2,left_distance_m=transport.cell_widths_m[left]/2,
                    right_distance_m=transport.cell_widths_m[right]/2,
                    left_conductivity_w_m_k=transport.conductivities_w_m_k[left],
                    right_conductivity_w_m_k=transport.conductivities_w_m_k[right])
                fe[face]=_sum((heat,transport._enthalpy(exchange)))
            if transport.outer_reservoir is not None:
                exchange=transport._face(gases[-1],transport.outer_reservoir,count-1,None)
                fn[-1,indices]=[exchange.net_mol_s[n] for n in names]
                fe[-1]=transport._enthalpy(exchange)
            if transport.outer_surface_temperature_k is not None:
                heat=conduction_rate_w(gases[-1].temperature_k,transport.outer_surface_temperature_k,
                    area_m2=transport.face_area_m2,left_distance_m=transport.cell_widths_m[-1]/4,
                    right_distance_m=transport.cell_widths_m[-1]/4,
                    left_conductivity_w_m_k=transport.conductivities_w_m_k[-1],
                    right_conductivity_w_m_k=transport.conductivities_w_m_k[-1])
                fe[-1]=_sum((fe[-1],heat))
        except _FAILURES as exc:_failure(exc)
        return SolidFluidHeatEvaluation(Rates(fn,fe,np.zeros_like(state.amounts_mol),np.zeros(count)),decoded,gases,inverses)

    def __call__(self,state,time_s):return self.evaluate(state,time_s).rates
