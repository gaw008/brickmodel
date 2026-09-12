"""Fixed-inventory dry reference plate using the native extensive-energy state.

The explicit molar array is locked bookkeeping and is absent from the constant
volumetric caloric law. This host does not infer composition, molar mass, pore
volume, density, a chemical reaction, or a three-dimensional deformation.
"""
from dataclasses import dataclass, field
import hashlib
import math

import numpy as np

from sludge_sandbox.integration import ConservedState, DomainExit, IntegrationError, Rates
from .thermoelastic_energy_storage import (
    EnergyDomainError,
    EnergyInverse,
    EnergyInversePolicy,
    EnergyStorageError,
    EnergyTarget,
    ThermoelasticEnergyStorage,
)


class ThermoelasticEnergyHostError(IntegrationError):
    """An incompatible native state or an unresolved numerical energy decode."""


@dataclass(frozen=True, slots=True)
class ThermoelasticEnergyEvaluation:
    rates: Rates
    inverse: EnergyInverse
    material_qualified: bool = field(default=False, init=False)
    full_cycle_qualified: bool = field(default=False, init=False)
    chemical_mass_qualified: bool = field(default=False, init=False)
    inventory_role: str = field(default='explicit_fixed_bookkeeping_outside_caloric_law', init=False)
    ledger_scope: str = field(default='reference_half_slab', init=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class ThermoelasticEnergyHost:
    storage: ThermoelasticEnergyStorage
    fixed_amounts_mol: np.ndarray
    inverse_policy: EnergyInversePolicy
    energy_model_identity: tuple = field(init=False)

    def __post_init__(self):
        if type(self.storage) is not ThermoelasticEnergyStorage:
            raise ThermoelasticEnergyHostError('validated_thermoelastic_storage_required')
        if type(self.inverse_policy) is not EnergyInversePolicy:
            raise ThermoelasticEnergyHostError('explicit_energy_inverse_policy_required')
        plate = self.storage.plate
        n = plate.reference.cells
        # Reuse native immutable, nonempty, numeric inventory validation.
        inventory = ConservedState(self.fixed_amounts_mol, np.zeros(n)).amounts_mol
        if np.any((inventory == 0.) & np.signbit(inventory)):
            raise ThermoelasticEnergyHostError('native_zero_updates_do_not_preserve_negative_zero_inventory')
        object.__setattr__(self, 'fixed_amounts_mol', inventory)
        fields = ('biaxial_modulus_pa', 'linear_expansion_per_k',
                  'stress_free_heat_capacity_j_m3_k', 'reference_temperature_k')
        law = tuple((name, float(getattr(plate, name)).hex()) for name in fields)
        geometry = ('reference_half_slab', float(plate.reference.half_thickness_m).hex(),
                    float(plate.reference.reference_area_m2).hex(), str(n))
        bounds = (tuple(float(t).hex() for t in plate.temperature_bounds_k),
                  tuple(float(e).hex() for e in plate.strain_bounds))
        inventory_key = ('fixed_inventory', str(inventory.shape[1]),
                         hashlib.sha256(inventory.tobytes()).hexdigest())
        # Heat boundary/conductivity and numerical tolerances do not define U.
        identity = ('thermoelastic_reference_internal_energy_v1', law, geometry, bounds,
                    plate.mechanical_regime, plate.coefficient_classification, inventory_key)
        object.__setattr__(self, 'energy_model_identity', identity)

    def _check_state(self, state):
        if type(state) is not ConservedState:
            raise ThermoelasticEnergyHostError('native_conserved_state_required')
        if state.energy_model_identity != self.energy_model_identity:
            raise ThermoelasticEnergyHostError('thermoelastic_energy_identity_mismatch')
        if state.mechanical_stretches is not None:
            raise ThermoelasticEnergyHostError('algebraic_strain_is_not_integrated_stretch')
        if (state.amounts_mol.shape != self.fixed_amounts_mol.shape
                or state.amounts_mol.tobytes() != self.fixed_amounts_mol.tobytes()):
            raise ThermoelasticEnergyHostError('fixed_inventory_changed')

    def state_from_temperatures(self, temperatures_k):
        """Store represented total U; retain the forward certificate separately.

        The returned pair makes initialization rounding visible to callers.
        No initialization correction is applied to U or temperature.
        """
        try:
            forward = self.storage.forward(temperatures_k)
        except EnergyDomainError as exc:
            raise DomainExit(str(exc)) from exc
        except EnergyStorageError as exc:
            raise ThermoelasticEnergyHostError(str(exc)) from exc
        state = ConservedState(self.fixed_amounts_mol, forward.cell_energy_j,
                               energy_model_identity=self.energy_model_identity)
        return state, forward

    def evaluate(self, state, time_s):
        try:
            valid_time = type(time_s) in (int, float) and math.isfinite(time_s)
        except OverflowError:
            valid_time = False
        if not valid_time:
            raise ThermoelasticEnergyHostError('finite_time_required')
        self._check_state(state)
        n, species = state.amounts_mol.shape
        # Zero uncertainty means the represented state is the decoding target.
        # It makes no assertion about integration error or material uncertainty.
        target = EnergyTarget(cell_energy_j=tuple(float(e) for e in state.internal_energy_j),
                              absolute_error_j=(0.,)*n)
        try:
            inverse = self.storage.inverse(target, self.inverse_policy)
        except EnergyDomainError as exc:
            raise DomainExit(str(exc)) from exc
        except EnergyStorageError as exc:
            raise ThermoelasticEnergyHostError(str(exc)) from exc
        evaluated = inverse.state.plate_evaluation
        power = np.asarray(evaluated.cell_mechanical_power_w)
        rates = Rates(face_species_mol_s=np.zeros((n+1, species)),
                      face_energy_w=np.asarray(evaluated.face_heat_outward_w),
                      reaction_species_mol_s=np.zeros((n, species)),
                      cell_power_w=power,
                      cell_power_components_w={'mechanical_constraint': power},
                      mechanical_rates_per_s=None)
        return ThermoelasticEnergyEvaluation(rates=rates, inverse=inverse)

    def __call__(self, state, time_s):
        return self.evaluate(state, time_s).rates
