"""Rigid available pore volume: planar liquid water plus complete ideal-gas inventory.

Only pressure/volume mechanical closure at prescribed temperature is solved.
No vapor-liquid chemical equilibrium, capillarity, or sludge constitutive law is
inferred. Liquid water retains its native IAPWS EOS and fitted gas constant.
"""
from sludge_sandbox.water_properties import is_water_provider
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from fractions import Fraction
import math
from numbers import Real
from types import MappingProxyType
from typing import ClassVar

from .water_properties import WaterProperties, WaterDomainError, WaterNumericalError


class RigidClosureDomainError(ValueError):
    """Inventory/geometry/model domain or the explicit stable pressure bracket is invalid."""


class RigidClosureNumericalError(ValueError):
    """Permitted closure cannot be resolved within explicit numerical requirements."""


_R = 8.31446261815324
_ASSUMPTION = 'planar_interface_no_capillary_pressure'


def _number(value,name,*,positive=False,nonnegative=False,error=RigidClosureDomainError):
    try:v=float(value) if isinstance(value,Real) and not isinstance(value,bool) else math.nan
    except (OverflowError,ValueError):v=math.nan
    if not math.isfinite(v) or (positive and v<=0) or (nonnegative and v<0):raise error('invalid_'+name)
    return v


def _finite(value,name,*,positive=False):
    return _number(value,name,positive=positive,error=RigidClosureNumericalError)


def _sum(values):
    try:return _finite(math.fsum(values),'finite_sum')
    except OverflowError as exc:raise RigidClosureNumericalError('nonfinite_sum') from exc


@dataclass(frozen=True)
class PressurePolicy:
    volume_tolerance_m3: float
    pressure_tolerance_pa: float
    maximum_iterations: int
    strategy: str | None = field(default=None, metadata={"omit_when_none": True})

    def __post_init__(self):
        if self.strategy is not None and (type(self.strategy) is not str or self.strategy != 'guarded_liquid_endpoint_interpolation_v1'):
            raise RigidClosureDomainError('invalid_pressure_strategy')
        _number(self.volume_tolerance_m3,'volume_tolerance',positive=True)
        _number(self.pressure_tolerance_pa,'pressure_tolerance',positive=True)
        if type(self.maximum_iterations) is not int or self.maximum_iterations<=0:raise RigidClosureDomainError('invalid_iteration_limit')


@dataclass(frozen=True)
class PressureTrialRecord:
    pressure_pa: float
    bracket_before_pa: tuple[float, float]
    residuals_before_m3: tuple[float | None, float | None]
    kind: str
    status: str
    liquid_volume_m3: float | None = None
    residual_m3: float | None = None
    bracket_after_pa: tuple[float, float] | None = None
    failure: str | None = None


@dataclass(frozen=True)
class RigidWaterGasState:
    temperature_k: float
    pressure_pa: float
    liquid_pressure_pa: float | None
    liquid_inventory_mol: float
    gas_inventory_mol: Mapping[str,float]
    liquid_volume_m3: float
    gas_volume_m3: float
    partial_pressures_pa: Mapping[str,float]
    volume_residual_m3: float
    pressure_residual_pa: float
    volume_resolution_m3: float
    pressure_resolution_pa: float
    pressure_bracket_pa: tuple[float,float]
    policy: PressurePolicy
    iterations: int
    source_ids: tuple[str,...]
    source_asset_sha256: Mapping[str,str]
    assumption: str = _ASSUMPTION
    qualification: str = 'pure_water_planar_interface_ideal_gas_not_sludge_or_phase_equilibrium'
    gas_constant_j_mol_k: float = _R
    liquid_native_molar_gas_constant_j_mol_k: float = 8.314371357587
    final_numerical_pressure_bracket_pa: tuple[float,float] | None = None
    final_bracket_volume_residuals_m3: tuple[float,float] | None = None
    pressure_solution_path: str = 'not_recorded'
    pressure_bracket_qualification: str = 'not_recorded_legacy_constructor'
    pressure_trial_ledger: tuple[PressureTrialRecord, ...] | None = field(default=None, metadata={'omit_when_none': True})


