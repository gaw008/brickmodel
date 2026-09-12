# Time-refinement harness review

APPROVE for the two preregistered executions. No open findings remain. The original 1-step run stays immutable; steps 2 and 4 each reconstruct the same raw case and perform full zero-time initialization, with duration 1 s and unchanged physical/source/error gates. This review did not execute EOS, a native driver, the series, or the old test suite.

The driver checks every initialization/dynamic ledger, full shapes and exact time grid; reconstructs each Nt/U target and shared J; checks actual mechanical inventories, full μ from the saved liquid/excess/actual-vapor values, pressure/error and conditional fixed-composition bounds; and charges state/face projections once with initialization inheritance. Cumulative water, energy and Q−H−decomposition use every dynamic ledger. Returned construction/init/run objects are saved before resource checks. Budgets remain 40/100/150/165+5 s for each new attempt; failure stops the next attempt, and exclusive paths prevent a retry from replacing evidence. Existing supervisor complete status already requires leader reaping; containment remains limited to its original process group.

The one MEDIUM finding (new harness drift between attempts) is closed: existing SERIES_STARTED.input_sha256 now binds the complete live input set and both new before/after snapshots. Author evidence preserves actual BINDING_RED01 (3 failures) and BINDING_GREEN02 (3 passes, 0.03 s). The earlier 9 passive author checks, including isolated --help, passed in 0.75 s. These are author runs read as evidence; I did not rerun them.

Comparison uses exact saved-value differences. Both adjacent differences must be nonzero, same-direction and above the declared necessary diagnostics before nominal r/p is shown; nonshrinking trends remain visible. Those diagnostics do not bound full equilibrium/log/material error, and no Richardson or convergence certificate is claimed.

Final SHA-256: driver `8201d27fe02584ddc39144591e63ca844a3db858f00d72b58618cf715b3749c8`; compare `1b79eba87475c8a925fd6238887d8a901164871c252852d91021d9ffc8bd49a0`; series `731224d1d7958b45238cd348292c6b6177c9beb3555d37a9c7f6e48a62b3def4`. PLAN/BASELINE and complete reviewed hashes are in FINAL_READ02.json; original FINDING01/READ01 remain preserved.

## Review Summary

| Severity | Open count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | one resolved |
| LOW | 0 | pass |

Verdict: APPROVE — bounded static execution review, not a scientific qualification.
