"""Atomic accounting for explicit exact-common-root affine terminal panels only.

No mode switch, physical localization, or wet-host admission is performed.
Nonrepresentable shared event clocks are deliberately unsupported.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import math
import numpy as np
from .depletion_group_clock import AffineDomain, RootInterval, group_roots
from .depletion_roundoff import DepletionRoundoffPolicy, DepletionRoundoffTotals, depletion_writeback
from .integration import ConservedState, StepLedger


class GroupRoundoffError(ValueError):
    """Unproved group membership, panel binding, or unsupported shared clock."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise GroupRoundoffError(reason)


@dataclass(frozen=True)
class GroupMember:
    cell_index: int
    positive_evaporated_mol: float

    def __post_init__(self) -> None:
        _require(type(self.cell_index) is int and self.cell_index >= 0, 'member_index')
        v = self.positive_evaporated_mol
        _require(type(v) in (int, float), 'finite_nonnegative_gross_evaporation')
        try:
            finite = math.isfinite(v)
        except OverflowError as exc:
            raise GroupRoundoffError('unrepresentable_gross_evaporation') from exc
        _require(finite and v >= 0, 'finite_nonnegative_gross_evaporation')


@dataclass(frozen=True)
class AffineLiquidTerms:
    """Signed left face, negative right face, source rates for one cell."""
    cell_index: int
    start_rates_mol_s: tuple[F, F, F]
    accelerations_mol_s2: tuple[F, F, F]

    def __post_init__(self) -> None:
        _require(type(self.cell_index) is int and self.cell_index >= 0, 'affine_terms_cell')
        for values in (self.start_rates_mol_s, self.accelerations_mol_s2):
            _require(type(values) is tuple and len(values) == 3 and all(type(v) is F for v in values),
                     'exact_affine_component_triples')


def _affine_panel(domain, panel, terms, elapsed, liquid_index):
    _require(type(terms) is tuple and all(type(t) is AffineLiquidTerms for t in terms), 'explicit_affine_terms')
    _require(len(terms) == domain.cell_count and sorted(t.cell_index for t in terms) == list(range(domain.cell_count)),
             'complete_affine_terms')
    by_cell = {t.cell_index: t for t in terms}
    for model in domain.inventories:
        i = model.cell_index
        component = by_cell[i]
        _require(sum(component.start_rates_mol_s, F()) == model.rate_mol_s
                 and sum(component.accelerations_mol_s2, F()) == model.acceleration_mol_s2,
                 'affine_model_component_binding')
        actual = (float(panel.face_species_mol[i, liquid_index]),
                  -float(panel.face_species_mol[i+1, liquid_index]),
                  float(panel.reaction_species_mol[i, liquid_index]))
        expected = tuple(float(r*elapsed+a*elapsed**2/2)
                         for r, a in zip(component.start_rates_mol_s, component.accelerations_mol_s2))
        _require(actual == expected, 'affine_component_quadrature_binding')
        if i+1 < domain.cell_count:
            following = by_cell[i+1]
            _require(component.start_rates_mol_s[1] == -following.start_rates_mol_s[0]
                     and component.accelerations_mol_s2[1] == -following.accelerations_mol_s2[0],
                     'affine_shared_face_binding')


@dataclass(frozen=True)
class GroupWriteback:
    state: ConservedState
    corrections: tuple
    totals: DepletionRoundoffTotals
    members: tuple[int, ...]
    event_time_s: float
    qualification: str = 'exact_affine_common_root_accounting_only_no_mode_switch'


def _panel_binding(initial: ConservedState, raw: ConservedState, panel: StepLedger) -> None:
    _require(initial.amounts_mol.shape == raw.amounts_mol.shape, 'state_shape')
    _require(initial.energy_model_identity == raw.energy_model_identity, 'energy_identity')
    cells, columns = initial.amounts_mol.shape
    _require(panel.face_species_mol.shape == (cells+1, columns)
             and panel.reaction_species_mol.shape == (cells, columns)
             and panel.face_energy_j.shape == (cells+1,)
             and panel.cell_work_j.shape == (cells,), 'panel_shape')
    for i, j in np.ndindex(initial.amounts_mol.shape):
        value = F(float(initial.amounts_mol[i, j])) + F(float(panel.face_species_mol[i, j])) - F(float(panel.face_species_mol[i+1, j])) + F(float(panel.reaction_species_mol[i, j]))
        _require(float(value) == raw.amounts_mol[i, j], 'raw_inventory_panel_binding')
    for i in range(cells):
        value = F(float(initial.internal_energy_j[i])) + F(float(panel.face_energy_j[i])) - F(float(panel.face_energy_j[i+1])) + F(float(panel.cell_work_j[i]))
        _require(float(value) == raw.internal_energy_j[i], 'raw_energy_panel_binding')
    if initial.mechanical_stretches is None:
        _require(raw.mechanical_stretches is None and panel.stretch_increment is None, 'mechanical_schema')
    else:
        _require(raw.mechanical_stretches is not None and panel.stretch_increment is not None
                 and initial.mechanical_stretches.shape == raw.mechanical_stretches.shape == panel.stretch_increment.shape,
                 'mechanical_schema')
        expected = [float(F(float(x))+F(float(d))) for x, d in zip(initial.mechanical_stretches, panel.stretch_increment)]
        _require(np.array_equal(expected, raw.mechanical_stretches), 'raw_mechanical_panel_binding')


