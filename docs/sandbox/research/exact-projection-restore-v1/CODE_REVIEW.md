# Independent numerical projection restore review

APPROVE source 6c5ec48fda6c2600ca9000bd9b4c87c2f09a8cfa58d83e4c8e73abc0cd9e6d25 and tests 75dfbe4f33d4a6f447bc9c2c9b521fc2327f6e4dae3370c1e755439d15b2fd94 for the explicitly bounded projection contract. No blocking findings.

The public entrypoint requires actual bytes and the exact external operator type, reparses and consumes fresh validate_binding output, and reconstructs values only through a fixed whitelist. Mode-specific operators are rebuilt from the externally supplied original operator and checked by actual live identity. No input-controlled class import, live inverse reconstruction or fabricated WaterTransferEvaluation occurs. Historical TerminalObservation and Observation remain explicitly labeled EvidenceNode projections.

Every reconstructed value object must roundtrip to its complete original packed representation, including derived fields. The whole result is checked before and after canonicalizing committed ledger references. Exact start/end pairs locate one accepted ledger, complete ledger values and before/after states must agree, each committed accepted index is used at most once, and corrections remain bound to their selected cell and selected clock evidence. The actual object alias is then verified with `is`, matching the existing audit_commit id(ledger) seam. Speculative copies remain historical evidence rather than being counted or committed again.

All accepted states/ledgers and numerical evidence remain immutable through their existing constructors or immutable decoded backing. The returned frozen wrapper retains canonical bytes and record SHA, keeps all costs/refinements/attempts, and always sets resume_authorized=False. A typed result alone is not an audited continuation; no existing integrator admission is changed.

Independent pure test rerun: 8 passed in 9.79 s. Tests include exact re-encoding, real ledger aliases, cancelled prefix preservation, duplicate/missing/value-mismatched ledgers, live source mutation and correction cell/clock attacks. Tests use the explicitly instrumented source-bound numerical fixture and do not establish native-host restore evidence. No EOS, installation, repository or author-source edits occurred during review.

Remaining scope: this helper restores a numerical projection and canonical aliases, not complete physical callback objects or all acceptance proofs. Separate original-prefix, terminal proof, comparison and resource audits plus an explicit continuation gate are still required. Historical observations must not be consumed as live inverses.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — typed numerical projection only, no resume authority.
