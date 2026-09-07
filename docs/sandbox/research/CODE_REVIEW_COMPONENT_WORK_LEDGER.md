# Component work ledger independent review

Verdict: APPROVE for optional named work accounting in ordinary `integrate`. It does not certify each component's time-discretization error or add equivalent support to depletion panels/wrappers.

Read the complete changed integration code and new tests, compared HEAD, and traced initial evaluation, discarded full trial, fine stages, accepted-state validation and commit/failure paths. Component keys are normalized and frozen; every evaluation must retain the same key set or None status, including rejected/coarse stages. Dissipation cannot be negative. Rates require the existing total power to equal the correctly rounded exact sum of represented components and retain its exact decomposition residual. Total power remains the sole driver of state energy; residuals are not extra sources.

Each accepted fine RK stage contributes its component powers using the same actual subinterval weights as total work. The final StepLedger records each represented component integral and the exact Fraction difference from the sum of represented stage powers times those weights. It includes multiplication and both summation-rounding levels. Nonzero subnormal component integrals can round to zero, but their full signed lost quantity remains in this separate diagnostic; no fictitious physical zero is inferred. Component-sum residual is separately the represented total integral minus the exact sum of represented component integrals.

The proposed per-cell cumulative sum of **absolute** decomposition residuals is checked against the original energy absolute tolerance before any global cumulative state/ledger mutation. Rejected trials and failed post-validation/budget/cancellation paths do not commit component entries. Counters/schema reflect actual attempted evaluations; accepted arrays and cumulative residuals reflect only committed steps. Schema change is a numerical contract failure rather than an adaptive physics rejection. Existing exception boundaries do not catch unrelated Python errors.

## Independent execution and default compatibility

Independent new + old integration suite: **44 passed in 0.50 s**, XML `/private/tmp/component-work-review.xml`. This includes schema changes both directions, accepted stages after rejections, partial resource termination, exact cumulative-budget failure before a second commit, subnormal opposite terms and signed multicell components.

Saved actual HEAD source to `/private/tmp/integration-before-components.py`, SHA256 `4b5da50910ac4591e77787cef135df11afe396683ab74f5a9c0868d8d5cac1d7`, and compiled its original integrate AST against unchanged helper logic. On an independent no-components state-dependent reaction/heat example with a .37 s breakpoint, old/new results match exactly in all 123 accepted times, state arrays, legacy ledger arrays, status/reason, evaluation count and three rejection counts. Elapsed runtime was appropriately excluded. This is a real old-function comparison, not two calls to the new default implementation.

An additional independent one-step probe recorded all actual operator calls with elastic/pore powers of opposite magnitude 1e200 and state-dependent body power. It reconstructed the four accepted fine-stage contributions with exact Fractions, excluding initial, discarded-coarse and final-validation calls. All three component quadrature residuals exactly matched the saved diagnostics; cumulative absolute decomposition residual matched the accepted ledger. This cancellation probe does not assert that net-energy adaptivity resolves the individual component trajectories.

## Bounds and integration scope

The cumulative acceptance budget covers total-versus-component **decomposition** rounding, not each component's quadrature truncation error or a cumulative absolute sum of each quadrature-roundoff diagnostic. Large mutually cancelling physical powers still require separate accuracy studies before physical stress/energy claims. Manually constructed StepLedger objects may lack stage-roundoff evidence. No component metadata implies a verified material source. Existing wrappers and terminal event panels must explicitly forward and integrate these fields before claiming this support; the implementation docstring states that limitation.

Final bindings:

- `src/sludge_sandbox/integration.py`: `7316bd04a91c32ed45ea1aa5011b39dd4b6ba3b893b2f49acf1e8cb95ec47a64`.
- `tests/sandbox/test_component_work_ledger.py`: `aeb92b6ee2f822a08a2e9e730f78f6474e13655a29e4695d5c5acaadd9bbab2d`.

No production source/tests were changed by this reviewer, no full/EOS suite was run and no commit was made.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — accepted-stage component bookkeeping preserves the original authoritative total and reports numerical decomposition honestly within the stated ordinary-integrator scope.
