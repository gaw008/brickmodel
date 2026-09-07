"""Independent fixed-composition entropy reference; no tested storage imports.

Only native water TP EOS can be shared. This is an isolated validation solver,
not a material constitutive model or certified interval root solver.
"""
from dataclasses import dataclass
import math
import time
from scipy.optimize import brentq


class EntropyOracleError(ValueError):pass


def _number(x,name,positive=False,nonnegative=False):
    if type(x) not in (int,float):raise EntropyOracleError('invalid_'+name)
    try:y=float(x)
    except OverflowError as exc:raise EntropyOracleError('invalid_'+name) from exc
    if not math.isfinite(y) or (positive and y<=0) or (nonnegative and y<0):raise EntropyOracleError('invalid_'+name)
    return y


def _pair(x,name):
    if type(x) is not tuple or len(x)!=2:raise EntropyOracleError('explicit_'+name+'_required')
    a,b=(_number(v,name,positive=True) for v in x)
    if a>=b:raise EntropyOracleError('unordered_'+name)
    return a,b


@dataclass(frozen=True)
class OracleInputs:
    liquid_mol: float
    gas_mol: float
    solid_mol: float
    gas_cp_j_mol_k: float
    solid_cp_j_mol_k: float
    solid_molar_volume_m3_mol: float
    initial_temperature_k: float
    initial_bulk_volume_m3: float
    gas_constant_j_mol_k: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=name not in ('liquid_mol','solid_mol'),nonnegative=True))
        if self.gas_constant_j_mol_k!=8.31446261815324:raise EntropyOracleError('registered_mixture_R_required')
        if self.gas_cp_j_mol_k<=self.gas_constant_j_mol_k:raise EntropyOracleError('positive_gas_Cv_required')
        if self.initial_bulk_volume_m3<=self.solid_mol*self.solid_molar_volume_m3_mol:raise EntropyOracleError('initial_pore_exhausted')


@dataclass(frozen=True)
class OraclePolicy:
    temperature_bracket_k: tuple
    pressure_bracket_pa: tuple
    temperature_xtol_k: float
    pressure_xtol_pa: float
    entropy_residual_tolerance_j_k: float
    volume_residual_tolerance_m3: float
    maximum_iterations: int

    def __post_init__(self):
        for name in ('temperature_bracket_k','pressure_bracket_pa'):object.__setattr__(self,name,_pair(getattr(self,name),name))
        for name in ('temperature_xtol_k','pressure_xtol_pa','entropy_residual_tolerance_j_k','volume_residual_tolerance_m3'):
            object.__setattr__(self,name,_number(getattr(self,name),name,positive=True))
        if type(self.maximum_iterations) is not int or self.maximum_iterations<=0:raise EntropyOracleError('invalid_iterations')


@dataclass(frozen=True)
class ReferencePoint:
    temperature_k: float
    pressure_pa: float
    bulk_volume_m3: float
    gas_volume_m3: float
    liquid_volume_m3: float
    entropy_residual_j_k: float
    volume_residual_m3: float
    water_calls: int
    pressure_solves: int
    elapsed_seconds: float
    qualification: str='independent_entropy_root_shared_native_water_EOS_fixed_phase_inventories_not_interval_error_certificate'


