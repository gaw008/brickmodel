"""Manufactured field projections for the pure cross-stage balance auditor.

These are arrays/ledgers with stated residuals, not source evaluations, physical
providers, or SourcePrefixTrial/SourceDryCandidate evidence. SimpleNamespace is
used only to supply the documented already-validated projection fields.
"""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace

import numpy as np
import pytest

from sludge_sandbox.exact_event_clock import ExactEventTime as T
from sludge_sandbox.exact_integration import ExactStepLedger
from sludge_sandbox.integration import ConservedState, IntegrationPolicy
from sludge_sandbox.source_dry_transition import _audit_balance_fields


UNIT = F(1, 2**20)
BUDGET = 5 * UNIT
PREFIX_ERROR = 3 * UNIT  # Exactly 0.6 of the original binary64 budget.
SELECTED = 1


def _ledger(start, end, *, phase=False):
    reaction = np.zeros((3, 4))
    if phase:
        reaction[SELECTED, 0] = -.5
        reaction[SELECTED, 3] = .5
    return ExactStepLedger(T(F(start)), T(F(end)), np.zeros((4, 4)), np.zeros(4),
                           reaction, np.zeros(3))


def _reference(before, after, ledger):
    return SimpleNamespace(states=(before, after), times_s=(ledger.start_s, ledger.end_s),
                           steps=(ledger,))


def _error_state(state, amount_error=F(), energy_error=F()):
    amounts = state.amounts_mol.copy()
    energy = state.internal_energy_j.copy()
    amounts[SELECTED, 1] = float(F(float(amounts[SELECTED, 1])) + amount_error)
    energy[SELECTED] = float(F(float(energy[SELECTED])) + energy_error)
    return replace(state, amounts_mol=amounts, internal_energy_j=energy)


def _projection(quantity, *, ordinary_fraction=F(3, 5)):
    policy = IntegrationPolicy(initial_step_s=1., maximum_step_s=1., minimum_step_s=.125,
        relative_tolerance=1e-8, amount_absolute_tolerance_mol=float(BUDGET),
        energy_absolute_tolerance_j=float(BUDGET), amount_scale_mol=1., energy_scale_j=1.,
        maximum_steps=4, maximum_rejections=4, maximum_wall_seconds=1.)
    amount = PREFIX_ERROR if quantity in ('amount', 'both') else F()
    energy = PREFIX_ERROR if quantity in ('energy', 'both') else F()
    initial = ConservedState(np.array([[.5, 1., 1., .25]] * 3), np.zeros(3),
                             ('manufactured:source-continuation-balance-projection',))
    # An ordinary wet prefix, then an exact half-mole selected-cell transfer.
    wet = _reference(initial, initial, _ledger(0, 1))
    n = initial.amounts_mol.copy()
    n[SELECTED, 0] = 0.
    n[SELECTED, 3] += .5
    terminal_state = _error_state(replace(initial, amounts_mol=n), amount, energy)
    terminal_ledger = _ledger(1, 2, phase=True)
    integrals = tuple((rate_name, tuple(F(float(x)) for x in getattr(terminal_ledger, ledger_name).flat),
                       'manufactured_exact_field_projection') for rate_name, ledger_name in (
        ('face_species_mol_s', 'face_species_mol'), ('reaction_species_mol_s', 'reaction_species_mol'),
        ('face_energy_w', 'face_energy_j'), ('cell_power_w', 'cell_work_j')))
    terminal = SimpleNamespace(raw_state=terminal_state, ledger=terminal_ledger, integrals=integrals)
    # This projected root is exactly zero, so writeback changes neither N nor U.
    corrected = replace(terminal_state)
    dry = _reference(corrected, corrected, _ledger(2, 3))
    ordinary_error = BUDGET * ordinary_fraction
    amount_after = ordinary_error if quantity in ('amount', 'both') else F()
    energy_after = ordinary_error if quantity in ('energy', 'both') else F()
    continued = _error_state(corrected, amount_after, energy_after)
    ordinary = _reference(corrected, continued, _ledger(3, 4))
    kwargs = dict(initial=initial, start=T(F()), policy=policy,
        masses=tuple({'O2': .0319988, 'N2': .0280134, 'H2O': .018015268} for _ in range(3)),
        wet_references=(wet,), terminal_prefix=terminal, corrected_state=corrected,
        selected_cell_index=SELECTED, signed_storage_roundoff_mol=F(), dry_reference=dry)
    return kwargs, ordinary


