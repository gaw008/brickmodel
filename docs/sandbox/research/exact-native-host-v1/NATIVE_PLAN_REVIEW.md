# Native parity runner review

Reviewed run_native_parity.py SHA256 eb28d4b76577df135192933b63157d17a4046413770f421f6bad6ddfedfe9106.

Adapter identity now brackets both evaluations. Full initial state and original case bytes bind to retained four-cell data. The exact time contains an unrepresentable remainder, with no projection used by the adapter. Full WaterTransferEvaluation encode equality is appropriate: nested output has no elapsed-time field requiring removal. Finally saves runtime-after and structured traceback/report; original and output case bytes must remain equal. Output directory cannot overwrite a prior attempt. External 45-second watchdog remains parent responsibility. Two calls counts explicit host evaluations, not EOS calls during case construction. No native result claimed in this review.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE bounded point parity script only.

## Capture correction after retained native-attempt01 failure

Earlier statement that verification encode handles the complete returned tree was incorrect: current_host embeds a water provider whose native HEOSCandidate cannot be encoded. The first run failed during legacy capture before the exact call; that failure and prior script are retained.

Reviewed revised run_native_parity.py SHA256 ab53d1b884c30e50588b6b6acfd0b3657304be4d99b1c9ddef90d2bc36926477. capture recursively preserves all dataclass fields, mapping entries, sequences and numerical values. Only supported water provider objects are represented by concrete type, canonical physical/source/numerical inputs and full implementation descriptor, excluding nonserializable native runtime objects. This is the same explicit boundary used for source identity. Full captured output equality remains; no numerical result fields were dropped. Existing before/after identity, initial state, runtime and case checks remain. APPROVE the bounded attempt02 script, not a native result.
