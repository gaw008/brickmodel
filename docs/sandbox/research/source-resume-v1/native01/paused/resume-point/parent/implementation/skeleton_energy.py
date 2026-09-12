"""Manufactured diagonal skeleton energy; not a material admission.

Interval arithmetic encloses formulas for exact represented binary64 inputs.
It does not cover parameter uncertainty, geometry uncertainty or constitutive error.
"""
from dataclasses import dataclass
from decimal import Context, Decimal, ROUND_HALF_EVEN, DecimalException
from fractions import Fraction
import math
from types import MappingProxyType
from collections.abc import Mapping
from sludge_sandbox.geometry import ReferenceSlab


class SkeletonEnergyError(ValueError):
    """Invalid declared model, state domain or unrepresentable arithmetic."""


def _number(x,name,positive=False,nonnegative=False):
    if type(x) not in (int,float):raise SkeletonEnergyError('invalid_'+name)
    try:y=float(x)
    except OverflowError as exc:raise SkeletonEnergyError('invalid_'+name) from exc
    if not math.isfinite(y) or (x!=0 and y==0) or (positive and y<=0) or (nonnegative and y<0):
        raise SkeletonEnergyError('invalid_'+name)
    return y


def _label(x):
    if not isinstance(x,str) or not x or x!=x.strip():raise SkeletonEnergyError('explicit_identity_required')
    return x


def _identity(x):
    if not isinstance(x,tuple) or not x:raise SkeletonEnergyError('immutable_provider_identity_required')
    for v in x:
        if isinstance(v,tuple):_identity(v)
        else:_label(v)
    return x


@dataclass(frozen=True)
class _Interval:
    lo: Fraction
    hi: Fraction

    @classmethod
    def exact(cls,x):
        f=Fraction(x);return cls(f,f)

    def __add__(self,other):
        other=_iv(other);return _Interval(self.lo+other.lo,self.hi+other.hi)
    __radd__=__add__

    def __neg__(self):return _Interval(-self.hi,-self.lo)
    def __sub__(self,other):return self+-_iv(other)
    def __rsub__(self,other):return _iv(other)+-self

    def __mul__(self,other):
        other=_iv(other);v=[a*b for a in (self.lo,self.hi) for b in (other.lo,other.hi)]
        return _Interval(min(v),max(v))
    __rmul__=__mul__

    def __truediv__(self,other):
        other=_iv(other)
        if other.lo<=0<=other.hi:raise SkeletonEnergyError('interval_division_by_zero')
        return self*_Interval(1/other.hi,1/other.lo)

    def square(self):
        return _Interval(0 if self.lo<=0<=self.hi else min(self.lo*self.lo,self.hi*self.hi),max(self.lo*self.lo,self.hi*self.hi))


def _iv(x):return x if isinstance(x,_Interval) else _Interval.exact(x)


def _ln(x):
    if x==1:return _iv(0)
    # Decimal ln is correctly rounded HALF_EVEN. Adjacent decimals enclose
    # the exact logarithm; conversion to Fraction loses no further precision.
    ctx=Context(prec=80,rounding=ROUND_HALF_EVEN)
    try:
        value=Decimal.from_float(x).ln(context=ctx)
        return _Interval(Fraction(value.next_minus(context=ctx)),Fraction(value.next_plus(context=ctx)))
    except (DecimalException,ValueError,OverflowError) as exc:
        raise SkeletonEnergyError('logarithm_interval_failed') from exc


def _output(x):
    x=_iv(x);mid=(x.lo+x.hi)/2
    try:value=float(mid)
    except OverflowError as exc:raise SkeletonEnergyError('unrepresentable_output') from exc
    if not math.isfinite(value) or (mid!=0 and value==0):raise SkeletonEnergyError('unrepresentable_output')
    error=max(abs(Fraction(value)-x.lo),abs(Fraction(value)-x.hi))
    try:bound=float(error)
    except OverflowError as exc:raise SkeletonEnergyError('unrepresentable_error_bound') from exc
    if Fraction(bound)<error:bound=math.nextafter(bound,math.inf)
    if not math.isfinite(bound):raise SkeletonEnergyError('unrepresentable_error_bound')
    return value,bound