def closure_diagnostics(volume: float, vl: float, p: float, nrt: float,
                        nrt_resolution: float) -> tuple[float, float, float, float, float, float]:
    """Original represented closure residuals and resolution, without an EOS."""
    vg=_finite(_sum((volume,-vl)),'open_gas_volume',positive=True)
    ideal_p=_finite(nrt/vg,'gas_pressure',positive=True)
    residual_p=_sum((p,-ideal_p))
    residual_v=_sum((vl,nrt/p,-volume))
    vr=_sum((math.ulp(volume),math.ulp(vl),math.ulp(vg),math.ulp(nrt/p),nrt_resolution/p))
    pr=_sum((math.ulp(p),math.ulp(ideal_p),abs(ideal_p)*vr/vg))
    return vg,ideal_p,residual_p,residual_v,vr,pr


@dataclass(frozen=True)
class RigidWaterGas:
    water: WaterProperties
    gas_species_ids: tuple[str,...]
    available_pore_volume_m3: float
    pressure_bracket_pa: tuple[float,float]
    assumption: str
    policy: PressurePolicy
    gas_constant_j_mol_k: ClassVar[float] = _R
    constant_source_ids: ClassVar[tuple[str,...]] = ('nist-codata-2022',)

    def __post_init__(self):
        if not is_water_provider(self.water):raise RigidClosureDomainError('source_gated_water_required')
        ids=self.gas_species_ids
        if not isinstance(ids,tuple) or not ids or any(not isinstance(x,str) or not x.strip() for x in ids) or len(set(ids))!=len(ids):
            raise RigidClosureDomainError('explicit_unique_complete_gas_species_required')
        _number(self.available_pore_volume_m3,'available_volume',positive=True)
        if not isinstance(self.pressure_bracket_pa,tuple) or len(self.pressure_bracket_pa)!=2:raise RigidClosureDomainError('explicit_pressure_bracket_required')
        lo,hi=(_number(x,'pressure',positive=True) for x in self.pressure_bracket_pa)
        if lo>=hi:raise RigidClosureDomainError('invalid_pressure_bracket')
        if self.assumption!=_ASSUMPTION:raise RigidClosureDomainError('explicit_planar_interface_assumption_required')
        if type(self.policy) is not PressurePolicy:raise RigidClosureDomainError('explicit_pressure_policy_required')

    def _liquid_volume(self,t,p,n):
        if not n:return 0.
        try:s=self.water.state_tp(t,p,phase='liquid')
        except WaterDomainError as exc:raise RigidClosureDomainError('unstable_liquid_pressure_bracket_or_water_domain:'+str(exc)) from exc
        except WaterNumericalError as exc:raise RigidClosureNumericalError('liquid_property_solution:'+str(exc)) from exc
        return _finite(n*s.molar_mass_kg_mol/s.density_kg_m3,'liquid_volume',positive=True)

    def evaluate_at_temperature(self,temperature_k,liquid_inventory_mol,gas_inventory_mol):
        ledger = [] if self.policy.strategy is not None else None
        try:
            result = self._evaluate_at_temperature(temperature_k,liquid_inventory_mol,gas_inventory_mol,ledger)
            return result if ledger is None else replace(result,pressure_trial_ledger=tuple(ledger))
        except Exception as exc:
            if ledger is not None:
                if ledger and ledger[-1].status == 'evaluated':
                    ledger[-1]=replace(ledger[-1],status='failed',failure=type(exc).__name__+':'+str(exc))
                exc.pressure_trial_ledger = tuple(ledger)
            raise

    def _evaluate_at_temperature(self,temperature_k,liquid_inventory_mol,gas_inventory_mol,ledger):
        t=_number(temperature_k,'temperature',positive=True)
        nl=_number(liquid_inventory_mol,'liquid_inventory',nonnegative=True)
        if not isinstance(gas_inventory_mol,Mapping) or set(gas_inventory_mol)!=set(self.gas_species_ids):
            raise RigidClosureDomainError('complete_gas_inventory_keys_required')
        gas={key:_number(gas_inventory_mol[key],'gas_inventory',nonnegative=True) for key in self.gas_species_ids}
        ng=_sum(gas.values())
        if ng<=0:raise RigidClosureDomainError('positive_total_gas_inventory_required')
        nrt=_finite(ng*_R*t,'gas_inventory_RT',positive=True)
        nrt_resolution=_sum((math.ulp(ng)*_R*t,math.ulp(ng*_R)*t,math.ulp(nrt)))
        lo,hi=self.pressure_bracket_pa
        if max(math.ulp(lo),math.ulp(hi))>self.policy.pressure_tolerance_pa:
            raise RigidClosureNumericalError('unresolvable_pressure_precision')
        volume=self.available_pore_volume_m3

        flo=fhi=None
        trial_kind='initial_endpoint'
        def trial(p):
            if ledger is not None:
                ledger.append(PressureTrialRecord(p,(lo,hi),(flo,fhi),trial_kind,'started'))
            try:
                vl=self._liquid_volume(t,p,nl)
                vg=_finite(nrt/p,'trial_gas_volume',positive=True)
                f=_sum((vl,vg,-volume))
            except Exception as exc:
                if ledger is not None:
                    ledger[-1]=replace(ledger[-1],status='failed',failure=type(exc).__name__+':'+str(exc))
                raise
            if ledger is not None:
                ledger[-1]=replace(ledger[-1],status='evaluated',liquid_volume_m3=vl,residual_m3=f)
            return vl,f

        def finish(p,vl,iterations,final_bracket,endpoint_residuals,solution_path):
            # Preserve representability of the two large volumes even when
            # their difference leaves a very small open gas volume.
            vg,ideal_p,residual_p,residual_v,vr,pr=closure_diagnostics(volume,vl,p,nrt,nrt_resolution)
            if vr>self.policy.volume_tolerance_m3 or pr>self.policy.pressure_tolerance_pa:
                raise RigidClosureNumericalError('unresolvable_volume_pressure_precision')
            if abs(residual_v)>self.policy.volume_tolerance_m3 or abs(residual_p)>self.policy.pressure_tolerance_pa:
                return None
            # Form the ratio-product exactly from represented inputs: n/ng can
            # underflow even when n*p/ng is representable.
            partial={key:_finite(float(Fraction(n)*Fraction(p)/Fraction(ng)),
                       'partial_pressure',positive=n>0) for key,n in gas.items()}
            if abs(_sum(partial.values())-p)>self.policy.pressure_tolerance_pa:
                raise RigidClosureNumericalError('partial_pressure_sum_residual')
            return RigidWaterGasState(t,p,p if nl else None,nl,MappingProxyType(gas),vl,vg,
                MappingProxyType(partial),residual_v,residual_p,vr,pr,self.pressure_bracket_pa,
                self.policy,iterations,self.water.source_ids+self.constant_source_ids,
                self.water.source_asset_sha256,liquid_native_molar_gas_constant_j_mol_k=self.water.reference.native_molar_gas_constant_j_mol_k,
                final_numerical_pressure_bracket_pa=final_bracket,
                final_bracket_volume_residuals_m3=endpoint_residuals,
                pressure_solution_path=solution_path,
                pressure_bracket_qualification='numerical_forward_function_only_excludes_eos_error')

        if not nl:
            p=_finite(nrt/volume,'gas_pressure',positive=True)
            if not lo<=p<=hi:raise RigidClosureDomainError('pure_gas_pressure_out_of_explicit_bracket')
            residual=_sum((nrt/p,-volume))
            state=finish(p,0.,0,(p,p),(residual,residual),'pure_gas_analytic_rounded')
            if state is None:raise RigidClosureNumericalError('pure_gas_closure_residual')
            return state
        # F(P)=V_liquid(T,P)+Ng RT/P-V_available is strictly decreasing on
        # the stable liquid branch: dV_liquid/dP<0 and Ng>0. No density sampling
        # is presented as proof; mechanical stability is checked by water EOS.
        vl_lo,flo=trial(lo);vl_hi,fhi=trial(hi)
        if flo<0 or fhi>0:
            raise RigidClosureDomainError('no_root_in_stable_pressure_bracket_or_insufficient_volume')
        for edge,vl,f in ((lo,vl_lo,flo),(hi,vl_hi,fhi)):
            if f==0:
                state=finish(edge,vl,0,(edge,edge),(f,f),'liquid_exact_numerical_endpoint')
                if state is not None:return state
        if self.policy.strategy is not None:
            count=0
            while count < self.policy.maximum_iterations:
                start_width=hi-lo
                proposals=[]
                if start_width > self.policy.pressure_tolerance_pa:
                    for liquid,direction in ((vl_hi,-math.inf),(vl_lo,math.inf)):
                        denominator=Fraction(volume)-Fraction(liquid)
                        if denominator>0:
                            try:
                                candidate=float(Fraction(nrt)/denominator)
                            except OverflowError:
                                continue
                            candidate=math.nextafter(candidate,direction)
                            if math.isfinite(candidate) and lo<candidate<hi and candidate not in proposals:
                                proposals.append(candidate)
                # After at most two proposals, enforce bisection unless they
                # already halved the bracket. Width-gated finish still uses a
                # fresh evaluated candidate and the unchanged residual/precision checks.
                for candidate in proposals+[None]:
                    if count>=self.policy.maximum_iterations:break
                    if candidate is None:
                        if hi-lo<=start_width/2 and hi-lo>self.policy.pressure_tolerance_pa:
                            continue
                        candidate=lo+(hi-lo)/2
                        trial_kind='guarded_midpoint'
                    else:
                        trial_kind='liquid_endpoint_proposal'
                        if not lo<candidate<hi:continue
                    if candidate in (lo,hi):
                        raise RigidClosureNumericalError('unresolvable_pressure_bracket')
                    count+=1
                    vl,f=trial(candidate)
                    if not fhi<=f<=flo:
                        ledger[-1]=replace(ledger[-1],status='failed',failure='nonmonotonic_pressure_evaluation')
                        raise RigidClosureNumericalError('nonmonotonic_pressure_evaluation')
                    if hi-lo<=self.policy.pressure_tolerance_pa:
                        state=finish(candidate,vl,count,(lo,hi),(flo,fhi),'liquid_endpoint_interpolation')
                        if state is not None:
                            ledger[-1]=replace(ledger[-1],status='finished',bracket_after_pa=(lo,hi))
                            return state
                    if f>0:lo=candidate;flo=f;vl_lo=vl
                    else:hi=candidate;fhi=f;vl_hi=vl
                    ledger[-1]=replace(ledger[-1],status='bracket_updated',bracket_after_pa=(lo,hi))
            raise RigidClosureNumericalError('pressure_iteration_limit')
        for count in range(1,self.policy.maximum_iterations+1):
            middle=lo+(hi-lo)/2
            if middle in (lo,hi):raise RigidClosureNumericalError('unresolvable_pressure_bracket')
            vl,f=trial(middle)
            if not fhi<=f<=flo:raise RigidClosureNumericalError('nonmonotonic_pressure_evaluation')
            if hi-lo<=self.policy.pressure_tolerance_pa:
                state=finish(middle,vl,count,(lo,hi),(flo,fhi),'liquid_bisection')
                if state is not None:return state
            if f>0:lo=middle;flo=f
            else:hi=middle;fhi=f
        raise RigidClosureNumericalError('pressure_iteration_limit')
