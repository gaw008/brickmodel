"""Source-labelled, connected-liquid, horizontal upwind Darcy face.

A supplied-pressure conditional direction is not a full inverse/EOS certificate.
Tables are caller-bound constitutive declarations, not admitted sludge data.
"""
from bisect import bisect_left
from dataclasses import dataclass
from fractions import Fraction
import math

from .phase_storage import PhaseMetadata
from .incompressible_solid import _assets as _solid_assets, _sources as _solid_sources


class LiquidTransportError(ValueError):
    """Invalid interface/constitutive contract or nonrepresentable flux."""


class LiquidTransportDomainError(LiquidTransportError):
    """Unsupported active liquid/connectivity or constitutive state domain."""


def _num(v,*,positive=False,nonnegative=False):
    try:x=float(v) if type(v) in (int,float) else math.nan
    except OverflowError:x=math.nan
    if not math.isfinite(x) or (positive and x<=0) or (nonnegative and x<0):raise LiquidTransportError('invalid_finite_SI_value')
    return x


def _label(v):
    if not isinstance(v,str) or not v or v!=v.strip():raise LiquidTransportError('explicit_identity_required')
    return v


def _sources(v):
    try:return _solid_sources(v)
    except ValueError as exc:raise LiquidTransportError(str(exc)) from exc


def _assets(v):
    try:return _solid_assets(v)
    except ValueError as exc:raise LiquidTransportError(str(exc)) from exc


def _range(v):
    if not isinstance(v,(tuple,list)) or len(v)!=2:raise LiquidTransportError('invalid_state_domain')
    a,b=(_num(x,positive=True) for x in v)
    if a>=b:raise LiquidTransportError('invalid_state_domain')
    return a,b


def _float(v):
    try:x=float(v)
    except OverflowError as exc:raise LiquidTransportError('unrepresentable_liquid_face_value') from exc
    if not math.isfinite(x) or (v and x==0):raise LiquidTransportError('unrepresentable_liquid_face_value')
    return x


def _upper(v):
    x=_float(v)
    result=math.nextafter(x,math.inf) if Fraction(x)<v else x
    if not math.isfinite(result):raise LiquidTransportError('unrepresentable_liquid_pressure_bound')
    return result


@dataclass(frozen=True,kw_only=True)
class LiquidTransportState:
    temperature_k: float
    pressure_pa: float
    inventory_mol: float
    saturation: float
    pressure_error_pa: float
    molar_volume_m3_mol: float | None
    enthalpy_j_mol: float | None
    metadata: PhaseMetadata
    provider_id: str
    provider_version: str
    source_asset_sha256: tuple[tuple[str,str],...]

    def __post_init__(self):
        for name in ('temperature_k','pressure_pa'):
            object.__setattr__(self,name,_num(getattr(self,name),positive=True))
        for name in ('inventory_mol','saturation','pressure_error_pa'):
            object.__setattr__(self,name,_num(getattr(self,name),nonnegative=True))
        if self.saturation>1:raise LiquidTransportError('invalid_saturation')
        if type(self.metadata) is not PhaseMetadata or self.metadata.phase!='liquid' or self.metadata.species_id!='H2O':
            raise LiquidTransportError('explicit_water_liquid_metadata_required')
        _label(self.provider_id);_label(self.provider_version)
        object.__setattr__(self,'source_asset_sha256',_assets(self.source_asset_sha256))
        if self.inventory_mol==0:
            if self.saturation!=0 or self.molar_volume_m3_mol is not None or self.enthalpy_j_mol is not None:
                raise LiquidTransportError('dry_state_must_not_invent_liquid_values')
        else:
            if self.saturation<=0:raise LiquidTransportError('wet_state_requires_positive_saturation')
            object.__setattr__(self,'molar_volume_m3_mol',_num(self.molar_volume_m3_mol,positive=True))
            object.__setattr__(self,'enthalpy_j_mol',_num(self.enthalpy_j_mol))

    @property
    def identity(self):return (self.metadata,self.provider_id,self.provider_version,self.source_asset_sha256)