@dataclass(frozen=True)
class SkeletonEnergyState:
    elastic_energy_j: float
    interface_energy_j: float
    elastic_piola_pa: tuple
    interface_piola_pa: tuple
    viscous_piola_pa: tuple
    elastic_rate_w: float
    interface_rate_w: float
    dissipation_w: float
    rayleigh_potential_w: float
    numerical_error_bounds: Mapping
    model_identity: tuple
    normal_stretch: float
    tangential_stretch: float
    normal_rate_per_s: float
    tangential_rate_per_s: float
    qualification: str='manufactured_diagonal_model_exact_binary_input_numerical_enclosures_only'


@dataclass(frozen=True,kw_only=True)
class DiagonalSkeletonEnergy:
    reference: ReferenceSlab
    cell_index: int
    fixed_solid_inventory_mol: tuple
    solid_provider_identity: tuple
    bulk_modulus_pa: float
    shear_modulus_pa: float
    viscosity_pa_s: float
    interface_energy_j_m2: float
    reference_interface_area_m2: float
    stretch_range: tuple
    maximum_absolute_log_rate_per_s: float
    model_id: str
    version: str
    source_ids: tuple
    classification: str
    allow_manufactured: bool

    def __post_init__(self):
        if type(self.reference) is not ReferenceSlab or type(self.cell_index) is not int or not 0<=self.cell_index<self.reference.cells:
            raise SkeletonEnergyError('reference_cell_identity_required')
        _identity(self.solid_provider_identity)
        if type(self.allow_manufactured) is not bool or not self.allow_manufactured or self.classification!='manufactured_test_fixture':
            raise SkeletonEnergyError('explicit_manufactured_model_required')
        for name in ('model_id','version'):_label(getattr(self,name))
        if not isinstance(self.source_ids,tuple) or not self.source_ids:raise SkeletonEnergyError('explicit_sources_required')
        for v in self.source_ids:_label(v)
        if len(set(self.source_ids))!=len(self.source_ids):raise SkeletonEnergyError('duplicate_sources')
        if not isinstance(self.fixed_solid_inventory_mol,tuple) or not self.fixed_solid_inventory_mol:
            raise SkeletonEnergyError('fixed_solid_inventory_required')
        amounts=[]
        for item in self.fixed_solid_inventory_mol:
            if not isinstance(item,tuple) or len(item)!=2:raise SkeletonEnergyError('invalid_fixed_solid_inventory')
            key,n=item;_label(key);amounts.append((key,_number(n,'solid_mol',nonnegative=True)))
        if len({k for k,_ in amounts})!=len(amounts) or not any(n>0 for _,n in amounts):raise SkeletonEnergyError('invalid_fixed_solid_inventory')
        object.__setattr__(self,'fixed_solid_inventory_mol',tuple(sorted(amounts)))
        for name in ('bulk_modulus_pa','shear_modulus_pa','interface_energy_j_m2','reference_interface_area_m2','maximum_absolute_log_rate_per_s'):
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=True))
        object.__setattr__(self,'viscosity_pa_s',_number(self.viscosity_pa_s,'viscosity',nonnegative=True))
        if not isinstance(self.stretch_range,tuple) or len(self.stretch_range)!=2:raise SkeletonEnergyError('stretch_domain_required')
        a,b=(_number(v,'stretch_bound',positive=True) for v in self.stretch_range)
        if not a< b or not a<=1<=b:raise SkeletonEnergyError('reference_outside_stretch_domain')
        object.__setattr__(self,'stretch_range',(a,b))
        _number(self.reference_volume_m3,'reference_volume',positive=True)

    @property
    def reference_volume_m3(self):
        # Match the existing geometry's represented reference-cell volume.
        return self.reference.reference_area_m2*(self.reference.half_thickness_m/self.reference.cells)

    @property
    def identity(self):
        return (self.model_id,self.version,self.classification,self.source_ids,
                self.solid_provider_identity,self.fixed_solid_inventory_mol,
                (self.reference.half_thickness_m,self.reference.reference_area_m2,self.reference.cells,self.cell_index),
                self.bulk_modulus_pa,self.shear_modulus_pa,self.viscosity_pa_s,
                self.interface_energy_j_m2,self.reference_interface_area_m2,
                self.stretch_range,self.maximum_absolute_log_rate_per_s,
                'diagonal_logstrain_internal_surface_temperature_independent_v1',
                'decimal80_ln_neighbors_fraction_propagation_binary64_outward_error_v1',
                'elastic_zero_at_identity_interface_absolute_gamma_area')

    def evaluate(self,*,normal_stretch,tangential_stretch,normal_rate_per_s,tangential_rate_per_s,solid_inventory_mol):
        if not isinstance(solid_inventory_mol,Mapping) or set(solid_inventory_mol)!={k for k,_ in self.fixed_solid_inventory_mol}:
            raise SkeletonEnergyError('fixed_inventory_mismatch')
        for k,n in self.fixed_solid_inventory_mol:
            if _number(solid_inventory_mol[k],'solid_mol',nonnegative=True)!=n:raise SkeletonEnergyError('fixed_inventory_mismatch')
        n=_number(normal_stretch,'normal_stretch',positive=True);t=_number(tangential_stretch,'tangential_stretch',positive=True)
        nr=_number(normal_rate_per_s,'normal_rate');tr=_number(tangential_rate_per_s,'tangential_rate')
        lo,hi=self.stretch_range
        if not lo<=n<=hi or not lo<=t<=hi:raise SkeletonEnergyError('stretch_out_of_domain')
        if any(abs(Fraction(r)/Fraction(v))>Fraction(self.maximum_absolute_log_rate_per_s) for r,v in ((nr,n),(tr,t))):
            raise SkeletonEnergyError('log_rate_out_of_domain')
        stretch=tuple(map(_iv,(n,t,t)));rates=tuple(map(_iv,(nr,tr,tr)))
        logs=(_ln(n),_ln(t),_ln(t));theta=sum(logs);dev=tuple(v-theta/3 for v in logs)
        log_rates=tuple(r/v for r,v in zip(rates,stretch))
        v=_iv(self.reference_volume_m3);k=_iv(self.bulk_modulus_pa);g=_iv(self.shear_modulus_pa)
        eta=_iv(self.viscosity_pa_s);ga=_iv(self.interface_energy_j_m2)*self.reference_interface_area_m2
        elastic=v*(k*theta.square()/2+g*sum(d.square() for d in dev))
        surface=ga*stretch[1]*stretch[2]
        pe=tuple((k*theta+2*g*d)/l for d,l in zip(dev,stretch))
        ps=(_iv(0),ga*stretch[2]/v,ga*stretch[1]/v)
        pv=tuple(eta*r/l for r,l in zip(log_rates,stretch))
        er=v*sum(p*r for p,r in zip(pe,rates));sr=v*sum(p*r for p,r in zip(ps,rates))
        diss=eta*v*sum(r.square() for r in log_rates)
        raw=dict(elastic_energy_j=elastic,interface_energy_j=surface,elastic_piola_pa=pe,interface_piola_pa=ps,
                 viscous_piola_pa=pv,elastic_rate_w=er,interface_rate_w=sr,dissipation_w=diss,rayleigh_potential_w=diss/2)
        values={};bounds={}
        for key,value in raw.items():
            if isinstance(value,tuple):
                pairs=tuple(_output(x) for x in value);values[key]=tuple(a for a,_ in pairs);bounds[key]=tuple(b for _,b in pairs)
            else:values[key],bounds[key]=_output(value)
        return SkeletonEnergyState(**values,numerical_error_bounds=MappingProxyType(bounds),model_identity=self.identity,
            normal_stretch=n,tangential_stretch=t,normal_rate_per_s=nr,tangential_rate_per_s=tr)
