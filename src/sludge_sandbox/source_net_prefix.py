"""Checked affine source-prefix arithmetic; no physical stage/event permission."""
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction as F
import math
import numpy as np
from .exact_event_clock import ExactEventTime as T
from .exact_integration import ExactStepLedger
from .exact_terminal_panel import affine_integral, affine_integral_value, affine_update
from .integration import ConservedState, IntegrationPolicy, IntegrationError
from .source_net_panel import SourceAffinePanel
from .source_wet_column import ColumnFaceIntegral, LiquidColumnFaceIntegral, ColumnFaceRate, LiquidColumnFaceRate


def require(ok, reason):
    if not ok:
        raise IntegrationError(reason)


def _same(a, b):
    """Compare rebuilt records including array values and exact scalar types."""
    if type(a) is not type(b):
        return False
    if isinstance(a, np.ndarray):
        return a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes()
    if is_dataclass(a):
        return all(_same(getattr(a, f.name), getattr(b, f.name)) for f in fields(a))
    if isinstance(a, Mapping):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, tuple):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def _bounded(values, tolerance, name):
    require(all(abs(v) <= F(tolerance) for v in values), name)


@dataclass(frozen=True)
class SourcePrefix:
    panel: SourceAffinePanel
    end: T
    policy: IntegrationPolicy
    policy_binding: tuple
    ledger: ExactStepLedger
    raw_state: ConservedState
    # Rows are (component name, exact flattened tuple, signed projection tuple).
    integrals: tuple
    state_roundoff_mol: tuple[F, ...]
    state_roundoff_j: tuple[F, ...]
    full_residual_mol: tuple[F, ...]
    full_residual_j: tuple[F, ...]
    minima: tuple
    face_diagnostics: tuple[ColumnFaceIntegral, ...]
    # Strict interior sign change of affine J only. Endpoint zeros are excluded;
    # an empty tuple does not certify physical donor consistency.
    liquid_direction_reversal_faces: tuple[int, ...]
    status: str
    qualification: str = 'numerical_prefix_only_no_stage_event_or_wet_state_permission'

    def check(self) -> None:
        require(type(self.policy) is IntegrationPolicy and
                _same(self.policy_binding, tuple((f.name, getattr(self.policy, f.name))
                                                for f in fields(self.policy))),
                'source_prefix_original_policy_binding')
        rebuilt = build_source_prefix(self.panel, self.end, policy=self.policy)
        require(_same(self, rebuilt), 'source_prefix_derived_content_changed')


def _diagnostics(panel, h, hm):
    """Exact affine integrals of original represented face observations."""
    output, reversals = [], []
    left = panel.first.evaluation.source_evaluation.faces
    right = panel.interior.evaluation.source_evaluation.faces
    def number(x):
        require(type(x) in (float, F) and (type(x) is F or math.isfinite(x)),
                'finite_source_face_diagnostic_required')
        return F(x)
    def integral(x, y):
        x, y = number(x), number(y)
        return affine_integral_value(x, y, h, hm)
    for a, b in zip(left, right):
        require(type(a) in (ColumnFaceRate, LiquidColumnFaceRate) and type(a) is type(b),
                'source_face_diagnostic_schema_changed')
        gas = tuple(integral(x, y) for x, y in zip(a.gas_mol_s, b.gas_mol_s))
        diff = tuple(integral(x, y) for x, y in zip(a.diffusive_enthalpy_w, b.diffusive_enthalpy_w))
        adv = tuple(integral(x, y) for x, y in zip(a.advective_enthalpy_w, b.advective_enthalpy_w))
        require(len(gas) == len(diff) == len(adv) == 3
                and len(a.diffusive_enthalpy_w) == len(b.diffusive_enthalpy_w) == 3
                and len(a.advective_enthalpy_w) == len(b.advective_enthalpy_w) == 3,
                'source_face_diagnostic_shape')
        q = integral(a.energy_w, b.energy_w)
        conduction = integral(a.conduction_w, b.conduction_w)
        residual = q-conduction-sum(diff, F())-sum(adv, F())
        values = dict(face_id=a.face_id, gas_mol=gas, energy_j=q,
                      conduction_j=conduction, diffusive_enthalpy_j=diff,
                      advective_enthalpy_j=adv, energy_decomposition_roundoff_j=residual)
        if type(a) is LiquidColumnFaceRate:
            liquid_h = integral(a.liquid_enthalpy_w, b.liquid_enthalpy_w)
            values['energy_decomposition_roundoff_j'] -= liquid_h
            output.append(LiquidColumnFaceIntegral(**values,
                liquid_mol=integral(a.liquid_mol_s, b.liquid_mol_s),
                liquid_enthalpy_j=liquid_h,
                liquid_enthalpy_projection_j=integral(a.liquid_enthalpy_projection_w,
                                                     b.liquid_enthalpy_projection_w)))
            initial = number(a.liquid_mol_s)
            final = initial+(number(b.liquid_mol_s)-initial)*h/hm
            if initial*final < 0:
                reversals.append(a.face_id)
        else:
            output.append(ColumnFaceIntegral(**values))
    return tuple(output), tuple(reversals)


