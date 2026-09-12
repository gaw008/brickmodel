"""Exact common-root-interval pressure comparison at reported temperatures.

Provider adapters must establish root containment and stable liquid pressure
monotonicity. This kernel does not call EOS or assert material qualification.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import math

from .rational_intervals import (interval_difference, interval_sum,
                                 interval_divide_positive, residual_to_root_bound)


class PairedPressureError(ValueError):
    """Missing or inconsistent evidence for a paired pressure bound."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise PairedPressureError(reason)


def _number(value: Fraction, name: str, *, positive: bool = False) -> None:
    _require(type(value) is Fraction, 'exact_fraction_required:'+name)
    _require(value > 0 if positive else value >= 0, 'invalid_value:'+name)


def _identity(value: str) -> None:
    _require(type(value) is str and len(value) == 64 and
             all(c in '0123456789abcdef' for c in value), 'source_digest_required')


def _interval(value: tuple[Fraction, Fraction], name: str) -> None:
    _require(type(value) is tuple and len(value) == 2, 'interval_shape:'+name)
    for endpoint in value:
        _number(endpoint,name,positive=True)
    _require(value[0] <= value[1], 'interval_order:'+name)


@dataclass(frozen=True)
class PressureState:
    source_identity: str
    temperature_k: Fraction
    gas_mol: Fraction
    liquid_mol: Fraction
    solid_mol: tuple[Fraction, ...]
    bulk_volume_m3: Fraction
    jacobian: Fraction
    independent_volume_error_m3: Fraction
    root_interval_pa: tuple[Fraction, Fraction]

    def __post_init__(self) -> None:
        _identity(self.source_identity)
        for name in ('temperature_k','gas_mol','bulk_volume_m3','jacobian'):
            _number(getattr(self,name),name,positive=True)
        for name in ('liquid_mol','independent_volume_error_m3'):
            _number(getattr(self,name),name)
        _require(type(self.solid_mol) is tuple,'immutable_solid_inventory_required')
        for value in self.solid_mol:
            _number(value,'solid_mol')
        _interval(self.root_interval_pa,'root_interval_pa')


@dataclass(frozen=True)
class SharedVolumes:
    source_identity: str
    species: tuple[str, ...]
    solid_volume_m3_mol: tuple[Fraction, ...]
    solid_error_m3_mol: tuple[Fraction, ...]
    reference_volume_m3: Fraction
    reference_error_m3: Fraction
    contract: str = 'manufactured_shared_constant_volume_parameters_v1'

    def __post_init__(self) -> None:
        _identity(self.source_identity)
        _require(self.contract == 'manufactured_shared_constant_volume_parameters_v1',
                 'shared_constant_parameter_contract_required')
        _require(type(self.species) is tuple and bool(self.species) and
                 all(type(s) is str and bool(s) for s in self.species) and
                 len(set(self.species)) == len(self.species),'unique_species_required')
        for seq in (self.solid_volume_m3_mol,self.solid_error_m3_mol):
            _require(type(seq) is tuple and len(seq) == len(self.species),'solid_parameter_shape')
        for v,e in zip(self.solid_volume_m3_mol,self.solid_error_m3_mol):
            _number(v,'solid_volume',positive=True);_number(e,'solid_error')
            _require(v > e,'solid_volume_uncertainty_excludes_positive_domain')
        _number(self.reference_volume_m3,'reference_volume',positive=True)
        _number(self.reference_error_m3,'reference_error')
        _require(self.reference_volume_m3 > self.reference_error_m3,'reference_uncertainty_excludes_positive_domain')


