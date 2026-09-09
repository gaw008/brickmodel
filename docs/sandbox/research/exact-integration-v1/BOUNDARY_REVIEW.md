# Exact-time legacy boundary tests review

APPROVE scoped two-test addition, SHA256 ab34ad67fe4126ee6b6a2b92e8a7d47f74c293b423949f1c8be5c3eb27988f89. Read-only review; no tests/EOS rerun or source edits.

The first test passes actual ExactEventTime endpoints to legacy integrate and requires the specific invalid_start error before any callback, then independently requires legacy ScalarProgram.at to reject the exact query. The callback deliberately has no valid Rates result, so the empty-call assertion is essential and correctly establishes pre-callback refusal.

The second constructs a valid independent ExactStepLedger with distinct exact times whose binary64 displays coincide, serializes it through actual encode, and passes it to the actual old checkpoint ledger decoder. Requiring checkpoint_invalid_ledger_time verifies the old decoder does not silently cast either exact endpoint or use its lossy display. It does not test or claim a new exact checkpoint codec or resume implementation.

No existing consumer changes are introduced. Imports reuse existing test fixtures only. No blocking issue found; actual final execution remains root-owned.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — explicit legacy refusal tests only.

## Final expected-error correction

Reviewed the one-line regex change to actual established ScalarProgram error invalid_evaluation_time. The retained source-tests-red-boundary.txt shows the correct BoundaryProgramError was raised, with only the original invalid_time regex mismatching (1 failed,184 passed reported). No production code or rejection behavior changed; previous review's expected error wording was imprecise. Final test SHA256 2edd775266cd8b3755406eb9286d7ba6092c724c4851fd45f4fe26bedd561b3f. APPROVE this test expectation correction. Final source rerun is root-owned; no EOS or rerun by reviewer.
