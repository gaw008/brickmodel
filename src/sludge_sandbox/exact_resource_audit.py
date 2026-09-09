"""Original resource telemetry checks; no new budgets or resume authority."""
from collections.abc import Mapping
from collections import Counter
import json
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
import math

from sludge_sandbox.exact_record import ExactRunRecord, read_exact_run, pack, COSTS
from sludge_sandbox.integration import IntegrationPolicy


class ResourceAuditError(ValueError):
    pass


def require(value, reason):
    if not value:
        raise ResourceAuditError(reason)


def counters(values):
    require(isinstance(values, Mapping) and set(values) == COSTS, 'resource_counter_schema')
    require(all(type(v) is int and v >= 0 for v in values.values()), 'nonnegative_integer_counters')
    return values


@dataclass(frozen=True)
class ResourceAudit:
    record_sha256: str
    charged_panels: int
    remaining_panels: int
    remaining_rejections: int
    remaining_wall_seconds: Fraction
    terminal_calls: int
    cumulative_counters: Mapping
    cumulative_elapsed_seconds: Fraction
    scope: str = 'recorded_resource_consistency_and_original_remaining_allowance'
    telemetry_qualification: str = 'ordinary_discarded_calls_and_historical_wall_not_independently_reconstructed'
    resume_authorized: bool = False


def audit_exact_resources(record, *, original_policy: IntegrationPolicy) -> ResourceAudit:
    """Reparse canonical bytes and bind the external original policy.

    The run store must supply authoritative parent bytes. This validates recorded
    consistency and remaining allowances, not authenticity of editable wall data.
    No operator or EOS is evaluated, and no continuation capability is issued.
    """
    require(type(original_policy) is IntegrationPolicy, 'original_policy_required')
    raw = record.canonical_bytes if type(record) is ExactRunRecord else record
    checked = read_exact_run(raw)
    r = checked.result
    require(pack(r.initial_policy) == pack(original_policy), 'original_resource_policy_mismatch')
    total = counters(r.costs)
    terminal = {k: 0 for k in ('evaluation_attempts', 'evaluation_completed', 'predictor_panel_attempts', 'terminal_panel_attempts', 'terminal_panels')}
    terminal_elapsed = Fraction()
    for attempt in r.terminal_attempts:
        c = attempt.costs
        for key, value in c.values.items():
            if key == 'elapsed_seconds':
                require(type(value) is float and math.isfinite(value) and value >= 0, 'terminal_elapsed')
                terminal_elapsed += Fraction(value)
            else:
                require(type(value) is int and value >= 0, 'terminal_integer_cost')
        require(c.predictor_panels == int(attempt.predictor_panel is not None), 'materialized_predictor_count')
        require(c.terminal_panels == int(attempt.terminal_panel is not None), 'materialized_terminal_count')
        for field, counter in (('root_order', 'root_order_attempts'), ('corrected_state', 'writeback_attempts'), ('candidate_operator', 'mode_transition_attempts')):
            require(getattr(attempt, field) is None or getattr(c, counter) >= 1, 'materialized_stage_attempt:' + field)
        require(c.evaluation_completed == len(attempt.observations), 'terminal_observation_count')
        require(c.evaluation_attempts >= c.evaluation_completed, 'terminal_evaluation_order')
        require(c.predictor_panels <= c.predictor_panel_attempts, 'predictor_cost_order')
        require(c.terminal_panels <= c.terminal_panel_attempts, 'terminal_cost_order')
        for key in terminal:
            terminal[key] += getattr(c, key)
    for global_key, local_key in (('predictor_attempts', 'predictor_panel_attempts'), ('terminal_attempts', 'terminal_panel_attempts'), ('terminal_panels', 'terminal_panels')):
        require(total[global_key] == terminal[local_key], 'terminal_counter_reconstruction:' + global_key)
    require(total['evaluations_attempted'] >= terminal['evaluation_attempts'] and total['evaluations_completed'] >= terminal['evaluation_completed'], 'terminal_host_counter_lower_bound')
    require(terminal_elapsed <= Fraction(r.elapsed_seconds), 'terminal_wall_lower_bound')
    refined = dict.fromkeys(COSTS, 0)
    def ledger_key(ledger):
        return json.dumps(pack(ledger), sort_keys=True, separators=(',', ':'))
    speculative_ordinary = Counter()
    recorded_attempts = Counter(ledger_key(a) for a in r.terminal_attempts)
    refinement_terminals = Counter()
    for ref in r.refinements:
        values = counters(ref.costs)
        for key in COSTS:
            refined[key] += values[key]
        if ref.path is not None:
            # Frame terminal ledgers are a subset of path steps. Do not charge
            # the committed copies of these speculative paths a second time.
            frame_count = len(ref.path.frames)
            refinement_terminals.update(ledger_key(f.terminal) for f in ref.path.frames)
            require(len(ref.path.steps) >= frame_count, 'refinement_path_counts')
            terminal_keys = Counter(ledger_key(f.terminal.terminal_panel.ledger) for f in ref.path.frames)
            path_keys = Counter(ledger_key(step) for step in ref.path.steps)
            require(not (terminal_keys - path_keys), 'refinement_terminal_ledger_membership')
            speculative_ordinary.update(path_keys - terminal_keys)
            retained_ordinary = len(ref.path.steps) - frame_count
            require(values['ordinary_panels'] >= retained_ordinary, 'refinement_ordinary_lower_bound')
    require(all(refined[k] <= total[k] for k in COSTS), 'refinement_counter_lower_bound')
    require(not (refinement_terminals - recorded_attempts), 'refinement_terminal_attempt_membership')
    committed_attempts = Counter(ledger_key(f.terminal) for packet in r.packets for f in packet)
    require(not (committed_attempts - recorded_attempts), 'committed_terminal_attempt_membership')
    committed_events = sum(len(p) for p in r.packets)
    require(total['ordinary_panels'] >= len(checked.ledgers) - committed_events, 'committed_ordinary_lower_bound')
    require(total['terminal_panels'] >= committed_events, 'committed_terminal_lower_bound')
    committed_terminal = Counter(ledger_key(f.terminal.terminal_panel.ledger) for packet in r.packets for f in packet)
    committed_keys = Counter(ledger_key(step) for step in checked.ledgers)
    require(not (committed_terminal - committed_keys), 'committed_terminal_ledger_membership')
    committed_ordinary = committed_keys - committed_terminal
    # Refinement deltas already charge all their speculative ordinary work.
    # Count only committed work not represented there, using complete ledgers
    # including exact times; decoded object identity is not preserved.
    outside_refinements = sum((committed_ordinary - speculative_ordinary).values())
    require(total['ordinary_panels'] >= refined['ordinary_panels'] + outside_refinements, 'disjoint_ordinary_counter_lower_bound')
    charged = total['ordinary_panels'] + total['stage_replans'] + total['terminal_attempts']
    require(charged <= original_policy.maximum_steps, 'original_panel_budget_exceeded')
    require(total['ordinary_rejected'] <= original_policy.maximum_rejections, 'original_rejection_budget_exceeded')
    elapsed = Fraction(r.elapsed_seconds)
    # A cooperative wall check can finish after its deadline. Preserve the full
    # reported elapsed time and return zero credit; never clip the telemetry.
    remaining_wall = max(Fraction(), Fraction(original_policy.maximum_wall_seconds) - elapsed)
    return ResourceAudit(checked.sha256, charged, original_policy.maximum_steps - charged,
        original_policy.maximum_rejections - total['ordinary_rejected'], remaining_wall,
        len(r.terminal_attempts), MappingProxyType(dict(total)), elapsed)