def writeback_exact_group(initial: ConservedState, raw: ConservedState, panel: StepLedger, *,
                          domain: AffineDomain, roots: tuple[RootInterval, ...],
                          members: tuple[GroupMember, ...], liquid_terms: tuple[AffineLiquidTerms, ...], time_gate_s: F,
                          liquid_index: int, vapor_index: int,
                          policy: DepletionRoundoffPolicy, totals: DepletionRoundoffTotals) -> GroupWriteback:
    """Revalidate the earliest complete exact-root group, then write atomically.

    Gross evaporation is a supplied per-member diagnostic, not inferred from net
    removal. This accounting layer cannot certify its physical derivation.
    """
    _require(type(initial) is ConservedState and type(raw) is ConservedState and type(panel) is StepLedger,
             'explicit_state_panel')
    _require(type(policy) is DepletionRoundoffPolicy and type(totals) is DepletionRoundoffTotals
             and totals.policy == policy, 'original_prefix_policy')
    _require(type(members) is tuple and all(type(m) is GroupMember for m in members), 'immutable_members')
    analysis = group_roots(domain, roots, time_gate_s)
    _require(bool(analysis.groups) and analysis.groups[0].status == 'exact_common_root', 'earliest_exact_common_root_required')
    group = analysis.groups[0]
    indices = tuple(sorted(m.cell_index for m in members))
    _require(indices == group.members, 'complete_unique_earliest_members')
    _require(initial.amounts_mol.shape[0] == domain.cell_count, 'complete_domain_cells')
    columns = initial.amounts_mol.shape[1]
    _require(type(liquid_index) is int and type(vapor_index) is int
             and 0 <= liquid_index < columns and 0 <= vapor_index < columns and liquid_index != vapor_index,
             'distinct_valid_phase_columns')
    event = domain.start_s + group.lower_s
    try:
        start_float, end_float = float(domain.start_s), float(event)
    except OverflowError as exc:
        raise GroupRoundoffError('unrepresentable_shared_clock') from exc
    _require(F(start_float) == domain.start_s and F(end_float) == event,
             'nonrepresentable_shared_clock_unsupported')
    _require(panel.start_s == start_float and panel.end_s == end_float and end_float > start_float,
             'shared_terminal_panel_clock')
    _panel_binding(initial, raw, panel)
    _affine_panel(domain, panel, liquid_terms, group.lower_s, liquid_index)
    models = {p.cell_index: p for p in domain.inventories}
    for i, model in models.items():
        _require(F(float(initial.amounts_mol[i, liquid_index])) == model.initial_mol, 'initial_affine_inventory_binding')
        if i not in indices:
            _require(model.minimum(group.lower_s) > 0 and raw.amounts_mol[i, liquid_index] > 0,
                     'nonmember_must_remain_positive')
    # Work only on immutable local results; no caller state/totals is mutated.
    current, accumulated, corrections = raw, totals, []
    for member in sorted(members, key=lambda m: m.cell_index):
        i = member.cell_index
        terms = (float(panel.face_species_mol[i, liquid_index]),
                 -float(panel.face_species_mol[i+1, liquid_index]),
                 float(panel.reaction_species_mol[i, liquid_index]))
        # The model's ideal endpoint is exactly zero. Any represented discrepancy
        # must be local arithmetic roundoff, never a finite timing displacement.
        if current.amounts_mol[i, liquid_index] == 0:
            corrections.append(None)
            continue
        current, correction, accumulated = depletion_writeback(current, cell_index=i,
            liquid_index=liquid_index, vapor_index=vapor_index,
            panel_liquid_start_mol=float(initial.amounts_mol[i, liquid_index]),
            panel_liquid_terms_mol=terms, positive_evaporated_mol=member.positive_evaporated_mol,
            policy=policy, totals=accumulated)
        corrections.append(correction)
    return GroupWriteback(current, tuple(corrections), accumulated, indices, end_float)
