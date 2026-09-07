"""Isolated native-SI HEOS experiment, not a registered WaterProperties provider."""
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
from threading import RLock

from sludge_sandbox.water_properties import (
    WaterDomainError, WaterNumericalError, WaterSourceError, load_water_properties,
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def require(condition, reason):
    if not condition:
        raise WaterNumericalError(reason)


@dataclass(frozen=True)
class Snapshot:
    temperature: float
    pressure: float
    phase: str
    density: float
    h: float
    u: float
    s: float
    cp: float
    cv: float
    alpha: float
    kappa: float
    dv_dt: float
    dv_dp: float
    du_dp: float
    implementation: str
    residuals: tuple


class HEOSCandidate:
    """Native flash plus Table 3 checks; no mixture-host or alternate-source alias."""

    def __init__(self, manifest, water_sources):
        import CoolProp
        import CoolProp.CoolProp as CP
        expected = json.loads(Path(manifest).read_text())
        base = Path(CoolProp.__file__).resolve().parent
        if importlib.metadata.version('CoolProp') != expected['version'] or CP.get_global_param_string('gitrevision') != expected['git']:
            raise WaterSourceError('heos_runtime_identity_changed')
        for name, sha in expected['files'].items():
            if hashlib.sha256((base / name).read_bytes()).hexdigest() != sha:
                raise WaterSourceError('heos_runtime_file_changed:' + name)
        raw = CP.get_fluid_param_string('Water', 'JSON')
        if hashlib.sha256(raw.encode()).hexdigest() != expected['fluid_sha256'] or digest(json.loads(raw)) != expected['fluid_canonical_sha256']:
            raise WaterSourceError('heos_fluid_changed')
        eos = json.loads(raw)[0]['EOS'][0]
        if (eos['BibTeX_EOS'], eos['molar_mass'], eos['gas_constant'], eos['STATES']['reducing']['T']) != ('Wagner-JPCRD-2002', .018015268, 8.314371357587, 647.096):
            raise WaterSourceError('heos_eos_constants_changed')
        original = load_water_properties(water_sources)
        self.reference = original.reference
        self._cp = CP
        self._flash = CoolProp.AbstractState('HEOS', 'Water')
        self._check = CoolProp.AbstractState('HEOS', 'Water')
        self._lock = RLock()
        if self._flash.molar_mass() != .018015268 or self._flash.gas_constant() != self.reference.native_molar_gas_constant_j_mol_k:
            raise WaterSourceError('heos_native_constants_changed')
        self._r = self.reference.native_specific_gas_constant_j_kg_k
        self._mass = self.reference.molar_mass_kg_mol
        require(self._flash.T_reducing() == 647.096, 'heos_reducing_temperature')
        require(math.isclose(self._flash.rhomolar_reducing() * self._flash.molar_mass(), 322., rel_tol=2e-15), 'heos_reducing_density')
        # Preserve the exact published Python reference. Check its ideal anchor
        # against HEOS derivatives; never call global set_reference_state.
        c = self._check
        c.specify_phase(CP.iphase_gas)
        try:
            c.update(CP.DmassT_INPUTS, 1e-8, self.reference.anchor_temperature_k)
            t = self.reference.anchor_temperature_k
            anchor = self._r * t * (1 + 647.096 / t * c.dalpha0_dTau())
            old = original.ideal_vapor(t).native_enthalpy_j_kg
            require(abs(anchor - old) <= .002, 'heos_ideal_reference_anchor_mismatch')
        finally:
            c.unspecify_phase()
        self.descriptor_json = json.dumps({'backend':'HEOS::Water','implementation_status':'isolated_stage3_not_host_admitted','runtime':expected,'python_water_assets':dict(original.source_asset_sha256),'public_mass_hex':self._mass.hex(),'native_mass_hex':self._flash.molar_mass().hex(),'public_R_specific_hex':self._r.hex(),'reference':repr(self.reference)},sort_keys=True)
        self.identity = hashlib.sha256(self.descriptor_json.encode()).hexdigest()

    @staticmethod
    def _temperature(t):
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) or not 293 <= t <= 500:
            raise WaterDomainError('temperature_out_of_declared_domain')
        return float(t)

    def _snapshot(self, t, p, phase, saturation=False):
        a, c, CP = self._flash, self._check, self._cp
        rho,h,u,s,cp,cv = [f() for f in (a.rhomass,a.hmass,a.umass,a.smass,a.cpmass,a.cvmass)]
        require(all(math.isfinite(x) for x in (rho,h,u,s,cp,cv,a.T(),a.p())), 'heos_nonfinite_flash')
        require(min(rho,cp,cv) > 0 and abs(a.T()-t) <= 1e-9, 'heos_invalid_flash')
        require(abs(a.p()-p) <= max(.01, 2e-8*abs(p)), 'heos_returned_pressure')
        if saturation:
            require(a.phase() == CP.iphase_twophase and a.Q() == (0 if phase=='liquid' else 1), 'heos_wrong_quality')
        else:
            accepted = (CP.iphase_liquid, CP.iphase_supercritical_liquid) if phase=='liquid' else (CP.iphase_gas,)
            require(a.phase() in accepted, 'heos_wrong_phase')
        c.specify_phase(CP.iphase_liquid if phase=='liquid' else CP.iphase_gas)
        try:
            c.update(CP.DmassT_INPUTS, rho, t)
            tau,delta=647.096/t,rho/322.
            a0,ar=c.alpha0(),c.alphar()
            at=c.dalpha0_dTau()+c.dalphar_dTau()
            att=c.d2alpha0_dTau2()+c.d2alphar_dTau2()
            rd,rdd,rdt=c.dalphar_dDelta(),c.d2alphar_dDelta2(),c.d2alphar_dDelta_dTau()
        finally:
            c.unspecify_phase()
        require(all(math.isfinite(x) for x in (a0,ar,at,att,rd,rdd,rdt)), 'heos_nonfinite_derivative')
        D=1+2*delta*rd+delta*delta*rdd
        B=1+delta*rd-delta*tau*rdt
        require(D>0, 'heos_unstable_density')
        pc=rho*self._r*t*(1+delta*rd)
        hc=self._r*t*(1+tau*at+delta*rd)
        sc=self._r*(tau*at-a0-ar)
        cvc=-self._r*tau*tau*att
        cpc=cvc+self._r*B*B/D
        alpha,kappa=B/(t*D),1/(rho*self._r*t*D)
        volume=self._mass/rho
        dvdt,dvdp=volume*alpha,-volume*kappa
        dudp=math.fsum((-t*dvdt,-p*dvdp))
        residuals=(abs(pc-p),abs(h-u-p/rho),abs(hc-h),abs(sc-s)*t,abs(cpc-cp),abs(cvc-cv),abs((cp-cv)*self._mass-t*volume*alpha*alpha/kappa))
        limits=(max(.01,2e-8*abs(p)),1e-6,.002,.002,1e-5,1e-5,1e-7)
        require(all(math.isfinite(x) and x<=lim for x,lim in zip(residuals,limits)), 'heos_table3_residual:'+repr(residuals))
        require(all(math.isfinite(x) for x in (alpha,kappa,dvdt,dvdp,dudp)) and kappa>0,'heos_invalid_response')
        return Snapshot(t,p,phase,rho,h,u,s,cp,cv,alpha,kappa,dvdt,dvdp,dudp,self.identity,residuals)

    def saturation_pair(self,t):
        t=self._temperature(t)
        with self._lock:
            try:
                pair=[]
                for q,phase in ((0,'liquid'),(1,'vapor')):
                    self._flash.update(self._cp.QT_INPUTS,q,t)
                    pair.append(self._snapshot(t,self._flash.p(),phase,True))
                liquid,vapor=pair
                require(liquid.density>vapor.density,'heos_saturation_order')
                require(abs(liquid.pressure-vapor.pressure)<=max(.01,2e-8*liquid.pressure),'heos_saturation_pressure')
                require(abs(liquid.h-t*liquid.s-vapor.h+t*vapor.s)<=.001,'heos_saturation_gibbs')
                return tuple(pair)
            except (ArithmeticError,ValueError,RuntimeError,AttributeError,TypeError) as e:
                if isinstance(e,WaterNumericalError):raise
                raise WaterNumericalError('heos_saturation_failed') from e

    def state_tp(self,t,p,*,phase):
        t=self._temperature(t)
        if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<p<=1e8:
            raise WaterDomainError('pressure_out_of_declared_domain')
        if phase not in ('liquid','vapor'):
            raise WaterDomainError('phase_must_be_liquid_or_vapor')
        with self._lock:
            liquid,vapor=self.saturation_pair(t)
            ps=liquid.pressure
            if abs(p-ps)<=max(.01,2e-8*ps):raise WaterDomainError('saturation_ambiguous')
            if (phase=='liquid' and p<ps) or (phase=='vapor' and p>ps):raise WaterDomainError('unstable_requested_phase')
            try:
                self._flash.update(self._cp.PT_INPUTS,p,t)
                result=self._snapshot(t,p,phase)
                require(result.density>=liquid.density if phase=='liquid' else result.density<=vapor.density,'heos_density_branch')
                return result
            except (ArithmeticError,ValueError,RuntimeError,AttributeError,TypeError) as e:
                if isinstance(e,WaterNumericalError):raise
                raise WaterNumericalError('heos_tp_failed') from e
