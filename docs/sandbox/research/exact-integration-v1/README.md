# Exact-time conservative integration path

Baseline `5462deb`, with the companion exact-time and program primitives.
`integrate_exact` is an explicit independent SSPRK2 step-doubling path sharing
the existing `ConservedState`, `Rates`, `IntegrationPolicy` and representation
checks. It returns `ExactIntegrationResult` and `ExactStepLedger`, with exact
semantic endpoints. Every callback receives `ExactEventTime`; actual stage
durations, half-stage construction and quadrature reference weights use rational
seconds. Integrated physical arrays remain binary64.

## Numerical and transaction contract

The accepted path consists of two half steps, compared with the discarded full
step through the existing local error scales. Every Euler stage, the accepted
combination and all original-initial N/E/component/stretch accounts are checked
before committing history. Rejections, declared domain failures and cancellation
retain only the accepted prefix. Costs include explicit attempted trials.
Cooperative wall checks do not interrupt a blocking native call.

Only future **nominal durations** are projected downward to binary64 and adopted
as rationals, preventing unbounded denominator growth in the adaptive controller.
Actual endpoints and clipped stage durations are not projected. This controller
choice is explicit; the new path does not claim byte-identical legacy numerical
trajectories. Original error, positivity, min/max duration and resource gates
remain in force. A proposed landing that would leave a sub-minimum tail is
replanned into two admissible equal intervals; no tail is discarded. An entire
horizon below the minimum still fails.

## Actual validation

- New integrator tests cover autonomous origin translation from 0 to 10^12 s,
  where distinct accepted times display identically; per-prefix independent
  Fraction accounts; translated piecewise forcing and exact knot clipping;
  analytic nonlinear amount/mechanical evolution; positivity rejection; domain,
  wall/step/rejection/cancellation behavior; and a nonmultiple final horizon.
- Two root-added boundary tests verify that legacy integration/program queries
  and checkpoint decoding reject exact time objects/serialized ledgers before
  any silent float conversion. They do not provide a new checkpoint codec.
- **185 source tests passed in 7.22 s**. After offline noneditable installation,
  **132 tests passed in 6.98 s**, from `/private/tmp` without `PYTHONPATH`.
  **70 actual installed modules matched source**.
- No native EOS experiment was run for this milestone. The earlier four-cell
  failure remains the authoritative native outcome.

Code, numerical and boundary reviews are retained alongside this file. Preserved
failures include an invalid fixture component key, actual 30 s wall exhaustion
from rational controller denominator growth, a consuming fixture that correctly
hit rejection limits, and a root boundary test whose expected error spelling
was wrong. The controller, appropriate test fixtures and exact error expectation
were corrected before the final runs; no scientific threshold was loosened.

## Remaining integration

Exact affine depletion clock/writeback evidence, full ordered event refinement
and atomic packets, actual native host exact-query admission, provenance-bound
program adapters, new record/audit/resume and CLI/UI admission remain necessary.
Using exact durations while calling a time-dependent host with rounded display
times would violate this contract. An autonomous host must have a verified
state-only evaluation path, not an arbitrary float-time sentinel.

The original-sludge material evidence, three public mechanism comparisons and
heldout prediction, complete wet-to-fired/cooled simulation, spatial convergence
and full application acceptance remain unresolved. This milestone is numerical
infrastructure and its actual execution evidence, not Goal completion.