@dataclass(frozen=True)
class LiquidEndpoints:
    source_identity: str
    temperature_k: Fraction
    pressure_interval_pa: tuple[Fraction, Fraction]
    volume_at_lower_m3_mol: Fraction
    volume_at_upper_m3_mol: Fraction
    error_at_lower_m3_mol: Fraction
    error_at_upper_m3_mol: Fraction
    qualification: str = 'stable_liquid_pressure_monotone_reported_temperature_v1'

    def __post_init__(self) -> None:
        _identity(self.source_identity)
        _number(self.temperature_k,'liquid_temperature',positive=True)
        _interval(self.pressure_interval_pa,'liquid_pressure_interval')
        for name in ('volume_at_lower_m3_mol','volume_at_upper_m3_mol'):
            _number(getattr(self,name),name,positive=True)
        for name in ('error_at_lower_m3_mol','error_at_upper_m3_mol'):
            _number(getattr(self,name),name)
        _require(self.qualification == 'stable_liquid_pressure_monotone_reported_temperature_v1',
                 'stable_liquid_monotonicity_contract_required')
        low=self.volume_at_upper_m3_mol-self.error_at_upper_m3_mol
        high=self.volume_at_lower_m3_mol+self.error_at_lower_m3_mol
        _require(0 < low <= high,'invalid_monotone_liquid_enclosure')


def _json_value(value):
    if isinstance(value,Fraction):
        return {'numerator':value.numerator,'denominator':value.denominator}
    if isinstance(value,dict):
        return {key:_json_value(child) for key,child in value.items()}
    if isinstance(value,(tuple,list)):
        return [_json_value(child) for child in value]
    return value


@dataclass(frozen=True)
class PairedPressureCertificate:
    bound_pa: float
    exact_bound_pa: Fraction
    pair_bound_pa: Fraction
    independent_bound_pa: Fraction
    compliance_lower: Fraction
    residual_interval_m3: tuple[Fraction, Fraction]
    common_pressure_interval_pa: tuple[Fraction, Fraction]
    joint_pressure_interval_pa: tuple[Fraction, Fraction]
    decomposition: tuple[tuple[str, tuple[Fraction, Fraction]], ...]
    source_identity: str
    input_record_json: bytes
    input_sha256: str
    qualification: str = 'paired_pressure_reported_temperatures_shared_constant_volume_parameters_v1'

    def to_record(self) -> dict:
        result=_json_value(asdict(self))
        result['input_record_json']=json.loads(self.input_record_json)
        result['material_qualified']=False
        result['temperature_uncertainty_included']=False
        result['root_containment_and_liquid_monotonicity']='required_provider_preconditions'
        return result


