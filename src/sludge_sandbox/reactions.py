"""Explicit, irreversible single-cell reaction sources; no invented mechanism.

All inventories are actual mol. All species sources come from the same signed
stoichiometric matrix and nonnegative reaction extents. No heat source is added:
the coupled energy solver already stores compatible species formation energies.
"""
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Integral, Real
import sys
from types import MappingProxyType
from typing import Iterable, Mapping

from .materials import ELEMENT_SYMBOLS


class ReactionError(ValueError):
    """Invalid reaction data, unsupported domain or infeasible progress."""


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ReactionError(f'invalid_{name}')


def _number(value: object, name: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ReactionError(f'invalid_{name}')
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ReactionError(f'nonfinite_{name}') from exc
    if not math.isfinite(result):
        raise ReactionError(f'nonfinite_{name}')
    if (nonnegative and result < 0) or (positive and result <= 0):
        raise ReactionError(f'invalid_{name}')
    return result


def _sources(values: object) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ReactionError('source_ids_required')
    for value in values:
        _text(value, 'source_id')
    if len(set(values)) != len(values):
        raise ReactionError('duplicate_source_id')
    return tuple(values)


def _classification(value: str) -> None:
    if value not in ('manufactured', 'literature_candidate'):
        raise ReactionError('invalid_classification')


def _vector(values: object, size: int, name: str) -> tuple[float, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ReactionError(f'invalid_{name}_vector')
    try:
        values = tuple(values)
    except TypeError as exc:
        raise ReactionError(f'invalid_{name}_vector') from exc
    if len(values) != size:
        raise ReactionError(f'invalid_{name}_length')
    return tuple(_number(value, name, nonnegative=True) for value in values)


def _sum(values, name: str) -> float:
    values = tuple(values)
    if any(not math.isfinite(value) for value in values):
        raise ReactionError(f'nonfinite_{name}')
    try:
        total = math.fsum(values)
    except OverflowError as exc:
        raise ReactionError(f'nonfinite_{name}') from exc
    if not math.isfinite(total):
        raise ReactionError(f'nonfinite_{name}')
    return total


def _source_product(coefficient: float, extent: float) -> float:
    result = coefficient*extent
    if not math.isfinite(result):
        raise ReactionError('nonfinite_species_source')
    if coefficient != 0 and extent != 0 and abs(result) < sys.float_info.min:
        raise ReactionError('source_outside_float_range')
    return result


@dataclass(frozen=True)
class SpeciesDefinition:
    species_id: str
    phase: str
    elements: Mapping[str, int]
    molar_mass_kg_mol: float
    source_ids: tuple[str, ...]
    classification: str

    def __post_init__(self) -> None:
        _text(self.species_id, 'species_id')
        if self.phase not in ('solid', 'liquid', 'gas'):
            raise ReactionError('invalid_species_phase')
        _classification(self.classification)
        if not isinstance(self.elements, Mapping) or not self.elements:
            raise ReactionError('explicit_element_counts_required')
        elements = {}
        for element, count in self.elements.items():
            if element not in ELEMENT_SYMBOLS:
                raise ReactionError('unknown_element')
            if isinstance(count, bool) or not isinstance(count, Integral) or count <= 0:
                raise ReactionError('element_counts_must_be_positive_integers')
            elements[element] = int(count)
        object.__setattr__(self, 'elements', MappingProxyType(elements))
        object.__setattr__(self, 'molar_mass_kg_mol', _number(self.molar_mass_kg_mol, 'molar_mass', positive=True))
        object.__setattr__(self, 'source_ids', _sources(self.source_ids))


@dataclass(frozen=True)
class ArrheniusMassAction:
    """Versioned candidate using explicitly normalized bulk concentrations.

    rate density = A exp(-Ea/(R T)) product[(N_i/V)/c_ref]^order_i.
    A has mol/(m^3 s) units; changing c_ref requires a new matching A.
    This is an apparent bulk-volume law, not a gas-pore or surface-activity law.
    """
    candidate_id: str
    version: str
    prefactor_mol_m3_s: float
    activation_energy_j_mol: float
    concentration_reference_mol_m3: float
    concentration_basis: str
    orders: Mapping[str, float]
    temperature_range_k: tuple[float, float]
    gas_constant_j_mol_k: float
    constant_source_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    classification: str
    prefactor_unit: str
    activation_energy_unit: str
    concentration_unit: str
    gas_constant_unit: str

    def __post_init__(self) -> None:
        _text(self.candidate_id, 'candidate_id')
        _text(self.version, 'candidate_version')
        _classification(self.classification)
        if self.concentration_basis != 'current_cell_bulk_volume':
            raise ReactionError('unsupported_concentration_basis')
        if (self.prefactor_unit, self.activation_energy_unit, self.concentration_unit,
                self.gas_constant_unit) != ('mol/(m^3 s)', 'J/mol', 'mol/m^3', 'J/(mol K)'):
            raise ReactionError('incompatible_kinetic_units')
        for name in ('prefactor_mol_m3_s', 'activation_energy_j_mol',
                     'concentration_reference_mol_m3', 'gas_constant_j_mol_k'):
            value = _number(getattr(self, name), name,
                            nonnegative=name == 'prefactor_mol_m3_s',
                            positive=name in ('concentration_reference_mol_m3', 'gas_constant_j_mol_k'))
            object.__setattr__(self, name, value)
        if not isinstance(self.orders, Mapping) or not self.orders:
            raise ReactionError('explicit_reaction_orders_required')
        orders = {}
        for name, order in self.orders.items():
            _text(name, 'order_species_id')
            orders[name] = _number(order, 'reaction_order', positive=True)
        object.__setattr__(self, 'orders', MappingProxyType(orders))
        bounds = _vector(self.temperature_range_k, 2, 'temperature_range')
        if not 0 < bounds[0] < bounds[1]:
            raise ReactionError('invalid_temperature_range')
        object.__setattr__(self, 'temperature_range_k', bounds)
        object.__setattr__(self, 'source_ids', _sources(self.source_ids))
        object.__setattr__(self, 'constant_source_ids', _sources(self.constant_source_ids))


@dataclass(frozen=True)
class ReactionDefinition:
    reaction_id: str
    version: str
    stoichiometry: Mapping[str, Fraction | float | int]
    kinetics: ArrheniusMassAction
    pathway: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.reaction_id, 'reaction_id')
        _text(self.version, 'reaction_version')
        if not isinstance(self.kinetics, ArrheniusMassAction):
            raise ReactionError('explicit_kinetics_required')
        if self.pathway not in ('oxygen_free_pyrolysis', 'oxygen_consuming', 'other'):
            raise ReactionError('unknown_reaction_pathway')
        if not isinstance(self.stoichiometry, Mapping) or not self.stoichiometry:
            raise ReactionError('explicit_stoichiometry_required')
        coefficients = {}
        for name, value in self.stoichiometry.items():
            _text(name, 'stoichiometric_species_id')
            finite = _number(value, 'stoichiometric_coefficient')
            if finite == 0:
                raise ReactionError('zero_stoichiometric_coefficient')
            # Decimal inputs retain the explicit decimal; Fraction supports
            # exact rational values such as 1/3 without a balancing tolerance.
            if isinstance(value, (Fraction, Integral)):
                coefficients[name] = Fraction(value)
            else:
                coefficients[name] = Fraction(str(finite))
        if not any(v < 0 for v in coefficients.values()) or not any(v > 0 for v in coefficients.values()):
            raise ReactionError('reactants_and_products_required')
        object.__setattr__(self, 'stoichiometry', MappingProxyType(coefficients))
        object.__setattr__(self, 'source_ids', _sources(self.source_ids))


@dataclass(frozen=True)
class ReactionRates:
    species_order: tuple[str, ...]
    reaction_order: tuple[str, ...]
    extent_mol_s: tuple[float, ...]
    source_mol_s: tuple[float, ...]


@dataclass(frozen=True)
class ReactionNetwork:
    species: tuple[SpeciesDefinition, ...]
    reactions: tuple[ReactionDefinition, ...]
    allow_manufactured: bool = False

    def __post_init__(self) -> None:
        if type(self.allow_manufactured) is not bool:
            raise ReactionError('invalid_test_mode')
        if not isinstance(self.species, (tuple, list)) or not self.species or any(
                not isinstance(item, SpeciesDefinition) for item in self.species):
            raise ReactionError('explicit_species_required')
        if not isinstance(self.reactions, (tuple, list)) or not self.reactions or any(
                not isinstance(item, ReactionDefinition) for item in self.reactions):
            raise ReactionError('explicit_reactions_required')
        object.__setattr__(self, 'species', tuple(self.species))
        object.__setattr__(self, 'reactions', tuple(self.reactions))
        if len(set(self.species_order)) != len(self.species):
            raise ReactionError('duplicate_species_id')
        if len(set(self.reaction_order)) != len(self.reactions):
            raise ReactionError('duplicate_reaction_id')
        if self.contains_manufactured and not self.allow_manufactured:
            raise ReactionError('manufactured_requires_test_mode')
        by_id = {item.species_id: item for item in self.species}
        candidates = {}
        for reaction in self.reactions:
            identity = (reaction.kinetics.candidate_id, reaction.kinetics.version)
            if identity in candidates and candidates[identity] != reaction.kinetics:
                raise ReactionError('conflicting_candidate_identity')
            candidates[identity] = reaction.kinetics
            stoich = reaction.stoichiometry
            if set(stoich) - by_id.keys():
                raise ReactionError('unknown_species')
            reactants = {name for name, value in stoich.items() if value < 0}
            if set(reaction.kinetics.orders) != reactants:
                raise ReactionError('orders_must_cover_reactants')
            consumed_oxygen = any(by_id[name].phase == 'gas' and dict(by_id[name].elements) == {'O': 2}
                                  for name in reactants)
            if reaction.pathway == 'oxygen_free_pyrolysis' and consumed_oxygen:
                raise ReactionError('oxygen_free_pathway_consumes_oxygen')
            if reaction.pathway == 'oxygen_consuming' and not consumed_oxygen:
                raise ReactionError('oxygen_consuming_pathway_requires_oxygen')
            elements = {element for name in stoich for element in by_id[name].elements}
            for element in elements:
                residual = sum((coefficient*by_id[name].elements.get(element, 0)
                                for name, coefficient in stoich.items()), Fraction(0))
                if residual != 0:
                    raise ReactionError(f'element_balance:{reaction.reaction_id}:{element}:{residual}')
            # Separate from elemental balance: every explicit molecular mass
            # participates. No atomic weights or automatic mass repair exist.
            mass_terms = [coefficient*Fraction(str(by_id[name].molar_mass_kg_mol))
                          for name, coefficient in stoich.items()]
            residual = abs(sum(mass_terms, Fraction(0)))
            scale = sum((abs(term) for term in mass_terms), Fraction(0))
            if residual > Fraction(1, 10**12)*scale:
                raise ReactionError(f'mass_balance:{reaction.reaction_id}')

    @property
    def species_order(self) -> tuple[str, ...]:
        return tuple(item.species_id for item in self.species)

    @property
    def reaction_order(self) -> tuple[str, ...]:
        return tuple(item.reaction_id for item in self.reactions)

    @property
    def contains_manufactured(self) -> bool:
        return any(item.classification == 'manufactured' for item in self.species) or any(
            item.kinetics.classification == 'manufactured' for item in self.reactions)

    @property
    def material_qualified(self) -> bool:
        return False

    @property
    def scientific_status(self) -> str:
        return ('manufactured_not_material_qualified' if self.contains_manufactured
                else 'candidate_sources_not_resolved_not_material_qualified')

    @property
    def source_ids(self) -> tuple[str, ...]:
        sources = {source for item in self.species for source in item.source_ids}
        for reaction in self.reactions:
            sources.update(reaction.source_ids)
            sources.update(reaction.kinetics.source_ids)
            sources.update(reaction.kinetics.constant_source_ids)
        return tuple(sorted(sources))

    @property
    def stoichiometric_matrix(self) -> tuple[tuple[float, ...], ...]:
        """Rows = species_order, columns = reaction_order, signed mol/mol."""
        return tuple(tuple(float(reaction.stoichiometry.get(name, 0)) for reaction in self.reactions)
                     for name in self.species_order)

    def source_mol_s(self, extent_mol_s: Iterable[float]) -> tuple[float, ...]:
        progress = _vector(extent_mol_s, len(self.reactions), 'extent_mol_s')
        return tuple(_sum((_source_product(coefficient, extent) for coefficient, extent in zip(row, progress)), 'species_source')
                     for row in self.stoichiometric_matrix)

    def rates(self, amount_mol: Iterable[float], temperature_k: float, cell_volume_m3: float) -> ReactionRates:
        amounts = _vector(amount_mol, len(self.species), 'amount_mol')
        temperature = _number(temperature_k, 'temperature', positive=True)
        volume = _number(cell_volume_m3, 'cell_volume', positive=True)
        inventory = dict(zip(self.species_order, amounts))
        progress = []
        for reaction in self.reactions:
            law = reaction.kinetics
            if not law.temperature_range_k[0] <= temperature <= law.temperature_range_k[1]:
                raise ReactionError(f'temperature_out_of_kinetic_domain:{reaction.reaction_id}')
            if law.prefactor_mol_m3_s == 0 or any(inventory[name] == 0 for name in law.orders):
                progress.append(0.)
                continue
            rt = _number(law.gas_constant_j_mol_k*temperature, 'RT', positive=True)
            # Log form avoids spurious intermediate powers/product overflow.
            log_rate = _sum((
                math.log(law.prefactor_mol_m3_s), math.log(volume),
                -law.activation_energy_j_mol/rt,
                *[order*(math.log(inventory[name])-math.log(volume)
                         -math.log(law.concentration_reference_mol_m3)) for name, order in law.orders.items()],
            ), 'log_rate')
            try:
                rate = math.exp(log_rate)
            except OverflowError as exc:
                raise ReactionError('rate_outside_float_range') from exc
            if not math.isfinite(rate) or rate == 0:
                raise ReactionError('rate_outside_float_range')
            progress.append(rate)
        extents = tuple(progress)
        return ReactionRates(self.species_order, self.reaction_order, extents, self.source_mol_s(extents))

    def _gross_consumption(self, progress: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(_sum((_source_product(-coefficient, extent) for coefficient, extent in zip(row, progress) if coefficient < 0),
                          'gross_consumption') for row in self.stoichiometric_matrix)

    def maximum_forward_step_s(self, amount_mol: Iterable[float], extent_mol_s: Iterable[float]) -> float:
        """Conservative frozen-rate bound, not a stability/accuracy guarantee.

        Competing pathways share each initial inventory. Simultaneous product
        formation is not borrowed to pay for another reaction's consumption.
        No consuming rate means an infinite inventory-only bound.
        """
        amounts = _vector(amount_mol, len(self.species), 'amount_mol')
        progress = _vector(extent_mol_s, len(self.reactions), 'extent_mol_s')
        consumed = self._gross_consumption(progress)
        bounds = [amount/rate for amount, rate in zip(amounts, consumed) if rate > 0]
        if not bounds:
            return math.inf
        bound = min(bounds)
        return math.nextafter(bound, 0.) if bound > 0 else 0.

    def amounts_after_extents(self, amount_mol: Iterable[float], extent_mol: Iterable[float], *,
                              maximum_relative_increment_error: float = 1e-10) -> tuple[float, ...]:
        """Apply extents only when their changes remain numerically representable.

        The relative increment error bound is a numerical policy, not a material
        parameter. Its scale is each proposed change, never the stored inventory.
        No correction, clipping or invented products compensate failed updates.
        """
        resolution = _number(maximum_relative_increment_error, 'increment_error', positive=True)
        if resolution > 1e-10:
            raise ReactionError('increment_error_exceeds_resolution_cap')
        amounts = _vector(amount_mol, len(self.species), 'amount_mol')
        extents = _vector(extent_mol, len(self.reactions), 'extent_mol')
        consumed = self._gross_consumption(extents)
        if any(used > amount for used, amount in zip(consumed, amounts)):
            raise ReactionError('insufficient_inventory')
        changes = self.source_mol_s(extents)
        result = tuple(_sum((amount, change), 'updated_inventory') for amount, change in zip(amounts, changes))
        if any(amount < 0 for amount in result):
            raise ReactionError('insufficient_inventory')
        for before, after, change in zip(amounts, result, changes):
            residual = _sum((after, -before, -change), 'increment_residual')
            if (change == 0 and residual != 0) or (change != 0 and abs(residual/change) > resolution):
                raise ReactionError('unresolvable_inventory_increment')
        return result
