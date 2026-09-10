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


@dataclass(frozen=True,kw_only=True)
class LiquidTransportConfig:
    relations: tuple
    connections: tuple
    allow_manufactured: bool = False

    def __post_init__(self):
        from .liquid_transport import SaturationMobilityTable,LiquidConnection
        if (not isinstance(self.relations,(tuple,list)) or not self.relations
                or any(type(v) is not SaturationMobilityTable for v in self.relations)
                or not isinstance(self.connections,(tuple,list))
                or any(type(v) is not LiquidConnection for v in self.connections)
                or len(self.connections)!=len(self.relations)-1
                or type(self.allow_manufactured) is not bool):
            raise SolidFluidHeatError('explicit_liquid_relations_connections_required')
        object.__setattr__(self,'relations',tuple(self.relations))
        object.__setattr__(self,'connections',tuple(self.connections))
        if self.manufactured and not self.allow_manufactured:
            raise SolidFluidHeatError('manufactured_liquid_requires_explicit_test_mode')

    @property
    def manufactured(self):
        return any(v.classification=='manufactured_test_fixture' for v in self.relations+self.connections)

    @property
    def source_ids(self):return tuple(sorted({i for v in self.relations+self.connections for i in v.source_ids}))


@dataclass(frozen=True)
class SolidFluidHeatEvaluation:
    rates: Rates
    storage_states: tuple
    gas_states: tuple
    storage_inverses: tuple
    qualification: str = 'conditional_fixed_solid_inventory_fluid_transport_not_brick'
    liquid_faces: tuple = ()
    liquid_pressure_interval_scope: str = 'fixed_decoded_temperature'
    full_inverse_liquid_direction_certified: bool = False
    reaction_cells: tuple = ()
    temperature_brackets_k: tuple = ()
    inverse_bracket_policy_id: str | None = None
    inverse_bracket_policy_version: str | None = None
    inverse_bracket_policy_reason: str | None = None
    inverse_bracket_policy_classification: str = 'numerical_policy'