def build_source_prefix(panel: SourceAffinePanel, end: T, *, policy: IntegrationPolicy) -> SourcePrefix:
    require(type(panel) is SourceAffinePanel and type(policy) is IntegrationPolicy,
            'explicit_source_panel_policy_required')
    panel.check()
    policy.__post_init__()
    start = panel.first.evaluation.time
    require(type(end) is T and start < end <= panel.upper, 'source_prefix_exact_interval')
    h, hm = end.elapsed_since(start), panel.interior.evaluation.time.elapsed_since(start)
    require(all(p.initial > 0 for p in panel.inventories), 'source_prefix_zero_initial_unsupported')
    minima = tuple((p.family, p.cell, p.index, *p.minimum(h)) for p in panel.inventories)
    require(all(row[3] >= 0 for row in minima), 'source_prefix_negative_inventory_minimum')
    a, b = panel.first.evaluation.rates, panel.interior.evaluation.rates
    n = len(panel.fixed_dry_mass_kg)
    names = ('face_species_mol_s', 'face_energy_w', 'reaction_species_mol_s', 'cell_power_w')
    arrays, records = [], []
    for name in names:
        if name == 'reaction_species_mol_s':
            # One shared phase projection, with exact opposite liquid/vapor signs.
            phase, exact_phase = affine_integral(a.reaction_species_mol_s[:, 3],
                                                b.reaction_species_mol_s[:, 3], h, hm)
            array = np.zeros((n, 4)); array[:, 0] = -phase; array[:, 3] = phase
            exact = tuple(v for x in exact_phase for v in (-x, F(), F(), x))
        else:
            array, exact = affine_integral(getattr(a, name), getattr(b, name), h, hm)
        errors = tuple(F(float(v))-x for v, x in zip(array.flat, exact))
        tolerance = policy.energy_absolute_tolerance_j if name in ('face_energy_w', 'cell_power_w') else policy.amount_absolute_tolerance_mol
        _bounded(errors, tolerance, 'source_prefix_integral_roundoff_budget:'+name)
        arrays.append(array); records.append((name, exact, errors))
    fn, fu, rn, work = arrays
    before = panel.first.state
    amounts, amount_errors = affine_update(before.amounts_mol, (fn[:-1], -fn[1:], rn), policy.amount_absolute_tolerance_mol)
    energy, energy_errors = affine_update(before.internal_energy_j, (fu[:-1], -fu[1:], work), policy.energy_absolute_tolerance_j)
    require(np.all(amounts >= 0), 'source_prefix_represented_inventory_negative')
    full_amount = tuple(F(float(x))-(p.initial+p.linear*h+p.quadratic*h*h)
                        for x, p in zip(amounts.flat, panel.inventories))
    full_energy = tuple(F(float(x))-(p.initial+p.linear*h+p.quadratic*h*h)
                        for x, p in zip(energy.flat, panel.energies))
    _bounded(full_amount, policy.amount_absolute_tolerance_mol, 'source_prefix_full_inventory_budget')
    _bounded(full_energy, policy.energy_absolute_tolerance_j, 'source_prefix_full_energy_budget')
    diagnostics, reversals = _diagnostics(panel, h, hm)
    _bounded(tuple(f.energy_decomposition_roundoff_j for f in diagnostics),
             policy.energy_absolute_tolerance_j, 'source_prefix_energy_decomposition_budget')
    _bounded(tuple(f.liquid_enthalpy_projection_j for f in diagnostics if type(f) is LiquidColumnFaceIntegral),
             policy.energy_absolute_tolerance_j, 'source_prefix_liquid_enthalpy_projection_budget')
    raw = ConservedState(amounts, energy, before.energy_model_identity)
    ledger = ExactStepLedger(start, end, fn, fu, rn, work)
    status = 'numerical_boundary' if any(row[3] == 0 for row in minima) or np.any(amounts == 0) else 'strictly_positive_numerical_prefix'
    return SourcePrefix(panel, end, policy, tuple((f.name, getattr(policy, f.name)) for f in fields(policy)),
                        ledger, raw, tuple(records), amount_errors,
                        energy_errors, full_amount, full_energy, minima, diagnostics, reversals, status)


