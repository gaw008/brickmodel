"""Species thermal storage at prescribed phase pressures and fixed mol inventories.

No mechanical/volume closure, phase equilibrium, elastic/interface energy, or
material qualification is inferred. Inversion is conditional on explicitly
supplied continuous, increasing fixed-pressure path bounds.
"""
from sludge_sandbox.water_properties import is_water_provider
from collections.abc import Mapping
from dataclasses import dataclass, is_dataclass, replace
import math
from numbers import Real
from types import MappingProxyType
from typing import Protocol

from .ideal_water_vapor import IdealWaterVapor
from .joined_water_vapor import JoinedWaterVapor
from .continuous_caloric import ContinuousShomateGas
from .thermochemistry import ShomateGas
from .water_properties import WaterProperties

_REFERENCE = 'nist_298.15K_element_standard_formation'


class PhaseStorageError(ValueError):
    """Invalid phase metadata, missing inversion qualification, or numerical failure."""


def _number(value, name, *, positive=False, nonnegative=False):
    try:
        v = float(value) if isinstance(value, Real) and not isinstance(value, bool) else math.nan
    except (OverflowError, ValueError):
        v = math.nan
    if not math.isfinite(v) or (positive and v <= 0) or (nonnegative and v < 0):
        raise PhaseStorageError('invalid_'+name)
    return v


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise PhaseStorageError('invalid_'+name)
    return value


def _sources(values):
    if not isinstance(values, tuple) or not values or len(set(values)) != len(values):
        raise PhaseStorageError('invalid_source_ids')
    return tuple(_text(x, 'source_id') for x in values)


def _range(values):
    if not isinstance(values, tuple) or len(values) != 2:
        raise PhaseStorageError('invalid_temperature_range')
    a,b=(_number(v,'temperature',positive=True) for v in values)
    if a >= b:raise PhaseStorageError('invalid_temperature_range')
    return a,b


def _sum(values):
    try:return _number(math.fsum(values),'sum')
    except OverflowError as e:raise PhaseStorageError('nonfinite_sum') from e


@dataclass(frozen=True)
class PhaseMetadata:
    species_id: str
    phase: str
    molar_mass_kg_mol: float
    molar_basis_id: str
    energy_reference_id: str
    source_ids: tuple[str,...]
    classification: str

    def __post_init__(self):
        for name in ('species_id','molar_basis_id','energy_reference_id'):_text(getattr(self,name),name)
        if self.phase not in ('solid','liquid','gas'):raise PhaseStorageError('invalid_phase')
        if self.classification not in ('literature_constitutive_model','derived_from_evidence','manufactured_test_fixture'):
            raise PhaseStorageError('invalid_classification')
        _number(self.molar_mass_kg_mol,'molar_mass',positive=True)
        _sources(self.source_ids)


@dataclass(frozen=True)
class PhasePoint:
    temperature_k: float
    pressure_pa: float
    internal_energy_j_mol: float
    enthalpy_j_mol: float
    molar_volume_m3_mol: float

    def __post_init__(self):
        _number(self.temperature_k,'temperature',positive=True)
        _number(self.pressure_pa,'pressure',positive=True)
        _number(self.internal_energy_j_mol,'internal_energy')
        _number(self.enthalpy_j_mol,'enthalpy')
        _number(self.molar_volume_m3_mol,'molar_volume',positive=True)
        pv=_number(self.pressure_pa*self.molar_volume_m3_mol,'pressure_work')
        residual=_sum((self.enthalpy_j_mol,-self.internal_energy_j_mol,-pv))
        if abs(residual)>1e-8:raise PhaseStorageError('phase_h_u_pv_identity')


class PhaseProvider(Protocol):
    metadata: PhaseMetadata
    temperature_range_k: tuple[float,float]
    def evaluate(self, temperature_k: float, pressure_pa: float) -> PhasePoint: ...


