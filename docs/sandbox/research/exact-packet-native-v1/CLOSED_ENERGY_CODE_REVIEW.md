# Closed energy and constraint audit review

Read-only review of audit_closed_energy.py SHA256 d90ab4d91f08f9f0fe55c21ff07932a3a0f3317167d4700d259aba3796251248 and actual attempt01/closed-energy-audit.json. No script edits, repeated execution or EOS. Saved report core hash matches the actual result previously reviewed.

APPROVE. Exact reference volume is represented area times half-thickness divided by cell count; current slab volume is the reference cell volume times the sum of normal stretches times the common tangential stretch squared. Summing energy across the same four cells gives the correct closed-system check ΔE + external_pressure*ΔV. The script verifies no outer reservoir/temperature boundary, zero boundary species/energy flux integrals, and zero body work at every accepted panel, so omitting boundary/body cumulative terms here is justified by actual recorded zeros. External traction is not double-added to total energy; its integral plus pressure-volume change is reported separately.

The maximum absolute closed-energy residual covers every accepted prefix, not only the final endpoint. Cumulative absolute cross-cell constraint sums are monotone, so the final constraint gate covers every earlier prefix. Nonzero per-cell integrated constraint work confirms the fixture exercises coupling. The original F(2e-8) J gate is explicitly checked equal to four original per-cell energy absolute budgets and matches the earlier registered audit convention inspected at free-native-events-v1/audit.py:203-217. No tolerance was adjusted from observed results.

Actual report: 32 prefixes checked; maximum closed-energy residual 6.166833498764901e-11 J at state index 12; cumulative absolute constraint sum 2.3107070843279913e-20 J. Both pass the original 2e-8 J target. Report qualification correctly says the nonlinear pressure-volume residual includes quadrature error and is not implied by local ledger tolerances, spatial convergence or material validation. Prefix schema/correction checks and source/case binding are covered by the separately reviewed companion audits; this script is a targeted additional balance check.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE code and retained all-prefix closed-energy/constraint evidence in the stated scope.
