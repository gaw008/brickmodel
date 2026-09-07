"""Explicit balanced-network aliases bound to real full-storage phase providers.

Only the existing current-bulk-concentration kinetic law is supported. Source
labels and elemental declarations are not automatically admitted material data.
"""
from dataclasses import dataclass
import math
from numbers import Integral, Real

from .reactions import ReactionNetwork,ReactionRates,ReactionError,ArrheniusMassAction
from .phase_storage import IdealGasPhase,LiquidWaterPhase
from .joined_water_vapor import JoinedWaterVapor
from .incompressible_solid import IncompressibleSolidPhase
from .solid_fluid_storage import SolidFluidStorage,SolidFluidState
from .solid_fluid_heat import InventoryLayout
from .rigid_fluid_heat import _caloric_identity


class SolidReactionError(ReactionError):
    """Ambiguous inventory/provider binding or incompatible kinetic state."""


def _label(value):
    if not isinstance(value,str) or not value or value!=value.strip():raise SolidReactionError('explicit_binding_identity_required')


def _identity(provider):
    if type(provider) is IdealGasPhase:
        caloric_identity=((JoinedWaterVapor,provider.caloric.identity) if type(provider.caloric) is JoinedWaterVapor
                          else _caloric_identity(provider.caloric))
        return (type(provider),provider.metadata,caloric_identity,provider.segment_index,provider.additional_source_ids)
    if type(provider) is IncompressibleSolidPhase:return (type(provider),provider)
    if type(provider) is LiquidWaterPhase:
        water=provider.water
        return (type(provider),provider.metadata,water.reference,tuple(sorted(water.source_asset_sha256.items())),water.numerical_limits)
    raise SolidReactionError('explicit_supported_phase_provider_required')


@dataclass(frozen=True)
class ReactionSpeciesBinding:
    reaction_species_id: str
    inventory_column_id: str
    provider: object

    def __post_init__(self):
        _label(self.reaction_species_id);_label(self.inventory_column_id)
        _identity(self.provider)


@dataclass(frozen=True)
class SolidReactionEvaluation:
    source_mol_s: tuple[float,...]
    network_rates: ReactionRates
    temperature_k: float
    bulk_volume_m3: float
    source_ids: tuple[str,...]
    binding_id: str
    version: str
    qualification: str = 'continuous_net_stoichiometric_ODE_current_bulk_concentrations_not_material_qualified'


