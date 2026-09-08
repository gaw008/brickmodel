"""Shared gas/heat faces with actual per-cell liquid/gas mechanical caloric decode.

Liquid inventory has no face flux in this intermediate fixed-geometry model.
No phase change, liquid transport, solid storage or brick qualification is implied.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Real
from types import MappingProxyType

import numpy as np

from .exchanges import ExchangeError, conduction_rate_w
from .gas_heat_model import _mobility, _serial_coefficient, GasHeatModelError
from .gas_transport import GasState, GasTransportError, face_exchange, ideal_gas_state
from .integration import ConservedState, DomainExit, IntegrationError, Rates
from .ideal_water_vapor import IdealWaterVapor, IdealWaterVaporError
from .phase_storage import InversePolicy, PhaseStorageError
from .rigid_storage import ClosedStorageInverse, ClosedStorageState, RigidStorage, RigidStorageError
from .rigid_water_gas import RigidClosureDomainError, RigidClosureNumericalError
from .thermochemistry import ThermochemistryError
from .water_properties import WaterDomainError, WaterNumericalError


class RigidFluidHeatError(IntegrationError):
    """Configuration, representation or conditional inverse contract failure."""


def _num(value,name,*,positive=False,nonnegative=False):
    try:
        value=float(value) if isinstance(value,Real) and not isinstance(value,bool) else math.nan
    except (ValueError,OverflowError):value=math.nan
    if not math.isfinite(value) or (positive and value<=0) or (nonnegative and value<0):
        raise RigidFluidHeatError('invalid_'+name)
    return value


def _label(value):
    return isinstance(value,str) and bool(value) and value==value.strip()


def _sources(values):
    if (not isinstance(values,(tuple,list)) or not values or any(not _label(v) for v in values)
            or len(set(values))!=len(values)):
        raise RigidFluidHeatError('explicit_unique_sources_required')
    return tuple(values)


def _column(values,count,name,*,positive=False):
    if not isinstance(values,(tuple,list)) or len(values)!=count:
        raise RigidFluidHeatError('invalid_'+name+'_shape')
    return tuple(_num(v,name,positive=positive,nonnegative=True) for v in values)


def _sum(values):
    try:return _num(math.fsum(values),'face_energy')
    except OverflowError as exc:raise RigidFluidHeatError('nonfinite_face_energy') from exc


def _caloric_identity(caloric):
    if type(caloric) is IdealWaterVapor:
        # Independently verified loads have distinct internal EOS instances.
        # Compare the complete immutable scientific/numerical identity, not
        # private Python instance identity, while retaining the source hashes.
        return (type(caloric), caloric.species_id, caloric.method_id,
                caloric.classification, caloric.temperature_range_k,
                caloric.gas_constant_j_mol_k, caloric.constant_source_ids,
                caloric.constant_derivation, caloric.reference,
                tuple(sorted(caloric.source_asset_sha256.items())),
                caloric._water.numerical_limits)
    # Shomate and continuous derived objects contain immutable value records,
    # including all coefficients, source IDs, selected anchor and version.
    return (type(caloric), caloric)


def _raise_failure(exc):
    reason=str(exc)
    domain_reasons={
        'temperature_outside_error_envelope','energy_outside_closed_temperature_bracket',
        'temperature_out_of_domain','temperature_out_of_phase_domain',
        'positive_total_gas_inventory_required','pure_gas_pressure_out_of_explicit_bracket',
        'no_root_in_stable_pressure_bracket_or_insufficient_volume',
    }
    if (isinstance(exc,WaterDomainError) or reason in domain_reasons
            or reason.startswith('unstable_liquid_pressure_bracket_or_water_domain:')):
        raise DomainExit(reason) from exc
    raise RigidFluidHeatError(reason) from exc


_FAILURES=(RigidStorageError,RigidClosureDomainError,RigidClosureNumericalError,
           WaterDomainError,WaterNumericalError,ThermochemistryError,PhaseStorageError,
           GasTransportError,ExchangeError,GasHeatModelError,IdealWaterVaporError)


@dataclass(frozen=True)
class FluidHeatEvaluation:
    rates: Rates
    storage_states: tuple[ClosedStorageState,...]
    gas_states: tuple[GasState,...]
    storage_inverses: tuple[ClosedStorageInverse,...]
    qualification: str = 'conditional_fixed_liquid_rigid_fluid_transport_not_brick'


@dataclass(frozen=True,kw_only=True)
class RigidFluidHeat:
    storages: tuple[RigidStorage,...]
    gas_species_order: tuple[str,...]
    liquid_column_id: str
    face_area_m2: float
    cell_widths_m: tuple[float,...]
    conductivities_w_m_k: tuple[float,...]
    effective_diffusivities_m2_s: Mapping[str,tuple[float,...]]
    permeability_m2: tuple[float,...]
    relative_permeability: tuple[float,...]
    viscosity_pa_s: tuple[float,...]
    temperature_brackets_k: tuple[tuple[float,float],...]
    inverse_policy: InversePolicy
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    coefficient_source_ids: tuple[str,...]
    allow_manufactured: bool = False
    outer_reservoir: GasState | None = None
    outer_reservoir_source_ids: tuple[str,...] = ()
    outer_surface_temperature_k: float | None = None
    outer_heat_source_ids: tuple[str,...] = ()

    def __post_init__(self):
        if (not isinstance(self.storages,(tuple,list)) or not self.storages
                or any(type(s) is not RigidStorage for s in self.storages)):
            raise RigidFluidHeatError('explicit_cell_storages_required')
        object.__setattr__(self,'storages',tuple(self.storages))
        count=len(self.storages)
        names=self.gas_species_order
        if (not isinstance(names,(tuple,list)) or not names or any(not _label(n) for n in names)
                or len(set(names))!=len(names)):
            raise RigidFluidHeatError('explicit_unique_gas_species_required')
        names=tuple(names)
        object.__setattr__(self,'gas_species_order',names)
        if not _label(self.liquid_column_id) or self.liquid_column_id in names:
            raise RigidFluidHeatError('distinct_liquid_column_identity_required')
        if type(self.allow_manufactured) is not bool:
            raise RigidFluidHeatError('invalid_manufactured_gate')
        if self.coefficient_classification not in ('manufactured','literature_candidate'):
            raise RigidFluidHeatError('invalid_coefficient_classification')
        if not _label(self.coefficient_set_id) or not _label(self.coefficient_version):
            raise RigidFluidHeatError('explicit_coefficient_identity_required')
        object.__setattr__(self,'coefficient_source_ids',_sources(self.coefficient_source_ids))
        first=self.storages[0]
        for storage in self.storages:
            if storage.mechanical.gas_species_ids!=names:
                raise RigidFluidHeatError('complete_ordered_storage_gas_species_mismatch')
            for name in names:
                phase,reference=storage.gas_phases[name],first.gas_phases[name]
                if (phase.metadata!=reference.metadata or _caloric_identity(phase.caloric)!=_caloric_identity(reference.caloric)
                        or phase.segment_index!=reference.segment_index
                        or phase._curve.gas_constant_j_mol_k!=first.mechanical.gas_constant_j_mol_k):
                    raise RigidFluidHeatError('cross_cell_caloric_identity_mismatch')
                if phase.metadata.classification=='manufactured_test_fixture' and not self.allow_manufactured:
                    raise RigidFluidHeatError('manufactured_requires_explicit_test_mode')
            if (storage.mechanical.water.reference!=first.mechanical.water.reference
                    or storage.mechanical.water.source_asset_sha256!=first.mechanical.water.source_asset_sha256):
                raise RigidFluidHeatError('cross_cell_liquid_reference_mismatch')
        if self.coefficient_classification=='manufactured' and not self.allow_manufactured:
            raise RigidFluidHeatError('manufactured_requires_explicit_test_mode')
        area=_num(self.face_area_m2,'area',positive=True)
        object.__setattr__(self,'face_area_m2',area)
        for name in ('cell_widths_m','conductivities_w_m_k','permeability_m2','relative_permeability','viscosity_pa_s'):
            object.__setattr__(self,name,_column(getattr(self,name),count,name,
                positive=name in ('cell_widths_m','viscosity_pa_s')))
        if any(v>1 for v in self.relative_permeability):
            raise RigidFluidHeatError('relative_permeability_exceeds_one')
        for storage,width in zip(self.storages,self.cell_widths_m):
            if width/4==0 or storage.mechanical.available_pore_volume_m3>_num(area*width,'bulk_volume',positive=True):
                raise RigidFluidHeatError('cell_available_volume_exceeds_bulk_or_unresolvable_width')
        diffusion=self.effective_diffusivities_m2_s
        if not isinstance(diffusion,Mapping) or set(diffusion)!=set(names):
            raise RigidFluidHeatError('complete_diffusivity_keys_required')
        object.__setattr__(self,'effective_diffusivities_m2_s',MappingProxyType({
            n:_column(diffusion[n],count,'diffusivity') for n in names}))
        if type(self.inverse_policy) is not InversePolicy:
            raise RigidFluidHeatError('explicit_inverse_policy_required')
        ranges=self.temperature_brackets_k
        if not isinstance(ranges,(tuple,list)) or len(ranges)!=count:
            raise RigidFluidHeatError('explicit_cell_temperature_brackets_required')
        brackets=[]
        for storage,entry in zip(self.storages,ranges):
            pair=_column(entry,2,'temperature_bracket',positive=True)
            low,high=storage.envelope.temperature_range_k
            if not low<=pair[0]<pair[1]<=high:
                raise RigidFluidHeatError('temperature_bracket_outside_storage_envelope')
            brackets.append(pair)
        object.__setattr__(self,'temperature_brackets_k',tuple(brackets))
        if self.outer_reservoir is not None:
            gas=self.outer_reservoir
            masses={n:first.gas_phases[n].metadata.molar_mass_kg_mol for n in names}
            if (type(gas) is not GasState or gas.molar_masses_kg_mol!=masses
                    or gas.gas_constant_j_mol_k!=first.mechanical.gas_constant_j_mol_k):
                raise RigidFluidHeatError('outer_reservoir_identity_mismatch')
            object.__setattr__(self,'outer_reservoir_source_ids',_sources(self.outer_reservoir_source_ids))
        elif self.outer_reservoir_source_ids:
            raise RigidFluidHeatError('orphan_reservoir_sources')
        if self.outer_surface_temperature_k is not None:
            object.__setattr__(self,'outer_surface_temperature_k',_num(
                self.outer_surface_temperature_k,'surface_temperature',positive=True))
            object.__setattr__(self,'outer_heat_source_ids',_sources(self.outer_heat_source_ids))
        elif self.outer_heat_source_ids:
            raise RigidFluidHeatError('orphan_heat_sources')

    @property
    def species_order(self):
        return (self.liquid_column_id,)+self.gas_species_order

    @property
    def scientific_status(self):
        return 'conditional_fixed_liquid_rigid_fluid_transport_not_brick'

    @property
    def material_qualified(self):
        return False

    @property
    def source_ids(self):
        sources=set(self.coefficient_source_ids+self.outer_heat_source_ids+self.outer_reservoir_source_ids)
        for storage in self.storages:
            sources.update(storage.envelope.source_ids)
            sources.update(storage.mechanical.water.source_ids)
            sources.update(storage.mechanical.constant_source_ids)
            for phase in storage.gas_phases.values():sources.update(phase.metadata.source_ids)
        return tuple(sorted(sources))

    def _check_state(self,state):
        if type(state) is not ConservedState or state.amounts_mol.shape!=(len(self.storages),len(self.species_order)):
            raise RigidFluidHeatError('state_shape_mismatch')
        if state.mechanical_stretches is not None:
            raise RigidFluidHeatError('unsupported_mechanical_state')
        if state.energy_model_identity is not None:
            raise RigidFluidHeatError('unsupported_energy_model_identity')

    def _gas_inventory(self,row):
        return {n:float(v) for n,v in zip(self.gas_species_order,row[1:])}

    def state_from_temperatures(self,amounts_mol,temperatures_k):
        state=ConservedState(amounts_mol,np.zeros(len(self.storages)))
        self._check_state(state)
        temperatures=_column(temperatures_k,len(self.storages),'temperatures',positive=True)
        try:
            energies=[storage.evaluate_at_temperature(t,float(row[0]),self._gas_inventory(row)).internal_energy_j
                      for storage,t,row in zip(self.storages,temperatures,state.amounts_mol)]
        except _FAILURES as exc:_raise_failure(exc)
        return ConservedState(state.amounts_mol,energies)

    def decode(self,state):
        return tuple(result.state for result in self.decode_inverse(state))

    def decode_inverse(self,state):
        self._check_state(state)
        try:
            return tuple(storage.temperature_from_energy(float(u),float(row[0]),self._gas_inventory(row),
                         bracket,self.inverse_policy) for storage,row,u,bracket in zip(
                             self.storages,state.amounts_mol,state.internal_energy_j,self.temperature_brackets_k))
        except _FAILURES as exc:_raise_failure(exc)

    def _face(self,left,right,left_index,right_index):
        dl=self.cell_widths_m[left_index]/2
        dr=self.cell_widths_m[right_index]/2 if right_index is not None else 0.
        mobility=_mobility(self.permeability_m2[left_index],self.relative_permeability[left_index],self.viscosity_pa_s[left_index])
        viscosity=self.viscosity_pa_s[left_index]
        diffusion={n:v[left_index] for n,v in self.effective_diffusivities_m2_s.items()}
        if right_index is not None:
            right_mobility=_mobility(self.permeability_m2[right_index],self.relative_permeability[right_index],self.viscosity_pa_s[right_index])
            mobility=_serial_coefficient(mobility,right_mobility,dl,dr)
            weight=dr/(dl+dr)
            viscosity=weight*viscosity+(1-weight)*self.viscosity_pa_s[right_index]
            diffusion={n:_serial_coefficient(v[left_index],v[right_index],dl,dr)
                       for n,v in self.effective_diffusivities_m2_s.items()}
        permeability=_num(mobility*viscosity,'assembled_permeability',nonnegative=True)
        if mobility and permeability==0:raise RigidFluidHeatError('unresolvable_mobility_factorization')
        return face_exchange(left,right,area_m2=self.face_area_m2,distance_m=dl+dr,
            face_left_weight=dr/(dl+dr),effective_diffusivities_m2_s=diffusion,
            permeability_m2=permeability,relative_permeability=1.,viscosity_pa_s=viscosity)

    def _enthalpy(self,exchange):
        terms=[]
        for name in self.gas_species_order:
            curve=self.storages[0].gas_phases[name]._curve
            d,a=exchange.diffusive_mol_s[name],exchange.advective_mol_s[name]
            if d:terms.append(d*curve.enthalpy_j_mol(exchange.face_temperature_k))
            if a:terms.append(a*curve.enthalpy_j_mol(exchange.advective_donor_temperature_k))
        return _sum(terms)

    def evaluate(self,state,time_s):
        _num(time_s,'time')
        inverses=self.decode_inverse(state)
        decoded=tuple(result.state for result in inverses)
        names=self.gas_species_order
        masses={n:self.storages[0].gas_phases[n].metadata.molar_mass_kg_mol for n in names}
        count=len(self.storages)
        fn=np.zeros((count+1,len(names)+1));fe=np.zeros(count+1)
        try:
            gases=tuple(ideal_gas_state(self._gas_inventory(row),temperature_k=s.mechanical.temperature_k,
                gas_volume_m3=s.mechanical.gas_volume_m3,molar_masses_kg_mol=masses,
                gas_constant_j_mol_k=self.storages[0].mechanical.gas_constant_j_mol_k)
                for row,s in zip(state.amounts_mol,decoded))
            for face in range(1,count):
                left,right=face-1,face
                exchange=self._face(gases[left],gases[right],left,right)
                fn[face,1:]=[exchange.net_mol_s[n] for n in names]
                heat=conduction_rate_w(gases[left].temperature_k,gases[right].temperature_k,
                    area_m2=self.face_area_m2,left_distance_m=self.cell_widths_m[left]/2,
                    right_distance_m=self.cell_widths_m[right]/2,
                    left_conductivity_w_m_k=self.conductivities_w_m_k[left],
                    right_conductivity_w_m_k=self.conductivities_w_m_k[right])
                fe[face]=_sum((heat,self._enthalpy(exchange)))
            if self.outer_reservoir is not None:
                exchange=self._face(gases[-1],self.outer_reservoir,count-1,None)
                fn[-1,1:]=[exchange.net_mol_s[n] for n in names]
                fe[-1]=self._enthalpy(exchange)
            if self.outer_surface_temperature_k is not None:
                heat=conduction_rate_w(gases[-1].temperature_k,self.outer_surface_temperature_k,
                    area_m2=self.face_area_m2,left_distance_m=self.cell_widths_m[-1]/4,
                    right_distance_m=self.cell_widths_m[-1]/4,
                    left_conductivity_w_m_k=self.conductivities_w_m_k[-1],
                    right_conductivity_w_m_k=self.conductivities_w_m_k[-1])
                fe[-1]=_sum((fe[-1],heat))
        except _FAILURES as exc:_raise_failure(exc)
        return FluidHeatEvaluation(Rates(fn,fe,np.zeros_like(state.amounts_mol),np.zeros(count)),decoded,gases,inverses)

    def __call__(self,state,time_s):
        return self.evaluate(state,time_s).rates