@dataclass(frozen=True)
class SourcePrefixAudit:
    prefixes: tuple[SourcePrefix, ...]
    cumulative_inventory_exchange_mol: tuple[F, ...]
    cumulative_energy_exchange_j: tuple[F, ...]
    inventory_residual_mol: tuple[F, ...]
    energy_residual_j: tuple[F, ...]
    cumulative_exact_inventory_exchange_mol: tuple[F, ...]
    cumulative_exact_energy_exchange_j: tuple[F, ...]
    full_inventory_residual_mol: tuple[F, ...]
    full_energy_residual_j: tuple[F, ...]
    qualification: str = 'arithmetic_contiguity_only_not_trajectory_or_event_acceptance'

    def check(self) -> None:
        require(_same(self, audit_source_prefixes(self.prefixes)), 'source_prefix_audit_changed')


def audit_source_prefixes(prefixes: tuple[SourcePrefix, ...]) -> SourcePrefixAudit:
    """Gate signed represented accumulation and, separately, full exact residual.

    The first gate mirrors integrate_exact; the second additionally includes
    integral projection errors. Neither gate is a sum of absolute error costs.
    """
    require(type(prefixes) is tuple and bool(prefixes), 'nonempty_source_prefix_tuple')
    initial = None
    total_n = total_u = exact_n = exact_u = None
    previous = None
    for prefix in prefixes:
        require(type(prefix) is SourcePrefix, 'actual_source_prefix_required')
        prefix.check()
        if previous is None:
            initial = prefix.panel.first.state
            total_n = [F() for _ in initial.amounts_mol.flat]
            total_u = [F() for _ in initial.internal_energy_j.flat]
            exact_n = [F() for _ in initial.amounts_mol.flat]
            exact_u = [F() for _ in initial.internal_energy_j.flat]
        else:
            require(previous.end == prefix.panel.first.evaluation.time
                    and _same(previous.raw_state, prefix.panel.first.state)
                    and _same(previous.policy, prefix.policy)
                    and _same(previous.panel.operator_identity, prefix.panel.operator_identity)
                    and _same(previous.panel.energy_identity, prefix.panel.energy_identity)
                    and _same(previous.panel.fixed_dry_mass_kg, prefix.panel.fixed_dry_mass_kg),
                    'source_prefix_contiguity_binding')
        ledger = prefix.ledger
        components = {name: exact for name, exact, errors in prefix.integrals}
        fn = components['face_species_mol_s']; rn = components['reaction_species_mol_s']
        fu = components['face_energy_w']; work = components['cell_power_w']
        for i, j in np.ndindex(initial.amounts_mol.shape):
            total_n[i*4+j] += F(float(ledger.face_species_mol[i,j]))-F(float(ledger.face_species_mol[i+1,j]))+F(float(ledger.reaction_species_mol[i,j]))
            exact_n[i*4+j] += fn[i*4+j]-fn[(i+1)*4+j]+rn[i*4+j]
        for i in range(len(total_u)):
            total_u[i] += F(float(ledger.face_energy_j[i]))-F(float(ledger.face_energy_j[i+1]))+F(float(ledger.cell_work_j[i]))
            exact_u[i] += fu[i]-fu[i+1]+work[i]
        nr = tuple(F(float(x))-F(float(y))-v for x,y,v in zip(prefix.raw_state.amounts_mol.flat,initial.amounts_mol.flat,total_n))
        ur = tuple(F(float(x))-F(float(y))-v for x,y,v in zip(prefix.raw_state.internal_energy_j,initial.internal_energy_j,total_u))
        _bounded(nr, prefix.policy.amount_absolute_tolerance_mol, 'source_prefix_cumulative_inventory_budget')
        _bounded(ur, prefix.policy.energy_absolute_tolerance_j, 'source_prefix_cumulative_energy_budget')
        full_nr = tuple(F(float(x))-F(float(y))-v for x,y,v in zip(prefix.raw_state.amounts_mol.flat,initial.amounts_mol.flat,exact_n))
        full_ur = tuple(F(float(x))-F(float(y))-v for x,y,v in zip(prefix.raw_state.internal_energy_j,initial.internal_energy_j,exact_u))
        _bounded(full_nr, prefix.policy.amount_absolute_tolerance_mol, 'source_prefix_cumulative_full_inventory_budget')
        _bounded(full_ur, prefix.policy.energy_absolute_tolerance_j, 'source_prefix_cumulative_full_energy_budget')
        previous = prefix
    return SourcePrefixAudit(prefixes, tuple(total_n), tuple(total_u), nr, ur,
                             tuple(exact_n), tuple(exact_u), full_nr, full_ur)
