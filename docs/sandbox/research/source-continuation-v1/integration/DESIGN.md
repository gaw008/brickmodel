# Ordinary exact SSPRK2 accepted-prefix continuation

Read-only design against HEAD 9d7beffeeb7c1c18f357f2b3ab5ce690bca35181. No production changes, tests, backend construction or EOS calls were made for this investigation.

## 1. The missing state is real

`integrate_exact` retains only accepted times/states/ledgers and aggregate counters in ExactIntegrationResult. Its local `h`, `knot_index`, component schema, cumulative N/U exchanges and three mechanical accumulators are not returned. Restarting it on `result.states[-1]` with `start_s=result.times_s[-1]` resets the initial origin of every cumulative residual, initializes the controller from policy.initial_step_s, redoes the initial domain callback, and resets all resources. That is a new integration, not a continuation.

The source study codec does not supply these missing fields. `_replay_source_reference` can verify a completed source reference against saved observations with no EOS, but currently insists on a completed whole interval and reruns from its original start. Its wall duration is expressly not a cost certificate. It cannot recover missing controller state by simply wrapping a saved endpoint as SourcePrefixTrial.

The older exact-depletion continuation is a different driver and exact free/mechanical host. Useful conventions are fresh parent hash/runtime/policy admission, complete cumulative returned history, debit admission time, outward-rounded prior+new wall time, and returning an exhausted parent with zero new physics. Its ExactContinuationRequest/admit/restore logic, source-specific packet audits and ExactFreeWaterTransfer assumptions cannot be passed to ordinary integrate_exact as a substitute.

## 2. Two cancellation contracts must be distinguished

The current cancellation guard runs before/after every actual operator call and before committing a step. Thus cancellation can leave 1–7 charged observations and an attempted trial after the last accepted point. The current result does not retain that RK execution frame.

**Recommended smallest version: explicit pause at a committed boundary.** Finish the original accepted-state validation, ledgers, cumulative updates, history append, next-h controller update and last_domain reset atomically. Then issue a checkpoint notification and honour a pause request before entering the next attempt. A clean boundary pause and resume has the same physical callback sequence, requested exact times/states, accepted history, rejected/attempt/evaluation counts and next-step choices as an uninterrupted deterministic operator run, provided the original cumulative resource budget suffices. Wall duration is cumulative actual active duration including pause/resume overhead, so it cannot be numerically identical to the uninterrupted wall time and may legitimately exhaust sooner.

**Existing immediate cancel is preserved.** If it fires mid-attempt, retain original actual callbacks/failures and all spent counters/wall time. The simplest first version marks that stopped frame not eligible for the exact callback-equivalent boundary resume. A later explicitly labelled retry-from-last-accepted-boundary option may restart the unfinished trial with the saved current h and last_domain, but all abandoned work remains charged; its callback sequence/count is necessarily different. Do not present it as identical no-replay continuation. Exact arbitrary-RK resumption would require a new state machine holding the program counter, every completed local stage/result, pending return-validation state, fields/exact component quadratures and rejection bookkeeping; this is materially beyond an accepted-prefix interface.

Cancellation before any commit has no accepted prefix. A new ordinary source segment starting at a prior transition's admitted endpoint is also a fresh segment, not an integrate_exact checkpoint: it performs its own real initial domain evaluation once. Only subsequent resumes of that same segment skip that probe.

## 3. Minimum saved accepted-boundary data

An immutable `ExactAcceptedPrefix` should contain:

| Field group | Required content and reason |
|---|---|
| Original problem | Original initial state, exact original start/end, all original exact breakpoints, full original policy with strict typed snapshot; never substitute the checkpoint endpoint as original initial |
| Accepted history | Complete ordered times, states, ExactStepLedger records, including energy identity, float64 N/U arrays, optional stretches, work components and exact quadrature-roundoff fields |
| Controller | Exact Fraction next_step_s **after** original h update; knot_index in original knots+end; explicit schema state (`unobserved`, `none`, or ordered component names); initial_probe_done=True; boundary phase tag; last_domain=None at a fresh commit |
| Represented exchanges | cumulative_n flattened in original array order; cumulative_u; cumulative represented stretch increments when mechanical |
| Stronger accumulated bounds | cumulative absolute component-sum residual per cell; cumulative exact stretch quadrature; cumulative absolute stretch quadrature roundoff per face |
| Costs | evaluations attempted (current counter is incremented before operator, even on failure), rejected trials, attempted trials, accepted count from ledgers, actual active elapsed at clean stop; optional completed/returned callback count belongs to observation evidence, not a renamed evaluations field |
| Identity/admission | Schema/version, checkpoint content binding; service supplies original case/config/runtime/operator/energy/mode provenance and a freshly constructed live operator. A digest alone does not validate arithmetic or restore a provider |
| Numerical observations | Ordered initial probe and all actual attempt callbacks through the checkpoint, including successful returned Rates and explicit DomainExit failures. Preserve rejected attempts, their exact input states/times, terminal accepted-state validation, actual post-return cancellation/failure status, and stable ordinal/attempt/role associations |

