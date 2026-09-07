"""Independent accepted-trajectory ledger audit, without solving the model again.

Inventories are actual mol per cell; energy is stored total internal energy in J.
This module does NOT reconstruct U from species thermochemistry or establish
material validity. Its scales and tolerances come from an explicit audit policy,
never from an artifact's largest inventory, formation energy or throughflow.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from fractions import Fraction
import math
from numbers import Real
from types import MappingProxyType

from .integration import IntegrationResult


class ConservationAuditError(ValueError):
    """Malformed trajectory, basis, policy or unrepresentable audit arithmetic."""


def _number(value, name, *, nonnegative=False, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ConservationAuditError(f"invalid_{name}")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise ConservationAuditError(f"invalid_{name}") from exc
    if not math.isfinite(value) or (nonnegative and value < 0) or (positive and value <= 0):
        raise ConservationAuditError(f"invalid_{name}")
    return value


def _sequence(value, name):
    if isinstance(value, (str, bytes, Mapping)):
        raise ConservationAuditError(f"invalid_{name}")
    try:
        return tuple(value)
    except TypeError as exc:
        raise ConservationAuditError(f"invalid_{name}") from exc


def _names(value, name):
    values = _sequence(value, name)
    if (not values or any(not isinstance(v, str) or not v or v != v.strip() for v in values)
            or len(set(values)) != len(values)):
        raise ConservationAuditError(f"invalid_{name}")
    return values


def _vector(value, size, name, *, nonnegative=False, positive=False):
    values = _sequence(value, name)
    if len(values) != size:
        raise ConservationAuditError(f"shape_{name}")
    return tuple(_number(v, name, nonnegative=nonnegative, positive=positive) for v in values)


def _matrix(value, rows, columns, name, *, nonnegative=False):
    values = _sequence(value, name)
    if len(values) != rows:
        raise ConservationAuditError(f"shape_{name}")
    return tuple(_vector(row, columns, name, nonnegative=nonnegative) for row in values)


def _sum(terms):
    try:
        result = float(_exact_sum(terms))
    except (OverflowError, ValueError) as exc:
        raise ConservationAuditError("audit_sum_outside_numeric_range") from exc
    return _number(result, "audit_sum")


def _exact_sum(terms):
    return sum((Fraction(term) for term in terms), Fraction(0))


def _product(a, b):
    result = _number(a*b, "weighted_term")
    if result == 0 and a != 0 and b != 0:
        raise ConservationAuditError("weighted_term_underflow")
    # Preserve the product's low bits until the complete residual is formed.
    return Fraction(a)*Fraction(b)


class _PrefixSum:
    """Short nonoverlapping float expansions consumed by exact residual sums.

    Preserve low-order terms across steps without rescanning an ever-growing
    raw ledger at every prefix. A plain previous_total + new_term loses small
    exchanges before a later large counterflow cancels the previous total.
    """

    def __init__(self):
        self.partials = []

    def add(self, term):
        x = term
        index = 0
        for y in self.partials:
            if abs(x) < abs(y):
                x, y = y, x
            high = _number(x+y, "prefix_sum")
            low = y-(high-x)
            if low:
                self.partials[index] = low
                index += 1
            x = high
        self.partials[index:] = [x]

    def terms(self):
        return tuple(self.partials)


@dataclass(frozen=True)
class ConservationBasis:
    """Explicit species order, kg/mol vector, and mol-atoms/mol-species matrix.

    These values are caller-supplied evidence, not independently identified
    material chemistry. Every species and every element row must be represented.
    Fractional nonnegative counts support explicitly defined pseudo-components.
    """

    species_order: tuple[str, ...]
    molar_masses_kg_mol: tuple[float, ...]
    element_order: tuple[str, ...]
    element_matrix: tuple[tuple[float, ...], ...]

    def __post_init__(self):
        species = _names(self.species_order, "species_order")
        elements = _names(self.element_order, "element_order")
        masses = _vector(self.molar_masses_kg_mol, len(species), "molar_masses", positive=True)
        matrix = _matrix(self.element_matrix, len(elements), len(species), "element_matrix", nonnegative=True)
        if any(not any(row) for row in matrix) or any(not any(row[k] for row in matrix) for k in range(len(species))):
            raise ConservationAuditError("uncovered_element_or_species")
        for name, value in (("species_order", species), ("element_order", elements),
                            ("molar_masses_kg_mol", masses), ("element_matrix", matrix)):
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class ConservationPolicy:
    """Fixed audit allowances: abs_limit + relative_tolerance * declared_scale.

    No default material scale or acceptance tolerance is supplied. This policy
    is distinct from the forward solver's truncation-error control.
    """

    relative_tolerance: float
    amount_absolute_tolerance_mol: float
    amount_scale_mol: float
    mass_absolute_tolerance_kg: float
    mass_scale_kg: float
    element_absolute_tolerance_mol: float
    element_scale_mol: float
    energy_absolute_tolerance_j: float
    energy_scale_j: float

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _number(getattr(self, name), name,
                                                  positive="scale" in name, nonnegative=True))
        for quantity in ("amount", "mass", "element", "energy"):
            _, _, limit = self.allowance(quantity)
            if limit <= 0:
                raise ConservationAuditError("positive_audit_allowance_required")

    def allowance(self, quantity: str) -> tuple[float, float, float]:
        unit = {"amount": "mol", "mass": "kg", "element": "mol", "energy": "j"}[quantity]
        absolute = getattr(self, f"{quantity}_absolute_tolerance_{unit}")
        scale = getattr(self, f"{quantity}_scale_{unit}")
        return absolute, scale, _sum((absolute, _product(self.relative_tolerance, scale)))


@dataclass(frozen=True)
class ResidualLocation:
    step_index: int
    start_s: float
    end_s: float
    cell_index: int | None = None
    species_id: str | None = None
    element_id: str | None = None


@dataclass(frozen=True)
class ConservationCheck:
    unit: str
    absolute_tolerance: float
    fixed_scale: float
    limit: float
    count: int
    max_absolute_residual: float
    max_scaled_residual: float
    worst_signed_residual: float | None
    worst_location: ResidualLocation | None
    passed: bool


class _Check:
    def __init__(self, quantity, policy):
        self.unit = {"amount": "mol", "mass": "kg", "element": "mol_atoms", "energy": "J"}[quantity]
        self.absolute, self.scale, self.limit = policy.allowance(quantity)
        self.count, self.maximum, self.signed, self.location = 0, 0., None, None
        self.exact_maximum = Fraction(0)

    def observe(self, terms, location):
        exact = _exact_sum(terms)
        residual = _number(exact, "residual")
        self.count += 1
        if self.location is None or abs(exact) > self.exact_maximum:
            self.exact_maximum = abs(exact)
            self.maximum, self.signed, self.location = abs(residual), residual, location

    def result(self):
        scaled = _number(self.maximum/self.scale, "scaled_residual")
        return ConservationCheck(self.unit, self.absolute, self.scale, self.limit, self.count,
                                 self.maximum, scaled, self.signed, self.location,
                                 self.count > 0 and self.exact_maximum <= Fraction(self.limit))


@dataclass(frozen=True)
class SystemInventory:
    amounts_mol: tuple[float, ...]
    mass_kg: float
    elements_mol: tuple[float, ...]
    stored_internal_energy_j: float


@dataclass(frozen=True)
class ConservationReport:
    status: str
    integration_status: str
    audited_steps: int
    species_order: tuple[str, ...]
    element_order: tuple[str, ...]
    policy: ConservationPolicy
    checks: Mapping[str, ConservationCheck]
    initial: SystemInventory
    final: SystemInventory
    basis: ConservationBasis
    energy_scope: str = "stored_internal_energy_ledger_only"

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def trajectory_completed(self) -> bool:
        return self.integration_status == "completed"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1, "status": self.status, "passed": self.passed,
            "integration_status": self.integration_status,
            "trajectory_completed": self.trajectory_completed,
            "audited_steps": self.audited_steps,
            "species_order": list(self.species_order), "element_order": list(self.element_order),
            "basis": asdict(self.basis), "policy": asdict(self.policy),
            "checks": {name: asdict(check) for name, check in self.checks.items()},
            "initial": asdict(self.initial), "final": asdict(self.final),
            "energy_scope": self.energy_scope, "thermodynamic_reconstruction": "not_evaluated",
            "scientific_status": "ledger_consistency_only_not_material_validation",
        }


def _state_arrays(state, cells, species):
    try:
        amounts = _matrix(state.amounts_mol, cells, species, "state_amounts", nonnegative=True)
        energy = _vector(state.internal_energy_j, cells, "state_energy")
    except AttributeError as exc:
        raise ConservationAuditError("invalid_state") from exc
    return amounts, energy


def _inventory(amounts, energy, basis):
    totals = tuple(_sum(row[k] for row in amounts) for k in range(len(basis.species_order)))
    mass = _sum(_product(basis.molar_masses_kg_mol[k], row[k]) for row in amounts for k in range(len(totals)))
    elements = tuple(_sum(_product(weights[k], row[k]) for row in amounts for k in range(len(totals)))
                     for weights in basis.element_matrix)
    return SystemInventory(totals, mass, elements, _sum(energy))


def audit_conservation(result: IntegrationResult, *, basis: ConservationBasis,
                       policy: ConservationPolicy) -> ConservationReport:
    """Audit every accepted step and prefix from data alone, using independent sums.

    Local species: ΔN-F_left+F_right-reaction. System mass and elements must
    close against external faces alone; local reaction mass/element sums must
    separately vanish. Stored U closes against face energy and cell work.
    A valid partial prefix may pass; zero accepted steps are not evaluated.
    """
    if not isinstance(result, IntegrationResult) or not isinstance(basis, ConservationBasis) or not isinstance(policy, ConservationPolicy):
        raise ConservationAuditError("validated_result_basis_policy_required")
    if not isinstance(result.status, str) or result.status not in {"completed", "cancelled", "resource_limit", "domain_exit", "numerical_failure"}:
        raise ConservationAuditError("unknown_integration_status")
    states = _sequence(result.states, "states")
    ledgers = _sequence(result.steps, "steps")
    times = tuple(_number(t, "trajectory_time") for t in _sequence(result.times_s, "times"))
    if not states or len(states) != len(ledgers)+1 or len(times) != len(states):
        raise ConservationAuditError("trajectory_length_mismatch")
    if any(end <= start for start, end in zip(times, times[1:])):
        raise ConservationAuditError("trajectory_times_not_increasing")
    try:
        cells = len(states[0].amounts_mol)
    except (AttributeError, TypeError) as exc:
        raise ConservationAuditError("invalid_initial_state") from exc
    if cells == 0:
        raise ConservationAuditError("empty_cell_domain")
    species = len(basis.species_order)
    initial_n, initial_u = _state_arrays(states[0], cells, species)
    before_n, before_u = initial_n, initial_u
    checks = {name: _Check(quantity, policy) for name, quantity in (
        ("cell_species_step", "amount"), ("system_species_step", "amount"),
        ("system_species_prefix", "amount"), ("reaction_mass_cell_step", "mass"),
        ("reaction_element_cell_step", "element"), ("system_mass_step", "mass"),
        ("system_mass_prefix", "mass"), ("system_element_step", "element"),
        ("system_element_prefix", "element"), ("cell_energy_step", "energy"),
        ("system_energy_step", "energy"), ("system_energy_prefix", "energy"),
        ("cell_species_prefix", "amount"), ("cell_energy_prefix", "energy"),
    )}
    boundary_prefix = [_PrefixSum() for _ in range(species)]
    reaction_prefix = [_PrefixSum() for _ in range(species)]
    energy_prefix = _PrefixSum()
    cell_n_prefix = [[_PrefixSum() for _ in range(species)] for _ in range(cells)]
    cell_u_prefix = [_PrefixSum() for _ in range(cells)]
    measures = [("mass", basis.molar_masses_kg_mol, None),
                *(("element", row, name) for name, row in zip(basis.element_order, basis.element_matrix))]

    for step_index, ledger in enumerate(ledgers):
        try:
            start, end = _number(ledger.start_s, "step_start"), _number(ledger.end_s, "step_end")
            if start != times[step_index] or end != times[step_index+1]:
                raise ConservationAuditError("step_time_mismatch")
            face_n = _matrix(ledger.face_species_mol, cells+1, species, "face_species")
            reaction = _matrix(ledger.reaction_species_mol, cells, species, "reaction_species")
            face_u = _vector(ledger.face_energy_j, cells+1, "face_energy")
            work = _vector(ledger.cell_work_j, cells, "cell_work")
        except AttributeError as exc:
            raise ConservationAuditError("invalid_step_ledger") from exc
        after_n, after_u = _state_arrays(states[step_index+1], cells, species)
        location = ResidualLocation(step_index, start, end)
        prefix_location = ResidualLocation(step_index, times[0], end)

        for cell in range(cells):
            cell_location = ResidualLocation(step_index, start, end, cell_index=cell)
            for k, name in enumerate(basis.species_order):
                species_location = ResidualLocation(step_index, start, end, cell, name)
                checks["cell_species_step"].observe((after_n[cell][k], -before_n[cell][k],
                    -face_n[cell][k], face_n[cell+1][k], -reaction[cell][k]), species_location)
                for term in (face_n[cell][k], -face_n[cell+1][k], reaction[cell][k]):
                    cell_n_prefix[cell][k].add(term)
                checks["cell_species_prefix"].observe((after_n[cell][k], -initial_n[cell][k],
                    *(-term for term in cell_n_prefix[cell][k].terms())),
                    ResidualLocation(step_index, times[0], end, cell, name))
            checks["cell_energy_step"].observe((after_u[cell], -before_u[cell],
                                                -face_u[cell], face_u[cell+1], -work[cell]), cell_location)
            for term in (face_u[cell], -face_u[cell+1], work[cell]):
                cell_u_prefix[cell].add(term)
            checks["cell_energy_prefix"].observe((after_u[cell], -initial_u[cell],
                *(-term for term in cell_u_prefix[cell].terms())),
                ResidualLocation(step_index, times[0], end, cell_index=cell))
            for quantity, weights, element in measures:
                source_location = ResidualLocation(step_index, start, end, cell_index=cell, element_id=element)
                checks[f"reaction_{quantity}_cell_step"].observe(
                    (_product(weights[k], reaction[cell][k]) for k in range(species)), source_location)

        for k, name in enumerate(basis.species_order):
            boundary_prefix[k].add(face_n[0][k])
            boundary_prefix[k].add(-face_n[-1][k])
            for row in reaction:
                reaction_prefix[k].add(row[k])
            delta_terms = [term for cell in range(cells) for term in (after_n[cell][k], -before_n[cell][k])]
            checks["system_species_step"].observe((*delta_terms, -face_n[0][k], face_n[-1][k],
                *(-row[k] for row in reaction)), ResidualLocation(step_index, start, end, species_id=name))
            prefix_terms = [term for cell in range(cells) for term in (after_n[cell][k], -initial_n[cell][k])]
            checks["system_species_prefix"].observe((*prefix_terms,
                *(-term for term in boundary_prefix[k].terms()),
                *(-term for term in reaction_prefix[k].terms())),
                ResidualLocation(step_index, times[0], end, species_id=name))

        # Form representable per-species changes before multiplying by mass or
        # atom weights, so multiplication of a huge absolute inventory cannot
        # erase an otherwise resolvable small change.
        changes = [[_exact_sum((after_n[i][k], -before_n[i][k])) for k in range(species)] for i in range(cells)]
        prefix_changes = [[_exact_sum((after_n[i][k], -initial_n[i][k])) for k in range(species)] for i in range(cells)]
        for quantity, weights, element in measures:
            terms = [_product(weights[k], row[k]) for row in changes for k in range(species)]
            terms.extend(term for k in range(species) for term in (
                -_product(weights[k], face_n[0][k]), _product(weights[k], face_n[-1][k])))
            checks[f"system_{quantity}_step"].observe(terms,
                ResidualLocation(step_index, start, end, element_id=element))
            terms = [_product(weights[k], row[k]) for row in prefix_changes for k in range(species)]
            terms.extend(-_product(weights[k], term) for k in range(species) for term in boundary_prefix[k].terms())
            checks[f"system_{quantity}_prefix"].observe(terms,
                ResidualLocation(step_index, times[0], end, element_id=element))

        for term in (face_u[0], -face_u[-1], *work):
            energy_prefix.add(term)
        energy_changes = [term for i in range(cells) for term in (after_u[i], -before_u[i])]
        checks["system_energy_step"].observe((*energy_changes, -face_u[0], face_u[-1], *(-v for v in work)), location)
        prefix_energy_changes = [term for i in range(cells) for term in (after_u[i], -initial_u[i])]
        checks["system_energy_prefix"].observe((*prefix_energy_changes, *(-v for v in energy_prefix.terms())), prefix_location)
        before_n, before_u = after_n, after_u

    summaries = {name: check.result() for name, check in checks.items()}
    status = "not_evaluated_no_steps" if not ledgers else "passed" if all(c.passed for c in summaries.values()) else "failed"
    return ConservationReport(status, result.status, len(ledgers), basis.species_order, basis.element_order,
                              policy, MappingProxyType(summaries), _inventory(initial_n, initial_u, basis),
                              _inventory(before_n, before_u, basis), basis)
