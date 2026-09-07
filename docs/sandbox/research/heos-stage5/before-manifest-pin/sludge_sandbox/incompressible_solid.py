"""Single-branch solid caloric curve and explicit constant-volume approximation.

No gas R subtraction, crystal transition blending, equilibrium stability claim,
or automatic admission of a sludge material is supplied.
"""
from dataclasses import dataclass, field
from fractions import Fraction
import math

from .phase_storage import PhaseMetadata, PhasePoint, PhaseStorageError


class SolidPhaseError(PhaseStorageError):
    """Invalid solid contract, out-of-domain state, or unresolvable arithmetic."""


def _number(v, name, *, positive=False, nonnegative=False):
    try: x=float(v) if type(v) in (int,float) else math.nan
    except OverflowError: x=math.nan
    if not math.isfinite(x) or (positive and x<=0) or (nonnegative and x<0):
        raise SolidPhaseError('invalid_'+name)
    return x


def _label(v):
    if not isinstance(v,str) or not v or v!=v.strip():raise SolidPhaseError('explicit_identity_required')
    return v


def _sources(v):
    if not isinstance(v,(tuple,list)) or not v:raise SolidPhaseError('explicit_sources_required')
    result=tuple(_label(x) for x in v)
    if len(set(result))!=len(result):raise SolidPhaseError('duplicate_sources')
    return result


def _assets(v):
    if not isinstance(v,(tuple,list)) or not v:raise SolidPhaseError('source_assets_required')
    out=[]
    for item in v:
        if not isinstance(item,(tuple,list)) or len(item)!=2:raise SolidPhaseError('invalid_source_asset')
        key,digest=item
        _label(key)
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise SolidPhaseError('invalid_source_hash')
        out.append((key,digest))
    if len({k for k,_ in out})!=len(out):raise SolidPhaseError('duplicate_source_asset')
    return tuple(out)


def _range(v):
    if not isinstance(v,(tuple,list)) or len(v)!=2:raise SolidPhaseError('invalid_range')
    a,b=(_number(x,'range',positive=True) for x in v)
    if a>=b:raise SolidPhaseError('invalid_range')
    return a,b


def _float(v):
    try:x=float(v)
    except OverflowError as exc:raise SolidPhaseError('unrepresentable_solid_value') from exc
    if not math.isfinite(x) or (v and x==0):raise SolidPhaseError('unrepresentable_solid_value')
    return x


def _classification(v):
    if v not in ('manufactured_test_fixture','literature_constitutive_model','derived_from_evidence'):
        raise SolidPhaseError('invalid_classification')
    return v


@dataclass(frozen=True,kw_only=True)
class SolidShomateCaloric:
    species_id: str
    crystal_phase_id: str
    temperature_range_k: tuple[float,float]
    coefficients: tuple[float,...]
    formation_enthalpy_298_j_mol: float
    dataset_id: str
    version: str
    classification: str
    source_ids: tuple[str,...]
    source_asset_sha256: tuple[tuple[str,str],...]
    cp_lower_bound_j_mol_k: float = field(init=False)
    method_id: str = field(default='single_solid_shomate_exact_binary_input_v1',init=False)

    def __post_init__(self):
        for value in (self.species_id,self.crystal_phase_id,self.dataset_id,self.version):_label(value)
        _classification(self.classification)
        object.__setattr__(self,'temperature_range_k',_range(self.temperature_range_k))
        if not isinstance(self.coefficients,(tuple,list)) or len(self.coefficients)!=8:
            raise SolidPhaseError('eight_shomate_coefficients_required')
        object.__setattr__(self,'coefficients',tuple(_number(x,'coefficient') for x in self.coefficients))
        h=_number(self.formation_enthalpy_298_j_mol,'formation_enthalpy')
        object.__setattr__(self,'formation_enthalpy_298_j_mol',h)
        if not math.isclose(self.coefficients[7]*1000,h,rel_tol=1e-13,abs_tol=1e-9):
            raise SolidPhaseError('incompatible_formation_reference')
        object.__setattr__(self,'source_ids',_sources(self.source_ids))
        object.__setattr__(self,'source_asset_sha256',_assets(self.source_asset_sha256))
        low,high=map(Fraction,self.temperature_range_k)
        stack=[(low/1000,high/1000,0)];bounds=[]
        a,b,c,d,e,_,_,_=map(Fraction,self.coefficients)
        while stack:
            x,y,depth=stack.pop()
            lower=a+min(b*x,b*y)+min(c*x*x,c*y*y)+min(d*x**3,d*y**3)+min(e/x**2,e/y**2)
            if lower>0:bounds.append(lower);continue
            if depth>=16:raise SolidPhaseError('positive_cp_not_certified')
            z=(x+y)/2
            stack.extend(((x,z,depth+1),(z,y,depth+1)))
        exact=min(bounds);bound=_float(exact)
        if Fraction(bound)>exact:bound=math.nextafter(bound,-math.inf)
        if bound<=0:raise SolidPhaseError('unrepresentable_positive_cp_bound')
        object.__setattr__(self,'cp_lower_bound_j_mol_k',bound)

    def _temperature(self,t):
        t=_number(t,'temperature',positive=True)
        if not self.temperature_range_k[0]<=t<=self.temperature_range_k[1]:
            raise SolidPhaseError('solid_temperature_out_of_domain')
        return Fraction(t)/1000

    def _h(self,t):
        x=self._temperature(t)
        a,b,c,d,e,f,_,h=map(Fraction,self.coefficients)
        return Fraction(self.formation_enthalpy_298_j_mol)+1000*(a*x+b*x*x/2+c*x**3/3+d*x**4/4-e/x+f-h)

    def enthalpy_j_mol(self,t):return _float(self._h(t))

    def enthalpy_difference_j_mol(self,start,end):
        x,y=self._temperature(start),self._temperature(end)
        a,b,c,d,e,_,_,_=map(Fraction,self.coefficients)
        return _float(1000*(a*(y-x)+b*(y*y-x*x)/2+c*(y**3-x**3)/3+d*(y**4-x**4)/4+e*(1/x-1/y)))

    def cp_j_mol_k(self,t):
        x=self._temperature(t)
        a,b,c,d,e,_,_,_=map(Fraction,self.coefficients)
        return _float(a+b*x+c*x*x+d*x**3+e/x**2)