@dataclass(frozen=True)
class LiquidWaterPhase:
    water: WaterProperties

    def __post_init__(self):
        if not is_water_provider(self.water):raise PhaseStorageError('verified_water_provider_required')

    @property
    def metadata(self):
        r=self.water.reference
        return PhaseMetadata('H2O','liquid',r.molar_mass_kg_mol,'mol_of_declared_species',_REFERENCE,self.water.source_ids,'derived_from_evidence')

    @property
    def temperature_range_k(self):return (293.,500.)

    def evaluate(self,temperature_k,pressure_pa):
        s=self.water.state_tp(temperature_k,pressure_pa,phase='liquid')
        return PhasePoint(s.temperature_k,s.pressure_pa,s.internal_energy_j_mol,s.enthalpy_j_mol,s.molar_mass_kg_mol/s.density_kg_m3)


@dataclass(frozen=True)
class IdealGasPhase:
    """Explicit original single branch, continuous derived gas, or water bridge."""
    caloric: object
    molar_mass_kg_mol: float
    segment_index: int | None = None
    additional_source_ids: tuple[str,...] = ()

    def __post_init__(self):
        if type(self.caloric) not in (IdealWaterVapor,JoinedWaterVapor,ShomateGas,ContinuousShomateGas):raise PhaseStorageError('supported_caloric_provider_required')
        _number(self.molar_mass_kg_mol,'molar_mass',positive=True)
        if type(self.caloric) in (IdealWaterVapor,JoinedWaterVapor):
            if self.segment_index is not None or self.molar_mass_kg_mol!=self.caloric.molar_mass_kg_mol:
                raise PhaseStorageError('water_molar_identity_mismatch')
        elif type(self.caloric) is ContinuousShomateGas:
            if self.segment_index is not None:
                raise PhaseStorageError('continuous_provider_must_not_select_single_segment')
        else:
            if type(self.segment_index) is not int or not 0<=self.segment_index<len(self.caloric.segments):
                raise PhaseStorageError('explicit_single_segment_required')
            _sources(self.additional_source_ids)
        if self.additional_source_ids:_sources(self.additional_source_ids)
        self.metadata

    @property
    def _curve(self):
        return self.caloric.segments[self.segment_index] if type(self.caloric) is ShomateGas else self.caloric

    @property
    def metadata(self):
        c=self.caloric
        ids=tuple(dict.fromkeys(c.source_ids+self._curve.source_ids+self.additional_source_ids))
        return PhaseMetadata(c.species_id,'gas',self.molar_mass_kg_mol,'mol_of_declared_species',_REFERENCE,ids,c.classification)

    @property
    def temperature_range_k(self):return self._curve.temperature_range_k

    def evaluate(self,temperature_k,pressure_pa):
        p=_number(pressure_pa,'pressure',positive=True)
        t=_number(temperature_k,'temperature',positive=True)
        c=self._curve
        return PhasePoint(t,p,c.internal_energy_j_mol(t),c.enthalpy_j_mol(t),c.gas_constant_j_mol_k*t/p)


@dataclass(frozen=True)
class MonotonicPath:
    """Declared fixed-pressure strict-increase bound, not automatically verified evidence."""
    temperature_range_k: tuple[float,float]
    pressure_pa: float
    minimum_du_dt_j_mol_k: float
    source_ids: tuple[str,...]
    method: str

    def __post_init__(self):
        _range(self.temperature_range_k)
        _number(self.pressure_pa,'pressure',positive=True)
        _number(self.minimum_du_dt_j_mol_k,'derivative_bound',positive=True)
        _sources(self.source_ids)
        _text(self.method,'qualification_method')


@dataclass(frozen=True)
class InversePolicy:
    energy_tolerance_j: float
    temperature_tolerance_k: float
    maximum_iterations: int

    def __post_init__(self):
        _number(self.energy_tolerance_j,'energy_tolerance',positive=True)
        _number(self.temperature_tolerance_k,'temperature_tolerance',positive=True)
        if type(self.maximum_iterations) is not int or self.maximum_iterations<=0:raise PhaseStorageError('invalid_maximum_iterations')