The exchanges need not be independently trusted duplicated truth. Recompute them from full original accepted ledgers on admission and require equality to the saved accumulators. For stretch, exact quadrature increment is F(saved stretch_increment) minus saved stretch_quadrature_roundoff, while the budget sums absolute per-step roundoff. For N/U, preserve the exact existing order: each represented left-face, negative right-face and source/work contribution enters the Fraction cumulative sum; compare the final represented state to the **original initial** state. Every local original check also remains in force.

At a boundary `knot_index` may still point at the knot just reached, because the increment occurs lazily at the next loop entry. Preserve that convention or validate the equivalent derived first knot >= current time; do not truncate/reset the original breakpoint list. Preserve the tail-avoidance rule that splits a remaining interval into two legal halves. Store physical clocks only as ExactEventTime with exact Fraction.seconds; recheck the underlying type to reject post-construction float/int/bool mutation. Display floats never choose an endpoint or callback time.

## 4. Minimal implementable API without changing old result/codec bytes

Keep `ExactIntegrationResult` unchanged. Appending even a default field would alter existing registered serialization and golden records. Use an opt-in separate public result wrapper:

```python
@dataclass(frozen=True)
class ExactAcceptedPrefixRun:
    result: ExactIntegrationResult       # complete cumulative old-format history
    checkpoint: ExactAcceptedPrefix | None
    # None unless a clean supported accepted boundary is actually resumable


def integrate_exact_checkpointed(
    initial, operator, *, start_s, end_s, policy,
    breakpoints_s=(), cancel=None,
    continuation: ExactAcceptedPrefix | None = None,
    pause_after_commit: Callable[[ExactAcceptedPrefix], bool] | None = None,
    on_commit: Callable[[ExactAcceptedPrefix], None] | None = None,
) -> ExactAcceptedPrefixRun: ...
```

Both this entry and unchanged `integrate_exact` must execute the same original arithmetic loop, via one narrowly extracted internal driver. With opt-in arguments absent, the original return fields, call sequence, guard/clock-read order, failures and arithmetic must remain unchanged. Do not duplicate the full integrator. New observational/checkpoint bookkeeping is only enabled for the new entry.

`on_commit` receives the completed immutable prefix after h/counters/balances have been committed. If the observer fails, return or propagate an explicit observer failure with the already committed prefix retained; never erase it or claim clean cancellation. The wrapper's final checkpoint should reflect actual stop-time wall debit, not merely the earlier timestamp at entry to an expensive observer. A durable callback snapshot is a recovery artifact; if the worker is killed during/after writing it, service-level elapsed accounting and lease/interrupt admission are needed before it is allowed to become a clean cancellation checkpoint.

The Root-owned service may expose a request-to-pause flag checked at boundaries while retaining a separate immediate cancel for urgent resource/safety stop. The generic core takes a freshly supplied callable. Source reconstruction and operator metadata binding are separate admission work, not serialization of a live adapter.

## 5. Passive admission and numeric controller evidence

The saved next h cannot be inferred from accepted ledgers alone: the full-step estimate that determined the adaptation error is discarded. Therefore an externally restored checkpoint must not gain numerical approval merely because its saved h is within min/max and its SHA matches.

A narrow passive audit can replay the existing arithmetic against retained callbacks, matching every requested state/time before returning the saved Rates and re-raising saved DomainExit. Stop the replay at exactly the accepted boundary with the new pause interface, then require all non-wall checkpoint fields to match, including h, rejected/attempt/evaluation counters, schema, and balances. This shares the actual RK/controller/rejection implementation and avoids hand-copied error estimators. No physical EOS or old live adapter is involved in that audit. All original observations and their authoritative binding must have been validated by the service/record layer; no replay call is charged as a newly executed physical callback. Admission CPU/wall time is charged to the original wall budget.

