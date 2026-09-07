"""Prescribed C1 slab motion; not a sintering constitutive law."""
from bisect import bisect_right
from dataclasses import dataclass, field
from fractions import Fraction
import math
from numbers import Real
import numpy as np
from sludge_sandbox.geometry import ReferenceSlab, CurrentSlab, GeometryError


class DeformationProgramError(ValueError):
    """Invalid identity, time domain or unrepresentable compatible geometry."""


def _number(value, name, positive=False):
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,Real):
        raise DeformationProgramError('invalid_'+name)
    try: result=float(value)
    except (ValueError,OverflowError) as exc: raise DeformationProgramError('invalid_'+name) from exc
    if not math.isfinite(result) or (value!=0 and result==0) or (positive and result<=0):
        raise DeformationProgramError('invalid_'+name)
    return result


def _rounded(value,name,positive=False):
    try: result=float(value)
    except (ValueError,OverflowError) as exc: raise DeformationProgramError('unrepresentable_'+name) from exc
    if not math.isfinite(result) or (value!=0 and result==0) or (positive and result<=0):
        raise DeformationProgramError('unrepresentable_'+name)
    return result


def _label(value,name):
    if not isinstance(value,str) or not value or value!=value.strip():raise DeformationProgramError('invalid_'+name)
    return value


def _length(values,name):
    if not isinstance(values,(list,tuple,np.ndarray)):
        raise DeformationProgramError('invalid_'+name+'_shape')
    try: return len(values)
    except TypeError as exc:
        raise DeformationProgramError('invalid_'+name+'_shape') from exc


def _vector(values,size,name,positive=False):
    if _length(values,name)!=size:
        raise DeformationProgramError('invalid_'+name+'_shape')
    return tuple(_number(v,name,positive) for v in values)


def _frozen(values):
    a=np.asarray(values,dtype=np.float64)
    return np.frombuffer(a.tobytes(),dtype=np.float64).reshape(a.shape)


def _snapshot(current):
    return CurrentSlab(*(_frozen(getattr(current,n)) for n in CurrentSlab.__dataclass_fields__))


def _check_geometry(current):
    for name in ('widths_m','face_areas_m2','reference_volumes_m3','volumes_m3','volume_ratios'):
        a=getattr(current,name)
        if not np.all(np.isfinite(a)) or np.any(a<=0):raise DeformationProgramError('invalid_current_'+name)
    if np.any(np.diff(current.faces_m)<=0):raise DeformationProgramError('face_positions_not_resolved')
    for expected,left,right in zip(current.widths_m,current.faces_m[:-1],current.faces_m[1:]):
        actual=float(right)-float(left)
        # Face subtraction inherits coordinate rounding, not only width rounding.
        allowance=math.fsum(math.ulp(float(v)) for v in (left,right,expected,actual))
        if allowance>=float(expected) or abs(actual-float(expected))>allowance:
            raise DeformationProgramError('face_spacing_unresolvable')
    if (not np.all(np.isfinite(current.centers_m)) or
            np.any(current.centers_m<=current.faces_m[:-1]) or np.any(current.centers_m>=current.faces_m[1:])):
        raise DeformationProgramError('cell_center_not_resolved')


@dataclass(frozen=True)
class ReferenceGeometryAlignment:
    cell_count: int
    area_residual_m2: float
    width_residuals_m: tuple
    volume_residuals_m3: tuple
    exact_match: bool
    tolerance_ulps: int = 2
    qualification: str = 'binary64_construction_allowance_not_physical_shape_uncertainty'


@dataclass(frozen=True)
class MotionSnapshot:
    time_s: float
    current: CurrentSlab
    normal_stretches: np.ndarray
    tangential_stretch: float
    normal_rates_per_s: np.ndarray
    tangential_rate_per_s: float
    width_rates_m_s: np.ndarray
    face_velocities_m_s: np.ndarray
    face_area_rate_m2_s: float
    volume_rates_m3_s: np.ndarray
    motion_identity: tuple
    source_ids: tuple
    source_asset_sha256: tuple
    method_id: str = 'reference_slab_c1_rest_to_rest_smoothstep_exact_input_arithmetic_v1'
    numerical_qualification: str = 'finite_compatible_prescribed_kinematics_no_experimental_or_material_error_bound'


