# Final applied case/test review

Verdict: **APPROVE for this local case-builder stage**. No source blocker found. Service trace revisions are excluded and are not approved by this report.

Verified production hashes:

- `src/sludge_sandbox/verification_case.py`: `e471398ba380a941aa4864ad7b7fd6b9342d660a47ddac897d9f7ccdb4642a34` — exact approved candidate.
- `data/sandbox/cases/reacting-wet-free-slab-v1.json`: `f39c6a1ae42853c2bb6435143419785981bbdbfe9a1eb210904145f506ac990f` — exact reviewed sample.
- `tests/sandbox/test_free_case_build.py`: `006e6d06dafcd398a9b8cf144de72c77b461baeaf61a47fbe342731fb3d98dcb`.

The test imports actual production code and locates source case fixtures from the absolute test-file root, supporting an installed-package test run outside the repository working directory. Existing strict model separation and dry two/four-cell reconstruction tests are retained.

The added nonzero-B test correctly keeps schema-compliant initial A=2/B=0. It evaluates a later dyadic reaction inventory A=1.5/B=0.5 and exactly halved children, rather than relaxing the schema to admit initial B. The parent reports the rejected initial-B fixture and its original failure are preserved; this reviewer did not rerun that attempt.

At this later composition the test independently sums represented q coefficients using Fraction, requires q>1 and equal parent/child q, and checks actual skeleton interface energy against q*gamma*A0*t^2 with the returned arithmetic bound. This detects an interface evaluation that silently reuses initial B=0. The test also checks uniform normal replication, unchanged common tangent, exact additional bulk and template bulk error scaling, and conservative initial inventory/energy sums.

Evidence limits: the q*viscosity assertion compares declared coefficients only; both provider evaluations use zero rates. It does not demonstrate current-q viscous stress, dissipation, or the solved free-rate denominator. Those require nonzero-rate or actual free-solver checks. The q oracle uses constructed weights, complementing the existing builder weight-doubling assertion; it does not independently verify absolute beta/V0 construction against original case values. No trajectory, nonzero-B thermal forward/inverse, or native two/four spatial convergence is established by these three tests. These are limits on broader validation claims, not blockers to the inspected builder stage. The earlier candidate's old-builder parity check remains historical evidence; it is not present as a fourth test in this applied file.

Read-only source/test review completed. No EOS, test execution, install, repository edit, or scientific service approval was performed. Parent reports three tests passed in 0.48 s; that run was not independently repeated here.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **APPROVE** for the exact applied case-builder snapshot, with the evidence limits above.
