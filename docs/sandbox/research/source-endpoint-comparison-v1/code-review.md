# Source endpoint comparison review

Baseline `00ec847`; read-only review of the two new source/test files, with surrounding source trial, sample validation, source bounds, strict event-policy codec and depletion-policy contracts. No production edits, EOS calls, installation or old 143-test rerun.

No confirmed unresolved defect in final source `a4927606c0c7392cde4b93c2e972ea9c02ba461d459caae1530a78c3aea90d77` or tests `c1730039a394d9e36f4e0c8653a29bf53b2fb0a51ff20f4684e3505facafb0c3`.

The checked successful source trial supplies two actually evaluated states at the same exact endpoint. Amount/energy differences and both error-radius sums use exact Fractions of represented values. The four original absolute event tolerances remain distinct from normalized integration discrepancy. Missing policy is explicit. The complete original policy, including nested approach, ordered packet and pressure-comparison fields, is reconstructed through the existing strict codec and retained without executing those mechanisms. Result checks rebuild measurements and reject modified gates, status, event-time or material claims.

The pressure comparison is explicitly limited to reported temperatures. Nonzero inverse-temperature uncertainty leaves `full_inverse_pressure_gate` unresolved; passing all four reported gates still grants neither event-time acceptance nor material qualification. Exactly zero inverse-temperature uncertainty allows only the corresponding recorded numerical pressure comparison scope. No new source physics is executed during comparison/recheck.

Actual bounded verification: **10 passed in 31.06 s**, zero failures/errors/skips (`final-review.log`, `final-review.xml`). Five independent probes exercise full nested policy copy and validation, forged qualifications, symmetric exact measurements, and 27 rational derivative/bound cases. Five selected production tests cover the no-new-source-evaluation path and all four independently tightened event tolerances. Both Python files parse; `git diff --check` passes. Full hashes and parsed XML counts are in `FINAL.json`.

## Pressure continuation path cross-check

Reviewed `physics/PRESSURE_PATH.md`, SHA-256 `8464ac7d4e918e424bfdd3e9f288189efd19ea21e49e9b526339488398770999`, against the actual prescribed-temperature closure, declared envelope, native envelope constructor and local water response implementations.

For fixed inventories and constant available-fluid volume, `G_P=-D/P`, where `D=Vg-Nl*P*vP`. Thus implicit differentiation gives `(Nl*P*vT+Ng*R)/D`. Substituting the recorded thermodynamic identity `uP=-T*vT-P*vP` gives `(P/T)*(1-Nl*uP/D)`. Under `vP<=0`, positive gas inventory and a whole-box `|uP|<=B`, `D>=Vg>0`; the proposed global Lipschitz bound follows and has Pa/K units. The 27 manufactured rational cases check positive, negative and zero expansion, zero liquid as an algebraic limit, and nonpositive volume-pressure derivative. These cases test the algebra only.

The continuation argument is conditional: every allowed constant volume needs an initially enclosed root, a smooth stable EOS branch on the entire rectangle and the whole-domain response bound. Strict containment of the propagated pressure interval prevents boundary escape along that branch. Bootstrap tightening is justified only after the global bound establishes the smaller enclosure. Reusing uncertain volume does not prove correlated cancellation between endpoints.

The current native `B=1e-4` envelope is explicitly a manufactured conditional numerical envelope. Pointwise HEOS stability and derivative checks, or a finite grid of such calls, do not prove a whole-domain bound, universal root existence or interval-backend error enclosure. Certification additionally needs the same EOS/backend/coefficient identity and validated root/derivative/model-error bounds. The reviewed endpoint source **does not implement this continuation helper** and does not claim the conditional proposal as certified pressure propagation. Zero-liquid algebra likewise does not widen the current wet-trial domain.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — endpoint accounting at the stated hashes; pressure continuation remains a conditional future implementation.
