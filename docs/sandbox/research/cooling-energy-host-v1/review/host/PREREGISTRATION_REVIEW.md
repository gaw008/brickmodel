# Native energy host preregistration review

Reviewed repository `docs/sandbox/research/cooling-energy-host-v1/PREREGISTRATION.md`
at SHA-256 `930dc01adad74d8eed7b53f47816db1d6424bb2977ba3adff10406cfc7ca7cde`.
This bounded review used source reading, direct budget arithmetic, and read-only
JSON inspection. No trajectory, integrator, reference solve, or candidate
parameter change was executed.

## Findings

[HIGH] Energy acceptance inequalities omit absolute residuals

File: `docs/sandbox/research/cooling-energy-host-v1/PREREGISTRATION.md:44`

Issue: The cell and global energy gates on lines 44–45 are written as signed
residuals divided by 80 J being at most `1e-8`. Literally, arbitrarily large
negative errors pass. The source B-path preregistration explicitly used absolute
residuals, so this is an accidental weakening of its unchanged `8e-7 J` gate.

Fix: State `max |Delta E_i - sum Q_i - sum P_i| / 80 J <= 1e-8` over every cell
and accepted prefix, and `max |sum Delta E - cumulative boundary heat| / 80 J <=
1e-8` over all prefixes. Preserve the same 80 J denominator and threshold.

[LOW] StepLedger is incorrectly described as storing accepted states

File: `docs/sandbox/research/cooling-energy-host-v1/PREREGISTRATION.md:21`

Issue: Native `StepLedger` stores accepted-panel endpoints, face/source
increments, cell work, optional work decomposition, and their roundoff evidence.
The actual states and node times are `IntegrationResult.states` and
`IntegrationResult.times_s`; they are not fields of `StepLedger`.

Fix: Name the result's states/times and its separate step ledgers explicitly.
For a successful return the endpoint arrays have `len(states) == len(times_s)
== len(steps) + 1`; each ledger covers the corresponding consecutive endpoints.

## Checked semantics and scope

- The native method really compares one discarded full SSPRK2 panel against two
  accepted half panels. Only the latter panels contribute exchanges and named
  work components. Rejected trials and the discarded full panel do not enter
  the accepted ledger. The two half panels are combined into one `StepLedger`
  per accepted outer panel; intermediate RK stages are not additional accepted
  states in `IntegrationResult`.
- An explicit interior breakpoint is reached as an actual binary64 endpoint,
  with the integrator's exact clock reset to that represented endpoint. Initial
  and final endpoints plus 99 declared interior nodes therefore provide 101
  common accepted states for a completed run. There is no native dense output.
- The stored B-path `fine.json` and `reference.json` under
  `cooling-stress-v1/execution/cooling01/worker/` each contain the same 101-node
  `times_s` array. Those nodes equal `0.1*k`; 35 of them differ bitwise from
  `k/10`. Reuse the saved array directly for breakpoint construction and verify
  the two reference node arrays are identical; do not interpolate to repair an
  independently regenerated exact-key mismatch.
- Stored `INPUTS.json` confirms initial temperatures `(304, 304)` K and the
  preregistered two-cell B-path constants, geometry, and boundary. The original
  reference method is `independent_dense_rhs`; its independence concerns RHS
  assembly, not independent experimental data. Reading its saved temperatures
  alongside the saved fine T-state trajectory respects that boundary.
- Fixed inventories `[2, 3]` mol are explicitly interface test bookkeeping,
  outside the constant volumetric C law. No species definition, density,
  chemical mass qualification, gas EOS, or material validation is inferred.
- The represented target E's zero input uncertainty, initialization evaluation
  roundoff, numerical inverse budgets, trajectory errors, and physical parameter
  uncertainty are kept distinct. The `1e-10 J` inverse allowance is not in
  conflict with the native `1e-11 J` absolute policy entry: native adaptive net
  energy scaling is `1e-11 + 1e-9 * 80 = 8.001e-8 J`, while the absolute entry also
  constrains arithmetic ledger residuals rather than material/decoder error.
- `1e-9 K` inverse error is 4000 times smaller than the `4e-6 K` reference gate
  and 400 times smaller than the `4e-7 K` inter-run temporal gate. `1e-10 J` is
  8000 times smaller than the `8e-7 J` trajectory ledger gate. These are numerical
  policies; none establishes real-material accuracy.
- The 60-second internal limit for each of two sequential calls and the single
  130-second external limit are consistent upper bounds. The latter also covers
  import, initialization, comparison, and persistence. They do not guarantee
  completion within budget. Native wall-time guards run at evaluation/step
  boundaries; the external supervisor supplies the overall deadline. A hard
  kill can only preserve evidence already obtained and made available; missing
  final output must remain missing, not be relabelled a completed final state.
- The two maximum step sizes imply roughly 2000 and 4000 outer accepted panels
  before adaptivity or floating endpoint splitting; the 12000 accepted-step caps
  permit additional refinement. Identical adaptive tolerances mean the actual
  coarse and fine step ratios need not be exactly two. The preregistration claims
  a fixed maximum-step comparison, not a proved temporal convergence order.

## Follow-up verification

Both findings and the saved-node clarification were corrected before freezing.
Re-read the changed document at SHA-256
`613acf986f1824603ff50a3995658e0a20e03630d307a4361703d238bee321de`:

- Cell/global gates now explicitly use `max_i abs(...)` / `abs(...)` and retain
  the unchanged `8e-7 J` gate.
- Accepted states/times now explicitly come from `IntegrationResult`, separately
  from the exchanges and work in `StepLedger`.
- The driver is required to inherit saved B-path `fine.times_s` and check exact
  equality against `reference.times_s`, without generating replacement nodes.

No remaining actionable preregistration defect was found in this bounded scope.
The initial findings above are retained as review history, not open findings.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — corrected preregistration at the follow-up hash, with no change
to physical inputs, trajectory gates, resource ceilings, or research scope.
This review has not executed or accepted a trajectory.
