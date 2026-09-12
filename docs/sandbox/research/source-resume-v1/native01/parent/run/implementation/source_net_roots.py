"""Pure first zeros of saved source inventory quadratics; no event permission.

Net liquid drainage need not be evaporation. These numerical records neither
permit correction/writeback nor infer dry transport, rewetting or a physical
trajectory from a fitted panel. Zero-initial inventory requires separate work.
"""
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction as F
from .mass_wet_exact_stage import InventoryPolynomial
from .rational_polynomial import refine_descending_bracket, polynomial_gcd
from .source_net_panel import SourceAffinePanel
from .exact_event_clock import ExactEventTime


class SourceNetRootError(ValueError):
    """Invalid exact polynomial evidence or an altered saved record."""


def _need(ok, reason):
    if not ok:
        raise SourceNetRootError(reason)


def _same(a, b):
    """Evidence equality includes types: zero is not False or Fraction(0)."""
    if type(a) is not type(b):
        return False
    if is_dataclass(b):
        return all(_same(getattr(a, f.name), getattr(b, f.name)) for f in fields(b))
    if type(b) is tuple:
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def _validate_polynomial(p, duration, *, allow_zero=False):
    _need(type(p) is InventoryPolynomial, 'actual_inventory_polynomial_required')
    _need(p.family in ('liquid', 'gas') and type(p.family) is str,
          'only_liquid_gas_inventory_roots')
    _need(type(p.cell) is int and p.cell >= 0 and type(p.index) is int and p.index >= 0,
          'explicit_inventory_label')
    _need(type(duration) is F and duration > 0, 'exact_positive_root_duration')
    _need(all(type(v) is F for v in (p.initial, p.linear, p.quadratic)),
          'exact_polynomial_coefficients')
    _need(p.initial >= 0 if allow_zero else p.initial > 0,
          'positive_initial_inventory_required')


def _value(p, t):
    return p.initial + p.linear*t + p.quadratic*t*t


def _coefficients(p):
    return (p.initial, p.linear, p.quadratic)


def _isolation(p, duration):
    """Recompute the first descending branch, or its exact point root."""
    _validate_polynomial(p, duration)
    minimum, when = p.minimum(duration)
    if minimum > 0:
        return None
    n, r, q = _coefficients(p)
    if q == 0:
        _need(r < 0, 'linear_root_requires_descent')
        root = -n/r
        _need(0 < root <= duration, 'linear_root_outside_domain')
        return ('exact_endpoint' if root == duration else 'exact_crossing', root, root)
    vertex = -r/(2*q)
    if q > 0:
        # Tangency takes precedence over endpoint location. Do not shortcut a
        # second returning root at H into the first-root endpoint record.
        if 0 < vertex <= duration and _value(p, vertex) == 0:
            return ('exact_tangent', vertex, vertex)
        lower, upper = F(), min(vertex, duration)
    else:
        lower, upper = (vertex if 0 < vertex < duration else F()), duration
    _need(0 <= lower < upper <= duration and _value(p, lower) > 0
          and _value(p, upper) <= 0, 'first_descending_branch_not_bracketed')
    _need(r+2*q*lower <= 0 and r+2*q*upper <= 0,
          'first_branch_not_descending')
    if _value(p, upper) == 0:
        return ('exact_endpoint' if upper == duration else 'exact_crossing', upper, upper)
    return ('crossing', lower, upper)


@dataclass(frozen=True)
class QuadraticNoRoot:
    polynomial: InventoryPolynomial
    duration: F
    minimum: F
    minimum_time: F

    def __post_init__(self):
        self.check()

    def check(self) -> None:
        _validate_polynomial(self.polynomial, self.duration)
        expected = self.polynomial.minimum(self.duration)
        _need(_same((self.minimum, self.minimum_time), expected) and self.minimum > 0,
              'invalid_no_root_evidence')


@dataclass(frozen=True)
class QuadraticRoot:
    polynomial: InventoryPolynomial
    duration: F
    root_kind: str
    branch_lower: F
    branch_upper: F
    lower: F
    upper: F
    refinements: int = 0

    def __post_init__(self):
        self.check()

    def check(self) -> None:
        initial = _isolation(self.polynomial, self.duration)
        _need(initial is not None, 'root_record_for_excluded_polynomial')
        _need(type(self.refinements) is int and 0 <= self.refinements <= 256,
              'bounded_root_refinements_required')
        kind, lo, hi = initial
        _need(_same((self.root_kind, self.branch_lower, self.branch_upper), initial),
              'altered_first_root_branch')
        _need(lo != hi or self.refinements == 0, 'point_root_has_no_refinements')
        for _ in range(self.refinements):
            lo, hi = refine_descending_bracket(_coefficients(self.polynomial), lo, hi)
        _need(_same((self.lower, self.upper), (lo, hi)), 'altered_root_enclosure')


def isolate_first_root(polynomial: InventoryPolynomial, duration: F) -> QuadraticRoot | QuadraticNoRoot:
    """Pure first-zero evidence for a positive initial mol inventory."""
    branch = _isolation(polynomial, duration)
    if branch is None:
        return QuadraticNoRoot(polynomial, duration, *polynomial.minimum(duration))
    kind, lo, hi = branch
    return QuadraticRoot(polynomial, duration, kind, lo, hi, lo, hi)


def refine_first_root(record: QuadraticRoot) -> QuadraticRoot:
    _need(type(record) is QuadraticRoot, 'actual_root_record_required')
    record.check()
    if record.lower == record.upper:
        return record
    _need(record.refinements < 256, 'root_refinement_budget_exhausted')
    lo, hi = refine_descending_bracket(_coefficients(record.polynomial), record.lower, record.upper)
    return QuadraticRoot(record.polynomial, record.duration, record.root_kind,
                         record.branch_lower, record.branch_upper, lo, hi, record.refinements+1)


