"""Source-gated ideal vapor h/Cp join, with no liquid or chemical domain award."""
from dataclasses import dataclass,field
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar
import math

from .ideal_water_vapor import IdealWaterVapor
from .thermochemistry import load_thermochemistry,ThermochemistryError
from .continuous_caloric import ContinuousSegment,SegmentOffset,_cp_integral,_source_primitive


class JoinedWaterVaporError(ThermochemistryError):
    """Invalid fixed-source join, domain or conditional numerical contract."""


_ASSETS={'nist_gases_v1.json':'b3ed8274b56fd773a01340308651c301f133dbd097cf4abcc0baed05e5ef7e53',
         'sources.json':'6d4efbd566475b3542573af1fcd7049f2df8080ca966a342c57c4bd6b396b742'}


def _finite(v):
    try:x=float(v) if type(v) in (float,int) else math.nan
    except OverflowError:x=math.nan
    if not math.isfinite(x):raise JoinedWaterVaporError('finite_number_required')
    return x


def _out(value,*,upper=False):
    try:result=float(value)
    except OverflowError as exc:raise JoinedWaterVaporError("unrepresentable_join_value") from exc
    if not math.isfinite(result):raise JoinedWaterVaporError('unrepresentable_join_value')
    if upper and Fraction(result)<value:result=math.nextafter(result,math.inf)
    if not upper and Fraction(result)>value:result=math.nextafter(result,-math.inf)
    if not math.isfinite(result):raise JoinedWaterVaporError("unrepresentable_join_value")
    return result


def _cv_bound(segment):
    # Same rational interval-polynomial method as the solid caloric certificate;
    # subtract R before subdivision so the proof is for Cv, not merely Cp.
    a,b,c,d,e,*_=map(Fraction,segment.coefficients)
    a-=Fraction(segment.gas_constant_j_mol_k)
    lo,hi=map(Fraction,segment.temperature_range_k)
    stack=[(lo/1000,hi/1000,0)];bounds=[]
    while stack:
        x,y,depth=stack.pop()
        lower=a+min(b*x,b*y)+min(c*x*x,c*y*y)+min(d*x**3,d*y**3)+min(e/x**2,e/y**2)
        if lower>0:bounds.append(lower);continue
        if depth>=20:raise JoinedWaterVaporError('positive_cv_not_certified')
        mid=(x+y)/2;stack.extend(((x,mid,depth+1),(mid,y,depth+1)))
    return _out(min(bounds))


@dataclass(frozen=True)
class CpJump:
    temperature_k: float
    left_cp_j_mol_k: float
    right_cp_j_mol_k: float
    @property
    def jump_j_mol_k(self):return self.right_cp_j_mol_k-self.left_cp_j_mol_k


@dataclass(frozen=True)
class JoinedNumericalError:
    temperature_k: float
    anchor_enthalpy_error_j_mol: float
    integral_arithmetic_error_j_mol: float
    enthalpy_rounding_error_j_mol: float
    internal_energy_rounding_error_j_mol: float
    enthalpy_error_j_mol: float
    internal_energy_error_j_mol: float
    qualification: str = 'conditional_on_declared_low_domain_enthalpy_bound_not_independently_admitted'