@dataclass(frozen=True,kw_only=True)
class IncompressibleSolidPhase:
    caloric: SolidShomateCaloric
    molar_mass_kg_mol: float
    molar_volume_m3_mol: float
    reference_pressure_pa: float
    pressure_range_pa: tuple[float,float]
    volume_model_id: str
    volume_version: str
    volume_classification: str
    volume_source_ids: tuple[str,...]
    volume_source_asset_sha256: tuple[tuple[str,str],...]
    declared_u_error_j_mol: float
    declared_v_error_m3_mol: float
    error_method_id: str
    error_classification: str
    error_source_ids: tuple[str,...]
    allow_manufactured: bool = False
    method_id: str = field(default='incompressible_single_solid_standard_enthalpy_v1',init=False)
    qualification: str = field(default='declared_u_v_bounds_not_independently_admitted_constant_volume_not_phase_stability',init=False)

    def __post_init__(self):
        if type(self.caloric) is not SolidShomateCaloric:raise SolidPhaseError('explicit_solid_caloric_required')
        for name in ('molar_mass_kg_mol','molar_volume_m3_mol','reference_pressure_pa'):
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=True))
        for name in ('declared_u_error_j_mol','declared_v_error_m3_mol'):
            object.__setattr__(self,name,_number(getattr(self,name),name,nonnegative=True))
        object.__setattr__(self,'pressure_range_pa',_range(self.pressure_range_pa))
        if not self.pressure_range_pa[0]<=self.reference_pressure_pa<=self.pressure_range_pa[1]:
            raise SolidPhaseError('reference_pressure_outside_domain')
        for value in (self.volume_model_id,self.volume_version,self.error_method_id):_label(value)
        _classification(self.volume_classification)
        _classification(self.error_classification)
        for name in ('volume_source_ids','error_source_ids'):object.__setattr__(self,name,_sources(getattr(self,name)))
        object.__setattr__(self,'volume_source_asset_sha256',_assets(self.volume_source_asset_sha256))
        if type(self.allow_manufactured) is not bool:raise SolidPhaseError('invalid_manufactured_gate')
        if 'manufactured_test_fixture' in (self.caloric.classification,self.volume_classification,self.error_classification) and not self.allow_manufactured:
            raise SolidPhaseError('manufactured_requires_explicit_test_mode')
        # Declared u error includes at least the independently declared v error
        # in the standard-pressure reference correction; remaining caloric and
        # numerical uncertainty is the caller's explicit conditional contract.
        if Fraction(self.declared_u_error_j_mol)<Fraction(self.reference_pressure_pa)*Fraction(self.declared_v_error_m3_mol):
            raise SolidPhaseError('u_error_omits_reference_volume_contribution')

    @property
    def metadata(self):
        classification=('manufactured_test_fixture' if 'manufactured_test_fixture' in
            (self.caloric.classification,self.volume_classification,self.error_classification) else 'derived_from_evidence')
        return PhaseMetadata(self.caloric.species_id,'solid',self.molar_mass_kg_mol,
            'mol_of_declared_species','nist_298.15K_element_standard_formation',
            tuple(dict.fromkeys(self.caloric.source_ids+self.volume_source_ids+self.error_source_ids)),classification)

    @property
    def temperature_range_k(self):return self.caloric.temperature_range_k

    @property
    def cp_lower_bound_j_mol_k(self):return self.caloric.cp_lower_bound_j_mol_k

    @property
    def identity(self):return self

    @property
    def material_qualified(self):return False

    def cv_j_mol_k(self,t):return self.caloric.cp_j_mol_k(t)

    def evaluate(self,temperature_k,pressure_pa):
        p=_number(pressure_pa,'pressure',positive=True)
        if not self.pressure_range_pa[0]<=p<=self.pressure_range_pa[1]:raise SolidPhaseError('solid_pressure_out_of_domain')
        h0=self.caloric._h(temperature_k)
        v=Fraction(self.molar_volume_m3_mol)
        u=h0-Fraction(self.reference_pressure_pa)*v
        return PhasePoint(float(temperature_k),p,_float(u),_float(u+Fraction(p)*v),self.molar_volume_m3_mol)