@pytest.mark.parametrize('quantity', ['amount', 'energy', 'both'])
def test_two_individually_small_residuals_exceed_original_cross_stage_budget(quantity):
    kwargs, ordinary = _projection(quantity)
    prefix = _audit_balance_fields(**kwargs)
    assert [row.phase for row in prefix] == ['wet_reference', 'wet_terminal', 'writeback', 'dry_reference']
    last = prefix[-1]
    amount_local = F(float(ordinary.states[1].amounts_mol[SELECTED, 1])) - F(
        float(ordinary.states[0].amounts_mol[SELECTED, 1]))
    energy_local = F(float(ordinary.states[1].internal_energy_j[SELECTED])) - F(
        float(ordinary.states[0].internal_energy_j[SELECTED]))
    if quantity in ('amount', 'both'):
        assert last.inventory_residual_mol[1] == last.full_inventory_residual_mol[1] == PREFIX_ERROR
        assert amount_local == PREFIX_ERROR == F(3, 5) * BUDGET
        assert amount_local <= BUDGET < last.inventory_residual_mol[1] + amount_local
    if quantity in ('energy', 'both'):
        assert last.energy_residual_j == last.full_energy_residual_j == PREFIX_ERROR
        assert energy_local == PREFIX_ERROR == F(3, 5) * BUDGET
        assert energy_local <= BUDGET < last.energy_residual_j + energy_local
    with pytest.raises(ValueError, match='source_transition_cumulative_original_balance_budget'):
        _audit_balance_fields(**kwargs, post_dry_references=(ordinary,))


def test_correct_post_dry_chain_keeps_original_residuals_and_other_cells():
    kwargs, ordinary = _projection('both', ordinary_fraction=F(1, 5))
    second = _reference(ordinary.states[-1], ordinary.states[-1], _ledger(4, 5))
    rows = _audit_balance_fields(**kwargs, post_dry_references=(ordinary, second))
    assert [row.phase for row in rows[-2:]] == ['post_dry_reference', 'post_dry_reference']
    assert rows[-1].time == T(F(5))
    expected = F(4, 5) * BUDGET
    final = rows[-1]
    assert final.inventory_residual_mol[1] == final.full_inventory_residual_mol[1] == expected
    assert final.energy_residual_j == final.full_energy_residual_j == expected
    assert final.cell_balances[SELECTED].inventory_residual_mol[1] == expected
    assert final.cell_balances[SELECTED].energy_residual_j == expected
    for index in (0, 2):
        assert final.cell_balances[index].inventory_residual_mol == (F(),) * 4
        assert final.cell_balances[index].energy_residual_j == 0
    assert final.event_water_storage_roundoff_mol == 0


@pytest.mark.parametrize('fault', ['state', 'time', 'length', 'second_reference_state', 'ledger_time'])
def test_incorrect_post_dry_connection_is_rejected(fault):
    kwargs, ordinary = _projection('both', ordinary_fraction=F(1, 5))
    references = [ordinary]
    reason = 'source_transition_post_dry_connection_changed'
    if fault == 'state':
        references[0] = SimpleNamespace(states=(_error_state(ordinary.states[0], UNIT), ordinary.states[1]),
            times_s=ordinary.times_s, steps=ordinary.steps)
    elif fault == 'time':
        references[0] = SimpleNamespace(states=ordinary.states, times_s=(T(F(2)), T(F(4))),
                                       steps=ordinary.steps)
    elif fault == 'length':
        references[0] = SimpleNamespace(states=ordinary.states, times_s=ordinary.times_s[:1],
                                       steps=ordinary.steps)
    elif fault == 'second_reference_state':
        references.append(_reference(ordinary.states[0], ordinary.states[-1], _ledger(4, 5)))
    elif fault == 'ledger_time':
        references[0] = SimpleNamespace(states=ordinary.states, times_s=ordinary.times_s,
                                       steps=(_ledger(2, 4),))
        reason = 'source_transition_ledger_time_gap'
    with pytest.raises(ValueError, match=reason):
        _audit_balance_fields(**kwargs, post_dry_references=tuple(references))
