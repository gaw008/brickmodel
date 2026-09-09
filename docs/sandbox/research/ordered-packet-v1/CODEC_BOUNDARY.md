# Ordered-affine packet codec boundary audit

Read-only source audit, no EOS or edits. Scope is future packet-core isolation from existing single-event persistence, not a requirement that this primitive already support native wet packets. Carson owns core implementation; root owns any persistence boundary changes. Interface-specific addendum may follow the author's final contract.

## Existing entry points

- event_record.encode_depletion_result (line119): exact DepletionResult type gate, then dynamically serializes dataclass fields. Schema selection depends only on comparison endpoint counters, choosing v1/v2. This does not identify packet semantics.
- event_record.decode_result (line139): accepted names derive dynamically from fields(DepletionResult). New dataclass fields can silently expand the old schema shape. Each event also derives allowed fields dynamically from DepletionEvent through event()/object_fields().
- event_record.restore_final_operator (line128): direct public helper rebuilds modes from record before full audit. It currently does not independently validate schema; grouped changes cannot be interpreted as audited single-cell events merely because final mode arrays are valid.
- audit_depletion_record/_audit (line180/187): calls decode, checks v1/v2 based on pressure policy, then single-event assumptions: strictly increasing event times, exactly one terminal per step, one cell per event/correction, one active-mode update per event. Those are incompatible with a packet containing several ordered roots and corrections inside one accepted panel. Keep them intact for old schemas.
- AuditedDepletionRecord._restore: reconstructs DepletionPolicy and audits before decode; changes to policy constructor defaults must not automatically grant packet support. Core _restore_continuation accepts only this audited wrapper and then checks original policies/prefix, so this is the direct-core resume bridge too.
- run_service._run_event: declares water_depletion_v1, constructs/compares event policy, calls restore_final_operator before audit on resume, invokes core, then old encoder before saving raw depletion result. A packet result must fail before being labelled/encoded as water_depletion_v1; a guard only after encoding is too late.
- run_service._event_cancelled: shallow v1/v2 cancelled shape gate, not audit. resume_run then validates source/case/policy and _run_event performs full audit. replay/run_case _event_replay compares saved/fresh policy and calls the same _run_event; do not add an ordinary-integration fallback on packet rejection.
- verification_case._build_depletion_policy: exact case policy keys, v1/v2 schema only, terminal_method exactly affine_midpoint. This currently blocks packet fields/methods supplied through ordinary application cases. Preserve this until a dedicated case schema is implemented. _validate_event_resume_policy is structural scalar preflight, not proof of packet support.

## Minimal fail-closed choice

Prefer a distinct packet core result/policy type and entry point while the codec is absent. The existing exact type(run) is DepletionResult encoder check then fails naturally. Do not flatten packet members into old DepletionEvent objects or call the ordinary checkpoint encoder as fallback. Core packet results can remain inspectable via explicitly diagnostic encode output that makes no old record-schema claim.

If the core must extend DepletionResult/DepletionPolicy instead, add one explicit legacy-single-event guard shared by old encode/decode/audit/restore boundaries. Require terminal_method in the original {'euler','affine_midpoint'} and reject every non-default packet marker/policy/evidence/result field. Reject packet opt-in even when cancellation precedes the first packet, when packet collections are empty but packet policy is enabled, or when status is failed/unsupported. Do not infer old semantics solely from len(events)==0. For legacy default None/empty tails, deliberately omit them on encode and use a frozen old field set on decode so old canonical records remain unchanged; dynamic dataclass field reflection is insufficient schema versioning.

_run_event should guard the actual built event policy before initial snapshot/model work, and guard the returned result before old encoding. _event_cancelled should refuse packet markers early while leaving full validation to audit. Raw packet result fields and packet methods must also be refused in restore_final_operator before mode reconstruction, since it is callable independently. Existing v1/v2 pressure-comparison meaning must not be repurposed for packets.

## Future full codec version

Use a new explicit result/case/integration-kind version and deliberate field schemas. Required work spans event_record typed packet decoding, proof/source membership and complete ordering audit, shared panel ledger binding, every per-cell correction and cumulative budget, atomic mode transitions, failed/cancelled prefix audit, and policy restore. Extend run_service continuation boundary counters to packets/members/proofs and define replay equivalence without flattening packet semantics. Update verification_case declarations/building and run_provenance catalog semantics. Audit the full packet as an atomic operation: a legal earlier member does not authorize committing a partial later-invalid packet.

Useful no-EOS regressions: direct encoder rejects packet-result type; old-schema forged packet payload rejected even before first event; direct decode and restore modes reject packet evidence; cancelled packet-opt-in prefix cannot pass old resume/replay; ordinary legacy encoder canonical bytes unchanged; failed packet admission retains original accepted prefix and never invokes ordinary fallback. Do not require live wet packet integration for this boundary increment.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | design risk |
| LOW | 0 | pass |

Verdict: APPROVE current boundaries for existing single-event semantics; dynamic field/schema coupling must be guarded before packet fields share these dataclasses. This is a prospective integration risk, not a claim that current single-event records are already unsafe.

## Author interface addendum

Carson's planned interface is now known: DepletionPolicy optional trailing ordered_event_policy (None/default omitted; ordered_affine_packet_v1 opt-in), mandatory affine+nesting, packet continuation rejected before EOS; OrderedPacketResult subclasses DepletionResult with packets and packet_schema; no old DepletionEvent field changes. Actual current encoder already uses type(run) is DepletionResult, so this subclass is rejected correctly, not silently flattened. Preserve this exact-type check. For this interface, root's minimal additional boundary guard is rejecting non-None ordered_event_policy in old audit/restore/service policy boundaries, including zero-event cancelled prefixes. Do not change old record fields or v1/v2 schemas to accommodate the subclass. The subtype distinction plus policy rejection closes the prospective ambiguity without building the full packet codec now.
