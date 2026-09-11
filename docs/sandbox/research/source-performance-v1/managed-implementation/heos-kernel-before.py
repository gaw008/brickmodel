"""Isolated native-SI HEOS experiment, not a registered WaterProperties provider."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import math
import warnings
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

    def __setattr__(self, name, value):
        if getattr(self, '_sealed', False):
            raise AttributeError('immutable_HEOS_candidate')
        object.__setattr__(self, name, value)

    @property
    def last_coexistence(self):
        with self._lock:
            return json.loads(json.dumps(self._coexistence))

    @property
    def last_tp(self):
        with self._lock:
            return json.loads(json.dumps(self._tp_iterations))

    def __init__(self, manifest, water_sources):
        import CoolProp
        import CoolProp.CoolProp as CP
        expected = json.loads(Path(manifest).read_text())
        base = Path(CoolProp.__file__).resolve().parent
        if Path(CP.__file__).resolve() != base / 'CoolProp.abi3.so':
            raise WaterSourceError('heos_loaded_extension_path_mismatch')
        if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != expected['adapter_sha256']:
            raise WaterSourceError('heos_adapter_source_changed')
        if json.loads(CP.get_config_as_json_string()) != expected['config']:
            raise WaterSourceError('heos_config_changed')
        self._config = json.dumps(expected['config'], sort_keys=True)
        self._fluid_digest = expected['fluid_sha256']
        self._coexistence = []
        self._tp_iterations = []
        if importlib.metadata.version('CoolProp') != expected['version'] or CP.get_global_param_string('gitrevision') != expected['git']:
            raise WaterSourceError('heos_runtime_identity_changed')
        current_files={str(x.relative_to(base)) for x in base.rglob('*') if x.is_file() and x.suffix in ('.py','.so')}
        if current_files != set(expected['files']):
            raise WaterSourceError('heos_runtime_file_set_changed')
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
            native_phi = original._model._phi0(647.096/t, 1e-8/322.)
            self._entropy_anchor = self._r * (647.096/t*native_phi['fiot']-native_phi['fio'])
            entropy = self._r * (647.096/t*c.dalpha0_dTau()-c.alpha0())
            require(abs(entropy-self._entropy_anchor)*t <= .002, 'heos_ideal_entropy_anchor_mismatch')
        finally:
            c.unspecify_phase()
        self.descriptor_json = json.dumps({'backend':'HEOS::Water','implementation_status':'isolated_stage3_not_host_admitted','runtime':expected,'python_water_assets':dict(original.source_asset_sha256),'public_mass_hex':self._mass.hex(),'native_mass_hex':self._flash.molar_mass().hex(),'public_R_specific_hex':self._r.hex(),'reference':repr(self.reference)},sort_keys=True)
        self.identity = hashlib.sha256(self.descriptor_json.encode()).hexdigest()
        self._sealed = True

    @contextmanager
    def _transaction(self):
        with self._lock:
            if json.dumps(json.loads(self._cp.get_config_as_json_string()),sort_keys=True) != self._config:
                raise WaterSourceError('heos_runtime_config_changed')
            if hashlib.sha256(self._cp.get_fluid_param_string('Water','JSON').encode()).hexdigest() != self._fluid_digest:
                raise WaterSourceError('heos_runtime_fluid_changed')
            with warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter('always')
                yield
            if emitted:
                raise WaterNumericalError('heos_native_warning:'+str(emitted[0].message))
            if hashlib.sha256(self._cp.get_fluid_param_string('Water','JSON').encode()).hexdigest() != self._fluid_digest:
                raise WaterSourceError('heos_runtime_fluid_changed')
            if json.dumps(json.loads(self._cp.get_config_as_json_string()),sort_keys=True) != self._config:
                raise WaterSourceError('heos_runtime_config_changed')

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
        with self._transaction():
            return self._saturation_pair_locked(t)

    def _saturation_pair_locked(self,t):
        # Called only within the public operation's lock and source checks.
        try:
            # QT is an initial guess only. Solve coexistence on the EOS,
            # retaining both equal-pressure and equal-Gibbs residuals.
            densities=[]
            for q in (0,1):
                self._flash.update(self._cp.QT_INPUTS,q,t)
                require(self._flash.phase()==self._cp.iphase_twophase and self._flash.Q()==q,'heos_seed_quality')
                densities.append(self._flash.rhomass())
            self._coexistence.clear()
            def evaluate(rho,phase):
                a=self._flash
                a.specify_phase(self._cp.iphase_liquid if phase=='liquid' else self._cp.iphase_gas)
                try:
                    a.update(self._cp.DmassT_INPUTS,rho,t)
                    pressure,h,u,entropy=a.p(),a.hmass(),a.umass(),a.smass()
                    delta=rho/322.
                    D=1+2*delta*a.dalphar_dDelta()+delta*delta*a.d2alphar_dDelta2()
                    slope=self._r*t*D
                    require(all(math.isfinite(x) for x in (pressure,h,u,entropy,slope)) and slope>0,'heos_coexistence_invalid')
                    return pressure,h-t*entropy,slope,h,u,entropy
                finally:
                    a.unspecify_phase()
            left=right=None
            for iteration in range(8):
                rl,rv=densities
                require(rl>322>rv>0,'heos_coexistence_density_branches')
                if left is None:
                    left,right=evaluate(rl,'liquid'),evaluate(rv,'vapor')
                fp,fg=left[0]-right[0],left[1]-right[1]
                self._coexistence.append({'iteration':iteration,'rho':list(densities),'liquid':left,'vapor':right,'dp':fp,'dg':fg})
                if abs(fp)<=1e-4 and abs(fg)<=1e-6:
                    break
                if iteration == 7:
                    raise WaterNumericalError('heos_coexistence_not_converged')
                a,b,c,d=rl*left[2],-rv*right[2],left[2],-right[2]
                determinant=a*d-b*c
                require(math.isfinite(determinant) and determinant!=0,'heos_coexistence_singular')
                dx,dy=(-fp*d+b*fg)/determinant,(-a*fg+c*fp)/determinant
                require(max(abs(dx),abs(dy))<.1,'heos_coexistence_step_outside_seed_branch')
                # Numerical globalization only: retain the original EOS,
                # branch limits and both absolute coexistence tolerances.
                merit=max(abs(fp)/1e-4,abs(fg)/1e-6)
                attempts=[]
                self._coexistence[-1]['attempts']=attempts
                for trial in range(6):
                    fraction=2.**(-trial)
                    trial_densities=[rl*math.exp(fraction*dx),rv*math.exp(fraction*dy)]
                    require(trial_densities[0]>322>trial_densities[1]>0,
                            'heos_coexistence_density_branches')
                    # Invalid EOS responses remain fatal, rather than being
                    # treated as ordinary lack of numerical improvement.
                    trial_left=evaluate(trial_densities[0],'liquid')
                    trial_right=evaluate(trial_densities[1],'vapor')
                    trial_fp=trial_left[0]-trial_right[0]
                    trial_fg=trial_left[1]-trial_right[1]
                    trial_merit=max(abs(trial_fp)/1e-4,abs(trial_fg)/1e-6)
                    accepted=(abs(trial_fp)<=1e-4 and abs(trial_fg)<=1e-6) or trial_merit<merit
                    attempts.append({'fraction':fraction,'rho':trial_densities,
                                     'dp':trial_fp,'dg':trial_fg,'merit':trial_merit,
                                     'accepted':accepted})
                    if accepted:
                        densities=trial_densities
                        left,right=trial_left,trial_right
                        break
                else:
                    raise WaterNumericalError('heos_coexistence_backtracking_failed')
            else:
                raise WaterNumericalError('heos_coexistence_not_converged')
            # The converged vapor EOS pressure defines the common pressure;
            # the liquid pressure residual is independently checked below.
            # No h/u/s or inventory is algebraically reset to close energy.
            common_p=right[0]
            pair=[]
            for rho,phase in zip(densities,('liquid','vapor')):
                self._flash.specify_phase(self._cp.iphase_liquid if phase=='liquid' else self._cp.iphase_gas)
                try:
                    self._flash.update(self._cp.DmassT_INPUTS,rho,t)
                    pair.append(self._snapshot(t,common_p,phase))
                finally:
                    self._flash.unspecify_phase()
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
        with self._transaction():
            liquid,vapor=self._saturation_pair_locked(t)
            ps=liquid.pressure
            if abs(p-ps)<=max(.01,2e-8*ps):raise WaterDomainError('saturation_ambiguous')
            if (phase=='liquid' and p<ps) or (phase=='vapor' and p>ps):raise WaterDomainError('unstable_requested_phase')
            try:
                a=self._flash
                a.update(self._cp.PT_INPUTS,p,t)
                allowed=(self._cp.iphase_liquid,self._cp.iphase_supercritical_liquid) if phase=='liquid' else (self._cp.iphase_gas,)
                require(a.phase() in allowed,'heos_tp_seed_wrong_phase')
                rho=a.rhomass()
                self._tp_iterations.clear()
                a.specify_phase(self._cp.iphase_liquid if phase=='liquid' else self._cp.iphase_gas)
                try:
                    def evaluate_density(density: float, iteration: int, fraction: float | None) -> tuple[float, float, float, dict]:
                        require(math.isfinite(density) and density>0,'heos_tp_invalid_density')
                        require(density>=liquid.density if phase=='liquid' else density<=vapor.density,'heos_tp_density_branch')
                        record={'iteration':iteration,'rho':density,'target_p':p,
                                'fraction':fraction,'accepted':False,'status':'started'}
                        self._tp_iterations.append(record)
                        try:
                            a.update(self._cp.DmassT_INPUTS,density,t)
                            delta=density/322.
                            slope=density*self._r*t*(1+2*delta*a.dalphar_dDelta()+delta*delta*a.d2alphar_dDelta2())
                            residual=a.p()-p
                            record.update(native_p=a.p(),h=a.hmass(),u=a.umass(),residual_pa=residual,slope=slope)
                            require(math.isfinite(slope) and slope>0 and math.isfinite(residual),'heos_tp_invalid_slope')
                            require(a.phase() in allowed,'heos_tp_seed_wrong_phase')
                            gate=min(1e-4,density*1e-7)
                            # Keep the original gate even at underflow: only an
                            # actual zero residual passes a zero gate.
                            merit=abs(residual)/gate if gate>0 else (0. if residual==0 else math.inf)
                            record.update(gate_pa=gate,normalized_residual=merit,status='complete')
                            return slope,residual,merit,record
                        except BaseException as exc:
                            record.update(status='failed',error_type=type(exc).__name__,reason=str(exc))
                            raise

                    slope,residual,merit,record=evaluate_density(rho,0,None)
                    record['accepted']=True
                    for iteration in range(8):
                        if abs(residual)<=min(1e-4,rho*1e-7):
                            break
                        if iteration==7:
                            raise WaterNumericalError('heos_tp_not_converged')
                        step=-residual/slope
                        # Test the ORIGINAL Newton direction before damping.
                        require(math.isfinite(step) and abs(step)<.1,'heos_tp_step_outside_seed_branch')
                        for fraction in (1.,.5,.25,.125,.0625,.03125):
                            candidate=rho*math.exp(fraction*step)
                            trial_slope,trial_residual,trial_merit,trial_record=evaluate_density(candidate,iteration+1,fraction)
                            if abs(trial_residual)<=min(1e-4,candidate*1e-7) or trial_merit<merit:
                                trial_record['accepted']=True
                                rho,slope,residual,merit=candidate,trial_slope,trial_residual,trial_merit
                                break
                        else:
                            raise WaterNumericalError('heos_tp_backtracking_failed')
                        # The accepted candidate is already the current native
                        # state. Reuse it without another native evaluation.
                    result=self._snapshot(t,p,phase)
                finally:
                    a.unspecify_phase()
                require(result.density>=liquid.density if phase=='liquid' else result.density<=vapor.density,'heos_density_branch')
                return result
            except (ArithmeticError,ValueError,RuntimeError,AttributeError,TypeError) as e:
                if isinstance(e,WaterNumericalError):raise
                raise WaterNumericalError('heos_tp_failed') from e
