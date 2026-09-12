# Independent flash code/Python and first-native-plan review

**APPROVE the nominal single-cell implementation and the numbered-01 static execution plan.** The one original HIGH finding is fixed; no unresolved code finding remains. Source `low_moisture_equilibrium.py` SHA-256 is `26f329aeb9203986701e1c43dffde48394516f5234eda6324f22a3cfd34f5ded`. This is not approval of a successful physical outcome, a certified inverse or a material qualification.

The reviewer performed no EOS/native execution, installation, author-suite rerun or production edit. Two independent manufactured probes passed in **0.12 s** (`FINAL_GREEN02.log/.xml`). These replace actual source admission and property calls with the author's explicitly manufactured analytic fixture; they are not real source validation. The original failing probe, candidate source and output remain in `CALL_RED01.log/.xml`, `CALL_RED01_PROBE.py.txt`, `CANDIDATE01.py.txt` and `READ_SNAPSHOT01.json`.

## Original finding resolved

**[HIGH, closed] Returned provider observation lost on post-call timeout.** The initial candidate called its elapsed-time guard after a provider returned but before saving that result. The first manufactured liquid-boundary call returned normally, consumed the elapsed budget, and raised `FlashFailure` with provider count 1 and no accessible returned object. Actual RED: **1 failed in 0.12 s**. The fixed engine saves the same `last_completed_provider_result` and `(kind, args)` before the guard, and copies both into the failure. The independent GREEN uses object identity to prove the actual returned object survives. Unexpected ordinary provider exceptions now become named failures with their cause and accumulated observations, rather than escaping the promised result shape.

## Numerical and source-boundary review

The public API admits exact low-moisture storage and chemical types, validates policy/input types and positive finite carrier support, and retains the original represented full-U target. Exact Nt is split into requested Nc/Nv; their individual projection errors are bounded and returned, without resetting the target, deleting dry excess energy, moving carrier inventories or adding heat/latent terms. Point validation checks actual inventory, model identity, T and the complete original pressure interval, with source/thermal-chemical compatibility rechecked before return.

The pressure prefilter algebra inverts the fixed available-volume mechanical relation with conservative directions for declared volume/liquid-volume errors and inward pressure reserve. It avoids indiscriminately evaluating an inadmissible all-vapor endpoint. Stable-liquid monotonicity remains an explicit conditional assumption; two boundary values are not presented as an interval EOS certificate. Zero total water has its own no-water-chemical-potential branch. Empty/no-sign scan nodes break adjacency and remain recorded; failures inside attempted temperature solves terminate with a bounded trace.

The inner composition solve retains actual chemical and peq/pv residuals, side samples and a nominal x bracket. The outer solve uses original complete-U residual plus stated given-composition error, and local side samples or a sufficiently small visited T bracket. The second independent probe verifies both returned bracket widths/containment and the existence of actual saved endpoint chemical/energy signs. The policy correctly says that unvisited domain holes and composition-propagated energy errors remain unverified. `certified_temperature_error_bound_k` and composition-energy/error fields stay null; output is a separate `NominalEquilibriumCandidate`, never `SourceWetInverse`.

Secant proposals remain interior and every third proposal is a midpoint. Calls/iterations and elapsed checks are finite and explicit; the call budget covers top-level provider invocations, with no claim to count/preempt nested EOS work. Failures retain completed trials; source/model qualifications remain conditional, instantaneous equilibrium is a virtual assumption, and no kinetic timescale or full-cycle claim is added.

## Numbered-01 native plan, static only

The single-cell constructor retains the original .06 mol condensed water, 1e-6 mol vapor, 333 K, .01 kg dry mass, 1e-5 m³ available volume, declared carrier values and full-U reference. It constructs no column, transport or arbitrary Kph. Native policy explicitly records the original U/T and pressure gates, 500 provider calls, 40 composition/temperature iterations and 50 s inner elapsed limit; the wrapper supplies 60 s process supervision plus 5 s cleanup.

The driver writes original input hashes/policy, initial state and raw returned candidate before acceptance checks. `FlashFailure` output includes accumulated trials/counts and the last actual provider object/context. Existing `-I` process supervision snapshots the installed package, required source assets/upstreams, numerical runtimes, and the separate scratch flash/case modules. The clarification correctly limits the U error gate to the evaluated composition. Numbered outputs use `exist_ok=False`; a later carrier-320 design requires its separately listed plan and output number, preserving any first-case pressure/domain failure. No successful equilibrium or within-domain root is assumed in this review.

`FINAL_READ_SNAPSHOT02.json` records the reviewed code, tests, case, driver, supervisor wrapper and plan hashes. A full input freeze and actual process outcome remain the root runner's responsibility. Supervision covers the original process group, not escaped sessions.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded nominal flash and first-native static plan; no EOS, temperature-certificate, material or complete-Goal result is inferred.