def certify_paired_pressure(a: PressureState, b: PressureState, shared: SharedVolumes, *,
        gas_constant_j_mol_k: Fraction,
        pressure_domain_pa: tuple[Fraction, Fraction],
        temperature_domain_k: tuple[Fraction, Fraction],
        liquid_a: LiquidEndpoints | None, liquid_b: LiquidEndpoints | None) -> PairedPressureCertificate:
    """Bound paired roots; B's entire certified root interval is the only pivot set."""
    _require(type(a) is PressureState and type(b) is PressureState and type(shared) is SharedVolumes,
             'explicit_immutable_pair_inputs_required')
    _number(gas_constant_j_mol_k,'gas_constant',positive=True)
    _interval(pressure_domain_pa,'pressure_domain');_interval(temperature_domain_k,'temperature_domain')
    _require(a.source_identity == b.source_identity == shared.source_identity,'source_binding_mismatch')
    for state in (a,b):
        _require(len(state.solid_mol) == len(shared.species),'complete_solid_inventory_required')
        _require(temperature_domain_k[0] <= state.temperature_k <= temperature_domain_k[1],
                 'reported_temperature_outside_domain')
        _require(pressure_domain_pa[0] <= state.root_interval_pa[0] <= state.root_interval_pa[1] <= pressure_domain_pa[1],
                 'root_interval_outside_source_domain')
        _require(abs(state.bulk_volume_m3-state.jacobian*shared.reference_volume_m3) <= state.independent_volume_error_m3,
                 'unaccounted_nominal_geometry_discrepancy')
        available_lower=(state.bulk_volume_m3-state.jacobian*shared.reference_error_m3-
            state.independent_volume_error_m3-sum((n*(v+e) for n,v,e in
                zip(state.solid_mol,shared.solid_volume_m3_mol,shared.solid_error_m3_mol)),Fraction()))
        _require(available_lower > 0,'available_volume_uncertainty_excludes_positive_domain')
    common=b.root_interval_pa
    def liquid_interval(state: PressureState, endpoints: LiquidEndpoints | None) -> tuple[Fraction,Fraction]:
        if state.liquid_mol == 0:
            _require(endpoints is None,'zero_liquid_must_not_supply_endpoint_evidence')
            return Fraction(),Fraction()
        _require(type(endpoints) is LiquidEndpoints,'wet_pair_requires_liquid_endpoint_evidence')
        _require(endpoints.source_identity == shared.source_identity,'liquid_source_binding_mismatch')
        _require(endpoints.temperature_k == state.temperature_k,'liquid_reported_temperature_mismatch')
        _require(endpoints.pressure_interval_pa == common,'liquid_requires_entire_b_root_interval')
        return (state.liquid_mol*(endpoints.volume_at_upper_m3_mol-endpoints.error_at_upper_m3_mol),
                state.liquid_mol*(endpoints.volume_at_lower_m3_mol+endpoints.error_at_lower_m3_mol))
    la=liquid_interval(a,liquid_a);lb=liquid_interval(b,liquid_b)
    liquid=interval_difference(la,lb)
    gas_numerator=gas_constant_j_mol_k*(a.gas_mol*a.temperature_k-b.gas_mol*b.temperature_k)
    gas=interval_divide_positive((gas_numerator,gas_numerator),common)
    dn=tuple(x-y for x,y in zip(a.solid_mol,b.solid_mol))
    solid=sum((n*v for n,v in zip(dn,shared.solid_volume_m3_mol)),Fraction())
    solid_error=sum((abs(n)*e for n,e in zip(dn,shared.solid_error_m3_mol)),Fraction())
    geometry=b.bulk_volume_m3-a.bulk_volume_m3
    reference_error=abs(a.jacobian-b.jacobian)*shared.reference_error_m3
    independent_error=a.independent_volume_error_m3+b.independent_volume_error_m3
    pieces=(('liquid',liquid),('gas',gas),('solid_nominal',(solid,solid)),
            ('geometry_nominal',(geometry,geometry)),('shared_solid_error',(-solid_error,solid_error)),
            ('shared_reference_error',(-reference_error,reference_error)),
            ('independent_volume_errors',(-independent_error,independent_error)))
    residual=interval_sum(tuple(v for _,v in pieces))
    joint=(min(a.root_interval_pa[0],b.root_interval_pa[0]),max(a.root_interval_pa[1],b.root_interval_pa[1]))
    compliance=min(a.gas_mol*a.temperature_k,b.gas_mol*b.temperature_k)*gas_constant_j_mol_k/joint[1]**2
    _require(compliance > 0,'no_positive_gas_compliance')
    pair_bound=residual_to_root_bound(residual,compliance)
    independent=max(abs(a.root_interval_pa[0]-b.root_interval_pa[1]),abs(a.root_interval_pa[1]-b.root_interval_pa[0]))
    exact=min(pair_bound,independent)
    try:
        represented=float(exact)
    except OverflowError as exc:
        raise PairedPressureError('pressure_bound_unrepresentable') from exc
    _require(math.isfinite(represented) and (represented > 0 or exact == 0),'pressure_bound_unrepresentable')
    if Fraction(represented) < exact:
        represented=math.nextafter(represented,math.inf)
    _require(math.isfinite(represented),'pressure_bound_unrepresentable')
    inputs={'a':asdict(a),'b':asdict(b),'shared':asdict(shared),
            'gas_constant_j_mol_k':gas_constant_j_mol_k,'pressure_domain_pa':pressure_domain_pa,
            'temperature_domain_k':temperature_domain_k,
            'liquid_a':None if liquid_a is None else asdict(liquid_a),
            'liquid_b':None if liquid_b is None else asdict(liquid_b)}
    raw=json.dumps(_json_value(inputs),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return PairedPressureCertificate(represented,exact,pair_bound,independent,compliance,residual,
        common,joint,pieces,shared.source_identity,raw,hashlib.sha256(raw).hexdigest())