@dataclass(frozen=True,kw_only=True)
class PrescribedSlabMotion:
    reference: ReferenceSlab
    knot_times_s: tuple
    normal_stretches_at_knots: tuple
    tangential_stretches_at_knots: tuple
    motion_id: str
    version: str
    classification: str
    source_ids: tuple
    source_asset_sha256: tuple
    _reference_state: CurrentSlab = field(init=False,repr=False,compare=False)

    def __post_init__(self):
        if type(self.reference) is not ReferenceSlab:raise DeformationProgramError('explicit_reference_slab_required')
        if _length(self.knot_times_s,'knot_times')<2:
            raise DeformationProgramError('at_least_two_knots_required')
        times=_vector(self.knot_times_s,len(self.knot_times_s),'knot_times')
        if any(b<=a or not math.isfinite(b-a) or not a<a+(b-a)/2<b for a,b in zip(times,times[1:])):
            raise DeformationProgramError('strict_finite_time_intervals_required')
        normals=self.normal_stretches_at_knots
        if _length(normals,'normal_knots')!=len(times):
            raise DeformationProgramError('invalid_normal_knots_shape')
        normals=tuple(_vector(row,self.reference.cells,'normal_stretches',True) for row in normals)
        tangents=_vector(self.tangential_stretches_at_knots,len(times),'tangential_stretches',True)
        for key in ('motion_id','version'):_label(getattr(self,key),key)
        if not isinstance(self.classification,str) or self.classification not in ('virtual_design_choice','manufactured_test_fixture','literature_prescribed_history'):
            raise DeformationProgramError('invalid_classification')
        if not isinstance(self.source_ids,(tuple,list)) or not self.source_ids:raise DeformationProgramError('explicit_source_ids_required')
        sources=tuple(_label(s,'source_id') for s in self.source_ids)
        if len(set(sources))!=len(sources):raise DeformationProgramError('duplicate_source_ids')
        if not isinstance(self.source_asset_sha256,(tuple,list)):raise DeformationProgramError('explicit_asset_list_required')
        assets=[]
        for entry in self.source_asset_sha256:
            if not isinstance(entry,(tuple,list)) or len(entry)!=2:raise DeformationProgramError('invalid_asset_entry')
            name,digest=entry;_label(name,'asset_id')
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise DeformationProgramError('invalid_asset_sha256')
            assets.append((name,digest))
        if len({a for a,_ in assets})!=len(assets):raise DeformationProgramError('duplicate_assets')
        if self.classification=='literature_prescribed_history' and not assets:
            raise DeformationProgramError('literature_asset_identity_required')
        for name,value in (('knot_times_s',times),('normal_stretches_at_knots',normals),
                           ('tangential_stretches_at_knots',tangents),('source_ids',sources),('source_asset_sha256',tuple(assets))):
            object.__setattr__(self,name,value)
        try: reference=self.reference.deform((1.,)*self.reference.cells,tangential_stretch=1.)
        except (GeometryError,OverflowError,FloatingPointError,ValueError) as exc:
            raise DeformationProgramError('invalid_reference_geometry') from exc
        _check_geometry(reference)
        object.__setattr__(self,'_reference_state',_snapshot(reference))
        # Knot checks do not certify representability throughout every interval.
        for time in times:
            self.sample(time)

    @property
    def identity(self):
        return (self.motion_id,self.version,self.classification,self.source_ids,self.source_asset_sha256,
                (float(self.reference.half_thickness_m),float(self.reference.reference_area_m2),self.reference.cells),
                self.knot_times_s,self.normal_stretches_at_knots,self.tangential_stretches_at_knots,
                'c1_rest_to_rest_smoothstep_v1')

    @property
    def source_qualification(self):
        return 'declared_identity_not_runtime_verified_source_content_or_sintering_law'

    def breakpoints_s(self,start,end):
        a=_number(start,'start_time');b=_number(end,'end_time')
        if not self.knot_times_s[0]<=a<b<=self.knot_times_s[-1]:raise DeformationProgramError('time_interval_out_of_domain')
        return tuple(t for t in self.knot_times_s if a<t<b)

    def sample(self,time_s):
        t=_number(time_s,'time')
        if not self.knot_times_s[0]<=t<=self.knot_times_s[-1]:raise DeformationProgramError('time_out_of_domain')
        i=min(bisect_right(self.knot_times_s,t)-1,len(self.knot_times_s)-2)
        ta,tb=map(Fraction,self.knot_times_s[i:i+2]);q=(Fraction(t)-ta)/(tb-ta)
        blend=q*q*(3-2*q);derivative=6*q*(1-q)/(tb-ta)
        def interpolate(a,b):
            a,b=Fraction(a),Fraction(b)
            return _rounded(a+(b-a)*blend,'stretch',True),_rounded((b-a)*derivative,'stretch_rate')
        pairs=tuple(interpolate(a,b) for a,b in zip(self.normal_stretches_at_knots[i],self.normal_stretches_at_knots[i+1]))
        normal=tuple(p[0] for p in pairs);normal_rates=tuple(p[1] for p in pairs)
        tangent,tangent_rate=interpolate(*self.tangential_stretches_at_knots[i:i+2])
        try: current=self.reference.deform(normal,tangential_stretch=tangent)
        except (GeometryError,OverflowError,FloatingPointError,ValueError) as exc:
            raise DeformationProgramError('unrepresentable_current_geometry') from exc
        _check_geometry(current)
        width0=Fraction(float(self.reference.half_thickness_m/self.reference.cells))
        width_rates=tuple(_rounded(width0*Fraction(r),'width_rate') for r in normal_rates)
        area_rate=_rounded(2*Fraction(float(self.reference.reference_area_m2))*Fraction(tangent)*Fraction(tangent_rate),'area_rate')
        volume_rates=tuple(_rounded(Fraction(float(a))*Fraction(dr)+Fraction(area_rate)*Fraction(float(dx)),'volume_rate')
                           for a,dr,dx in zip(current.face_areas_m2[:-1],width_rates,current.widths_m))
        velocities=[0.];total=Fraction()
        for dr in width_rates:
            total+=Fraction(dr);velocities.append(_rounded(total,'face_velocity'))
        return MotionSnapshot(t,_snapshot(current),_frozen(normal),tangent,_frozen(normal_rates),tangent_rate,
            _frozen(width_rates),_frozen(velocities),area_rate,_frozen(volume_rates),self.identity,self.source_ids,self.source_asset_sha256)

    def validate_reference_geometry(self,*,cell_count,face_area_m2,cell_widths_m,gas_volumes_m3):
        if type(cell_count) is not int or cell_count!=self.reference.cells:
            raise DeformationProgramError('reference_cell_count_mismatch')
        area=_number(face_area_m2,'reference_area',True)
        widths=_vector(cell_widths_m,cell_count,'reference_widths',True)
        volumes=_vector(gas_volumes_m3,cell_count,'reference_volumes',True)
        def residual(actual,expected,name):
            expected=float(expected);difference=actual-expected
            if not math.isfinite(difference) or abs(difference)>2*max(math.ulp(actual),math.ulp(expected)):
                raise DeformationProgramError('reference_'+name+'_mismatch')
            return difference
        da=residual(area,self.reference.reference_area_m2,'area')
        dw=tuple(residual(a,b,'width') for a,b in zip(widths,self._reference_state.widths_m))
        dv=tuple(residual(a,b,'volume') for a,b in zip(volumes,self._reference_state.volumes_m3))
        return ReferenceGeometryAlignment(cell_count,da,dw,dv,all(v==0 for v in (da,*dw,*dv)))
