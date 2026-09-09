# Actual speculative terminal: independent saved-data review

Inspected native01 terminal-result.json SHA256 b932ded23eae77216406df7ccaa3435a54f1d38c7dd51f26d7a90d4f1fd30de9 and report, original retained failed-state source, input state/totals/policies, and both runtime manifests. Independent stdlib/Fraction audit_saved.py SHA256 a266618478230e96f48779f527bba7b2c234bf3a91b89ad7ea07915b87945424 executed successfully; no production numerical auditor, model imports or EOS calls used. audit-result.json records measurements.

The run used reviewed executor e3246434b9ee2d971b58e61e3afeba974e9273432fb26b987bdbcc194d8496e2. It returned speculative_completed after three initial/midpoint/endpoint observations, with 3 attempted/completed adapter evaluations, one predictor, one terminal panel and one mode transition. Initial state equals the retained failed-cell state with cell 3 already dry and totals.events=1; this was an uncommitted numerical state, not an accepted prefix. Endpoint has cells 2/3 dry and candidate totals.events=2. Runtime manifests are equal with 75 modules; original case bytes, input initial state/totals and original roundoff policy are matched. This review does not treat a later exception-status-only source revision as the same native runtime.

Independent arithmetic rederived every predictor and terminal shared-face species/energy integral, species source, cell work, power component and stretch integral from the actual saved first/midpoint rates and exact durations, checking once-rounded represented values. Complete raw N/E/stretch updates match represented ledgers under original absolute budgets. Maximum residuals: amount 3.6768315132835806e-17 mol, energy 6.898554109237729e-12 J, stretch 3.7401941270146863e-17. Component sums and recorded component/stretch quadrature errors match their exact Fraction values. Original state-to-observation and predictor-midpoint/terminal-endpoint bindings agree.

Root order selects cell 2 at level 27. Exact root samples bind to actual observation terms and separate phase evaporation rates. The complete input hash was independently reconstructed from all state/rates/clocks/source/policy/observations. Cells 0/1 are explicit positive-polynomial exclusions; whole-domain minima, coefficients and declared duration were independently recomputed. Selected dyadic enclosure signs, level/width and original time gate pass. Source label equals the digest of the saved original operator identity.

Writeback moves exactly the represented liquid correction to vapor, with all other amounts, E and stretches unchanged. Correction 4.868073823251425e-21 mol; independently integrated downward gross evaporation 1.5641070733517966e-12 mol; ratio 3.1123660944895586e-9 is below original 1e-8. Vapor storage residual 2.3656234608022867e-24 mol matches both paired state arithmetic and cumulative totals. Original local-ULP plus separately recorded exact clock residual, absolute correction, local/cumulative storage/element/mass and cumulative correction budgets pass. Candidate operator capture differs only in intended cell-2 interface mode. No tolerance was changed.

The first audit attempt incorrectly compared local_correction_limit_mol to local+clockresidual; actual record stores local alone and separately stores clock residual. That audit source is retained as audit-before-local-field-fix.py. Corrected audit compares each saved field to its own exact value and still applies local+clockresidual to the correction gate. This was an audit-schema correction, not a numerical/physical gate relaxation.

Scope: one actual speculative terminal and its saved numerical affine surrogate. No per-event/common-time refinement comparisons, successive passes, independent approach, global trajectory/pressure-work acceptance, packet commit, resume or material validation is inferred. Timing is not a speedup comparison. N/E budgets here are represented-ledger accounting, not total exact-integral truncation/error bounds.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE retained speculative terminal evidence in this explicitly limited scope; audit script awaits parent independent code review.
