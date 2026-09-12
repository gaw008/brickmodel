"""Exact affine-inventory certificates; no physical host or mode-switch admission.

Time coefficients use elapsed seconds from the declared origin. This explicit
manufactured model has zero polynomial remainder; samples alone cannot admit it.
"""
from dataclasses import dataclass
from fractions import Fraction
import math


class GroupClockError(ValueError):
    """Invalid model, enclosure, or insufficient root resolution."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise GroupClockError(reason)


def _fraction(value: Fraction, name: str) -> None:
    _require(type(value) is Fraction, 'exact_fraction_required:' + name)


@dataclass(frozen=True)
class AffineInventory:
    cell_index: int
    initial_mol: Fraction
    rate_mol_s: Fraction
    acceleration_mol_s2: Fraction

    def __post_init__(self) -> None:
        _require(type(self.cell_index) is int and self.cell_index >= 0, 'cell_index')
        for name in ('initial_mol', 'rate_mol_s', 'acceleration_mol_s2'):
            _fraction(getattr(self, name), name)
        _require(self.initial_mol > 0, 'positive_initial_inventory')

    def amount(self, elapsed_s: Fraction) -> Fraction:
        _fraction(elapsed_s, 'elapsed_s')
        return self.initial_mol + self.rate_mol_s * elapsed_s + self.acceleration_mol_s2 * elapsed_s**2 / 2

    def minimum(self, end_s: Fraction) -> Fraction:
        _fraction(end_s, 'end_s')
        _require(end_s >= 0, 'nonnegative_panel')
        values = [self.initial_mol, self.amount(end_s)]
        if self.acceleration_mol_s2 > 0:
            vertex = -self.rate_mol_s / self.acceleration_mol_s2
            if 0 < vertex < end_s:
                values.append(self.amount(vertex))
        return min(values)


@dataclass(frozen=True)
class AffineDomain:
    start_s: Fraction
    duration_s: Fraction
    cell_count: int
    inventories: tuple[AffineInventory, ...]

    def __post_init__(self) -> None:
        _fraction(self.start_s, 'start_s')
        _fraction(self.duration_s, 'duration_s')
        _require(self.duration_s > 0, 'positive_duration')
        _require(type(self.cell_count) is int and self.cell_count > 0, 'cell_count')
        _require(type(self.inventories) is tuple and len(self.inventories) == self.cell_count,
                 'complete_immutable_inventory_set')
        _require(all(type(p) is AffineInventory for p in self.inventories), 'explicit_affine_model')
        _require(sorted(p.cell_index for p in self.inventories) == list(range(self.cell_count)),
                 'complete_unique_cell_indices')


@dataclass(frozen=True)
class RootInterval:
    cell_index: int
    lower_s: Fraction
    upper_s: Fraction

    def __post_init__(self) -> None:
        _require(type(self.cell_index) is int and self.cell_index >= 0, 'root_cell_index')
        _fraction(self.lower_s, 'lower_s')
        _fraction(self.upper_s, 'upper_s')
        _require(0 <= self.lower_s <= self.upper_s, 'ordered_elapsed_root_interval')


@dataclass(frozen=True)
class RootGroup:
    members: tuple[int, ...]
    lower_s: Fraction
    upper_s: Fraction
    status: str


@dataclass(frozen=True)
class RootAnalysis:
    roots: tuple[RootInterval, ...]
    no_depletion_cells: tuple[int, ...]
    groups: tuple[RootGroup, ...]
    strict_order_edges: tuple[tuple[int, int], ...]


def _descent_end(model: AffineInventory, duration: Fraction) -> Fraction:
    if model.acceleration_mol_s2 > 0 and model.rate_mol_s < 0:
        return min(duration, -model.rate_mol_s / model.acceleration_mol_s2)
    return duration


def positive_panel(domain: AffineDomain, end_s: Fraction) -> tuple[Fraction, ...]:
    """Return per-cell strict lower minima on [0,end]; reject any touched root."""
    _require(type(domain) is AffineDomain, 'explicit_domain')
    _fraction(end_s, 'panel_end')
    _require(0 <= end_s <= domain.duration_s, 'panel_within_domain')
    minima = tuple(p.minimum(end_s) for p in sorted(domain.inventories, key=lambda p: p.cell_index))
    _require(all(value > 0 for value in minima), 'panel_not_strictly_positive')
    return minima


def isolate_roots(domain: AffineDomain, width_s: Fraction, *, maximum_bisections: int = 256) -> tuple[RootInterval, ...]:
    """Enclose every first zero in the declared domain using exact sign tests."""
    _require(type(domain) is AffineDomain, 'explicit_domain')
    _fraction(width_s, 'width_s')
    _require(width_s > 0 and type(maximum_bisections) is int and maximum_bisections > 0,
             'positive_resolution_budget')
    roots = []
    for model in domain.inventories:
        lo, hi = Fraction(0), _descent_end(model, domain.duration_s)
        if model.minimum(hi) > 0:
            continue
        if model.amount(hi) == 0:
            lo = hi
        else:
            for _ in range(maximum_bisections):
                if hi - lo <= width_s:
                    break
                mid = (lo + hi) / 2
                value = model.amount(mid)
                if value == 0:
                    lo = hi = mid
                    break
                if value > 0:
                    lo = mid
                else:
                    hi = mid
            _require(hi - lo <= width_s, 'root_resolution_budget_exhausted')
        roots.append(RootInterval(model.cell_index, lo, hi))
    return tuple(sorted(roots, key=lambda r: (r.lower_s, r.upper_s, r.cell_index)))


def group_roots(domain: AffineDomain, roots: tuple[RootInterval, ...], time_gate_s: Fraction) -> RootAnalysis:
    """Recheck complete first-root enclosures; cluster using union, never intersection."""
    _require(type(domain) is AffineDomain and type(roots) is tuple, 'explicit_immutable_roots')
    _fraction(time_gate_s, 'time_gate_s')
    _require(time_gate_s > 0, 'positive_time_gate')
    models = {p.cell_index: p for p in domain.inventories}
    expected = {i for i, p in models.items() if p.minimum(domain.duration_s) <= 0}
    _require(all(type(r) is RootInterval for r in roots), 'typed_root_interval')
    _require(len({r.cell_index for r in roots}) == len(roots) and {r.cell_index for r in roots} == expected,
             'all_first_roots_required_including_earlier_cells')
    for root in roots:
        p = models[root.cell_index]
        _require(root.upper_s <= _descent_end(p, domain.duration_s), 'first_root_branch_domain')
        if root.lower_s == root.upper_s:
            _require(p.amount(root.lower_s) == 0, 'exact_root_proof_required')
        else:
            _require(p.minimum(root.lower_s) > 0 and p.amount(root.upper_s) <= 0,
                     'first_root_sign_certificate')
    ordered = tuple(sorted(roots, key=lambda r: (r.lower_s, r.upper_s, r.cell_index)))
    clusters: list[list[RootInterval]] = []
    for root in ordered:
        if not clusters or root.lower_s - max(r.upper_s for r in clusters[-1]) > time_gate_s:
            clusters.append([root])
        else:
            clusters[-1].append(root)
    groups = []
    for cluster in clusters:
        lo, hi = min(r.lower_s for r in cluster), max(r.upper_s for r in cluster)
        status = ('ordered' if len(cluster) == 1 else 'exact_common_root' if lo == hi
                  else 'unresolved_narrow_cluster' if hi - lo <= time_gate_s else 'unresolved_wide_cluster')
        groups.append(RootGroup(tuple(sorted(r.cell_index for r in cluster)), lo, hi, status))
    edges = tuple((a.cell_index, b.cell_index) for a in ordered for b in ordered if a.upper_s < b.lower_s)
    return RootAnalysis(ordered, tuple(sorted(set(models) - expected)), tuple(groups), edges)


def outward_absolute_times(domain: AffineDomain, root: RootInterval) -> tuple[float, float]:
    """Outward binary64 absolute-time enclosure; rounding never proves exact roots."""
    _require(type(domain) is AffineDomain and type(root) is RootInterval, 'typed_time_inputs')
    _require(root.upper_s <= domain.duration_s, 'time_interval_domain')
    exact = (domain.start_s + root.lower_s, domain.start_s + root.upper_s)
    try:
        lo, hi = map(float, exact)
    except OverflowError as exc:
        raise GroupClockError('unrepresentable_absolute_time') from exc
    if Fraction(lo) > exact[0]:
        lo = math.nextafter(lo, -math.inf)
    if Fraction(hi) < exact[1]:
        hi = math.nextafter(hi, math.inf)
    _require(math.isfinite(lo) and math.isfinite(hi), 'unrepresentable_absolute_time')
    return lo, hi
