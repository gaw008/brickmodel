"""Explicit hybrid water adapter: verified HEOS real fluid, pinned Python ideal law."""
from .source_run_observer import emit_source_event, emit_source_failure
from dataclasses import dataclass,field,replace,asdict
import hashlib,json,sys,importlib.metadata
from pathlib import Path
from types import MappingProxyType
from .water_properties import WaterProperties,WaterState,WaterResponse,SaturationPair,NumericalLimits,WaterNumericalError,WaterSourceError
from .water_implementation import WaterImplementation
from ._heos_kernel import HEOSCandidate
from ._heos_kernel_v1 import HEOSCandidate as LegacyHEOSCandidate
from .heos_runtime_registry import RHS_MANIFEST_ASSET, WORKFLOW_MANIFEST_ASSET, RESUME_MANIFEST_ASSET


@dataclass(frozen=True,init=False)
class HEOSWaterProperties:
    reference: object
    source_asset_sha256: object
    numerical_limits: NumericalLimits
    implementation: WaterImplementation
    _kernel: object=field(repr=False,compare=False)
    _ideal: object=field(repr=False,compare=False)

    def __init__(self,source_directory,manifest):
        kernel = None
        try:
            emit_source_event('heos_started', source_directory=source_directory, manifest=manifest)
            try:
                verified_bytes=Path(manifest).read_bytes()
                manifest_sha = hashlib.sha256(verified_bytes).hexdigest()
                if manifest_sha not in ('5f9e39bf1d3376b931caaf8fbda478b482cafe4c8b57a490860ac6ed080bf6db',
                                         RHS_MANIFEST_ASSET[2], WORKFLOW_MANIFEST_ASSET[2], RESUME_MANIFEST_ASSET[2]):
                    raise WaterSourceError('unreviewed_heos_manifest')
                verified_manifest=json.loads(verified_bytes)
                candidate_type = HEOSCandidate if manifest_sha in (RHS_MANIFEST_ASSET[2], WORKFLOW_MANIFEST_ASSET[2], RESUME_MANIFEST_ASSET[2]) else LegacyHEOSCandidate
                if candidate_type is HEOSCandidate:
                    for name, expected in verified_manifest['execution_sources'].items():
                        if Path(name).name != name or not name.endswith('.py'):
                            raise WaterSourceError('heos_execution_source_path')
                        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != expected:
                            raise WaterSourceError('heos_execution_source_changed:' + name)
                kernel=candidate_type(manifest,source_directory)
            except (ImportError,OSError,json.JSONDecodeError,KeyError) as exc:
                raise WaterSourceError('required_heos_dependencies_or_manifest_unavailable') from exc
            emit_source_event('heos_kernel_returned', source_directory=source_directory, manifest=manifest, kernel=kernel)
            try:
                if json.loads(kernel.descriptor_json)['runtime']!=verified_manifest:
                    raise WaterSourceError('heos_manifest_changed_during_load')
            except (ImportError,OSError,json.JSONDecodeError,KeyError) as exc:
                raise WaterSourceError('required_heos_dependencies_or_manifest_unavailable') from exc
            ideal=WaterProperties(source_directory)
            if kernel.reference != ideal.reference:
                raise WaterNumericalError('hybrid_reference_mismatch')
            payload={'schema':'hybrid_water_v1','real_fluid':json.loads(kernel.descriptor_json),
                'ideal':'source_verified_python_iapws_1.5.5_ideal_helmholtz',
                'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'ideal_adapter_sha256':hashlib.sha256(Path(__file__).with_name('water_properties.py').read_bytes()).hexdigest(),
                'ideal_dispatch_sha256':hashlib.sha256(Path(__file__).with_name('_water_python_backend.py').read_bytes()).hexdigest(),
                'descriptor_code_sha256':hashlib.sha256(Path(__file__).with_name('water_implementation.py').read_bytes()).hexdigest(),
                'hybrid_runtime':{'python':sys.version,'packages':{name:importlib.metadata.version(name) for name in ('iapws','numpy','scipy')}},
                'public_state_schema':'water_state_optional_implementation_v1',
                'reference':asdict(kernel.reference),'numerical_limits':asdict(NumericalLimits())}
            descriptor=WaterImplementation('water_implementation_v1','heos95_python_ideal_hybrid','8.0.0+iapws1.5.5',
                ('coolprop-8.0.0-heos-water',),json.dumps(payload,sort_keys=True,separators=(',',':')))
            assets=dict(ideal.source_asset_sha256)
            assets['water_implementation_v1.json']=descriptor.sha256
            for name,value in [('reference',kernel.reference),('source_asset_sha256',MappingProxyType(assets)),
                ('numerical_limits',NumericalLimits()),('implementation',descriptor),('_kernel',kernel),('_ideal',ideal)]:
                object.__setattr__(self,name,value)
            emit_source_event('heos_returned', source_directory=source_directory, manifest=manifest, water=self)
        except BaseException as exc:
            emit_source_failure('heos_failed', exc, source_directory=source_directory, manifest=manifest, water=self, kernel=kernel)
            raise

    @property
    def _model(self):
        # Existing ideal entropy/coefficient proofs remain explicitly Python.
        return self._ideal._model

    @property
    def source_ids(self):
        return self.reference.source_ids+self.implementation.source_ids

    def _guard(self):
        if (self.reference is not self._kernel.reference or self._ideal.reference!=self.reference
            or self.numerical_limits!=NumericalLimits()
            or dict(self.source_asset_sha256)!=(dict(self._ideal.source_asset_sha256)|{'water_implementation_v1.json':self.implementation.sha256})
            or json.loads(self.implementation.canonical_descriptor)['real_fluid']!=json.loads(self._kernel.descriptor_json)):
            raise WaterNumericalError('hybrid_implementation_identity_changed')

    def _state(self,s):
        if s.implementation!=self._kernel.identity:
            raise WaterNumericalError('hybrid_snapshot_implementation_mismatch')
        return WaterState(s.temperature,s.h,s.u,s.cp,s.cv,self.reference,'iapws95_real_fluid_helmholtz',
            s.pressure,s.phase,s.density,s.s,s.residuals[0],s.residuals[1],implementation=self.implementation)

    def state_tp(self,temperature_k,pressure_pa,*,phase):
        self._guard()
        return self._state(self._kernel.state_tp(temperature_k,pressure_pa,phase=phase))

    def state_tp_response(self,temperature_k,pressure_pa,*,phase):
        self._guard()
        s=self._kernel.state_tp(temperature_k,pressure_pa,phase=phase)
        state=self._state(s)
        return WaterResponse(state,s.alpha,s.kappa,s.dv_dt,s.dv_dp,s.du_dp,s.residuals[-1])

    def saturation_pair(self,temperature_k):
        self._guard()
        a,b=self._kernel.saturation_pair(temperature_k)
        liquid,vapor=self._state(a),self._state(b)
        residual=liquid.native_enthalpy_j_kg-temperature_k*liquid.native_entropy_j_kg_k-vapor.native_enthalpy_j_kg+temperature_k*vapor.native_entropy_j_kg_k
        return SaturationPair(float(temperature_k),a.pressure,liquid,vapor,residual)

    def ideal_vapor(self,temperature_k):
        self._guard()
        return replace(self._ideal.ideal_vapor(temperature_k),reference=self.reference,implementation=self.implementation)
