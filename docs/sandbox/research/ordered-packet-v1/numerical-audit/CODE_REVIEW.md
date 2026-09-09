# Failed-capture diagnostic script review

APPROVE within the retained zero-packet research-evidence scope. Inspected source SHA256 9063d7b367a2ff0174aad4d4a1a34c5772280a02037650a95953cfc290947979. Read-only review, no rerun or EOS.

The script reads only saved files and hashes every input. It checks before/after runtime equality and the exact frozen core hash, requires the recorded correction-fraction failure with no events/packets/corrections, checks the single level0 refinement has no comparison result or endpoint attempts, and binds final state and still-wet modes. Its successful status is explicitly failed_capture_consistency_checked, not integration or packet success.

Missing comparison, root frames and failed correction amounts are explicitly reported unavailable rather than inferred. This is a narrow consistency check, not a complete integrity validator or conservation audit; the separate Fraction prefix audit covers accepted ledgers. Absolute temporary SOURCE path reflects retained execution provenance and would need a deliberately reviewed relocation for later replay. No blocking issue for archiving this actual bounded evidence.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — retained failed-capture consistency evidence only.
