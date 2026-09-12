"""Explicit real-pure-liquid / ideal-water-vapor chemical potential approximation.

Both phases use native IAPWS entropy and the already shared NIST energy offset.
The vapor pressure entropy term uses the registered mixture R at fixed 1 bar.
No sludge activity, arbitrary reference-pressure change or exact native psat is
implied. The ideal standard state need not be stable pure vapor at 1 bar.
"""
from sludge_sandbox.water_properties import is_water_provider
from dataclasses import dataclass, field
import math
from numbers import Real
from typing import ClassVar

from .ideal_water_vapor import IdealWaterVapor
from .water_properties import WaterProperties, WaterState, load_water_properties


class WaterChemicalError(ValueError):
    """Invalid chemical-model input, identity or unrepresentable derived result."""


_ENTROPY_REFERENCE = 'native_iapws95_not_aligned_to_nist'
_QUALIFICATION = 'ideal_water_vapor_real_pure_liquid_not_sludge_activity'
_METHOD_ID = 'derived_native_entropy_fixed_pressure_water_equilibrium_v1'


def _finite(value,name,*,positive=False):
    try:v=float(value) if isinstance(value,Real) and not isinstance(value,bool) else math.nan
    except (ValueError,OverflowError):v=math.nan
    if not math.isfinite(v) or (positive and v<=0):raise WaterChemicalError('invalid_'+name)
    return v


def _sum(values):
    try:return _finite(math.fsum(values),'chemical_sum')
    except OverflowError as exc:raise WaterChemicalError('chemical_sum_overflow') from exc


@dataclass(frozen=True)
class WaterVaporChemicalState:
    temperature_k: float
    partial_pressure_pa: float
    enthalpy_j_mol: float
    entropy_j_mol_k: float
    chemical_potential_j_mol: float
    source_ids: tuple[str,...]
    method_id: str = _METHOD_ID
    classification: str = 'derived_from_evidence'
    reference_pressure_pa: float = 1e5
    entropy_reference: str = _ENTROPY_REFERENCE
    qualification: str = _QUALIFICATION


@dataclass(frozen=True)
class WaterLiquidChemicalState:
    state: WaterState
    enthalpy_j_mol: float
    entropy_j_mol_k: float
    chemical_potential_j_mol: float
    source_ids: tuple[str,...]
    method_id: str = _METHOD_ID
    classification: str = 'derived_from_evidence'
    entropy_reference: str = _ENTROPY_REFERENCE


@dataclass(frozen=True)
class WaterPhaseEquilibrium:
    equilibrium_partial_pressure_pa: float
    phase_enthalpy_difference_j_mol: float
    chemical_potential_residual_j_mol: float
    liquid: WaterLiquidChemicalState
    vapor: WaterVaporChemicalState
    source_ids: tuple[str,...]
    method_id: str = _METHOD_ID
    classification: str = 'derived_from_evidence'
    qualification: str = _QUALIFICATION


