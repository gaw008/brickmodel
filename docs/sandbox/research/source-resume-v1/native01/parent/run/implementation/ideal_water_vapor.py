"""Explicit ideal-water caloric bridge to the registered mixture gas constant.

This derived model preserves source-gated IAPWS ideal enthalpy (already aligned
with NIST formation enthalpy), but defines u=h-R_mix*T. It is not the native
IAPWS real-fluid EOS, a phase-equilibrium model, or a qualified sludge material.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from numbers import Real
from os import PathLike
from typing import ClassVar

from .water_properties import WaterCaloricState, WaterProperties, WaterReference, load_water_properties


class IdealWaterVaporError(ValueError):
    """Invalid bridge construction, identity, or caloric output."""


_REGISTERED_R = 8.31446261815324


def _finite(value, name, *, positive=False):
    try:
        result = float(value) if isinstance(value, Real) and not isinstance(value, bool) else math.nan
    except (OverflowError, ValueError):
        result = math.nan
    if not math.isfinite(result) or (positive and result <= 0):
        raise IdealWaterVaporError(f'invalid_{name}')
    return result


@dataclass(frozen=True, init=False)
class IdealWaterVapor:
    """Fixed-R, 293–500 K caloric species loaded only from verified water sources.

    R is deliberately not configurable. Source and numerical errors from the
    underlying loader/provider retain their distinct error categories.
    """
    species_id: ClassVar[str] = 'H2O'
    temperature_range_k: ClassVar[tuple[float, float]] = (293., 500.)
    method_id: ClassVar[str] = 'derived_iapws95_ideal_water_fixed_r_bridge_v1'
    mixture_qualification: ClassVar[str] = 'not_established'
    classification: ClassVar[str] = 'derived_from_evidence'
    constant_source_ids: ClassVar[tuple[str, ...]] = ('nist-codata-2022',)
    constant_derivation: ClassVar[str] = 'R = exact Avogadro constant * exact Boltzmann constant'
    gas_constant_j_mol_k: float
    reference: WaterReference
    source_asset_sha256: Mapping[str, str]
    _water: WaterProperties = field(repr=False)

    def __init__(self, source_directory, *, backend="python", backend_manifest=None):
        if not isinstance(source_directory, (str, PathLike)):
            raise IdealWaterVaporError('explicit_source_directory_required')
        water = load_water_properties(source_directory,backend=backend,backend_manifest=backend_manifest)
        object.__setattr__(self, '_water', water)
        object.__setattr__(self, 'reference', water.reference)
        object.__setattr__(self, 'source_asset_sha256', water.source_asset_sha256)
        object.__setattr__(self, 'gas_constant_j_mol_k', _REGISTERED_R)
        # Fail construction if the source-derived identity cannot be used at its
        # reference anchor. The authoritative loader has verified source bytes.
        self._caloric(water.reference.anchor_temperature_k)

    @property
    def source_ids(self):
        return self._water.source_ids + self.constant_source_ids

    @property
    def molar_mass_kg_mol(self):
        return self.reference.molar_mass_kg_mol

    @property
    def cv_difference_j_mol_k(self):
        """Cv_bridge minus native ideal Cv, from the explicit R convention change."""
        return self.reference.native_molar_gas_constant_j_mol_k - self.gas_constant_j_mol_k

    def _caloric(self, temperature):
        if self._water.reference is not self.reference or self.gas_constant_j_mol_k != _REGISTERED_R:
            raise IdealWaterVaporError('bridge_reference_changed')
        state = self._water.ideal_vapor(temperature)
        if (type(state) is not WaterCaloricState or state.reference is not self.reference
                or state.implementation != self._water.implementation
                or state.method_id != 'derived_iapws95_ideal_helmholtz'):
            raise IdealWaterVaporError('unexpected_water_reference_or_method')
        t = _finite(state.temperature_k, 'temperature', positive=True)
        if t != temperature:
            raise IdealWaterVaporError('returned_temperature_mismatch')
        mass = self.reference.molar_mass_kg_mol
        h = _finite(state.enthalpy_j_mol, 'enthalpy')
        native_u = _finite(state.internal_energy_j_mol, 'native_internal_energy')
        cp = _finite(state.cp_j_kg_k * mass, 'cp', positive=True)
        native_cv = _finite(state.cv_j_kg_k * mass, 'native_cv', positive=True)
        native_r = self.reference.native_molar_gas_constant_j_mol_k
        # These are roundoff checks of native caloric identities, not material
        # uncertainty allowances. SI-to-molar conversion has already occurred.
        if abs(h-native_u-native_r*t) > 1e-9 or abs(cp-native_cv-native_r) > 1e-10:
            raise IdealWaterVaporError('native_caloric_identity_residual')
        u = _finite(h-self.gas_constant_j_mol_k*t, 'internal_energy')
        cv = _finite(cp-self.gas_constant_j_mol_k, 'cv', positive=True)
        return h, u, cp, cv, t

    def enthalpy_j_mol(self, temperature_k):
        return self._caloric(temperature_k)[0]

    def internal_energy_j_mol(self, temperature_k):
        return self._caloric(temperature_k)[1]

    def cp_j_mol_k(self, temperature_k):
        return self._caloric(temperature_k)[2]

    def cv_j_mol_k(self, temperature_k):
        return self._caloric(temperature_k)[3]

    def internal_energy_difference_j_mol(self, temperature_k):
        """U_bridge minus native aligned ideal U per mol; not an extra heat source."""
        temperature = self._caloric(temperature_k)[4]
        return self.cv_difference_j_mol_k * temperature
