# Independent saved-result review — 500 s conditional probe

**PASS / APPROVE.** Reusing the short-run Fraction audit, the single passive execution completed **56 independent grouped checks with zero failures in 0.047 s**. The original driver has **299 distinct passing gates**, consistent with the preregistered long-probe plan. No application import, EOS, native replay, installation or test run occurred.

The case differs from the prior short case only in its declared fixture identity, common per-cell carrier inventories **O2=0.0000714 mol, N2=0.0002686 mol**, and the **333 K / 0.1 W/K** heat bath and control source ID. Saved initial Nc **0 / 0.06 mol**, Nv **1e-6 mol each**, T **330 / 333 K**, dry mass, geometry, water/source definitions and original domains match those declarations. The exact represented carrier sum was retained; no decimal correction was imposed. Kph remains manufactured, while the boundary is virtual.

All **five 100 s steps / 11 RHS / final time 500 s** completed. Every local and transport substage's Nc, three gas inventories and U update closes exactly with its recorded signed writeback residuals. Shared local BE J/E/H, outer-cell-only outlet, heat-only slow boundary, zero internal gas exchange and cumulative water/U prefixes agree. Both projections and all used face/bath fees sum to **6.36376e-12 J** and **1.68727e-17 mol**, within the unchanged **1e-8 J / 1e-12 mol** budgets. The **20 after-local/final full-U inverse records** retain original domain and energy/minimum-Cv/T gates: maximum U allowance **6.91097e-6 J**, maximum T bound **4.30519e-7 K**.

Recomputed net water out is **0.0002872405470952494 mol**, leaving **0.05971475945290476 mol**: about **0.478718%** of initial water removed. Shared-reference carried energy **H=-69.12653546465545 J** and bath heat **Q=13.398875802931798 J** give **ΔU=82.52541126758615 J** with recorded roundoff. The sign of H follows the common formation reference. Final T is **330.233380565 / 332.793121731 K** and P **93502.312818 / 105552.464280 Pa**; original carrier inventories remain.

Measured integrator/driver/supervisor times are **21.462466 / 22.591371 / 27.827406 s**, within original **60/80/100 + 5 s** limits. Exit **0**, leader reaped, and all **2,786** normalized input hashes agree. **184 package files / 177 modules** retain the prior source/installed freeze through `AFTER_LONG_PROBE.json`; the unchanged original installation record remains **46 passed**, without a new test execution. Supervisor containment is limited to the original process group.

This is cost/domain feasibility for one manufactured/virtual scenario. No refinement was performed; long-time/all-field/spatial convergence, material qualification and complete drying remain unestablished. A reviewer-script preparation SyntaxError is preserved in `PREPARATION_FAILURE01.log`; it was corrected before the sole passive audit and did not affect native data. Evidence: `audit_saved01.py`, `AUDIT01.log`, `SAVED_REVIEW01.json`, `REVIEW_SHA256.json`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — this saved conditional long-probe result only; no material or full-Goal completion claim.