@dataclass(frozen=True,init=False,eq=False)
class JoinedWaterVapor:
    low_model: IdealWaterVapor = field(repr=False)
    source_gas: object
    segments: tuple
    segment_offsets: tuple
    cp_jumps: tuple
    anchor_enthalpy_j_mol: float
    cv_lower_bound_j_mol_k: float
    low_cv_lower_bound_j_mol_k: float
    high_cv_lower_bounds_j_mol_k: tuple
    low_enthalpy_error_j_mol: float
    numerical_error_source_ids: tuple
    source_asset_sha256: object
    species_id: ClassVar[str]='H2O'
    temperature_range_k: ClassVar[tuple]=(293.,6000.)
    classification: ClassVar[str]='derived_from_evidence'
    method_id: ClassVar[str]='low_iapws_ideal_high_nist_cp_integral_v1'
    model_id: ClassVar[str]='joined_water_vapor_fixed_500K_anchor'
    version: ClassVar[str]='1'
    mixture_qualification: ClassVar[str]='not_established'

    def __init__(self,water_source_directory,thermochemistry_source_directory,*,low_enthalpy_error_j_mol,numerical_error_source_ids):
        error=_finite(low_enthalpy_error_j_mol)
        if error<0:raise JoinedWaterVaporError('nonnegative_low_enthalpy_error_required')
        ids=numerical_error_source_ids
        if (not isinstance(ids,(tuple,list)) or not ids or any(not isinstance(v,str) or not v or v!=v.strip() for v in ids)
                or len(set(ids))!=len(ids)):raise JoinedWaterVaporError('explicit_numerical_error_sources_required')
        try:
            directory=Path(thermochemistry_source_directory)
            for name,expected in _ASSETS.items():
                if sha256((directory/name).read_bytes()).hexdigest()!=expected:
                    raise JoinedWaterVaporError('fixed_nist_source_hash_mismatch:'+name)
        except (OSError,TypeError) as exc:raise JoinedWaterVaporError('fixed_nist_sources_required') from exc
        low=IdealWaterVapor(water_source_directory)
        gas=load_thermochemistry(directory/'nist_gases_v1.json').gases['H2O']
        if (gas.temperature_range_k!=(500.,6000.) or gas.classification!='literature_constitutive_model'
                or any(s.gas_constant_j_mol_k!=low.gas_constant_j_mol_k for s in gas.segments)):
            raise JoinedWaterVaporError('incompatible_fixed_high_water_source')
        phi=low._water._model.Fi0
        if (phi['ao_log']!=[1,3.00632] or phi['pow']!=[0,1]
                or not all(v>0 for v in phi['ao_exp']+phi['titao'])):
            raise JoinedWaterVaporError('native_ideal_positive_cv_proof_not_applicable')
        low_bound=_out(Fraction(low.reference.native_specific_gas_constant_j_kg_k)
            *Fraction(low.molar_mass_kg_mol)*(1+Fraction(3.00632))-Fraction(low.gas_constant_j_mol_k))
        high_bounds=tuple(_cv_bound(s) for s in gas.segments)
        if min((low_bound,)+high_bounds)<=0:raise JoinedWaterVaporError('positive_cv_not_certified')
        anchor=low.enthalpy_j_mol(500.);current=Fraction(anchor)
        segments=[];offsets=[];jumps=[]
        prior_cp=low.cp_j_mol_k(500.)
        for source in gas.segments:
            a,b=source.temperature_range_k
            segments.append(ContinuousSegment(source,current))
            offsets.append(SegmentOffset((a,b),float(current-_source_primitive(source,a)),a,
                source.enthalpy_j_mol(a),float(current),source.source_ids))
            jumps.append(CpJump(a,prior_cp,source.cp_j_mol_k(a)))
            prior_cp=source.cp_j_mol_k(b)
            current+=_cp_integral(source,a,b)
        assets={f'water/{k}':v for k,v in low.source_asset_sha256.items()}
        assets.update({f'thermochemistry/{k}':v for k,v in _ASSETS.items()})
        values=dict(low_model=low,source_gas=gas,segments=tuple(segments),segment_offsets=tuple(offsets),
            cp_jumps=tuple(jumps),anchor_enthalpy_j_mol=anchor,low_cv_lower_bound_j_mol_k=low_bound,
            high_cv_lower_bounds_j_mol_k=high_bounds,cv_lower_bound_j_mol_k=min((low_bound,)+high_bounds),
            low_enthalpy_error_j_mol=error,numerical_error_source_ids=tuple(ids),source_asset_sha256=MappingProxyType(assets))
        for key,value in values.items():object.__setattr__(self,key,value)

    @property
    def cp_lower_bound_j_mol_k(self):
        return _out(Fraction(self.cv_lower_bound_j_mol_k)+Fraction(self.gas_constant_j_mol_k))
    @property
    def gas_constant_j_mol_k(self):return self.low_model.gas_constant_j_mol_k
    @property
    def molar_mass_kg_mol(self):return self.low_model.molar_mass_kg_mol
    @property
    def reference(self):return self.low_model.reference
    @property
    def source_ids(self):return tuple(sorted(set(self.low_model.source_ids+self.source_gas.source_ids+self.numerical_error_source_ids)))
    @property
    def identity(self):
        return (self.model_id,self.version,self.method_id,self.classification,self.temperature_range_k,
            self.low_model.method_id,self.reference,self.gas_constant_j_mol_k,self.low_model._water.numerical_limits,
            tuple(sorted(self.source_asset_sha256.items())),self.source_gas,self.segments,self.segment_offsets,
            self.cp_jumps,self.low_enthalpy_error_j_mol,self.numerical_error_source_ids)
    def __eq__(self,other):return type(other) is JoinedWaterVapor and self.identity==other.identity
    def __hash__(self):return hash(self.identity)

    def _temperature(self,t):
        t=_finite(t)
        if not 293<=t<=6000:raise JoinedWaterVaporError('temperature_out_of_domain')
        return t

    def segment_for(self,t):
        t=self._temperature(t)
        if t<=500:return self.low_model
        return next(s for s in reversed(self.segments) if t>=s.temperature_range_k[0])

    def enthalpy_j_mol(self,t):return self.segment_for(t).enthalpy_j_mol(t)
    def internal_energy_j_mol(self,t):return self.segment_for(t).internal_energy_j_mol(t)
    def cp_j_mol_k(self,t):return self.segment_for(t).cp_j_mol_k(t)
    def cv_j_mol_k(self,t):return self.segment_for(t).cv_j_mol_k(t)

    def numerical_error(self,t):
        t=self._temperature(t);h=self.enthalpy_j_mol(t);u=self.internal_energy_j_mol(t)
        # Low h declaration already covers returned low h. On high branches
        # Fraction integration is exact for binary64 coefficients and the stored
        # low anchor. Full output ulps conservatively cover nearest rounding.
        h_round=0. if t<=500 else math.ulp(h)
        u_round=(math.ulp(self.gas_constant_j_mol_k*t)+math.ulp(u) if t<=500 else math.ulp(u))
        base=Fraction(self.low_enthalpy_error_j_mol)
        return JoinedNumericalError(t,self.low_enthalpy_error_j_mol,0.,h_round,u_round,
            _out(base+Fraction(h_round),upper=True),_out(base+Fraction(u_round),upper=True))
