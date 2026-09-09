# Exact autonomous host candidate review — pending binding fix

[HIGH] Thermal water backend implementations omitted from exact adapter identity
File: exact_free_host.py, ExactFreeWaterTransfer._binding

_digest(operator) calls the established water-provider canonicalizer, which includes reference/assets/numerical limits but deliberately omits concrete backend type/implementation. The additional explicit SHA only covers operator.chemical.water. Actual thermal water providers in operator._fluid_storages can be distinct instances; the existing WPT bridge checks reference/assets, not backend equality. Thus a thermal provider's implementation can change without changing the new exact adapter identity. Existing paired_pressure_host explicitly handles this same distinction.

Fix: bind concrete backend class and implementation for every actual thermal provider as well as chemical water, with the same check before/after evaluation (or enforce a strict shared backend contract). Add an instrumented distinct thermal-provider mutation test that exercises the real _binding rather than monkeypatching it away. No EOS is necessary.

Other scoped inspection: legacy FreeSolidSlab evaluate retains _check_state then float-time validation before the unchanged shared body. Legacy WPT evaluate retains interface precheck then base evaluation then unchanged transfer assembly. New autonomous entry points explicitly restrict direct FreeSolidSlab/WPT types and do not manufacture a float timestamp. Exact adapter rejects implicit query types and brackets calls with identity checks. No other concrete blocking issue found so far.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — close thermal backend identity gap before approval. No source edits or EOS by reviewer.

## Final repair review

Reviewed exact_free_host.py SHA256 1153884bad187c94d156c351a85aacb11983d9bff346c02ceba4d64277bb3918 and test_host_seam.py a97facba635f79b716798f82a170a8913ae30ecf202444afc6a962363a607f99. The prior HIGH is closed. Additional traversal follows every canonical dataclass/mapping/sequence slot, stopping at supported water providers to bind concrete module/qualname and complete implementation digest. This supplements complete canonical physical input binding while excluding native kernels/caches. Pre/post checks and structured binding errors remain.

Actual binding-green02.log: 9 passed in 0.12 s. Real digest/chemical check/provider identification exercise four distinct shells: chemical and thermal water plus both ideal bridges. Four post-callback implementation mutations and one pre-callback backend-class replacement are rejected; unchanged control passes. These are identity tests, not native physical evidence. Original RED and prior review are preserved. Legacy shared-body diff retains prior arithmetic and check order. No EOS/tests rerun by reviewer.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE scoped autonomous adapter and shared-body extraction; no event integration or material admission.