@dataclass(frozen=True,init=False)
class WaterChemicalPotential:
    """Source-gated model with fixed standard pressure; no configurable entropy shift."""
    water: WaterProperties = field(repr=False)
    vapor: IdealWaterVapor = field(repr=False)
    reference_pressure_pa: ClassVar[float] = 1e5
    method_id: ClassVar[str] = _METHOD_ID
    classification: ClassVar[str] = 'derived_from_evidence'
    temperature_range_k: ClassVar[tuple[float,float]] = (293.,500.)
    qualification: ClassVar[str] = _QUALIFICATION

    def __init__(self,source_directory,*,backend="python",backend_manifest=None):
        object.__setattr__(self,'water',load_water_properties(source_directory,backend=backend,backend_manifest=backend_manifest))
        object.__setattr__(self,'vapor',IdealWaterVapor(source_directory,backend=backend,backend_manifest=backend_manifest))
        self._check_identity()

    @property
    def reference(self):return self.water.reference

    @property
    def source_asset_sha256(self):return self.water.source_asset_sha256

    @property
    def source_ids(self):return self.vapor.source_ids

    @property
    def gas_constant_j_mol_k(self):return self.vapor.gas_constant_j_mol_k

    @property
    def caloric_method_id(self):return self.vapor.method_id

    def _check_identity(self):
        if (not is_water_provider(self.water) or type(self.vapor) is not IdealWaterVapor
                or self.water.reference!=self.vapor.reference
                or self.water.source_asset_sha256!=self.vapor.source_asset_sha256
                or self.vapor.gas_constant_j_mol_k!=8.31446261815324
                or self.vapor.method_id!='derived_iapws95_ideal_water_fixed_r_bridge_v1'):
            raise WaterChemicalError('incompatible_water_caloric_reference')

    def _standard_entropy(self,t):
        try:
            r=self.reference.native_specific_gas_constant_j_kg_k
            mass=self.reference.molar_mass_kg_mol
            delta=self.reference_pressure_pa/(r*t*322.)
            tau=647.096/t
            phi=self.water._model._phi0(tau,delta)
            fio=_finite(phi['fio'],'ideal_helmholtz')
            fiot=_finite(phi['fiot'],'ideal_helmholtz_tau')
            return _finite(r*mass*_sum((tau*fiot,-fio)),'standard_entropy')
        except WaterChemicalError:raise
        except (ArithmeticError,ValueError,TypeError,KeyError,AttributeError) as exc:
            raise WaterChemicalError('ideal_entropy_evaluation_failed') from exc

    def ideal_vapor(self,temperature_k,partial_pressure_pa):
        self._check_identity()
        p=_finite(partial_pressure_pa,'positive_partial_pressure_zero_mu_is_not_finite',positive=True)
        h=self.vapor.enthalpy_j_mol(temperature_k)  # validates T; already contains common C_E
        t=float(temperature_k)
        s0=self._standard_entropy(t)
        # Avoid ratio underflow for positive representable p. Near pref use
        # log1p to retain the small pressure perturbation accurately.
        difference=p-self.reference_pressure_pa
        logarithm=(math.log1p(difference/self.reference_pressure_pa)
                   if abs(difference)<.5*self.reference_pressure_pa
                   else math.log(p)-math.log(self.reference_pressure_pa))
        entropy=_sum((s0,-self.gas_constant_j_mol_k*logarithm))
        mu=_sum((h,-t*entropy))
        return WaterVaporChemicalState(t,p,h,entropy,mu,self.source_ids)

    def _liquid(self,state):
        self._check_identity()
        if (type(state) is not WaterState or state.reference is not self.reference
                or state.implementation != self.water.implementation
                or state.phase!='liquid' or state.method_id!='iapws95_real_fluid_helmholtz'):
            raise WaterChemicalError('incompatible_liquid_state')
        h=_finite(state.enthalpy_j_mol,'liquid_enthalpy')
        entropy=_finite(state.native_entropy_j_kg_k*state.molar_mass_kg_mol,'liquid_entropy')
        mu=_sum((h,-state.temperature_k*entropy))
        return WaterLiquidChemicalState(state,h,entropy,mu,state.source_ids)

    def liquid_tp(self,temperature_k,liquid_pressure_pa):
        return self._liquid(self.water.state_tp(temperature_k,liquid_pressure_pa,phase='liquid'))

    def saturated_liquid(self,temperature_k):
        return self._liquid(self.water.saturation_pair(temperature_k).liquid)

    def _equilibrium(self,liquid):
        t=liquid.state.temperature_k
        standard=self.ideal_vapor(t,self.reference_pressure_pa)
        exponent=_sum((liquid.chemical_potential_j_mol,-standard.chemical_potential_j_mol))/(self.gas_constant_j_mol_k*t)
        try:
            pressure=_finite(math.exp(exponent)*self.reference_pressure_pa,'equilibrium_pressure',positive=True)
        except OverflowError as exc:raise WaterChemicalError('equilibrium_pressure_overflow') from exc
        vapor=self.ideal_vapor(t,pressure)
        residual=_sum((liquid.chemical_potential_j_mol,-vapor.chemical_potential_j_mol))
        if abs(residual)>1e-7:raise WaterChemicalError('equilibrium_mu_residual')
        latent=_sum((vapor.enthalpy_j_mol,-liquid.enthalpy_j_mol))
        return WaterPhaseEquilibrium(pressure,latent,residual,liquid,vapor,self.source_ids)

    def equilibrium_at_liquid_tp(self,temperature_k,liquid_pressure_pa):
        return self._equilibrium(self.liquid_tp(temperature_k,liquid_pressure_pa))

    def equilibrium_at_saturation(self,temperature_k):
        return self._equilibrium(self.saturated_liquid(temperature_k))