For a version accepting only a live in-memory engine-issued checkpoint, strict binding+recomputed ledger checks may support that narrower trust scope, but it is insufficient to advertise arbitrary archived JSON as a numerically verified checkpoint. The installed read/write goal needs the retained observation branch above or an equivalent complete RK proof.

Each uninterrupted attempted trial requests, in order: full first/second (at,next), left-half first/second (at,midpoint), right-half first/second (midpoint,next), and, if the estimated error passes, an additional accepted-state domain validation at next. The initial-domain observation is separate and occurs once per original segment. Failures can truncate this sequence. Record roles explicitly; equal time labels do not make different-state observations interchangeable. Never deduplicate callbacks merely by equal time.

## 6. Admission refusal / exhausted results

Reject before new physical calls if any original initial/energy identity/layout, policy field/type, start/end/breakpoint, runtime/source/mode binding or original parent bytes disagree. Reject unsupported/failed/non-boundary checkpoints, missing initial probe, completed endpoint labelled resumable, inconsistent counts, nonfinite elapsed or negative credits, malformed arrays, missing mechanical/component fields, altered h/control proof, dropped rejected observations, or any cumulative ledger mismatch. Changed tolerance/resource limits are a changed problem, never an implicit continuation.

A legitimate checkpoint with exhausted original accepted/rejection/wall budget returns the same resource-limit reason and cumulative history with zero new operator calls. Do not create a remaining-time policy that forgets already spent wall time; compare outward-rounded F(prior_elapsed)+F(new_elapsed) against the original policy.maximum_wall_seconds. Count read/audit/reconstruction/admission time according to one explicit service/core boundary, without either omitting or double-charging it. Process monotonic origins themselves are not persisted or compared across processes.

## 7. Independent finite tests, no EOS

1. Freeze original integrate_exact full outputs and actual callback inputs/returns before extraction; exact optional-entry None keeps all non-wall bytes and callback/guard behavior unchanged.
2. Manufactured nonlinear N/U/mechanical operator that actually rejects before acceptance: pause after a commit, resume more than once and compare every requested Fraction time, binary64 input/rate/accepted state/ledger, h and counters to one uninterrupted run. Pause after a breakpoint too.
3. Large absolute origin (10**12 plus tiny exact duration), coincident display times, nonmultiple endpoint and minimum-tail cases: original final exact endpoint and quarter-stage times remain identical.
4. Independent cumulative-roundoff trap: each resumed segment's local N/U or stretch/absolute-component residual stays below tolerance while the original cumulative sum exceeds it; resumed continuation must refuse at the same step as uninterrupted execution. Verify saved accumulator rehash tampering separately.
5. Actual DomainExit rejection and component-schema establishment on a rejected attempt: continue with original rejection debt and schema. Delete the rejected callback or loosen the saved schema/h and require passive replay rejection before new physics.
6. Initial zero dry liquid with zero dry transfer and wet neighbours is a valid ordinary segment input; no artificial SourcePrefixTrial positivity requirement. Negative or outflow-from-zero rate still fails the original Rates.derivatives check.
7. Pause at boundary versus cancel at every RK phase: exact-boundary path has no repeated initial probe/callback; mid-attempt cancel preserves spent observations/counters and is explicitly non-eligible for strict boundary continuation in v1.
8. Fake monotonic clock: admission/observer time debited; already exhausted step/rejection/wall budget yields zero physics; budget cannot be reset by a new process's clock origin.
9. Observer failure immediately after commit retains the accepted prefix as failure evidence. Unknown callback exceptions and failed returned records remain explicit and never become successful observations.
10. Strict types and mutation: Fraction/int/bool/float clocks, ndarray dtype/nonfinite, policy field changes, same-value independent source host versus required explicit live source reconstruction, wrong end/initial state, dropped work/stretch records.

This slice provides ordinary source integration continuation after a selected dry transition. It does not re-enter SourcePrefixTrial, rerun the wet-to-dry event as if it were a continuation, or qualify additional drying/chemistry/material/full-cycle behaviour.