@dataclass(frozen=True)
class LiquidMobility:
    permeability_m2: float
    relative_permeability: float
    viscosity_pa_s: float
    model_id: str
    version: str
    classification: str
    source_ids: tuple[str,...]
    relation_kind: str
    source_asset_sha256: tuple[tuple[str,str],...]
    temperature_k: float
    pressure_pa: float
    saturation: float
    interpolation_method: str = 'piecewise_linear_saturation_no_extrapolation_binary_input_fraction_v1'

    @property
    def exact_mobility(self):return Fraction(self.permeability_m2)*Fraction(self.relative_permeability)/Fraction(self.viscosity_pa_s)


@dataclass(frozen=True,kw_only=True)
class SaturationMobilityTable:
    saturation_knots: tuple[float,...]
    permeability_m2: tuple[float,...]
    relative_permeability: tuple[float,...]
    viscosity_pa_s: tuple[float,...]
    temperature_range_k: tuple[float,float]
    pressure_range_pa: tuple[float,float]
    model_id: str
    version: str
    classification: str
    source_ids: tuple[str,...]
    source_asset_sha256: tuple[tuple[str,str],...]
    relation_kind: str

    def __post_init__(self):
        _label(self.model_id);_label(self.version)
        if self.classification not in ('manufactured_test_fixture','literature_constitutive_model','derived_from_evidence'):
            raise LiquidTransportError('invalid_relation_classification')
        if self.relation_kind not in ('frozen_manufactured','tabulated_saturation_relation'):
            raise LiquidTransportError('explicit_relation_kind_required')
        if self.relation_kind=='frozen_manufactured' and self.classification!='manufactured_test_fixture':
            raise LiquidTransportError('frozen_relation_requires_manufactured_classification')
        if not isinstance(self.saturation_knots,(tuple,list)) or len(self.saturation_knots)<2:
            raise LiquidTransportError('explicit_saturation_knots_required')
        knots=tuple(_num(x,nonnegative=True) for x in self.saturation_knots)
        if knots[-1]>1 or any(a>=b for a,b in zip(knots,knots[1:])):raise LiquidTransportError('invalid_saturation_knots')
        object.__setattr__(self,'saturation_knots',knots)
        for name in ('permeability_m2','relative_permeability','viscosity_pa_s'):
            values=getattr(self,name)
            if not isinstance(values,(tuple,list)) or len(values)!=len(knots):raise LiquidTransportError('matching_relation_columns_required')
            values=tuple(_num(x,positive=name=='viscosity_pa_s',nonnegative=True) for x in values)
            if name=='relative_permeability' and any(x>1 for x in values):raise LiquidTransportError('relative_permeability_exceeds_one')
            if self.relation_kind=='frozen_manufactured' and len(set(values))!=1:raise LiquidTransportError('frozen_relation_must_be_constant')
            object.__setattr__(self,name,values)
        for name in ('temperature_range_k','pressure_range_pa'):object.__setattr__(self,name,_range(getattr(self,name)))
        object.__setattr__(self,'source_ids',_sources(self.source_ids))
        object.__setattr__(self,'source_asset_sha256',_assets(self.source_asset_sha256))

    @property
    def material_qualified(self):return False

    def evaluate(self,state):
        if type(state) is not LiquidTransportState:raise LiquidTransportError('explicit_liquid_state_required')
        if not (self.temperature_range_k[0]<=state.temperature_k<=self.temperature_range_k[1]
                and self.pressure_range_pa[0]<=state.pressure_pa<=self.pressure_range_pa[1]
                and self.saturation_knots[0]<=state.saturation<=self.saturation_knots[-1]):
            raise LiquidTransportDomainError('liquid_relation_state_out_of_domain')
        index=bisect_left(self.saturation_knots,state.saturation)
        values=[]
        for name in ('permeability_m2','relative_permeability','viscosity_pa_s'):
            column=getattr(self,name)
            if self.saturation_knots[index]==state.saturation:value=column[index]
            else:
                a,b=map(Fraction,self.saturation_knots[index-1:index+1]);w=(Fraction(state.saturation)-a)/(b-a)
                value=_float((1-w)*Fraction(column[index-1])+w*Fraction(column[index]))
            values.append(value)
        return LiquidMobility(*values,self.model_id,self.version,self.classification,self.source_ids,self.relation_kind,
            self.source_asset_sha256,state.temperature_k,state.pressure_pa,state.saturation)