@dataclass(frozen=True,kw_only=True)
class SolidFluidHeat:
    storages: tuple
    inventory_layout: InventoryLayout
    transport: RigidFluidHeat
    liquid_transport: LiquidTransportConfig | None = None
    solid_reactions: object | None = None
    dry_temperature_brackets_k: tuple | None = None
    inverse_bracket_policy_id: str | None = None
    inverse_bracket_policy_version: str | None = None
    inverse_bracket_policy_reason: str | None = None

    def __post_init__(self):
        from .solid_fluid_storage import SolidFluidStorage
        if (type(self.inventory_layout) is not InventoryLayout or type(self.transport) is not RigidFluidHeat
                or not isinstance(self.storages,(tuple,list)) or not self.storages
                or any(type(s) is not SolidFluidStorage for s in self.storages)):
            raise SolidFluidHeatError('explicit_solid_storage_layout_transport_required')
        object.__setattr__(self,'storages',tuple(self.storages))
        dry=self.dry_temperature_brackets_k
        labels=(self.inverse_bracket_policy_id,self.inverse_bracket_policy_version,self.inverse_bracket_policy_reason)
        if dry is None:
            if any(v is not None for v in labels):
                raise SolidFluidHeatError('inverse_bracket_policy_without_dry_brackets')
        else:
            if any(not isinstance(v,str) or not v or v!=v.strip() for v in labels):
                raise SolidFluidHeatError('explicit_inverse_bracket_policy_identity_reason_required')
            if not isinstance(dry,(tuple,list)) or len(dry)!=len(self.storages):
                raise SolidFluidHeatError('per_cell_dry_temperature_brackets_required')
            brackets=[]
            for pair in dry:
                if not isinstance(pair,(tuple,list)) or len(pair)!=2:
                    raise SolidFluidHeatError('invalid_dry_temperature_bracket')
                try:lo,hi=(_num(v,'dry_temperature_bracket',positive=True) for v in pair)
                except IntegrationError as exc:raise SolidFluidHeatError(str(exc)) from exc
                if lo>=hi:raise SolidFluidHeatError('invalid_dry_temperature_bracket_order')
                brackets.append((lo,hi))
            object.__setattr__(self,'dry_temperature_brackets_k',tuple(brackets))
        if self.solid_reactions is not None:
            from .solid_reactions import SolidReactionConfig
            config=self.solid_reactions
            if (type(config) is not SolidReactionConfig or config.inventory_layout!=self.inventory_layout
                    or len(config.storages)!=len(self.storages)
                    or any(a is not b for a,b in zip(config.storages,self.storages))):
                raise SolidFluidHeatError('reaction_storage_layout_identity_mismatch')
            if config.contains_manufactured and not self.transport.allow_manufactured:
                raise SolidFluidHeatError('manufactured_reaction_requires_explicit_test_mode')
        if self.liquid_transport is not None:
            if self.transport.spherical_geometry is not None:
                raise SolidFluidHeatError('spherical_liquid_transport_not_supported')
            if type(self.liquid_transport) is not LiquidTransportConfig or len(self.liquid_transport.relations)!=len(self.storages):
                raise SolidFluidHeatError('per_cell_liquid_configuration_required')
            if self.liquid_transport.manufactured and not self.transport.allow_manufactured:
                raise SolidFluidHeatError('manufactured_liquid_requires_explicit_test_mode')
        if (len(self.storages)!=len(self.transport.storages)
                or self.gas_species_order!=self.transport.gas_species_order
                or self.inventory_layout.liquid_column_id!=self.transport.liquid_column_id):
            raise SolidFluidHeatError('transport_inventory_identity_mismatch')
        for index,(storage,template,width) in enumerate(zip(self.storages,self.transport.storages,self.transport.cell_widths_m)):
            # Exact object binding retains all template caloric, water, source,
            # pressure policy and numerical envelope settings without shallow name checks.
            if storage.fluid_template is not template:
                raise SolidFluidHeatError('transport_fluid_template_identity_mismatch')
            if set(storage.solid_phases)!=set(self.inventory_layout.solid_species_order):
                raise SolidFluidHeatError('complete_solid_inventory_identity_mismatch')
            volume=self.transport.cell_bulk_volume_m3(index)
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
    def has_manufactured_liquid_transport(self):
        return self.liquid_transport is not None and self.liquid_transport.manufactured
    @property
    def has_manufactured_reactions(self):
        return self.solid_reactions is not None and self.solid_reactions.contains_manufactured
    @property
    def material_qualified(self):return False
    @property
    def source_ids(self):
        sources=set(self.transport.source_ids)
        if self.liquid_transport is not None:sources.update(self.liquid_transport.source_ids)
        if self.solid_reactions is not None:sources.update(self.solid_reactions.source_ids)
        for storage in self.storages:
            sources.update(storage.source_ids)
        return tuple(sorted(sources))

    def _check_state(self,state):
        if type(state) is not ConservedState or state.amounts_mol.shape!=(len(self.storages),len(self.species_order)):
            raise SolidFluidHeatError('state_shape_mismatch')
        if state.mechanical_stretches is not None:
            raise SolidFluidHeatError('unsupported_mechanical_state')
        if state.energy_model_identity is not None:
            raise SolidFluidHeatError('unsupported_energy_model_identity')

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

    def temperature_brackets_for(self,state):
        """Select a numerical search interval, never alter a material domain."""
        self._check_state(state)
        return tuple(self.dry_temperature_brackets_k[i]
                     if self.dry_temperature_brackets_k is not None
                     and row[self.inventory_layout.liquid_index]==0 else wet
                     for i,(row,wet) in enumerate(zip(state.amounts_mol,self.transport.temperature_brackets_k)))

    def decode_inverse(self,state):
        self._check_state(state)
        from .solid_fluid_storage import SolidFluidStorageError
        try:
            return tuple(s.temperature_from_energy(float(u),*self._inputs(row),bracket,self.transport.inverse_policy)
                for s,row,u,bracket in zip(self.storages,state.amounts_mol,state.internal_energy_j,
                                           self.temperature_brackets_for(state)))
        except (SolidFluidStorageError,)+_FAILURES as exc:_failure(exc)

    def decode(self,state):return tuple(v.state for v in self.decode_inverse(state))

    def _liquid_faces(self,decoded):
        if self.liquid_transport is None:return ()
        from .liquid_transport import LiquidTransportState,liquid_face_exchange,LiquidTransportError,LiquidTransportDomainError
        from .phase_storage import LiquidWaterPhase
        states=[]
        try:
            for closed,storage in zip(decoded,self.storages):
                mechanical=closed.mechanical
                water=storage.fluid_template.mechanical.water
                volume=enthalpy=None
                if mechanical.liquid_inventory_mol>0:
                    point=water.state_tp(mechanical.temperature_k,mechanical.liquid_pressure_pa,phase='liquid')
                    volume=point.molar_mass_kg_mol/point.density_kg_m3
                    enthalpy=point.enthalpy_j_mol
                states.append(LiquidTransportState(temperature_k=mechanical.temperature_k,
                    pressure_pa=mechanical.pressure_pa,inventory_mol=mechanical.liquid_inventory_mol,
                    saturation=mechanical.liquid_volume_m3/closed.available_pore_volume_m3,
                    pressure_error_pa=closed.pressure_error_bound_pa,molar_volume_m3_mol=volume,
                    enthalpy_j_mol=enthalpy,metadata=LiquidWaterPhase(water).metadata,
                    provider_id=('iapws95_real_fluid_helmholtz' if water.implementation is None else water.implementation.provider_id),
                    provider_version=('1.5.5' if water.implementation is None else water.implementation.provider_version),
                    source_asset_sha256=tuple(sorted(water.source_asset_sha256.items()))))
            config=self.liquid_transport
            return tuple(liquid_face_exchange(states[i],states[i+1],left_relation=config.relations[i],
                right_relation=config.relations[i+1],connection=connection,area_m2=self.transport.face_area_m2,
                left_distance_m=self.transport.cell_widths_m[i]/2,right_distance_m=self.transport.cell_widths_m[i+1]/2,
                allow_manufactured=config.allow_manufactured) for i,connection in enumerate(config.connections))
        except LiquidTransportDomainError as exc:raise DomainExit(str(exc)) from exc
        except LiquidTransportError as exc:raise SolidFluidHeatError(str(exc)) from exc
        except _FAILURES as exc:_failure(exc)

    def evaluate(self,state,time_s):
        _num(time_s,'time')
        inverses=self.decode_inverse(state)
        return self._assemble_decoded(state.amounts_mol,inverses,self.temperature_brackets_for(state))

    def _assemble_decoded(self,amounts_mol,storage_inverses,temperature_brackets_k):
        """Private assembly from validated inverses; never solves another target."""
        from .solid_fluid_storage import SolidFluidInverse
        from fractions import Fraction
        amounts_mol=np.asarray(amounts_mol)
        inverses=tuple(storage_inverses)
        if amounts_mol.shape!=(len(self.storages),len(self.species_order)) or len(inverses)!=len(self.storages):
            raise SolidFluidHeatError('decoded_assembly_shape')
        if len(temperature_brackets_k)!=len(inverses):raise SolidFluidHeatError('decoded_bracket_shape')
        for row,inv,storage,bracket in zip(amounts_mol,inverses,self.storages,temperature_brackets_k):
            if type(inv) is not SolidFluidInverse:raise SolidFluidHeatError('original_thermal_inverse_required')
            state=inv.state;m=state.mechanical
            if (m.liquid_inventory_mol!=float(row[self.inventory_layout.liquid_index])
                or dict(m.gas_inventory_mol)!=self.inventory_layout.gas_inventory(row)
                or dict(state.solid_inventory_mol)!=self.inventory_layout.solid_inventory(row)):
                raise SolidFluidHeatError('decoded_inventory_mismatch')
            volume=Fraction(state.available_pore_volume_m3)+Fraction(state.solid_volume_m3)
            if abs(volume-Fraction(storage.bulk_volume_m3))>2*Fraction(math.ulp(storage.bulk_volume_m3)):
                raise SolidFluidHeatError('decoded_geometry_mismatch')
            if state.source_ids!=storage.source_ids:raise SolidFluidHeatError('decoded_source_mismatch')
            if not bracket[0]<=m.temperature_k<=bracket[1]:raise SolidFluidHeatError('decoded_temperature_outside_bracket')
        decoded=tuple(v.state for v in inverses)
        transport=self.transport
        first=transport.storages[0]
        liquid_faces=self._liquid_faces(decoded)
        reactions=np.zeros_like(amounts_mol)
        reaction_cells=()
        if self.solid_reactions is not None:
            from .solid_reactions import SolidReactionError
            try:
                reaction_cells=tuple(self.solid_reactions.evaluate_cell(row,closed,i)
                    for i,(row,closed) in enumerate(zip(amounts_mol,decoded)))
                reactions=np.array([cell.source_mol_s for cell in reaction_cells],dtype=float)
            except SolidReactionError as exc:
                if str(exc).startswith('temperature_out_of_kinetic_domain:'):
                    raise DomainExit(str(exc)) from exc
                raise SolidFluidHeatError(str(exc)) from exc
        names=self.gas_species_order
        masses={n:first.gas_phases[n].metadata.molar_mass_kg_mol for n in names}
        count=len(self.storages)
        fn=np.zeros((count+1,len(self.species_order)));fe=np.zeros(count+1)
        indices=[self.species_order.index(n) for n in names]
        try:
            gases=tuple(ideal_gas_state(self.inventory_layout.gas_inventory(row),
                temperature_k=s.mechanical.temperature_k,gas_volume_m3=s.mechanical.gas_volume_m3,
                molar_masses_kg_mol=masses,gas_constant_j_mol_k=first.mechanical.gas_constant_j_mol_k)
                for row,s in zip(amounts_mol,decoded))
            for face in range(1,count):
                left,right=face-1,face
                exchange=transport._face(gases[left],gases[right],left,right)
                fn[face,indices]=[exchange.net_mol_s[n] for n in names]
                heat=transport._conduction(gases[left].temperature_k,gases[right].temperature_k,left,right)
                liquid=liquid_faces[face-1] if liquid_faces else None
                if liquid is not None:fn[face,self.inventory_layout.liquid_index]=liquid.molar_flow_mol_s
                fe[face]=_sum((heat,transport._enthalpy(exchange),liquid.enthalpy_flow_w if liquid is not None else 0.))
            if transport.outer_reservoir is not None:
                exchange=transport._face(gases[-1],transport.outer_reservoir,count-1,None)
                fn[-1,indices]=[exchange.net_mol_s[n] for n in names]
                fe[-1]=transport._enthalpy(exchange)
            if transport.outer_surface_temperature_k is not None:
                heat=transport._conduction(gases[-1].temperature_k,transport.outer_surface_temperature_k,count-1,None)
                fe[-1]=_sum((fe[-1],heat))
        except _FAILURES as exc:_failure(exc)
        return SolidFluidHeatEvaluation(Rates(fn,fe,reactions,np.zeros(count)),decoded,gases,inverses,liquid_faces=liquid_faces,reaction_cells=reaction_cells,
            temperature_brackets_k=tuple(temperature_brackets_k),
            inverse_bracket_policy_id=self.inverse_bracket_policy_id,
            inverse_bracket_policy_version=self.inverse_bracket_policy_version,
            inverse_bracket_policy_reason=self.inverse_bracket_policy_reason)

    def __call__(self,state,time_s):return self.evaluate(state,time_s).rates
