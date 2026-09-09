# Single speculative exact terminal executor review

Reviewed exact_terminal_executor.py SHA256 e3246434b9ee2d971b58e61e3afeba974e9273432fb26b987bdbcc194d8496e2 and test_exact_terminal_executor.py a7713739eaf035c7e2a26eddece481750ad2ebad6a3cf44eee63b8f5f82f0e1e. Read actual tests04.log: 12 passed in 0.15 s. No EOS or repeated tests executed by reviewer.

No blocking code issue identified for the stated single speculative terminal scope. Initial model identity, exact clock ordering, original roundoff policy/totals and actual water molar mass are checked. Initial modes must exactly cover positive liquid inventories. All observations use the actual exact adapter, whose source check brackets native dispatch; executor also checks original identity between stages. Transition content comparison excludes only the intended interface_modes field and retains all other physical fields, water backend types/implementations and energy identity. A tangent estimate chooses a predictor, not the accepted selected root: fresh midpoint rates feed complete exact root ordering and full-state panel construction before original writeback budgets and endpoint evaluation.

Inputs are not committed or overwritten. Intermediate predictor/root/panel/corrected state and candidate totals/operator are retained separately; a failed endpoint can therefore expose speculative candidates but status remains failed. No returned speculative_completed value implies event comparison, packet acceptance or trajectory convergence. Cancellation/wall exits retain observations and completed stages. Counters distinguish attempted calls/panels from completed ones, including failed predictor, source mutation, and endpoint failure; mode/root/writeback attempts are explicit. Evaluation counters count successful exact-adapter returns rather than low-level EOS invocations. Resource guards are cooperative before/after calls and between bounded pure stages, with the 256-level root routine bounded independently; external watchdog is still necessary for a blocked native call.

Tests exercise the real pure root/panel/writeback chain and exact adapter with instrumented native host and mode-constructor seams, not physical EOS. They cover alternate root selection from state-dependent midpoint, initial identity/mass refusal, coefficient-smuggling mode change, provider mutation, endpoint failure, predictor failure, exact ties, cancellation and wall limits before calls and after midpoint. Frozen result containers retain provider-backed evaluations; this is not an immutable serialized source snapshot or a legacy checkpoint format.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE bounded speculative executor and pure tests. Full event comparisons, cumulative trajectory audits, packet atomic commit and resume remain outside this implementation.

## Narrow DomainExit classification fix

Reviewed final source d004b1b750375df9ec79996929f70ccfc249440bfc7bbd39eb02e5edc9ea42fa and tests 09c07ff097e66f3c44c10baded4ad81e9f0ad8490c8e3d4a9474f9281e29ebf5 against retained before-domain-status.py. Only source changes are importing DomainExit and assigning domain_exit by exception type, after preserving cancellation/resource classification. Same-reason IntegrationError remains failed. No success-path arithmetic, callback, state, cost or rollback change. Actual domain-green.log: 13 passed in 0.15 s; original RED retained. APPROVE this narrow fix. The actual successful native evidence used e3246434, not this later source identity; no repeated native result claimed for d004b1b7.