def same_first_root(left: QuadraticRoot, right: QuadraticRoot) -> bool:
    """Common polynomial roots must lie in both certified first branches."""
    _need(type(left) is QuadraticRoot and type(right) is QuadraticRoot,
          'actual_root_records_required')
    left.check(); right.check()
    gcd = polynomial_gcd(_coefficients(left.polynomial), _coefficients(right.polynomial))
    if len(gcd) == 3:
        # Proportional quadratics, each independently validated as first root.
        return True
    if len(gcd) != 2:
        return False
    root = -gcd[0]/gcd[1]
    return all(r.branch_lower <= root <= r.branch_upper and r.lower <= root <= r.upper
               and _value(r.polynomial, root) == 0 for r in (left, right))


def _label(p):
    return (p.family, p.cell, p.index)


@dataclass(frozen=True)
class InventoryRootOrder:
    polynomials: tuple[InventoryPolynomial, ...]
    duration: F
    maximum_refinements: int
    status: str
    roots: tuple[QuadraticRoot, ...]
    exclusions: tuple[QuadraticNoRoot, ...]
    earliest_labels: tuple
    zero_initial_labels: tuple
    refinement_level: int
    complete: bool
    qualification: str = 'numerical_first_zero_order_not_physical_event_admission'

    def check(self) -> None:
        expected = order_inventory_roots(self.polynomials, self.duration,
                                         maximum_refinements=self.maximum_refinements)
        _need(_same(self, expected), 'altered_inventory_root_order')


def order_inventory_roots(polynomials: tuple[InventoryPolynomial, ...], duration: F,
                          *, maximum_refinements: int = 256) -> InventoryRootOrder:
    """All declared positive liquid/gas inventories compete, including ties.

    A zero-initial inventory makes this route incomplete; it is never omitted
    as a no-root inventory. Unresolved ordering retains every current bracket.
    """
    _need(type(polynomials) is tuple and bool(polynomials), 'complete_inventory_tuple_required')
    _need(type(maximum_refinements) is int and 1 <= maximum_refinements <= 256,
          'bounded_root_refinements_required')
    for p in polynomials:
        _validate_polynomial(p, duration, allow_zero=True)
    _need(len(set(map(_label, polynomials))) == len(polynomials), 'duplicate_inventory_labels')
    zero = tuple(_label(p) for p in polynomials if p.initial == 0)
    records = tuple(isolate_first_root(p, duration) for p in polynomials if p.initial > 0)
    roots = tuple(r for r in records if type(r) is QuadraticRoot)
    exclusions = tuple(r for r in records if type(r) is QuadraticNoRoot)
    def output(status, selected=(), level=0, complete=True):
        return InventoryRootOrder(polynomials, duration, maximum_refinements, status,
                                  roots, exclusions, selected, zero, level, complete)
    if zero:
        return output('unsupported_zero_initial', complete=False)
    if not roots:
        return output('no_roots')
    for level in range(maximum_refinements+1):
        first = min(roots, key=lambda r: r.lower)
        group = tuple(r for r in roots if same_first_root(first, r))
        outside = tuple(r for r in roots if r not in group)
        if all(first.upper < other.lower for other in outside):
            selected = tuple(_label(r.polynomial) for r in group)
            return output('tied' if len(group) > 1 else 'ordered', selected, level)
        if level == maximum_refinements:
            return output('unresolved', level=level, complete=False)
        roots = tuple(refine_first_root(r) for r in roots)
    raise AssertionError('unreachable_refinement_loop')


@dataclass(frozen=True)
class SourcePanelRootOrder:
    panel: SourceAffinePanel
    start: ExactEventTime
    upper: ExactEventTime
    operator_identity: tuple
    sample_bindings: tuple
    order: InventoryRootOrder
    qualification: str = 'saved_source_panel_roots_not_event_or_writeback_permission'

    def check(self) -> None:
        _need(type(self.panel) is SourceAffinePanel, 'actual_source_panel_required')
        _need(type(self.order) is InventoryRootOrder, 'actual_inventory_root_order_required')
        self.panel.check()
        expected = order_source_panel_roots(self.panel,
                    maximum_refinements=self.order.maximum_refinements)
        # The live panel is revalidated above; compare only its saved bindings,
        # rather than ndarray-containing dataclass equality on the panel itself.
        _need(all(_same(getattr(self, name), getattr(expected, name)) for name in
                  ('start', 'upper', 'operator_identity', 'sample_bindings', 'order', 'qualification')),
              'altered_source_panel_root_order')


def order_source_panel_roots(panel: SourceAffinePanel, *, maximum_refinements: int = 256) -> SourcePanelRootOrder:
    _need(type(panel) is SourceAffinePanel, 'actual_source_panel_required')
    panel.check()
    start, upper = panel.first.evaluation.time, panel.upper
    expected_labels = tuple(('liquid' if j == 0 else 'gas', i, j)
                            for i in range(len(panel.fixed_dry_mass_kg)) for j in range(4))
    _need(tuple(map(_label, panel.inventories)) == expected_labels, 'all_source_fluid_inventories_required')
    order = order_inventory_roots(panel.inventories, upper.elapsed_since(start),
                                   maximum_refinements=maximum_refinements)
    return SourcePanelRootOrder(panel, start, upper, panel.operator_identity, panel.sample_bindings, order)