@dataclass(frozen=True)
class StorageResult:
    temperature_k: float
    internal_energy_j: float
    enthalpy_j: float
    phase_volumes_m3: Mapping[str,float]
    source_ids: tuple[str,...]
    energy_resolution_j: float
    inverse_paths: Mapping[str,MonotonicPath] | None = None
    inverse_status: str = 'not_requested'
    energy_scope: str = 'species_thermal_storage_only'
    source_status: str = 'provider_declarations_not_material_qualification'


@dataclass(frozen=True,init=False)
class PhaseStorage:
    providers: Mapping[str,PhaseProvider]
    _identity: Mapping[str,tuple]

    def __init__(self,providers,*,allow_manufactured=False):
        if not isinstance(providers,Mapping) or not providers or type(allow_manufactured) is not bool:
            raise PhaseStorageError('invalid_providers')
        values=dict(providers)
        references=set();bases=set();masses={}
        for key,p in values.items():
            _text(key,'phase_key')
            if not is_dataclass(p) or not getattr(type(p),'__dataclass_params__').frozen:
                raise PhaseStorageError('immutable_provider_required')
            m=p.metadata
            if type(m) is not PhaseMetadata:raise PhaseStorageError('phase_metadata_required')
            if m.classification=='manufactured_test_fixture' and not allow_manufactured:raise PhaseStorageError('manufactured_opt_in_required')
            _range(p.temperature_range_k)
            references.add(m.energy_reference_id);bases.add(m.molar_basis_id)
            if m.species_id in masses and masses[m.species_id]!=m.molar_mass_kg_mol:raise PhaseStorageError('molar_identity_mismatch')
            masses[m.species_id]=m.molar_mass_kg_mol
        if len(references)!=1:raise PhaseStorageError('energy_reference_mismatch')
        if len(bases)!=1:raise PhaseStorageError('molar_basis_mismatch')
        object.__setattr__(self,'providers',MappingProxyType(values))
        object.__setattr__(self,'_identity',MappingProxyType({k:(p.metadata,p.temperature_range_k) for k,p in values.items()}))

    def _active(self,amounts,pressures):
        if not isinstance(amounts,Mapping) or not isinstance(pressures,Mapping):raise PhaseStorageError('inventory_mapping_required')
        if set(amounts)-self.providers.keys() or set(pressures)-self.providers.keys():raise PhaseStorageError('unknown_phase_id')
        for key,provider in self.providers.items():
            if (provider.metadata,provider.temperature_range_k)!=self._identity[key]:
                raise PhaseStorageError('provider_identity_changed')
        active=[]
        for key,amount in amounts.items():
            n=_number(amount,'inventory',nonnegative=True)
            if n:
                if key not in pressures:raise PhaseStorageError('explicit_phase_pressure_required')
                active.append((key,n,_number(pressures[key],'pressure',positive=True)))
        return active

    def evaluate(self,amounts,pressures,temperature_k):
        t=_number(temperature_k,'temperature',positive=True)
        terms_u=[];terms_h=[];resolutions=[];volumes={};sources=set()
        for key,n,p in self._active(amounts,pressures):
            provider=self.providers[key]
            a,b=provider.temperature_range_k
            if not a<=t<=b:raise PhaseStorageError('temperature_out_of_phase_domain')
            s=provider.evaluate(t,p)
            if type(s) is not PhasePoint or s.temperature_k!=t or s.pressure_pa!=p:raise PhaseStorageError('phase_state_identity_mismatch')
            terms_u.append(_number(n*s.internal_energy_j_mol,'extensive_internal_energy'))
            resolutions.append(_sum((n*math.ulp(s.internal_energy_j_mol),math.ulp(terms_u[-1]))))
            terms_h.append(_number(n*s.enthalpy_j_mol,'extensive_enthalpy'))
            volumes[key]=_number(n*s.molar_volume_m3_mol,'phase_volume',positive=True)
            if (provider.metadata,provider.temperature_range_k)!=self._identity[key]:raise PhaseStorageError('provider_identity_changed')
            sources.update(provider.metadata.source_ids)
        energy=_sum(terms_u)
        resolution=_sum(resolutions+[math.ulp(energy)])
        return StorageResult(t,energy,_sum(terms_h),MappingProxyType(volumes),tuple(sorted(sources)),resolution)

    def temperature_from_energy(self,target_j,amounts,pressures,*,paths,policy):
        target=_number(target_j,'target_energy')
        if type(policy) is not InversePolicy or not isinstance(paths,Mapping):raise PhaseStorageError('inverse_policy_and_paths_required')
        active=self._active(amounts,pressures)
        if not active:raise PhaseStorageError('no_active_inventory')
        low=0.;high=math.inf;bounds=[]
        for key,n,p in active:
            if key not in paths or type(paths[key]) is not MonotonicPath:raise PhaseStorageError('monotonic_qualification_required')
            path=paths[key]
            if path.pressure_pa!=p:raise PhaseStorageError('qualification_pressure_mismatch')
            a,b=self.providers[key].temperature_range_k;x,y=path.temperature_range_k
            low=max(low,a,x);high=min(high,b,y)
            bounds.append(_number(n*path.minimum_du_dt_j_mol_k,'extensive_derivative_bound',positive=True))
        if low>=high:raise PhaseStorageError('no_common_temperature_domain')
        slope=_number(_sum(bounds),'total_derivative_bound',positive=True)
        left=self.evaluate(amounts,pressures,low);right=self.evaluate(amounts,pressures,high)
        def check_increase(a,b):
            delta=_sum((b.internal_energy_j,-a.internal_energy_j))
            allowance=_sum((a.energy_resolution_j,b.energy_resolution_j))
            if delta+allowance<slope*(b.temperature_k-a.temperature_k):
                raise PhaseStorageError('contradicted_monotonic_derivative_bound')
        check_increase(left,right)
        if right.internal_energy_j<=left.internal_energy_j:raise PhaseStorageError('contradicted_monotonic_qualification')
        if not left.internal_energy_j<=target<=right.internal_energy_j:raise PhaseStorageError('energy_out_of_domain')
        if max(math.ulp(target),math.ulp(left.internal_energy_j),math.ulp(right.internal_energy_j))>policy.energy_tolerance_j:
            raise PhaseStorageError('unresolvable_energy_precision')
        energy_spacing=_sum((math.ulp(target),max(left.energy_resolution_j,right.energy_resolution_j)))
        if energy_spacing>policy.energy_tolerance_j or energy_spacing/slope>policy.temperature_tolerance_k:
            raise PhaseStorageError('unresolvable_energy_temperature_precision')
        if max(math.ulp(low),math.ulp(high))>policy.temperature_tolerance_k:
            raise PhaseStorageError('unresolvable_temperature_precision')
        for _ in range(policy.maximum_iterations):
            middle=low+(high-low)/2
            if middle in (low,high):raise PhaseStorageError('unresolvable_temperature_precision')
            state=self.evaluate(amounts,pressures,middle)
            value=state.internal_energy_j
            combined_resolution=_sum((math.ulp(target),state.energy_resolution_j))
            if combined_resolution>policy.energy_tolerance_j or combined_resolution/slope>policy.temperature_tolerance_k:
                raise PhaseStorageError('unresolvable_energy_temperature_precision')
            check_increase(left,state);check_increase(state,right)
            if not left.internal_energy_j<=value<=right.internal_energy_j:raise PhaseStorageError('contradicted_monotonic_qualification')
            residual=_sum((value,-target))
            if abs(residual)<=policy.energy_tolerance_j and high-low<=policy.temperature_tolerance_k:
                used={key:paths[key] for key,_,_ in active}
                sources=tuple(sorted(set(state.source_ids).union(*(p.source_ids for p in used.values()))))
                return replace(state,source_ids=sources,inverse_paths=MappingProxyType(used),
                    inverse_status='conditional_on_declared_monotonic_paths_not_independently_admitted')
            if residual<0:low=middle;left=state
            else:high=middle;right=state
        raise PhaseStorageError('inverse_iteration_limit')
