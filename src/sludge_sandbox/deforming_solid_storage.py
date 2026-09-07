"""Fixed-solid total-energy point storage, not an integration host."""
from dataclasses import dataclass,fields,is_dataclass,replace,field
from fractions import Fraction
from collections.abc import Mapping
import hashlib,json,math
from sludge_sandbox.solid_fluid_storage import SolidFluidStorage
from sludge_sandbox.incompressible_solid import IncompressibleSolidPhase
from sludge_sandbox.skeleton_energy import DiagonalSkeletonEnergy
from sludge_sandbox.deformation_program import PrescribedSlabMotion
from sludge_sandbox.water_properties import WaterProperties

SCOPE='thermal_plus_skeleton_recoverable_plus_declared_interface_internal_energy'

class DeformingStorageError(ValueError):pass


def _num(x,name,nonnegative=False):
    if type(x) not in (int,float,Fraction):raise DeformingStorageError('invalid_'+name)
    try:y=float(x)
    except (OverflowError,ValueError) as exc:raise DeformingStorageError('invalid_'+name) from exc
    if not math.isfinite(y) or (x!=0 and y==0) or (nonnegative and x<0):raise DeformingStorageError('invalid_'+name)
    return y


def _out(x):
    try:y=float(x)
    except OverflowError as exc:raise DeformingStorageError('unrepresentable_energy') from exc
    if not math.isfinite(y) or (x!=0 and y==0):raise DeformingStorageError('unrepresentable_energy')
    return y


def _upper(x):
    if x<0:raise DeformingStorageError('negative_error')
    try:y=float(x)
    except OverflowError as exc:raise DeformingStorageError('unrepresentable_error') from exc
    if not math.isfinite(y):raise DeformingStorageError('unrepresentable_error')
    if Fraction(y)<x:y=math.nextafter(y,math.inf)
    if not math.isfinite(y):raise DeformingStorageError('unrepresentable_error')
    return y


def _label(x):
    if not isinstance(x,str) or not x or x.strip()!=x:raise DeformingStorageError('explicit_identity_required')
    return x


def _canonical(x):
    if x is None or type(x) in (str,bool,int):return x
    if type(x) is float:
        if not math.isfinite(x):raise DeformingStorageError('nonfinite_identity')
        return ['float',x.hex()]
    if type(x) is WaterProperties:
        return ['source_gated_water',_canonical(x.reference),_canonical(x.source_asset_sha256),_canonical(x.numerical_limits)]
    if isinstance(x,Mapping):return ['mapping',[[k,_canonical(v)] for k,v in sorted(x.items())]]
    if isinstance(x,(tuple,list)):return [_canonical(v) for v in x]
    if is_dataclass(x):return [type(x).__module__,type(x).__qualname__,[[f.name,_canonical(getattr(x,f.name))] for f in fields(x)]]
    raise DeformingStorageError('unsupported_identity_type:'+type(x).__name__)


