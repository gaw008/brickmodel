# Exact-time integrator code review

APPROVE for the isolated candidate's code/control-flow contracts. Confirmed source SHA256c225da066745682080a06b9af06ee80ca25f13e7dd128e52fba0c0665b726f0c and tests SHA256fc6e7ccf160906b9368694242759bc39d77b0b1b43f93988e420245b960fbaa5. Read full source/tests and actual tests06.log:16 passed4.73s. No repository edits, EOS or test rerun. Numerical quadrature review is separately owned by Averroes.

ExactIntegrationResult and ExactStepLedger are independent types rather than subclasses of legacy result/ledger types. Entry endpoints and breakpoints require ExactEventTime. Internal semantic times and actual quadrature intervals remain Fraction, and callbacks receive fresh exact-time objects. No absolute callback-time display projection is used. _duration_control explicitly rounds only a requested nominal controller duration downward to binary64 then adopts it as Fraction, limiting denominator growth without pretending arbitrary controller proposals remain exact. Origin-translation tests exercise identical dynamics even when all displayed times coincide.

Every speculative step performs accepted-state callback validation, local updates, cumulative N/E/stretch accounts, exact represented-stage stretch roundoff, ledger construction and component limits before global arrays/histories are appended. Proposed cumulative structures remain local until the final guard succeeds. Rejected trials and callback-domain failures do not commit candidate state. Cancellation and wall limits are checked before and after callbacks and before commit; evaluation/attempt/rejection counters retain work already attempted. Initial domain failure exits directly; subsequent domain/positivity failures reduce the step and eventually respect rejection/minimum-step bounds. Accepted-step and rejection budgets remain separate, bounding total attempted trials through their sum.

Endpoint remainder planning never silently accepts a sub-minimum interval; the two-half remaining-tail plan is allowed only within existing min/cap bounds. Exact stage midpoints cannot collapse due to a large origin. Component schema is fixed across all callbacks including speculative trials. Immutable arrays/mappings and exact ledger times are preserved by existing validation helpers and the new ledger constructor.

Tests cover cancellation after one accepted step, initial/trial domain failure, accepted-state rejection, resource limits without extra callback, schema change, positivity, mechanical-only adaptation, exact stage sequence, translated forcing and a nonmultiple endpoint. Successful type checks explicitly distinguish the new result/ledger from legacy types. No codec or resume API is added, and accepting an exact-time callback does not admit a legacy float-time physical host by inference.

No concrete blocking issue found in the assigned scope. This candidate remains a separate exact-time numerical primitive; native physical provider, ordered depletion packet and persistence admission require later explicit work.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — code/atomic-prefix/resource/type scope only, with separate numerical review.
