"""Source-labelled ideal-gas caloric properties with honest fit discontinuities.

Molar enthalpy contains formation enthalpy in the 298.15 K elemental reference.
Ideal-gas internal energy is h - R*T. Reactions change inventories; callers must
not add the same reaction enthalpy as an additional source of total energy.

This module supplies no liquid/solid properties, equilibrium composition,
latent-heat model, real-gas pressure range, or raw-sludge constitutive values.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Protocol


class ThermochemistryError(ValueError):
    """Invalid caloric data, unavailable temperature domain, or nonunique inverse."""


class CaloricSpecies(Protocol):
    """Future condensed phases must provide their own sourced u/h relation."""

    species_id: str
    source_ids: tuple[str, ...]
    temperature_range_k: tuple[float, float]

    def enthalpy_j_mol(self, temperature_k: float) -> float: ...
    def internal_energy_j_mol(self, temperature_k: float) -> float: ...
    def cp_j_mol_k(self, temperature_k: float) -> float: ...
    def cv_j_mol_k(self, temperature_k: float) -> float: ...


def _number(value: object, name: str) -> float:
    if type(value) not in (int, float):
        raise ThermochemistryError(f'{name}_must_be_finite_number')
    try:
        result = float(value)
    except OverflowError as exc:
        raise ThermochemistryError(f'{name}_must_be_finite_number') from exc
    if not math.isfinite(result):
        raise ThermochemistryError(f'{name}_must_be_finite_number')
    return result


def _source_ids(values: object) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ThermochemistryError('source_ids_required')
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ThermochemistryError('invalid_source_ids')
    if len(set(values)) != len(values):
        raise ThermochemistryError('duplicate_source_id')
    return tuple(values)


def _fields(value: object, fields: str) -> None:
    if type(value) is not dict or set(value) != set(fields.split()):
        raise ThermochemistryError('invalid_schema_fields')


def _finite_sum(terms: list[float], error: str) -> float:
    if any(not math.isfinite(value) for value in terms):
        raise ThermochemistryError(error)
    try:
        value = math.fsum(terms)
    except OverflowError as exc:
        raise ThermochemistryError(error) from exc
    if not math.isfinite(value):
        raise ThermochemistryError(error)
    return value


@dataclass(frozen=True)
class ShomateSegment:
    """Unaltered A-H coefficients; kJ/mol Shomate primitive converted to J/mol."""

    temperature_range_k: tuple[float, float]
    coefficients: tuple[float, ...]
    formation_enthalpy_298_j_mol: float
    gas_constant_j_mol_k: float
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.temperature_range_k) != 2:
            raise ThermochemistryError('invalid_temperature_range')
        low, high = (_number(value, 'temperature') for value in self.temperature_range_k)
        if not 0 < low < high:
            raise ThermochemistryError('invalid_temperature_range')
        if len(self.coefficients) != 8:
            raise ThermochemistryError('eight_shomate_coefficients_required')
        coefficients = tuple(_number(value, 'coefficient') for value in self.coefficients)
        formation = _number(self.formation_enthalpy_298_j_mol, 'formation_enthalpy')
        constant = _number(self.gas_constant_j_mol_k, 'gas_constant')
        if constant <= 0:
            raise ThermochemistryError('invalid_gas_constant')
        object.__setattr__(self, 'temperature_range_k', (low, high))
        object.__setattr__(self, 'coefficients', coefficients)
        object.__setattr__(self, 'source_ids', _source_ids(self.source_ids))
        if not math.isclose(coefficients[7]*1000, formation, rel_tol=1e-13, abs_tol=1e-9):
            raise ThermochemistryError('incompatible_formation_reference')
        self._certify_positive_cv()

    def _scaled_temperature(self, temperature_k: float) -> float:
        temperature = _number(temperature_k, 'temperature')
        if not self.temperature_range_k[0] <= temperature <= self.temperature_range_k[1]:
            raise ThermochemistryError('temperature_out_of_domain')
        return temperature/1000

    def cp_j_mol_k(self, temperature_k: float) -> float:
        t = self._scaled_temperature(temperature_k)
        a, b, c, d, e, _, _, _ = self.coefficients
        value = a + b*t + c*t*t + d*t**3 + e/t**2
        if not math.isfinite(value) or value <= self.gas_constant_j_mol_k:
            raise ThermochemistryError('nonpositive_heat_capacity')
        return value

    def cv_j_mol_k(self, temperature_k: float) -> float:
        return self.cp_j_mol_k(temperature_k) - self.gas_constant_j_mol_k

    def enthalpy_j_mol(self, temperature_k: float) -> float:
        t = self._scaled_temperature(temperature_k)
        a, b, c, d, e, f, _, h = self.coefficients
        sensible_kj_mol = a*t + b*t*t/2 + c*t**3/3 + d*t**4/4 - e/t + f - h
        value = self.formation_enthalpy_298_j_mol + 1000*sensible_kj_mol
        if not math.isfinite(value):
            raise ThermochemistryError('nonfinite_enthalpy')
        return value

    def internal_energy_j_mol(self, temperature_k: float) -> float:
        return self.enthalpy_j_mol(temperature_k) - self.gas_constant_j_mol_k*temperature_k

    def _certify_positive_cv(self) -> None:
        """Interval bounds, not a finite sample masquerading as monotonicity proof.

        Each monomial's minimum over a positive temperature interval occurs at
        an endpoint. Their sum bounds cv from below. Subdivide if that bound
        is inconclusive; refuse a curve that cannot be certified in 16 levels.
        """
        a, b, c, d, e, _, _, _ = self.coefficients
        stack = [(*self.temperature_range_k, 0)]
        while stack:
            low, high, depth = stack.pop()
            self.cp_j_mol_k(low)
            self.cp_j_mol_k(high)
            x, y = low/1000, high/1000
            lower = (a - self.gas_constant_j_mol_k + min(b*x, b*y)
                     + min(c*x*x, c*y*y) + min(d*x**3, d*y**3)
                     + min(e/x**2, e/y**2))
            if math.isfinite(lower) and lower > 1e-12:
                continue
            if depth >= 16:
                raise ThermochemistryError('nonpositive_heat_capacity_not_certified')
            middle = (low+high)/2
            stack.extend(((low, middle, depth+1), (middle, high, depth+1)))


@dataclass(frozen=True)
class ShomateGas:
    species_id: str
    segments: tuple[ShomateSegment, ...]
    classification: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.species_id, str) or not self.species_id.strip() or not self.segments:
            raise ThermochemistryError('invalid_species')
        if self.classification not in ('literature_constitutive_model', 'manufactured_test_fixture'):
            raise ThermochemistryError('invalid_thermochemistry_classification')
        object.__setattr__(self, 'segments', tuple(self.segments))
        object.__setattr__(self, 'source_ids', _source_ids(self.source_ids))
        for left, right in zip(self.segments, self.segments[1:]):
            if left.temperature_range_k[1] != right.temperature_range_k[0]:
                raise ThermochemistryError('shomate_ranges_must_be_adjacent_and_ordered')
            if (left.gas_constant_j_mol_k != right.gas_constant_j_mol_k
                    or left.formation_enthalpy_298_j_mol != right.formation_enthalpy_298_j_mol):
                raise ThermochemistryError('incompatible_thermodynamic_reference')

    @property
    def temperature_range_k(self) -> tuple[float, float]:
        return self.segments[0].temperature_range_k[0], self.segments[-1].temperature_range_k[1]

    @property
    def formation_enthalpy_298_j_mol(self) -> float:
        return self.segments[0].formation_enthalpy_298_j_mol

    def segment_for(self, temperature_k: float) -> ShomateSegment:
        temperature = _number(temperature_k, 'temperature')
        # At a shared breakpoint, the higher-temperature range owns the point.
        for segment in reversed(self.segments):
            if segment.temperature_range_k[0] <= temperature <= segment.temperature_range_k[1]:
                return segment
        raise ThermochemistryError('temperature_out_of_domain')

    def cp_j_mol_k(self, temperature_k: float) -> float:
        return self.segment_for(temperature_k).cp_j_mol_k(temperature_k)

    def cv_j_mol_k(self, temperature_k: float) -> float:
        return self.segment_for(temperature_k).cv_j_mol_k(temperature_k)

    def enthalpy_j_mol(self, temperature_k: float) -> float:
        return self.segment_for(temperature_k).enthalpy_j_mol(temperature_k)

    def internal_energy_j_mol(self, temperature_k: float) -> float:
        return self.segment_for(temperature_k).internal_energy_j_mol(temperature_k)

    def seam_diagnostics(self) -> list[dict]:
        results = []
        for left, right in zip(self.segments, self.segments[1:]):
            temperature = right.temperature_range_k[0]
            results.append(dict(
                temperature_k=temperature,
                cp_right_minus_left_j_mol_k=right.cp_j_mol_k(temperature)-left.cp_j_mol_k(temperature),
                h_right_minus_left_j_mol=right.enthalpy_j_mol(temperature)-left.enthalpy_j_mol(temperature),
                treatment='original_fit_preserved; upper_range_owns_breakpoint; inverse_checks_each_branch',
            ))
        return results


class Thermochemistry:
    """Ideal-gas mixture in actual mol/J; no pressure work or reaction heat added."""

    def __init__(self, pack_id: str, gases: Mapping[str, ShomateGas],
                 gas_constant_j_mol_k: float, constant_source_ids: tuple[str, ...],
                 *, allow_manufactured: bool = False):
        if type(allow_manufactured) is not bool:
            raise ThermochemistryError('invalid_test_mode')
        if not isinstance(pack_id, str) or not pack_id or not gases:
            raise ThermochemistryError('invalid_pack')
        constant = _number(gas_constant_j_mol_k, 'gas_constant')
        if constant <= 0:
            raise ThermochemistryError('invalid_gas_constant')
        for name, gas in gases.items():
            if name != gas.species_id or any(segment.gas_constant_j_mol_k != constant for segment in gas.segments):
                raise ThermochemistryError('incompatible_species_or_constant')
            if gas.classification == 'manufactured_test_fixture' and not allow_manufactured:
                raise ThermochemistryError('manufactured_model_requires_test_mode')
        self.pack_id = pack_id
        self.gases = MappingProxyType(dict(gases))
        self.gas_constant_j_mol_k = constant
        self.constant_source_ids = _source_ids(constant_source_ids)
        self.contains_manufactured_models = any(g.classification == 'manufactured_test_fixture' for g in gases.values())
        self.provenance_status = ('manufactured_test_fixture' if self.contains_manufactured_models
                                  else 'source_links_declared_not_registry_validated')

    def species(self, species_id: str) -> ShomateGas:
        try:
            return self.gases[species_id]
        except (KeyError, TypeError) as exc:
            raise ThermochemistryError('unknown_species') from exc

    def _active(self, amounts_mol: Mapping[str, float]) -> tuple[tuple[ShomateGas, float], ...]:
        if not isinstance(amounts_mol, Mapping):
            raise ThermochemistryError('invalid_inventory_mapping')
        active = []
        for name, amount in amounts_mol.items():
            gas = self.species(name)
            amount = _number(amount, 'inventory')
            if amount < 0:
                raise ThermochemistryError('negative_inventory')
            if amount > 0:
                active.append((gas, amount))
        if not active:
            raise ThermochemistryError('empty_thermal_inventory')
        return tuple(active)

    def source_ids_for(self, amounts_mol: Mapping[str, float]) -> tuple[str, ...]:
        sources = set(self.constant_source_ids)
        for gas, _ in self._active(amounts_mol):
            sources.update(gas.source_ids)
            for segment in gas.segments:
                sources.update(segment.source_ids)
        return tuple(sorted(sources))

    def mixture_internal_energy_j(self, amounts_mol: Mapping[str, float], temperature_k: float) -> float:
        terms = [amount*gas.internal_energy_j_mol(temperature_k) for gas, amount in self._active(amounts_mol)]
        return _finite_sum(terms, 'nonfinite_mixture_energy')

    def mixture_cv_j_k(self, amounts_mol: Mapping[str, float], temperature_k: float) -> float:
        value = _finite_sum([amount*gas.cv_j_mol_k(temperature_k) for gas, amount in self._active(amounts_mol)],
                            'nonfinite_mixture_heat_capacity')
        if value <= 0:
            raise ThermochemistryError('nonpositive_mixture_heat_capacity')
        return value

    def temperature_from_internal_energy_j(
        self, energy_j: float, amounts_mol: Mapping[str, float],
        *, energy_tolerance_j: float = 1e-8, temperature_tolerance_k: float = 1e-9,
        max_iterations: int = 100,
    ) -> float:
        """Solve every continuous fit branch; reject gaps and multiple roots.

        The absolute energy tolerance is a numerical policy in J, independent
        of potentially large formation energies. It is never a fit uncertainty.
        A rounded zero residual alone cannot establish temperature accuracy.
        Reject an inverse whose floating-point energy spacing is too coarse.
        """
        target = _number(energy_j, 'energy')
        tolerance = _number(energy_tolerance_j, 'energy_tolerance')
        temperature_tolerance = _number(temperature_tolerance_k, 'temperature_tolerance')
        if (tolerance <= 0 or temperature_tolerance <= 0
                or type(max_iterations) is not int or max_iterations <= 0):
            raise ThermochemistryError('invalid_inverse_policy')
        active = self._active(amounts_mol)
        low = max(gas.temperature_range_k[0] for gas, _ in active)
        high = min(gas.temperature_range_k[1] for gas, _ in active)
        if low >= high:
            raise ThermochemistryError('no_common_temperature_domain')
        breaks = sorted({low, high} | {
            segment.temperature_range_k[0] for gas, _ in active for segment in gas.segments
            if low < segment.temperature_range_k[0] < high
        })
        candidates = []
        energy_edges = []
        for lower, upper in zip(breaks, breaks[1:]):
            branch = [(gas.segment_for((lower+upper)/2), amount) for gas, amount in active]

            def energy(temperature: float) -> float:
                return _finite_sum([amount*segment.internal_energy_j_mol(temperature) for segment, amount in branch],
                                   'nonfinite_mixture_energy')

            first, last = energy(lower), energy(upper)
            energy_edges.extend((first, last))
            if not first < last:
                raise ThermochemistryError('nonmonotone_internal_energy')
            if not first <= target <= last:
                continue
            # Exclude the left branch's upper endpoint, which is owned by the
            # next raw fit. A discontinuity is never filled by interpolation.
            if target == last and upper != high:
                continue
            a, b = lower, upper
            if target == first:
                candidate = a
            elif target == last:
                candidate = b
            else:
                for _ in range(max_iterations):
                    candidate = (a+b)/2
                    residual = energy(candidate)-target
                    if abs(residual) <= tolerance and b-a <= temperature_tolerance/2:
                        break
                    if candidate in (a, b):
                        raise ThermochemistryError('temperature_inverse_stagnation')
                    if residual < 0:
                        a = candidate
                    else:
                        b = candidate
                else:
                    raise ThermochemistryError('temperature_inverse_not_converged')
            # At a breakpoint, check the actual public branch-selection rule.
            if abs(self.mixture_internal_energy_j(amounts_mol, candidate)-target) > tolerance:
                continue
            # Products and the supplied total each have finite float spacing.
            # In particular, subnormal inventories may map a broad interval of
            # temperatures to exactly the same rounded energy. Do not accept
            # that equality as an accurate inverse. Full ulps avoid underflow
            # from halving the smallest subnormal. This is a representability
            # guard, not a bound on all polynomial evaluation roundoff.
            terms = [amount*gas.internal_energy_j_mol(candidate) for gas, amount in active]
            spacing = _finite_sum([math.ulp(target), *[math.ulp(term) for term in terms]],
                                  'insufficient_energy_resolution')
            cv = self.mixture_cv_j_k(amounts_mol, candidate)
            if spacing/cv > temperature_tolerance/4:
                raise ThermochemistryError('insufficient_energy_resolution')
            candidates.append(candidate)
        unique = set(candidates)
        if len(unique) > 1:
            raise ThermochemistryError('ambiguous_temperature')
        if not unique:
            if target < min(energy_edges) or target > max(energy_edges):
                raise ThermochemistryError('energy_out_of_temperature_domain')
            raise ThermochemistryError('energy_in_property_gap')
        return unique.pop()


def load_thermochemistry(path: str | Path, *, allow_manufactured: bool = False) -> Thermochemistry:
    """Load explicit units, formation reference, original ranges and source IDs.

    Source IDs are linkage metadata; the separate evidence registry must check
    their authenticity, accessible assets, and application-domain suitability.
    """
    def pairs(items: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in items:
            if key in result:
                raise ThermochemistryError('duplicate_key')
            result[key] = value
        return result

    def invalid_constant(_: str) -> None:
        raise ThermochemistryError('nonfinite_json')

    try:
        text = Path(path).read_text(encoding='utf-8')
        if len(text) > 2_000_000:
            raise ThermochemistryError('thermochemistry_file_too_large')
        pack = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
        _fields(pack, 'schema_version pack_id model energy_reference reference_temperature_k units gas_constant species')
        if (type(pack['schema_version']) is not int or pack['schema_version'] != 1
                or pack['model'] != 'ideal_gas_shomate'
                or pack['energy_reference'] != 'formation_enthalpy_plus_sensible'
                or _number(pack['reference_temperature_k'], 'reference_temperature') != 298.15):
            raise ThermochemistryError('unsupported_thermochemistry_schema')
        if pack['units'] != {'temperature': 'K', 'enthalpy': 'J/mol', 'heat_capacity': 'J/(mol K)', 'inventory': 'mol'}:
            raise ThermochemistryError('incompatible_thermochemistry_units')
        _fields(pack['gas_constant'], 'value_j_mol_k source_ids derivation')
        constant = _number(pack['gas_constant']['value_j_mol_k'], 'gas_constant')
        constant_sources = _source_ids(pack['gas_constant']['source_ids'])
        gases = {}
        for entry in pack['species']:
            _fields(entry, 'species_id phase classification formation_enthalpy_298_j_mol source_ids segments')
            if entry['phase'] != 'ideal_gas':
                raise ThermochemistryError('unsupported_phase')
            name = entry['species_id']
            if name in gases:
                raise ThermochemistryError('duplicate_species')
            for segment in entry['segments']:
                _fields(segment, 'temperature_range_k coefficients source_ids')
            segments = tuple(ShomateSegment(
                tuple(segment['temperature_range_k']), tuple(segment['coefficients']),
                entry['formation_enthalpy_298_j_mol'], constant, _source_ids(segment['source_ids']),
            ) for segment in entry['segments'])
            gases[name] = ShomateGas(name, segments, entry['classification'], _source_ids(entry['source_ids']))
        return Thermochemistry(pack['pack_id'], gases, constant, constant_sources,
                               allow_manufactured=allow_manufactured)
    except ThermochemistryError:
        raise
    except (OSError, ValueError, TypeError, KeyError, OverflowError, ZeroDivisionError, RecursionError) as exc:
        raise ThermochemistryError('invalid_thermochemistry_data') from exc