class FixedInventoryEntropyReference:
    def __init__(self,inputs,policy,water):
        if type(inputs) is not OracleInputs or type(policy) is not OraclePolicy:raise EntropyOracleError('explicit_inputs_policy_required')
        self.inputs,self.policy,self.water=inputs,policy,water
        if not policy.temperature_bracket_k[0]<=inputs.initial_temperature_k<=policy.temperature_bracket_k[1]:raise EntropyOracleError('initial_T_outside_bracket')
        self.water_calls=0;self.pressure_solves=0
        if inputs.liquid_mol:
            from sludge_sandbox.water_properties import WaterProperties
            if type(water) is not WaterProperties:raise EntropyOracleError('source_gated_native_water_required')
            self.water_mass=water.reference.molar_mass_kg_mol
            if water.reference.entropy_reference!='native_iapws95_not_aligned_to_nist':raise EntropyOracleError('unexpected_native_entropy_reference')
        else:self.water_mass=0.
        started=time.monotonic()
        p,vg,vl,s,res=self._pressure(inputs.initial_temperature_k,inputs.initial_bulk_volume_m3)
        self.initial_pressure_pa=p;self.initial_gas_volume_m3=vg;self.initial_liquid_entropy_j_kg_k=s
        self.initial_water_calls=self.water_calls;self.initial_elapsed_seconds=time.monotonic()-started

    def _pore_volume(self,bulk):
        i=self.inputs;vp=bulk-i.solid_mol*i.solid_molar_volume_m3_mol
        return _number(vp,'available_pore_volume',positive=True)

    def _pressure(self,t,bulk):
        i=self.inputs;vp=self._pore_volume(bulk);ngrt=i.gas_mol*i.gas_constant_j_mol_k*t
        self.pressure_solves+=1
        if not i.liquid_mol:
            p=ngrt/vp
            if not self.policy.pressure_bracket_pa[0]<=p<=self.policy.pressure_bracket_pa[1]:raise EntropyOracleError('dry_pressure_outside_bracket')
            residual=ngrt/p-vp
            if abs(residual)>self.policy.volume_residual_tolerance_m3:raise EntropyOracleError('pressure_root_residual_exceeds_gate')
            return p,vp,0.,0.,residual
        states={}
        def residual(p):
            self.water_calls+=1
            s=self.water.state_tp(t,p,phase='liquid')
            vl=i.liquid_mol*self.water_mass/s.density_kg_m3
            r=vl+ngrt/p-vp
            _number(r,'volume_residual');states[p]=(vl,s.native_entropy_j_kg_k,r)
            return r
        try:
            p=brentq(residual,*self.policy.pressure_bracket_pa,xtol=self.policy.pressure_xtol_pa,
                rtol=8*math.ulp(1.),maxiter=self.policy.maximum_iterations)
        except (ValueError,RuntimeError,OverflowError) as exc:raise EntropyOracleError('pressure_root_failed:'+str(exc)) from exc
        if p not in states:residual(p)
        vl,s,r=states[p];vg=_number(vp-vl,'gas_volume',positive=True)
        if abs(r)>self.policy.volume_residual_tolerance_m3:raise EntropyOracleError('pressure_root_residual_exceeds_gate')
        return p,vg,vl,s,r

    def solve(self,bulk_volume_m3):
        bulk=_number(bulk_volume_m3,'bulk_volume',positive=True);self._pore_volume(bulk)
        i=self.inputs;calls=self.water_calls;solves=self.pressure_solves;start=time.monotonic();cache={}
        c=i.gas_mol*(i.gas_cp_j_mol_k-i.gas_constant_j_mol_k)+i.solid_mol*i.solid_cp_j_mol_k
        def entropy(t):
            if t not in cache:cache[t]=self._pressure(t,bulk)
            p,vg,vl,s,r=cache[t]
            value=math.fsum((i.liquid_mol*self.water_mass*(s-self.initial_liquid_entropy_j_kg_k),
                c*math.log(t/i.initial_temperature_k),i.gas_mol*i.gas_constant_j_mol_k*math.log(vg/self.initial_gas_volume_m3)))
            return _number(value,'entropy_residual')
        try:
            t=brentq(entropy,*self.policy.temperature_bracket_k,xtol=self.policy.temperature_xtol_k,
                rtol=8*math.ulp(1.),maxiter=self.policy.maximum_iterations)
        except (ValueError,RuntimeError,OverflowError) as exc:raise EntropyOracleError('entropy_root_failed:'+str(exc)) from exc
        ds=entropy(t);p,vg,vl,s,r=cache[t]
        if abs(ds)>self.policy.entropy_residual_tolerance_j_k:raise EntropyOracleError('entropy_root_residual_exceeds_gate')
        return ReferencePoint(t,p,bulk,vg,vl,ds,r,self.water_calls-calls,self.pressure_solves-solves,time.monotonic()-start)
