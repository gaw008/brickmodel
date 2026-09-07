# Independent nominal-clock implementation review

Approve the reviewed source/test change. Source SHA a2afb84f816cb30f9d5305d636f1841b3670f71f1e416a405ebb8182c5cae3b2. Reviewer made no source/test edits and ran no EOS. Reviewer-owned tests/results are in this directory.

Line-by-line diff confirms exact Fraction(start) initialization, target-capped nominal addition, float endpoint conversion with target reanchoring, accepted-only clock advancement and reanchoring in both rejection branches. All RK formulas, actual stage differences, ledger construction, physical tolerances, conservation checks, resource guards and minimum/stage-resolution checks remain unchanged. The doc explicitly distinguishes nominal step limits from rounded absolute intervals. No state timestamp is snapped without integrating its actual interval. No critical/high issue found.

New ten tests exercise positive/negative/large time origins at2/4/8 panels with nonzero analytic boundary flux and energy, exact Fraction ledger consistency, target callback and a breakpoint. Read actual before.xml:10 tests,7 failures,3 passing; after.xml:38 tests,zero failures/errors,0.509 s. The failures before the fix establish the reported tail issue was not merely asserted retrospectively.

Additional actual no-EOS reviewer checks passed:

- A once-only DomainExit after accepted steps with fractional carry reanchors and completes,one rejected/nine accepted, preserving constant-power analytic energy and ledger.
- A quadratic time-dependent source after accepted steps triggers three local-error rejections and completes with282 accepted steps. Its global error equals the analytic composite trapezoidal error of the two SSPRK2 half steps to1e-10 J, validating actual interval weights across rejection/adaptation.
- Subnormal one-ULP and1e16-origin one-ULP spans remain numerical_failure/unresolvable_stage_time with no accepted ledger.
- Independently reran existing rejected_step_must_reduce_its_represented_endpoint regression:1 passed,27 deselected,0.05 s.

Reviewer test-development correction retained transparently: reviewer_checks_initial.py asserted an arbitrary2e-5 J global accuracy bound for the quadratic case; actual error2.2425164532435815e-5 J exceeded it. Local integration tolerance is not that global bound. Replaced only the reviewer test with the exact known quadratic quadrature-error expression; it passes without changing production source or tolerance. Final actual outputs are reviewer-check-results.json.

This clock fix changes scheduling, so prior scientific results stay tied to old source. The failed finest stage9 run is not retroactively complete; installed-module binding and the original active refinement must be rerun before claiming three-scale consistency. No broad convergence-order/material admission follows from these clock tests.
