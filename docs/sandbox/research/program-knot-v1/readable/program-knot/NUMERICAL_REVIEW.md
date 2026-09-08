# Ordinary program-knot endpoint coalescence: numerical design review

Scope: read-only design review of the ordinary branch in depletion_integration.py. No source/test changes, model imports, EOS calls or tests were performed. `git diff -- '*.py'` was empty at inspection. This approves the bounded design below for implementation and independent regression; it is not evidence that a candidate or the retained failure has passed.

## Evidence and target

The retained .005-step failure is documented in /private/tmp/brick-fixed-spatial-audit-v1/NEXT_NUMERICAL_PRIORITY.md and /private/tmp/brick-affine-terminal-v1/second-integration-tests.xml. Repeated outer rounded endpoints can produce .045 -> .049999999999999996 just below the known knot .05. The next residual interval has adjacent binary64 endpoints, so no strictly interior midpoint exists. The current stage-time guard correctly rejects it. The ordinary wrapper starts a fresh integrator for each segment, losing the persistent exact clock across those separate calls. An unchanged-source minimal regression is still required to confirm this precise path, rather than presenting the arithmetic hypothesis as a new executed reproduction.

The fix must select .05 while still at the preceding resolvable .045 panel, then integrate that complete interval. It must not advance only a timestamp or discard the residual interval.

## Approved narrow contract

Let t be the accepted start, tb the immediate known allowed program boundary or overall end, c the positive intended ordinary maximum step, and finish the existing unmodified minimum-selected endpoint. Let F denote exact Fraction conversion of a finite binary64 value. If an inventory candidate exists, its exact tau is already a Fraction; define S = F(safe_inventory_fraction) * tau.

Preserve the original endpoint unless every applicable condition holds:

1. All time/cap inputs are finite, c > 0, and t < finish < tb. In particular finish == tb is never repaired by this helper.
2. The original finish equals min(tb, t+c). This identifies the ordinary numerical cap proposal, rather than an unrelated physical/event-limited endpoint.
3. When an inventory candidate exists, require F(c) <= S and F(tb)-F(t) <= S. These are two different obligations: the intended cap is inventory-safe, and the adjusted endpoint is inventory-safe. The original rounded safe-limiter calculation cannot substitute for these exact checks.
4. The positive represented gap tb-finish is at most min(ulp(tb), 32*ulp(min(c, tb-t))). This is a local representation allowance, not an absolute epsilon or event-tolerance-based snap.
5. Also require abs((F(tb)-F(t))-F(c)) <= 32*F(ulp(c)). This prevents a large absolute-time ULP from permitting a large duration change. Use the exact difference of the two endpoint Fractions here and in item 3; F(tb-t) first rounds the subtraction and is not equivalent.

Only then return tb; otherwise return the legacy finish. The known boundary must remain the immediate permitted target. Neither an arbitrary future program knot nor a terminal event time should be supplied as a substitute merely to pass this check. Keep ordinary approach/event call sites unchanged until separately reproduced and reviewed. The already-depleted dry branch can continue using its existing full-target ordinary integrator with a persistent internal clock.

## Why the contract is safe within its stated scope

The two exact inventory checks prohibit crossing the currently certified safe fraction of depletion time. This also handles the subtle case where a rounded safe-limiter endpoint happens to equal a cap endpoint: equality alone is insufficient, but the exact checks disambiguate safety. The helper does not claim the constant-current-rate limiter proves nonlinear positivity across a whole panel; existing stage-state validation and error rejection continue to supply that protection.

The adjustment ends exactly at the known boundary and cannot cross it. The finite cap-scale bound qualifies a small representational exception to the numerical maximum-step policy. It does not authorize changing source uncertainty, physical data, event tolerances, minimum-step rules or acceptance gates. Existing integrator stage-time checks remain essential and unchanged.

For negative times, use math.ulp on the signed boundary normally; do not define the allowance by epsilon times t. Crossing zero is acceptable only if all the same checks hold. At tb == 0, ulp(tb) is the smallest subnormal, so the proposed rule may conservatively decline otherwise imaginable adjustments; that is preferable to enlarging the policy without a separate case and evidence. Nonfinite values must never reach Fraction conversion. Extremely small caps and subtraction underflow remain subject to the unchanged resolvability checks.

A genuinely requested adjacent-endpoint physical panel already has finish == tb. The helper leaves it untouched and the original midpoint guard must still reject it. Even an eligible coalesced panel is passed to the ordinary integrator, not accepted directly; if its midpoint or sub-stages cannot be represented, the original failure is retained.

## Weights, ledgers and evidence

Pass the selected endpoint to normal() and let the existing integrator compute every actual endpoint-derived duration and stage weight. Do not keep c as an integration weight after choosing tb. State increments, all signed inventory/energy exchanges, cumulative ledgers and accepted timestamps must all describe the same complete interval. No post-commit clock relabeling, zero-duration artificial step or synthetic conservation correction is acceptable.

An additional public event/correction schema is not necessary for this scheduling repair: actual accepted start/end and stage/ledger weights provide the essential numerical evidence. The helper docstring and regression should explicitly document that the numerical cap admits at most the declared representational duration adjustment. If existing diagnostics present the cap as an exact hard inequality, update that description rather than concealing the exception. Source/provider bindings, rollback, cancellation and resource accounting must remain on their original paths.

## Required independent regression before claiming a fix

First preserve an unchanged-source failure with constant manufactured inventory source and power, safely distant from depletion, .005 cap, interior knot .05, and end .06. Record exact hexadecimal failing endpoints and the accepted prefix. Expected integrals should come from the declared source and actual overall duration, independently of the endpoint helper.

After implementation require exact knot/end arrival, strictly increasing accepted times, no ledger crossing the knot, no zero-duration fabricated panel, and unchanged physical/ledger gates. Require the actual prior panel to end at .05, not a later timestamp-only repair. Include a piecewise-program check honoring the adapter's documented endpoint-side convention; a discontinuity must not be silently averaged across the knot.

Add pure helper counterexamples for: safe limiter shorter than cap; cap nominally safe but adjusted target beyond exact S; rounded limiter/cap equality masking an unsafe exact target; gap larger than one boundary ULP; large-time ULP exceeding the cap-scale bound; negative and zero absolute times; cap or endpoint nonfinite; and finish already equal to an adjacent physical endpoint. Equality at the exact safe bound is permitted only if existing stage validation permits the resulting state. A no-EOS integration test must retain the original unresolvable_stage_time outcome for a genuinely adjacent physical panel.

Finally rerun the retained .005 fixtures and existing ordinary/depletion source, rollback and cancellation regressions under unchanged acceptance gates. A standalone integrate() control with the same program knot distinguishes this outer scheduling defect from the core clock. No native EOS is needed for the first proof. Approval for installed/native validation follows review of the actual diff and passing independent regressions, not this design alone.

Conclusion: approve this narrowly scoped design, conditional on the exact Fraction endpoint safety checks and unchanged stage/ledger guards. No broader event, approach or spatial redesign is needed to test this concrete failure.
