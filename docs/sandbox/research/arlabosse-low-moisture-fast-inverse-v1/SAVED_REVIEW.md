# Fast-inverse native01 — bounded independent saved review

**PASS: 77 passive checks, zero failures, 0.058 s.** No EOS, solver replay, author-test rerun, installation or production edit occurred. The review reads saved results and source text only; `audit_saved01.py` and `SAVED_REVIEW01.json` retain the actual checks.

The case differs from the preceding low-W case only by the numerical-policy import and explicit inverse selection. The driver differs only by WORK path. Physical initial states, decoded construction points, actual m/q/water source nodes and all non-strategy provenance match exactly. Numerical wrapper identities and the declared strategy differ as intended. Both original 232-gate reports are green with identical IDs and unchanged conditions.

Both runs contain 2 steps / 6 RHS / 0.05 s. The 12 saved inverses in each run independently pass target/residual correspondence, inventory/source identity, full-U residual plus error <= 1e-5 J, outward temperature error <= 1e-6 K, bracket, iteration and full pressure-interval checks. Fast-run maximum U allowance is **6.728870728417887e-6 J** and maximum T bound **4.1916267019105373e-7 K**. The dry-end excess contribution remains included.

For the new run, pure Fraction arithmetic verifies each predictor/accepted cell's Nc, three gases and U balance; each face decomposition; accepted global and prefix balances; and the exact sum of recorded arithmetic fees. Energy fee **2.2575484726129193e-12 J** and inventory fee **8.19592630629623e-18 mol** match the saved totals and original budgets. This is a minimal ledger recomputation based on the actual saved face/phase integrals and signed writeback errors; it does not repeat the prior full low-W physical/source audit.

| Saved comparison | Previous inverse | Explicit fast inverse |
|---|---:|---:|
| Measured integrator wall time | 25.0924087499734 s | 9.990391541039571 s |
| Recorded candidate iterations, summed | 280 | 48 |
| Inferred storage evaluate calls, iterations + 2 per inverse | 304 | 72 |

The wall ratio is **2.5116541876157896** for this one fixed case. The evaluate counts are inferred from returned iterations and the reviewed solver structure, **not independently instrumented native EOS counts**. The new driver/supervisor times are 11.305650207970757 / 16.53868054196937 s, within the unchanged budgets.

The saved comparison correctly retains unequal final trajectories. New-minus-old final temperatures are **+7.852733006075141e-7 / +2.922678845607152e-7 K**, and state U differences are **−1.2664713722188026e-10 / +1.1641532182693481e-10 J**; condensed/vapor differences also match the saved report. No bitwise trajectory identity or convergence conclusion follows from the common acceptance thresholds.

All **2782 supervised inputs** match after correctly comparing metadata's nested `sha256` values to status's hash strings; `inputs_unchanged=true`, exit 0 and leader reaping are confirmed. The earlier dict-versus-string diagnostic is not an input-change failure. Shared old/new input paths differ only at the two reviewed source/installed Column files; the new solver is the explicit added module. **182 package files / 175 modules** match freeze, installed snapshots before/after tests/native and current bytes. Saved installed XML has **23 tests, zero failure/error/skip, 51.862 s**. No check was rerun.

This is a single-case performance and saved-correspondence result. Material/training qualification, temporal/spatial convergence, general speed, equal-budget success and the complete Goal remain unproven. The subsequent implicit draft is outside this frozen run.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **PASS** for the bounded saved comparison.