@dataclass(frozen=True,kw_only=True)
class SolidReactionConfig:
    network: ReactionNetwork
    bindings: tuple[ReactionSpeciesBinding,...]
    storages: tuple[SolidFluidStorage,...]
    inventory_layout: InventoryLayout
    allow_manufactured: bool
    binding_id: str
    version: str
    source_ids: tuple[str,...]

    def __post_init__(self):
        if type(self.network) is not ReactionNetwork or type(self.inventory_layout) is not InventoryLayout:
            raise SolidReactionError('explicit_network_and_layout_required')
        if not isinstance(self.bindings,(tuple,list)) or not self.bindings or any(type(b) is not ReactionSpeciesBinding for b in self.bindings):
            raise SolidReactionError('explicit_species_bindings_required')
        if not isinstance(self.storages,(tuple,list)) or not self.storages or any(type(s) is not SolidFluidStorage for s in self.storages):
            raise SolidReactionError('explicit_complete_storages_required')
        object.__setattr__(self,'bindings',tuple(self.bindings));object.__setattr__(self,'storages',tuple(self.storages))
        _label(self.binding_id);_label(self.version)
        if not isinstance(self.source_ids,(tuple,list)) or not self.source_ids:raise SolidReactionError('binding_sources_required')
        for v in self.source_ids:_label(v)
        if len(set(self.source_ids))!=len(self.source_ids):raise SolidReactionError('duplicate_binding_sources')
        if type(self.allow_manufactured) is not bool:raise SolidReactionError('invalid_manufactured_gate')
        if self.contains_manufactured and not self.allow_manufactured:raise SolidReactionError('manufactured_requires_explicit_test_mode')
        ids=[b.reaction_species_id for b in self.bindings];columns=[b.inventory_column_id for b in self.bindings]
        if len(set(ids))!=len(ids) or set(ids)!=set(self.network.species_order):raise SolidReactionError('complete_unique_reaction_species_bindings_required')
        if len(set(columns))!=len(columns) or not set(columns)<=set(self.inventory_layout.species_order):
            raise SolidReactionError('injective_inventory_column_binding_required')
        by_species={s.species_id:s for s in self.network.species}
        sources=set(tuple(self.source_ids)+self.network.source_ids)
        for storage in self.storages:
            if set(storage.solid_phases)!=set(self.inventory_layout.solid_species_order) or tuple(storage.fluid_template.mechanical.gas_species_ids)!=self.inventory_layout.gas_species_order:
                raise SolidReactionError('storage_layout_phase_identity_mismatch')
            for reaction in self.network.reactions:
                law=reaction.kinetics
                if type(law) is not ArrheniusMassAction or law.concentration_basis!='current_cell_bulk_volume':
                    raise SolidReactionError('explicit_current_bulk_concentration_law_required')
                if law.gas_constant_j_mol_k!=storage.fluid_template.mechanical.gas_constant_j_mol_k:
                    raise SolidReactionError('kinetic_gas_constant_mismatch')
            for binding in self.bindings:
                definition=by_species[binding.reaction_species_id]
                column=binding.inventory_column_id
                if column==self.inventory_layout.liquid_column_id:
                    actual=LiquidWaterPhase(storage.fluid_template.mechanical.water)
                elif column in self.inventory_layout.gas_species_order:
                    actual=storage.fluid_template.gas_phases[column]
                else:actual=storage.solid_phases[column]
                m=actual.metadata
                if definition.phase!=m.phase:raise SolidReactionError('reaction_phase_binding_mismatch')
                if definition.molar_mass_kg_mol!=m.molar_mass_kg_mol:raise SolidReactionError('reaction_molar_mass_mismatch')
                if (m.energy_reference_id!='nist_298.15K_element_standard_formation'
                        or m.molar_basis_id!='mol_of_declared_species'):
                    raise SolidReactionError('reaction_common_energy_or_molar_reference_mismatch')
                if _identity(actual)!=_identity(binding.provider):raise SolidReactionError('reaction_provider_identity_mismatch')
                sources.update(m.source_ids)
            sources.update(storage.source_ids)
        object.__setattr__(self,'source_ids',tuple(sorted(sources)))

    @property
    def contains_manufactured(self):
        return self.network.contains_manufactured or any(s.geometry_classification=='manufactured_test_fixture' or
            any(p.metadata.classification=='manufactured_test_fixture' for p in (*s.solid_phases.values(),*s.fluid_template.gas_phases.values()))
            for s in self.storages)

    @property
    def material_qualified(self):return False

    def evaluate_cell(self,row,decoded,cell_index):
        if isinstance(cell_index,bool) or not isinstance(cell_index,Integral) or not 0<=cell_index<len(self.storages):
            raise SolidReactionError('invalid_cell_index')
        if type(decoded) is not SolidFluidState:raise SolidReactionError('actual_solid_fluid_decoded_state_required')
        try:
            raw=tuple(row)
            if any(isinstance(v,bool) or not isinstance(v,Real) for v in raw):raise SolidReactionError('invalid_inventory_row')
            values=tuple(float(v) for v in raw)
        except (TypeError,ValueError,OverflowError) as exc:raise SolidReactionError('invalid_inventory_row') from exc
        if len(values)!=len(self.inventory_layout.species_order) or any(not math.isfinite(v) or v<0 for v in values):
            raise SolidReactionError('invalid_inventory_row')
        layout=self.inventory_layout
        if (values[layout.liquid_index]!=decoded.mechanical.liquid_inventory_mol
                or layout.gas_inventory(values)!=dict(decoded.mechanical.gas_inventory_mol)
                or layout.solid_inventory(values)!=dict(decoded.solid_inventory_mol)):
            raise SolidReactionError('decoded_inventory_row_mismatch')
        storage=self.storages[cell_index]
        by_species={b.reaction_species_id:b for b in self.bindings}
        amounts=[values[layout.species_order.index(by_species[n].inventory_column_id)] for n in self.network.species_order]
        temperature=decoded.mechanical.temperature_k
        try:rates=self.network.rates(amounts,temperature,storage.bulk_volume_m3)
        except ReactionError as exc:raise SolidReactionError(str(exc)) from exc
        full=[0.]*len(values)
        for name,source in zip(rates.species_order,rates.source_mol_s):
            full[layout.species_order.index(by_species[name].inventory_column_id)]=source
        return SolidReactionEvaluation(tuple(full),rates,temperature,storage.bulk_volume_m3,self.source_ids,self.binding_id,self.version)