def _digest(x):return hashlib.sha256(json.dumps(_canonical(x),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def solid_provider_identity(phases):
    if not isinstance(phases,Mapping) or not phases or any(type(v) is not IncompressibleSolidPhase or k!=v.metadata.species_id for k,v in phases.items()):
        raise DeformingStorageError('actual_solid_providers_required')
    return ('full_incompressible_solid_dataclass_sha256_v1',_digest(phases))


@dataclass(frozen=True)
class DeformationErrorBounds:
    time_range_s: tuple
    additional_bulk_volume_error_m3: float
    additional_mechanical_energy_error_j: float
    source_ids: tuple
    qualification: str

    def __post_init__(self):
        if not isinstance(self.time_range_s,tuple) or len(self.time_range_s)!=2:raise DeformingStorageError('time_error_domain_required')
        a,b=(_num(v,'error_time') for v in self.time_range_s)
        if a>=b:raise DeformingStorageError('invalid_error_domain')
        object.__setattr__(self,'time_range_s',(a,b))
        for name in ('additional_bulk_volume_error_m3','additional_mechanical_energy_error_j'):
            raw=getattr(self,name);_num(raw,name,nonnegative=True)
            object.__setattr__(self,name,_upper(Fraction(raw)))
        if not isinstance(self.source_ids,tuple) or not self.source_ids:raise DeformingStorageError('error_sources_required')
        for s in self.source_ids:_label(s)
        _label(self.qualification)


@dataclass(frozen=True)
class TotalEnergyTarget:
    value_j: float
    error_bound_j: float
    model_identity: tuple
    energy_scope: str=SCOPE

    def __post_init__(self):
        raw=self.value_j;value=_num(raw,'total_energy');object.__setattr__(self,'value_j',value)
        _num(self.error_bound_j,'target_error',nonnegative=True)
        error=Fraction(self.error_bound_j)+abs(Fraction(raw)-Fraction(value))
        object.__setattr__(self,'error_bound_j',_upper(error))
        if not isinstance(self.model_identity,tuple) or not self.model_identity:raise DeformingStorageError('total_model_identity_required')


@dataclass(frozen=True)
class DeformingSolidState:
    thermal_state: object
    skeleton_state: object
    motion: object
    total_energy_j: float
    energy_error_bound_j: float
    mechanical_energy_error_bound_j: float
    total_addition_roundoff_j: float
    current_bulk_error_bound_m3: float
    error_bounds: DeformationErrorBounds
    model_identity: tuple
    energy_scope: str=SCOPE
    qualification: str='conditional_declared_geometry_and_mechanical_bounds_not_material_admission'


@dataclass(frozen=True)
class DeformingSolidInverse:
    state: DeformingSolidState
    thermal_inverse: object
    target: TotalEnergyTarget
    total_energy_residual_j: float
    subtraction_roundoff_j: float
    temperature_error_bound_k: float


@dataclass(frozen=True,kw_only=True)
class DeformingSolidStorage:
    template: SolidFluidStorage
    motion: PrescribedSlabMotion
    skeleton: DiagonalSkeletonEnergy
    error_bounds: DeformationErrorBounds
    model_id: str
    version: str
    allow_manufactured: bool
    _template_digest: str=field(init=False,repr=False)

    def __post_init__(self):
        if type(self.template) is not SolidFluidStorage or type(self.motion) is not PrescribedSlabMotion or type(self.skeleton) is not DiagonalSkeletonEnergy or type(self.error_bounds) is not DeformationErrorBounds:
            raise DeformingStorageError('explicit_storage_motion_skeleton_bounds_required')
        if type(self.allow_manufactured) is not bool or not self.allow_manufactured:raise DeformingStorageError('manufactured_opt_in_required')
        _label(self.model_id);_label(self.version)
        if self.motion.reference!=self.skeleton.reference:raise DeformingStorageError('reference_geometry_mismatch')
        if solid_provider_identity(self.template.solid_phases)!=self.skeleton.solid_provider_identity:raise DeformingStorageError('actual_solid_identity_mismatch')
        if {k for k,_ in self.skeleton.fixed_solid_inventory_mol}!=set(self.template.solid_phases):raise DeformingStorageError('complete_solid_inventory_required')
        expected=self.skeleton.reference_volume_m3;actual=self.template.bulk_volume_m3
        if abs(actual-expected)>2*max(math.ulp(actual),math.ulp(expected)):raise DeformingStorageError('reference_bulk_volume_mismatch')
        if not self.error_bounds.time_range_s[0]<=self.motion.knot_times_s[0]<self.motion.knot_times_s[-1]<=self.error_bounds.time_range_s[1]:raise DeformingStorageError('motion_outside_error_domain')
        object.__setattr__(self,'_template_digest',_digest(self.template))

    @property
    def identity(self):
        return (self.model_id,self.version,self._template_digest,self.motion.identity,self.skeleton.identity,
                _digest(self.error_bounds),'deforming_solid_total_point_v1',SCOPE)

    def target(self,value_j,error_bound_j):return TotalEnergyTarget(value_j,error_bound_j,self.identity)

    def _prepare(self,time_s,solid_mol):
        if _digest(self.template)!=self._template_digest:raise DeformingStorageError('runtime_template_identity_changed')
        snap=self.motion.sample(time_s);i=self.skeleton.cell_index
        sk=self.skeleton.evaluate(normal_stretch=float(snap.normal_stretches[i]),tangential_stretch=snap.tangential_stretch,
            normal_rate_per_s=float(snap.normal_rates_per_s[i]),tangential_rate_per_s=snap.tangential_rate_per_s,solid_inventory_mol=solid_mol)
        ref=self.motion.reference
        exact_v0=Fraction(ref.reference_area_m2)*Fraction(ref.half_thickness_m)/ref.cells
        reference_error=Fraction(self.template.bulk_volume_error_m3)+abs(Fraction(self.template.bulk_volume_m3)-exact_v0)
        j=Fraction(float(snap.normal_stretches[i]))*Fraction(snap.tangential_stretch)**2
        current=float(snap.current.volumes_m3[i])
        volume_error=j*reference_error+abs(Fraction(current)-j*exact_v0)+Fraction(self.error_bounds.additional_bulk_volume_error_m3)
        bulk_error=_upper(volume_error)
        current_storage=replace(self.template,bulk_volume_m3=current,bulk_volume_error_m3=bulk_error)
        # Elastic energy is linear in represented V0. Explicit additional bound
        # must cover any other physical/kinematic parameter uncertainty.
        e_el=Fraction(sk.elastic_energy_j);el_error=Fraction(sk.numerical_error_bounds['elastic_energy_j'])
        v0_error=reference_error+abs(Fraction(self.skeleton.reference_volume_m3)-exact_v0)
        elastic_geometry_error=(abs(e_el)+el_error)*v0_error/Fraction(self.skeleton.reference_volume_m3)
        mechanical_error=el_error+Fraction(sk.numerical_error_bounds['interface_energy_j'])+elastic_geometry_error+Fraction(self.error_bounds.additional_mechanical_energy_error_j)
        return snap,sk,current_storage,_upper(mechanical_error),bulk_error

    def _assemble(self,thermal,snap,sk,error,bulk_error):
        exact=Fraction(thermal.internal_energy_j)+Fraction(sk.elastic_energy_j)+Fraction(sk.interface_energy_j)
        total=_out(exact);rounding=abs(Fraction(total)-exact)
        bound=_upper(Fraction(thermal.energy_error_bound_j)+Fraction(error)+rounding)
        return DeformingSolidState(thermal,sk,snap,total,bound,error,_upper(rounding),bulk_error,self.error_bounds,self.identity)

    def forward(self,temperature_k,*,liquid_mol,gas_mol,solid_mol,time_s):
        snap,sk,storage,error,bulk=self._prepare(time_s,solid_mol)
        thermal=storage.evaluate_at_temperature(temperature_k,liquid_mol,gas_mol,solid_mol)
        return self._assemble(thermal,snap,sk,error,bulk)

    def temperature_from_total_energy(self,target,*,liquid_mol,gas_mol,solid_mol,time_s,temperature_bracket_k,policy):
        if type(target) is not TotalEnergyTarget or target.energy_scope!=SCOPE or target.model_identity!=self.identity:
            raise DeformingStorageError('matching_explicit_total_energy_target_required')
        snap,sk,storage,error,bulk=self._prepare(time_s,solid_mol)
        exact=Fraction(target.value_j)-Fraction(sk.elastic_energy_j)-Fraction(sk.interface_energy_j)
        thermal_target=_out(exact);rounding=abs(Fraction(thermal_target)-exact)
        target_error=_upper(Fraction(target.error_bound_j)+Fraction(error)+rounding)
        inverse=storage.temperature_from_energy(thermal_target,liquid_mol,gas_mol,solid_mol,temperature_bracket_k,policy,
            target_energy_error_bound_j=target_error)
        state=self._assemble(inverse.state,snap,sk,error,bulk)
        residual=_out(Fraction(state.total_energy_j)-Fraction(target.value_j))
        return DeformingSolidInverse(state,inverse,target,residual,_upper(rounding),inverse.temperature_error_bound_k)
