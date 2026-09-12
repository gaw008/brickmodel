"""Rigid gas-only multi-cell coupling for operator integration validation.

Every trial state is decoded through thermochemistry and pore-volume EOS.
Each face's species and enthalpy exchange is evaluated once and shared by both
neighbors. This module supplies no solid/liquid caloric storage or brick model.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import math
from numbers import Real
from types import MappingProxyType
from typing import NoReturn

import numpy as np
from numpy.typing import ArrayLike

from .exchanges import ExchangeError, conduction_rate_w, gas_enthalpy_exchange
from .gas_transport import GasState, GasTransportError, face_exchange, ideal_gas_state
from .integration import ConservedState, DomainExit, IntegrationError, Rates
from .reactions import ReactionError, ReactionNetwork
from .thermochemistry import Thermochemistry, ThermochemistryError


class GasHeatModelError(IntegrationError):
    """Invalid coupling configuration or a state incompatible with the model."""


def _raise_operator_failure(exc: Exception) -> NoReturn:
    """Translate only explicitly named property-domain failures as DomainExit.

    The existing modules also use their own exception classes for programming
    contracts and floating-point failures; the class alone is not a domain tag.
    """
    reason = str(exc)
    thermo_domains = {
        'temperature_out_of_domain', 'empty_thermal_inventory',
        'no_common_temperature_domain', 'energy_out_of_temperature_domain',
        'energy_in_property_gap', 'ambiguous_temperature',
    }
    if ((isinstance(exc, ThermochemistryError) and reason in thermo_domains)
            or (isinstance(exc, ReactionError) and reason.startswith('temperature_out_of_kinetic_domain:'))):
        raise DomainExit(reason) from exc
    raise GasHeatModelError(reason) from exc


def _number(value, name, *, positive=False, nonnegative=False):
    try:
        valid = isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
        result = float(value) if valid else math.nan
    except (OverflowError, ValueError):
        result = math.nan
    if not math.isfinite(result) or (positive and result <= 0) or (nonnegative and result < 0):
        raise GasHeatModelError(f'invalid_{name}')
    return result


def _values(values, size, name, *, positive=False):
    if isinstance(values, (str, bytes, Mapping)):
        raise GasHeatModelError(f'invalid_{name}')
    try:
        result = tuple(_number(value, name, positive=positive, nonnegative=True) for value in values)
    except TypeError as exc:
        raise GasHeatModelError(f'invalid_{name}') from exc
    if len(result) != size:
        raise GasHeatModelError(f'invalid_{name}_length')
    return result


def _sources(values):
    if not isinstance(values, (list, tuple)) or not values:
        raise GasHeatModelError('source_ids_required')
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise GasHeatModelError('invalid_source_id')
    if len(set(values)) != len(values):
        raise GasHeatModelError('duplicate_source_id')
    return tuple(values)


def _sum(values):
    try:
        return _number(math.fsum(values), 'assembled_face_energy')
    except OverflowError as exc:
        raise GasHeatModelError('nonfinite_assembled_face_energy') from exc


def _serial_coefficient(left, right, dl, dr):
    if left == 0 or right == 0:
        return 0.
    resistance = dl/left+dr/right
    if not math.isfinite(resistance) or resistance <= 0:
        raise GasHeatModelError('transport_resistance_outside_float_range')
    result = (dl+dr)/resistance
    if not math.isfinite(result) or result <= 0:
        raise GasHeatModelError('transport_resistance_outside_float_range')
    return result


def _mobility(permeability, relative, viscosity):
    if permeability == 0 or relative == 0:
        return 0.
    try:
        value = math.exp(math.log(permeability)+math.log(relative)-math.log(viscosity))
    except OverflowError as exc:
        raise GasHeatModelError('darcy_mobility_outside_float_range') from exc
    if not math.isfinite(value) or value <= 0:
        raise GasHeatModelError('darcy_mobility_outside_float_range')
    return value


def _thermo_signature(thermo):
    return (thermo.pack_id, thermo.gas_constant_j_mol_k, thermo.constant_source_ids,
            tuple(thermo.gases.items()), thermo.contains_manufactured_models, thermo.provenance_status)


@dataclass(frozen=True, kw_only=True)
class GasHeatEvaluation:
    """Single-decode diagnostics from the state used for shared exchanges."""

    rates: Rates
    temperatures_k: tuple[float, ...]
    gas_states: tuple[GasState, ...]
    source_ids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class GasHeatModel:
    thermochemistry: Thermochemistry
    species_order: tuple[str, ...]
    molar_masses_kg_mol: Mapping[str, float]
    face_area_m2: float
    cell_widths_m: tuple[float, ...]
    gas_volumes_m3: tuple[float, ...]
    conductivities_w_m_k: tuple[float, ...]
    effective_diffusivities_m2_s: Mapping[str, tuple[float, ...]]
    permeability_m2: tuple[float, ...]
    relative_permeability: tuple[float, ...]
    viscosity_pa_s: tuple[float, ...]
    coefficient_source_ids: tuple[str, ...]
    coefficient_set_id: str
    coefficient_version: str
    coefficient_classification: str
    allow_manufactured: bool = False
    reaction_network: ReactionNetwork | None = None
    outer_reservoir: GasState | None = None
    outer_reservoir_source_ids: tuple[str, ...] = ()
    outer_surface_temperature_k: float | Callable[[float], float] | None = None
    outer_heat_source_ids: tuple[str, ...] = ()
    _caloric_signature: tuple = field(init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.thermochemistry, Thermochemistry):
            raise GasHeatModelError('explicit_thermochemistry_required')
        if type(self.allow_manufactured) is not bool:
            raise GasHeatModelError('invalid_test_mode')
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.coefficient_set_id, self.coefficient_version)):
            raise GasHeatModelError('coefficient_identity_required')
        if self.coefficient_classification not in ('manufactured', 'literature_candidate'):
            raise GasHeatModelError('invalid_coefficient_classification')
        if self.coefficient_classification == 'manufactured' and not self.allow_manufactured:
            raise GasHeatModelError('manufactured_requires_test_mode')
        if not isinstance(self.species_order, (list, tuple)) or not self.species_order:
            raise GasHeatModelError('explicit_species_order_required')
        names = tuple(self.species_order)
        if any(not isinstance(name, str) or not name.strip() or name != name.strip() for name in names):
            raise GasHeatModelError('invalid_species_id')
        if len(set(names)) != len(names) or set(names)-self.thermochemistry.gases.keys():
            raise GasHeatModelError('duplicate_or_unknown_gas_species')
        object.__setattr__(self, 'species_order', names)
        if not isinstance(self.molar_masses_kg_mol, Mapping) or set(self.molar_masses_kg_mol) != set(names):
            raise GasHeatModelError('explicit_full_molar_mass_set_required')
        masses = {name: _number(self.molar_masses_kg_mol[name], 'molar_mass', positive=True) for name in names}
        object.__setattr__(self, 'molar_masses_kg_mol', MappingProxyType(masses))
        area = _number(self.face_area_m2, 'face_area', positive=True)
        object.__setattr__(self, 'face_area_m2', area)
        try:
            count = len(self.cell_widths_m)
        except TypeError as exc:
            raise GasHeatModelError('explicit_cell_widths_required') from exc
        if count == 0:
            raise GasHeatModelError('explicit_cells_required')
        for name in ('cell_widths_m', 'gas_volumes_m3', 'conductivities_w_m_k',
                     'permeability_m2', 'relative_permeability', 'viscosity_pa_s'):
            object.__setattr__(self, name, _values(getattr(self, name), count, name,
                                positive=name in ('cell_widths_m', 'gas_volumes_m3', 'viscosity_pa_s')))
        if any(value > 1 for value in self.relative_permeability):
            raise GasHeatModelError('relative_permeability_exceeds_one')
        for width, gas_volume in zip(self.cell_widths_m, self.gas_volumes_m3):
            if width/4 == 0:
                raise GasHeatModelError('cell_width_outside_float_range')
            bulk = _number(area*width, 'cell_bulk_volume', positive=True)
            if gas_volume > bulk:
                raise GasHeatModelError('gas_volume_exceeds_cell_bulk_volume')
        if not isinstance(self.effective_diffusivities_m2_s, Mapping) or set(self.effective_diffusivities_m2_s) != set(names):
            raise GasHeatModelError('explicit_full_diffusivity_set_required')
        diffusion = {name: _values(self.effective_diffusivities_m2_s[name], count, 'diffusivity') for name in names}
        object.__setattr__(self, 'effective_diffusivities_m2_s', MappingProxyType(diffusion))
        object.__setattr__(self, 'coefficient_source_ids', _sources(self.coefficient_source_ids))
        thermo = self.thermochemistry
        if thermo.contains_manufactured_models and not self.allow_manufactured:
            raise GasHeatModelError('manufactured_requires_test_mode')
        # Own the mutable Thermochemistry wrapper; its constituent gases are
        # frozen. Detect later edits to this wrapper's caloric/source settings.
        thermo = Thermochemistry(thermo.pack_id, thermo.gases, thermo.gas_constant_j_mol_k,
                                 thermo.constant_source_ids, allow_manufactured=self.allow_manufactured)
        object.__setattr__(self, 'thermochemistry', thermo)
        object.__setattr__(self, '_caloric_signature', _thermo_signature(thermo))
        network = self.reaction_network
        if network is not None:
            if not isinstance(network, ReactionNetwork) or network.species_order != names:
                raise GasHeatModelError('reaction_species_order_mismatch')
            if any(item.phase != 'gas' or item.molar_mass_kg_mol != masses[item.species_id] for item in network.species):
                raise GasHeatModelError('reaction_requires_matching_gas_species_and_masses')
            if any(reaction.kinetics.gas_constant_j_mol_k != thermo.gas_constant_j_mol_k for reaction in network.reactions):
                raise GasHeatModelError('reaction_thermochemistry_gas_constant_mismatch')
            if network.contains_manufactured and not self.allow_manufactured:
                raise GasHeatModelError('manufactured_requires_test_mode')
        if self.outer_reservoir is not None:
            reservoir = self.outer_reservoir
            if (not isinstance(reservoir, GasState) or reservoir.molar_masses_kg_mol != masses
                    or reservoir.gas_constant_j_mol_k != thermo.gas_constant_j_mol_k):
                raise GasHeatModelError('incompatible_outer_gas_reservoir')
            object.__setattr__(self, 'outer_reservoir_source_ids', _sources(self.outer_reservoir_source_ids))
        elif self.outer_reservoir_source_ids:
            raise GasHeatModelError('orphan_reservoir_sources')
        if self.outer_surface_temperature_k is not None:
            if not callable(self.outer_surface_temperature_k):
                object.__setattr__(self, 'outer_surface_temperature_k',
                                   _number(self.outer_surface_temperature_k, 'surface_temperature', positive=True))
            object.__setattr__(self, 'outer_heat_source_ids', _sources(self.outer_heat_source_ids))
        elif self.outer_heat_source_ids:
            raise GasHeatModelError('orphan_heat_boundary_sources')

    @property
    def scientific_status(self) -> str:
        return 'operator_integration_validation_not_material_qualified'

    @property
    def material_qualified(self) -> bool:
        return False

    @property
    def source_ids(self) -> tuple[str, ...]:
        sources = set(self.coefficient_source_ids)
        sources.update(self.thermochemistry.source_ids_for({name: 1 for name in self.species_order}))
        sources.update(self.outer_reservoir_source_ids)
        sources.update(self.outer_heat_source_ids)
        if self.reaction_network is not None:
            sources.update(self.reaction_network.source_ids)
        return tuple(sorted(sources))

    def _check_state(self, state):
        if not isinstance(state, ConservedState) or state.amounts_mol.shape != (len(self.cell_widths_m), len(self.species_order)):
            raise GasHeatModelError('model_state_shape_mismatch')
        if state.mechanical_stretches is not None:
            raise GasHeatModelError('unsupported_mechanical_state')
        if state.energy_model_identity is not None:
            raise GasHeatModelError('unsupported_energy_model_identity')
        if _thermo_signature(self.thermochemistry) != self._caloric_signature:
            raise GasHeatModelError('thermochemistry_changed_after_construction')

    def _inventory(self, row):
        return {name: float(amount) for name, amount in zip(self.species_order, row)}

    def state_from_temperatures(self, amount_mol: ArrayLike, temperatures_k: ArrayLike) -> ConservedState:
        state = ConservedState(amount_mol, np.zeros(len(self.cell_widths_m)))
        self._check_state(state)
        temperatures = _values(temperatures_k, len(self.cell_widths_m), 'temperature', positive=True)
        try:
            energies = [self.thermochemistry.mixture_internal_energy_j(self._inventory(row), temperature)
                        for row, temperature in zip(state.amounts_mol, temperatures)]
        except ThermochemistryError as exc:
            _raise_operator_failure(exc)
        return ConservedState(state.amounts_mol, energies)

    def temperatures_k(self, state: ConservedState) -> tuple[float, ...]:
        self._check_state(state)
        try:
            return tuple(self.thermochemistry.temperature_from_internal_energy_j(
                float(energy), self._inventory(row))
                for row, energy in zip(state.amounts_mol, state.internal_energy_j))
        except ThermochemistryError as exc:
            _raise_operator_failure(exc)

    def _face(self, left, right, left_index, right_index):
        dl = self.cell_widths_m[left_index]/2
        dr = self.cell_widths_m[right_index]/2 if right_index is not None else 0.
        left_mobility = _mobility(self.permeability_m2[left_index], self.relative_permeability[left_index],
                                  self.viscosity_pa_s[left_index])
        if right_index is None:
            diffusion = {name: values[left_index] for name, values in self.effective_diffusivities_m2_s.items()}
            mobility = left_mobility
            viscosity = self.viscosity_pa_s[left_index]
        else:
            diffusion = {name: _serial_coefficient(values[left_index], values[right_index], dl, dr)
                         for name, values in self.effective_diffusivities_m2_s.items()}
            right_mobility = _mobility(self.permeability_m2[right_index], self.relative_permeability[right_index],
                                       self.viscosity_pa_s[right_index])
            mobility = _serial_coefficient(left_mobility, right_mobility, dl, dr)
            weight = dr/(dl+dr)
            viscosity = weight*self.viscosity_pa_s[left_index]+(1-weight)*self.viscosity_pa_s[right_index]
        # Algebraic factorization: kr=1 here, because the ORIGINAL cell kr values
        # are already included in the series mobility, not reset physically.
        permeability = _number(mobility*viscosity, 'assembled_permeability', nonnegative=True)
        if mobility > 0 and permeability == 0:
            raise GasHeatModelError('mobility_factorization_outside_float_range')
        return face_exchange(left, right, area_m2=self.face_area_m2, distance_m=dl+dr,
                             face_left_weight=dr/(dl+dr), effective_diffusivities_m2_s=diffusion,
                             permeability_m2=permeability, relative_permeability=1., viscosity_pa_s=viscosity)

    def __call__(self, state: ConservedState, time_s: float) -> Rates:
        return self.evaluate(state, time_s).rates

    def evaluate(self, state: ConservedState, time_s: float) -> GasHeatEvaluation:
        self._check_state(state)
        at = _number(time_s, 'time')
        temperatures = self.temperatures_k(state)
        count, species_count = state.amounts_mol.shape
        faces_n, faces_u = np.zeros((count+1, species_count)), np.zeros(count+1)
        reactions, powers = np.zeros_like(state.amounts_mol), np.zeros(count)
        try:
            gases = [ideal_gas_state(self._inventory(row), temperature_k=temperature,
                                    gas_volume_m3=volume, molar_masses_kg_mol=self.molar_masses_kg_mol,
                                    gas_constant_j_mol_k=self.thermochemistry.gas_constant_j_mol_k)
                     for row, temperature, volume in zip(state.amounts_mol, temperatures, self.gas_volumes_m3)]
            for face in range(1, count):
                left, right = face-1, face
                exchange = self._face(gases[left], gases[right], left, right)
                faces_n[face] = [exchange.net_mol_s[name] for name in self.species_order]
                heat = conduction_rate_w(temperatures[left], temperatures[right], area_m2=self.face_area_m2,
                                         left_distance_m=self.cell_widths_m[left]/2,
                                         right_distance_m=self.cell_widths_m[right]/2,
                                         left_conductivity_w_m_k=self.conductivities_w_m_k[left],
                                         right_conductivity_w_m_k=self.conductivities_w_m_k[right])
                faces_u[face] = _sum((heat, gas_enthalpy_exchange(exchange, self.thermochemistry).total_w))
            if self.outer_reservoir is not None:
                exchange = self._face(gases[-1], self.outer_reservoir, count-1, None)
                faces_n[-1] = [exchange.net_mol_s[name] for name in self.species_order]
                faces_u[-1] = gas_enthalpy_exchange(exchange, self.thermochemistry).total_w
            if self.outer_surface_temperature_k is not None:
                boundary = self.outer_surface_temperature_k
                surface = _number(boundary(at) if callable(boundary) else boundary, 'surface_temperature', positive=True)
                # The existing two-resistance function splits this ONE half-cell
                # into two equal quarters with the same k. There is no film.
                heat = conduction_rate_w(temperatures[-1], surface, area_m2=self.face_area_m2,
                                         left_distance_m=self.cell_widths_m[-1]/4,
                                         right_distance_m=self.cell_widths_m[-1]/4,
                                         left_conductivity_w_m_k=self.conductivities_w_m_k[-1],
                                         right_conductivity_w_m_k=self.conductivities_w_m_k[-1])
                faces_u[-1] = _sum((faces_u[-1], heat))
            if self.reaction_network is not None:
                for cell, (row, temperature) in enumerate(zip(state.amounts_mol, temperatures)):
                    rates = self.reaction_network.rates(row, temperature,
                                                       self.face_area_m2*self.cell_widths_m[cell])
                    reactions[cell] = rates.source_mol_s
        except (ThermochemistryError, GasTransportError, ExchangeError, ReactionError) as exc:
            _raise_operator_failure(exc)
        return GasHeatEvaluation(rates=Rates(faces_n, faces_u, reactions, powers),
                                 temperatures_k=temperatures, gas_states=tuple(gases),
                                 source_ids=self.source_ids)
