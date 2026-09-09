# Packet boundary changes review

APPROVE scoped changes. Read actual git diff and complete new boundary test file. No source edits, EOS, or test rerun. Final test edit uses explicit empty event/correction arrays; prior7-pass report predates that edit, so combined final execution remains root-owned.

Inspected SHA256:
- src/sludge_sandbox/event_record.py: b3e2c8dca11ab3c50e75aed4606e3716ef51e26a563a8a9c54eae29dad89f787
- src/sludge_sandbox/run_service.py: 21a81f18859fb0a2d9aa9f4e3057c9103ca8c87c8cbc23de8718474ba1ef5d0a
- tests/sandbox/test_ordered_packet_record_boundary.py: 4d5cf463af7559da8c39bae2b7b30665932419f3cdf41bba63de1ab19adb0186

_legacy_record_fields extracts the existing decode shape/schema checks without changing their accepted set and now applies them before restore_final_operator reads state or transitions modes. New packet fields, including an empty packet collection, and a new packet schema are rejected. The existing exact DepletionResult encoder type check continues to reject the planned OrderedPacketResult subclass. Since packet fields are on the separate subtype, dynamic reflection on the original base class does not expand the legacy field set in this design.

_audit rejects non-None ordered_event_policy before record canonicalization, decoding, source/model binding and event traversal. Thus an empty-event prefix cannot obtain an old audit certificate for a packet policy. _run_event rejects the policy before snapshot, restored-mode processing, policy encoding or integration. Its earlier assignment of integration_kind is only in-memory metadata; no result is persisted before the rejection here. Existing case exact-key validation remains unchanged.

Tests cover altered schema, empty/nonempty packet fields before restore, ordinary mode restoration, subtype encoding refusal, service rejection before absent built fields could be accessed, and early audit refusal with explicitly empty event/correction arrays. The latter intentionally tests guard precedence rather than validity of a reconstructed ordinary empty prefix. No concrete blocking issue found; no full packet codec or resume support is claimed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — scoped fail-closed boundaries; final combined test execution pending root.
