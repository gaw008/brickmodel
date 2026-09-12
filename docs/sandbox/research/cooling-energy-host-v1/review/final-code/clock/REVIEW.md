# Independent clock-delta code review

Status: **APPROVE the scoped core-clock delta**, with no actionable findings above 80% confidence. Independent mathematical review and a newly preregistered formal native-energy attempt remain separate requirements. The original `native01` failure is unchanged.

Reviewed the complete diff in `src/sludge_sandbox/integration.py` and `tests/sandbox/test_integration_clock.py`, the surrounding integration/ledger contracts, and the preserved baseline and red/green logs. Baseline core SHA256 is `cda9310e0cb4c6941e85e56e1ce17162b70388d92df5b1329251d60d10317576`.

| Reviewed file | SHA256 |
|---|---|
| integration.py | `784d21f65c616bb435ec04ed35a67c6083d362ad9a8115a8a7705a2ebf4848d1` |
| test_integration_clock.py | `6f00a0aaa47c359f57334fbdf31c7283e797bd69c1e960b0a272cca9124efd99` |

The new branch acts before any candidate state or ledger is committed. It applies only when a candidate strictly precedes the current forcing knot and would leave a tail lacking valid RK stages. It chooses a strictly earlier candidate endpoint only when both replacement intervals independently have representable interior midpoints and positive half-stage weights. The candidate exact clock is reanchored to that new represented endpoint. Previously accepted times and states are not changed; knot identity and ordering remain intact.

Full and half RK paths continue using their actual endpoint differences. Face/species/reaction/work and optional mechanical-stretch quadratures inherit those same durations; the existing unequal-half error factor is retained. Acceptance checks, rejection handling, positivity, component accounting, nominal step policies, accepted-step/rejection limits, cancellation, and wall limits are unchanged. The new branch itself never lengthens a candidate. The existing documented distinction between nominal step limits and rounded actual endpoint durations remains applicable.

The shared `stage_midpoint` helper enforces the former stage admissibility condition. A truly adjacent forcing-knot interval cannot be repartitioned and still returns `unresolvable_stage_time`; no forcing knot is merged or renamed. Numerical completion is not guaranteed where no admissible split exists, or where the additional accepted panel exhausts the existing budget.

## Independent verification

- Four new public-API linear-flux checks passed in 0.15 s using the current source module. They cover both .005 s and .0025 s nominal steps, with the separately rounded 0.30000000000000004 s knot inside a longer .2–.305 s interval. Every accepted prefix is checked against an independent Fraction antiderivative for species amount, heat, and named work; the subsequent segment completes without crossing or dropping the knot.
- With the original nominal panel-count cap (20 or 40), the additional partition correctly returns `resource_limit / accepted_step_limit`. All returned prefix ledgers retain the analytic balance. The implementation does not silently grant an extra step.
- Author evidence was read, not rerun: `RED_CLOCK.log` records the two intended `unresolvable_stage_time` failures against the original core; `SOURCE_GREEN.log` reports 183 passed after the delta. The earlier `RED.log` is an invalid-component-key fixture failure and was not counted as clock-regression evidence.
- `git diff --check` passed. This reviewer ran only the four authorized linear-flux regressions, with bytecode and pytest cache disabled. No thermoelastic/B or old trajectory was run. Source, source tests, preregistration, and failure evidence were not edited; all review writes are under this directory.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — scoped clock code only, at the recorded hashes; no formal native-energy success is implied.
