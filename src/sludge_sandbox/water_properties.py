"""Source-gated pure-water IAPWS-95 properties, with a common NIST energy offset.

IAPWS R6-95(2018) supplies the mass-based equation and its fixed fitted constant.
jjgomera/iapws 1.5.5 is an external GPLv3 dependency; its unmodified source and
license are retained in data/sandbox/water. No upstream implementation is copied
into this adapter. The defective upstream ideal u0/a0 outputs are never read.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import importlib
import importlib.metadata
import json
import math
from numbers import Real
from pathlib import Path
from types import MappingProxyType
from typing import Literal
import warnings
import zipfile


class WaterError(ValueError):
    """Base error for the bounded pure-water adapter."""


class WaterDomainError(WaterError):
    """Requested input or phase is outside the declared physical domain."""


class WaterNumericalError(WaterError):
    """A permitted input did not produce a verified finite numerical solution."""


class WaterSourceError(WaterError):
    """The fixed source package, evidence assets, or runtime could not be verified."""


class WaterCompatibilityError(WaterError):
    """Another thermochemical model uses an incompatible reference convention."""


_SOURCE_IDS = ("iapws-r6-95-2018", "jjgomera-iapws-1.5.5", "nist-h2o-chase-1998-reference")
_ASSET_HASHES = {
    "IAPWS95-2018.pdf": "512879217b94f4d0741c88cab743d41098268914d538d73e680a736cb1c3aad7",
    "iapws-1.5.5-py3-none-any.whl": "97810dca5155cce1e2ec964dd254fc9e4858fbb1c9967da6c4f817adaf3a818e",
    "iapws-1.5.5-iapws95.py": "89edb7c0e3b77533319d253819cdb4c1da50775d2e7b324249574607d6790520",
    "iapws-1.5.5-LICENSE": "fe3eea6c599e23a00c08c5f5cb2320c30adc8f8687db5fcec9b79a662c53ff6b",
    "source_facts.json": "53af498b3974d180d273d7b17a6619d49d9a7d90bbacdd6e0304651f33bd79d6",
}
_MIN_T = 293.0
_MAX_T = 500.0
_MAX_PRESSURE_PA = 100_000_000.0
_CRITICAL_T = 647.096
_CRITICAL_RHO = 322.0


def _number(value, name, *, error=WaterDomainError, positive=False):
    try:
        valid = isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
        result = float(value) if valid else math.nan
    except (OverflowError, ValueError):
        result = math.nan
    if not math.isfinite(result) or (positive and result <= 0):
        raise error(f"invalid_finite_{name}")
    return result


def _temperature(value):
    value = _number(value, "temperature")
    if not _MIN_T <= value <= _MAX_T:
        raise WaterDomainError("temperature_out_of_declared_293_500_K_domain")
    return value


@dataclass(frozen=True)
class NumericalLimits:
    """Solver acceptance limits, not experimental or material uncertainty."""

    pressure_relative: float = 2e-8
    pressure_absolute_pa: float = 0.01
    energy_identity_absolute_j_kg: float = 1e-6
    eos_caloric_absolute_j_kg: float = 0.002
    heat_capacity_absolute_j_kg_k: float = 1e-5
    gibbs_absolute_j_kg: float = 0.001
    temperature_absolute_k: float = 1e-9

    def pressure_tolerance(self, pressure_pa):
        return max(self.pressure_absolute_pa, self.pressure_relative * abs(pressure_pa))


@dataclass(frozen=True)
class WaterReference:
    molar_mass_kg_mol: float
    native_specific_gas_constant_j_kg_k: float
    native_molar_gas_constant_j_mol_k: float
    energy_offset_j_mol: float
    anchor_temperature_k: float
    ideal_gas_formation_enthalpy_j_mol: float
    source_ids: tuple[str, ...] = _SOURCE_IDS
    native_reference: str = "iapws95_triple_point_saturated_liquid_u_s_zero"
    energy_reference: str = "nist_chase_ideal_water_298.15K_common_offset_all_water_phases"
    entropy_reference: str = "native_iapws95_not_aligned_to_nist"

    def relative_gas_constant_difference(self, external_gas_constant_j_mol_k):
        external = _number(external_gas_constant_j_mol_k, "external_gas_constant", positive=True)
        return self.native_molar_gas_constant_j_mol_k / external - 1

    def require_same_gas_constant(self, external_gas_constant_j_mol_k):
        """Necessary compatibility check; equality alone does not authorize a mixture EOS."""
        external = _number(external_gas_constant_j_mol_k, "external_gas_constant", positive=True)
        if external != self.native_molar_gas_constant_j_mol_k:
            raise WaterCompatibilityError("gas_constant_mismatch_requires_explicit_model_transition")


@dataclass(frozen=True)
class WaterCaloricState:
    temperature_k: float
    native_enthalpy_j_kg: float
    native_internal_energy_j_kg: float
    cp_j_kg_k: float
    cv_j_kg_k: float
    reference: WaterReference
    method_id: str

    @property
    def enthalpy_j_kg(self):
        return self.native_enthalpy_j_kg + self.reference.energy_offset_j_mol / self.molar_mass_kg_mol

    @property
    def internal_energy_j_kg(self):
        return self.native_internal_energy_j_kg + self.reference.energy_offset_j_mol / self.molar_mass_kg_mol

    @property
    def enthalpy_j_mol(self):
        return self.native_enthalpy_j_kg * self.molar_mass_kg_mol + self.reference.energy_offset_j_mol

    @property
    def internal_energy_j_mol(self):
        return self.native_internal_energy_j_kg * self.molar_mass_kg_mol + self.reference.energy_offset_j_mol

    @property
    def molar_mass_kg_mol(self):
        return self.reference.molar_mass_kg_mol

    @property
    def source_ids(self):
        return self.reference.source_ids

    @property
    def material_qualification(self):
        return "pure_water_only"


@dataclass(frozen=True)
class WaterState(WaterCaloricState):
    pressure_pa: float
    phase: Literal["liquid", "vapor"]
    density_kg_m3: float
    native_entropy_j_kg_k: float
    pressure_eos_residual_pa: float
    energy_identity_residual_j_kg: float


@dataclass(frozen=True)
class WaterResponse:
    """Local TP derivatives, not pressure-interval error bounds or material data."""

    state: WaterState
    thermal_expansion_k_inverse: float
    isothermal_compressibility_pa_inverse: float
    molar_dv_dt_m3_mol_k: float
    molar_dv_dp_m3_mol_pa: float
    molar_du_dp_j_mol_pa: float
    cp_cv_identity_residual_j_mol_k: float
    derivative_scope: str = "local_state_sensitivity_not_interval_bound"
    method_id: str = "derived_iapws95_local_tp_response_v1"

    @property
    def source_ids(self):
        return self.state.source_ids


@dataclass(frozen=True)
class SaturationPair:
    temperature_k: float
    pressure_pa: float
    liquid: WaterState
    vapor: WaterState
    equilibrium_gibbs_difference_j_kg: float

    @property
    def latent_enthalpy_j_mol(self):
        return self.vapor.enthalpy_j_mol - self.liquid.enthalpy_j_mol


def _verify_sources(directory):
    directory = Path(directory)
    try:
        for name, expected in _ASSET_HASHES.items():
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
                raise WaterSourceError(f"source_hash_mismatch:{name}")
        backend = importlib.import_module("iapws")
        if backend.__version__ != "1.5.5" or importlib.metadata.version("iapws") != "1.5.5":
            raise WaterSourceError("iapws_runtime_version_must_be_1.5.5")
        installed = Path(backend.__file__).resolve().parent
        with zipfile.ZipFile(directory / "iapws-1.5.5-py3-none-any.whl") as wheel:
            for member in wheel.namelist():
                if member.startswith("iapws/") and (member.endswith(".py") or member.endswith("/VERSION")):
                    if (installed / member.removeprefix("iapws/")).read_bytes() != wheel.read(member):
                        raise WaterSourceError(f"runtime_source_hash_mismatch:{member}")
        if (installed / "IAPWS95_anc.json").exists():
            raise WaterSourceError("unverified_saturation_ancillary_asset")
        facts = json.loads((directory / "source_facts.json").read_text())
        return backend, facts
    except WaterSourceError:
        raise
    except (OSError, ImportError, AttributeError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise WaterSourceError("required_fixed_water_sources_unavailable") from exc


@dataclass(frozen=True, init=False)
class WaterProperties:
    """Immutable provider, limited to pure stable water at 293–500 K and <=100 MPa.

    It intentionally does not implement the project's ideal-gas caloric protocol.
    Callers must explicitly reconcile phase/EOS, molar mass, R, and energy reference.
    """

    reference: WaterReference
    source_asset_sha256: Mapping[str, str]
    numerical_limits: NumericalLimits
    _backend: object = field(repr=False)
    _model: object = field(repr=False)

    def __init__(self, source_directory):
        backend, facts = _verify_sources(source_directory)
        model = backend.IAPWS95()
        mass = float(model.M) / 1000
        r_specific = float(model.R) * 1000
        r_molar = float(model.R) * float(model.M)
        if not math.isclose(r_specific, facts["iapws_constants"]["R_specific_j_kg_k"], rel_tol=1e-12):
            raise WaterSourceError("native_iapws_fitted_constant_mismatch")
        anchor_t = float(facts["reference_temperature_k"])
        anchor_h = float(facts["gas_formation_h_j_mol"])
        phi = model._phi0(_CRITICAL_T / anchor_t, 1.0)
        anchor_native_h = r_specific * anchor_t * (1 + _CRITICAL_T / anchor_t * phi["fiot"])
        reference = WaterReference(mass, r_specific, r_molar, float(anchor_h - mass * anchor_native_h), anchor_t, anchor_h)
        object.__setattr__(self, "reference", reference)
        object.__setattr__(self, "source_asset_sha256", MappingProxyType(dict(_ASSET_HASHES)))
        object.__setattr__(self, "numerical_limits", NumericalLimits())
        object.__setattr__(self, "_backend", backend)
        object.__setattr__(self, "_model", model)

    def _solve(self, **inputs):
        try:
            with warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter("always")
                result = self._backend.IAPWS95(**inputs)
            if emitted:
                raise WaterNumericalError("iapws_solver_warning:" + str(emitted[0].message))
            if result.status != 1:
                raise WaterNumericalError("iapws_solver_status_not_success")
            if not math.isclose(_number(result.T, "backend_temperature", error=WaterNumericalError), inputs["T"],
                                rel_tol=0, abs_tol=self.numerical_limits.temperature_absolute_k):
                raise WaterNumericalError("iapws_returned_wrong_temperature")
            return result
        except WaterNumericalError:
            raise
        except (ArithmeticError, ValueError, RuntimeError, AttributeError, TypeError) as exc:
            raise WaterNumericalError("iapws_solver_failed") from exc

    def _state(self, raw, temperature, pressure, phase):
        try:
            values = {name: _number(getattr(raw, name), f"backend_{name}", error=WaterNumericalError,
                                    positive=name in ("rho", "cp", "cv")) for name in ("rho", "h", "u", "s", "cp", "cv")}
            rho = values["rho"]
            h, u, entropy = (values[name] * 1000 for name in ("h", "u", "s"))
            cp = _number(values['cp'] * 1000, 'cp_SI', error=WaterNumericalError, positive=True)
            cv = _number(values['cv'] * 1000, 'cv_SI', error=WaterNumericalError, positive=True)
            for name, value in (("h_SI", h), ("u_SI", u), ("s_SI", entropy)):
                _number(value, name, error=WaterNumericalError)
            eos = self._model._Helmholtz(rho, temperature)
            eos_h = _number(eos['h'] * 1000, 'eos_h_SI', error=WaterNumericalError)
            eos_s = _number(eos['s'] * 1000, 'eos_s_SI', error=WaterNumericalError)
            pressure_residual = _number(float(eos["P"]) * 1000 - pressure, "eos_pressure_residual", error=WaterNumericalError)
            if abs(pressure_residual) > self.numerical_limits.pressure_tolerance(pressure):
                raise WaterNumericalError("iapws_eos_pressure_residual")
            identity_residual = h - u - pressure / rho
            if abs(identity_residual) > self.numerical_limits.energy_identity_absolute_j_kg:
                raise WaterNumericalError("iapws_h_minus_u_pressure_work_residual")
            if (abs(eos_h - h) > self.numerical_limits.eos_caloric_absolute_j_kg
                    or abs(eos_s - entropy) > self.numerical_limits.eos_caloric_absolute_j_kg / temperature):
                raise WaterNumericalError("iapws_caloric_eos_residual")
            delta = rho / _CRITICAL_RHO
            residual = self._model._phir(_CRITICAL_T / temperature, delta)
            stability = _number(1 + 2 * delta * residual["fird"] + delta**2 * residual["firdd"],
                                "mechanical_stability", error=WaterNumericalError)
            if stability <= 0:
                raise WaterNumericalError("iapws_mechanically_unstable_root")
            # IAPWS-95 Table 3: independent caloric derivatives at this (T,rho),
            # including the ideal contribution; not merely Cp/Cv positivity.
            tau = _CRITICAL_T / temperature
            ideal = self._model._phi0(tau, delta)
            r_specific = self.reference.native_specific_gas_constant_j_kg_k
            expected_cv = _number(-r_specific*tau**2*(ideal['fiott']+residual['firtt']),
                                  'helmholtz_cv', error=WaterNumericalError, positive=True)
            expected_cp = _number(expected_cv+r_specific*(1+delta*residual['fird']
                                  -delta*tau*residual['firdt'])**2/stability,
                                  'helmholtz_cp', error=WaterNumericalError, positive=True)
            if (abs(cp-expected_cp) > self.numerical_limits.heat_capacity_absolute_j_kg_k
                    or abs(cv-expected_cv) > self.numerical_limits.heat_capacity_absolute_j_kg_k):
                raise WaterNumericalError('iapws_heat_capacity_derivative_residual')
            return WaterState(temperature, h, u, cp, cv,
                              self.reference, "iapws95_real_fluid_helmholtz", pressure, phase,
                              rho, entropy, pressure_residual, identity_residual)
        except WaterNumericalError:
            raise
        except (ArithmeticError, ValueError, TypeError, AttributeError, KeyError) as exc:
            raise WaterNumericalError("iapws_invalid_phase_result") from exc

    def saturation_pair(self, temperature_k) -> SaturationPair:
        temperature = _temperature(temperature_k)
        raw = self._solve(T=temperature, x=0.5)
        try:
            if raw.x != 0.5:
                raise WaterNumericalError("iapws_wrong_saturation_quality")
            pressure = _number(raw.P * 1e6, "saturation_pressure", error=WaterNumericalError, positive=True)
            liquid = self._state(raw.Liquid, temperature, pressure, "liquid")
            vapor = self._state(raw.Gas, temperature, pressure, "vapor")
        except (AttributeError, TypeError) as exc:
            raise WaterNumericalError("iapws_missing_saturation_phase") from exc
        if liquid.density_kg_m3 <= vapor.density_kg_m3:
            raise WaterNumericalError("iapws_reversed_saturation_densities")
        gibbs = (liquid.native_enthalpy_j_kg - temperature * liquid.native_entropy_j_kg_k
                 - vapor.native_enthalpy_j_kg + temperature * vapor.native_entropy_j_kg_k)
        if abs(gibbs) > self.numerical_limits.gibbs_absolute_j_kg:
            raise WaterNumericalError("iapws_saturation_chemical_equilibrium_residual")
        return SaturationPair(temperature, pressure, liquid, vapor, gibbs)

    def state_tp(self, temperature_k, pressure_pa, *, phase: Literal["liquid", "vapor"]) -> WaterState:
        temperature = _temperature(temperature_k)
        pressure = _number(pressure_pa, "pressure", positive=True)
        if pressure > _MAX_PRESSURE_PA:
            raise WaterDomainError("pressure_out_of_declared_100_MPa_domain")
        if phase not in ("liquid", "vapor"):
            raise WaterDomainError("phase_must_be_liquid_or_vapor")
        pair = self.saturation_pair(temperature)
        difference = pressure - pair.pressure_pa
        if abs(difference) <= self.numerical_limits.pressure_tolerance(pair.pressure_pa):
            raise WaterDomainError("ambiguous_TP_use_saturation_pair")
        if (phase == "liquid" and difference < 0) or (phase == "vapor" and difference > 0):
            raise WaterDomainError("unstable_requested_phase")
        pressure_mpa = _number(pressure / 1e6, "pressure_MPa_resolution", error=WaterNumericalError, positive=True)
        raw = self._solve(T=temperature, P=pressure_mpa)
        if raw.x != (0 if phase == "liquid" else 1):
            raise WaterNumericalError("iapws_returned_wrong_phase")
        state = self._state(raw, temperature, pressure, phase)
        if ((phase == "liquid" and state.density_kg_m3 < pair.liquid.density_kg_m3)
                or (phase == "vapor" and state.density_kg_m3 > pair.vapor.density_kg_m3)):
            raise WaterNumericalError("iapws_returned_wrong_density_branch")
        return state

    def state_tp_response(self, temperature_k, pressure_pa, *, phase: Literal["liquid", "vapor"]) -> WaterResponse:
        """Evaluate sourced IAPWS Table 3 derivatives at one verified TP state.

        Kappa is computed directly in 1/Pa from SI mass-based constants. No
        upstream MPa response property, ideal u0, or numerical differencing is
        used. These are local sensitivities, never a certified interval bound.
        """
        state = self.state_tp(temperature_k, pressure_pa, phase=phase)
        if (type(state) is not WaterState or state.temperature_k != temperature_k
                or state.pressure_pa != pressure_pa or state.phase != phase
                or state.reference is not self.reference
                or state.method_id != "iapws95_real_fluid_helmholtz"):
            raise WaterNumericalError("response_state_identity_mismatch")
        try:
            t = state.temperature_k
            rho = _number(state.density_kg_m3, "response_density", error=WaterNumericalError, positive=True)
            delta = rho / _CRITICAL_RHO
            tau = _CRITICAL_T / t
            residual = self._model._phir(tau, delta)
            derivatives = {key: _number(residual[key], "response_"+key, error=WaterNumericalError)
                           for key in ("fird", "firdd", "firdt")}
            d = _number(1 + 2*delta*derivatives["fird"] + delta**2*derivatives["firdd"],
                        "response_stability", error=WaterNumericalError, positive=True)
            alpha = _number((1+delta*derivatives["fird"]-delta*tau*derivatives["firdt"])/(t*d),
                            "response_expansion", error=WaterNumericalError)
            kappa = _number(1/(rho*self.reference.native_specific_gas_constant_j_kg_k*t*d),
                            "response_compressibility", error=WaterNumericalError, positive=True)
            volume = _number(state.molar_mass_kg_mol/rho, "response_molar_volume", error=WaterNumericalError, positive=True)
            dv_dt = _number(volume*alpha, "response_dv_dt", error=WaterNumericalError)
            dv_dp = -_number(volume*kappa, "response_negative_dv_dp", error=WaterNumericalError, positive=True)
            du_dp = _number(math.fsum((-t*dv_dt, -state.pressure_pa*dv_dp)),
                            "response_du_dp", error=WaterNumericalError)
            cp_cv = _number((state.cp_j_kg_k-state.cv_j_kg_k)*state.molar_mass_kg_mol,
                            "response_cp_minus_cv", error=WaterNumericalError)
            expected = _number(t*volume*alpha**2/kappa, "response_cp_cv_identity", error=WaterNumericalError)
            identity = _number(cp_cv-expected, "response_cp_cv_residual", error=WaterNumericalError)
            if abs(identity) > 1e-7:
                raise WaterNumericalError("response_cp_cv_identity_residual")
            return WaterResponse(state, alpha, kappa, dv_dt, dv_dp, du_dp, identity)
        except WaterNumericalError:
            raise
        except (ArithmeticError, ValueError, TypeError, AttributeError, KeyError) as exc:
            raise WaterNumericalError("iapws_invalid_response_result") from exc

    def ideal_vapor(self, temperature_k) -> WaterCaloricState:
        """Independent ideal-Helmholtz caloric limit; no pure-fluid TP or mud claim."""
        temperature = _temperature(temperature_k)
        tau = _CRITICAL_T / temperature
        phi = self._model._phi0(tau, 1.0)
        r_specific = self.reference.native_specific_gas_constant_j_kg_k
        u = r_specific * temperature * tau * phi["fiot"]
        h = u + r_specific * temperature
        cv = -r_specific * tau**2 * phi["fiott"]
        cp = cv + r_specific
        values = [_number(value, name, error=WaterNumericalError, positive=name in ("cp", "cv"))
                  for name, value in (("h", h), ("u", u), ("cp", cp), ("cv", cv))]
        return WaterCaloricState(temperature, *values, self.reference, "derived_iapws95_ideal_helmholtz")


def load_water_properties(source_directory) -> WaterProperties:
    """Verify archived original sources and the exact runtime before creating a provider."""
    return WaterProperties(source_directory)