@dataclass(frozen=True,kw_only=True)
class LiquidConnection:
    status: str
    connection_id: str
    version: str
    classification: str
    source_ids: tuple[str,...]

    def __post_init__(self):
        if self.status not in ('connected','disconnected','unknown','disabled'):raise LiquidTransportError('invalid_connection_status')
        if self.classification not in ('virtual_design_choice','manufactured_test_fixture','literature_constitutive_model','derived_from_evidence'):
            raise LiquidTransportError('invalid_connection_classification')
        _label(self.connection_id);_label(self.version)
        object.__setattr__(self,'source_ids',_sources(self.source_ids))


@dataclass(frozen=True)
class LiquidFaceExchange:
    volume_flow_m3_s: float
    molar_flow_mol_s: float
    enthalpy_flow_w: float
    donor: str | None
    status: str
    pressure_difference_pa: float
    pressure_difference_error_pa: float
    direction_qualification: str
    left_mobility: LiquidMobility | None
    right_mobility: LiquidMobility | None
    source_ids: tuple[str,...]
    liquid_source_identity: tuple
    connection: LiquidConnection
    pressure_interval_scope: str = 'fixed_decoded_temperature'
    full_inverse_direction_certified: bool = False
    qualification: str = 'horizontal_planar_frozen_face_upwind_discretization_not_exact_compressible_steady_flow'


def liquid_face_exchange(left,right,*,left_relation,right_relation,connection,area_m2,left_distance_m,right_distance_m,allow_manufactured=False):
    if type(left) is not LiquidTransportState or type(right) is not LiquidTransportState:
        raise LiquidTransportError('explicit_liquid_states_required')
    if type(left_relation) is not SaturationMobilityTable or type(right_relation) is not SaturationMobilityTable or type(connection) is not LiquidConnection:
        raise LiquidTransportError('explicit_relation_connection_required')
    if left.identity!=right.identity:raise LiquidTransportError('liquid_caloric_source_identity_mismatch')
    if type(allow_manufactured) is not bool:raise LiquidTransportError('invalid_manufactured_gate')
    if 'manufactured_test_fixture' in (left.metadata.classification,right.metadata.classification,
        left_relation.classification,right_relation.classification,connection.classification) and not allow_manufactured:
        raise LiquidTransportError('manufactured_requires_explicit_test_mode')
    area,dl,dr=(_num(v,positive=True) for v in (area_m2,left_distance_m,right_distance_m))
    delta=Fraction(left.pressure_pa)-Fraction(right.pressure_pa)
    eps=Fraction(left.pressure_error_pa)+Fraction(right.pressure_error_pa)
    direction='conditional_direction_resolved' if abs(delta)>eps else 'nominal_direction_not_certified'
    sources=tuple(sorted(set(left.metadata.source_ids+right.metadata.source_ids+left_relation.source_ids+right_relation.source_ids+connection.source_ids)))
    def zero(status,l=None,r=None):
        return LiquidFaceExchange(0.,0.,0.,None,status,_float(delta),_upper(eps),direction,l,r,sources,left.identity,connection)
    if connection.status=='disabled':return zero('disabled')
    lm,rm=left_relation.evaluate(left),right_relation.evaluate(right)
    if not lm.exact_mobility or not rm.exact_mobility:return zero('zero_mobility',lm,rm)
    if connection.status!='connected':raise LiquidTransportDomainError('active_liquid_connection_not_supported')
    if not left.inventory_mol or not right.inventory_mol:raise LiquidTransportDomainError('active_face_requires_existing_liquid_both_sides')
    if not delta:return zero('zero_nominal_pressure_difference',lm,rm)
    resistance=Fraction(dl)/lm.exact_mobility+Fraction(dr)/rm.exact_mobility
    q=Fraction(area)*delta/resistance
    donor=left if q>0 else right
    n=q/Fraction(donor.molar_volume_m3_mol)
    energy=n*Fraction(donor.enthalpy_j_mol)
    return LiquidFaceExchange(_float(q),_float(n),_float(energy),'left' if q>0 else 'right','nominal_flow',
        _float(delta),_upper(eps),direction,lm,rm,sources,left.identity,connection)
