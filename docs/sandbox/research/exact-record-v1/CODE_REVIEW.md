# Exact record preliminary review

Snapshot 9634890467bf716d868520923dbcf010de51d74c45b246a0f2d5cb3ea5d87ae5 is not approved. No EOS or repository edits. One pure instrumented malformed-record reproduction executed.

[HIGH] Actual phase observation graph cannot be encoded.
CellWaterTransfer.equilibrium contains WaterPhaseEquilibrium.liquid, then WaterLiquidChemicalState.state: WaterState. WaterState is absent from CLASSES, so actual native wet observation capture raises unsupported_capture_type:WaterState. Existing test fixture uses equilibrium=None. Add the complete real data-only WaterState/reference/implementation closure and a saved-native-phase roundtrip regression without rebuilding providers.

[HIGH] Nested observation Rates structure bypasses strict validation.
Only top-level committed states/ledgers receive constructors. Nested Rates remains EvidenceNode, with array-type checks but no rank or complete state pairing. Actual valid fixture record with terminal_attempts[0].observations[0].evaluation.rates.reaction_species_mol_s changed from matrix to shape[2]/two values is accepted. Validate every nested state/rate/ledger constructor and observation/state shape association; preserve the rule that midpoint derivatives cannot be checked against the wrong initial state. Check component schemas and derived residuals too.

[HIGH] validate_binding verifies bytes but leaves public supplied object unchecked.
It reparses record.canonical_bytes but returns None, without rejecting a manually replaced record.result/states/binding. Callers may then consume public fields that were never verified. Return the newly checked object as the only verified result and/or strictly reject inconsistent public fields. Add a dataclasses.replace attack. This is an object/bytes binding issue, independent of resume admission.

Bytes-backed decoded arrays fix the previously reported mutable-buffer issue. Duplicate JSON keys, exact rational/float/time tags, fixed registry and no-provider restoration are positive boundaries, but do not close the above gaps.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 3 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — resolve before application or native record claims.


# Final repair review — supersedes preliminary disposition

Source SHA256: f03abafa6251f3ad57a73b3622a2fd852c7246c376bd4cc43fbaebec06db4408

Test SHA256: 450a41c18a48d009e934a8d7c4be5138ddb9dee4afbb8602cd691d99b95c6139

APPROVE within the explicit numerical-evidence codec boundary. All previously reported HIGH findings are closed in this snapshot:

- WaterState, WaterReference and WaterImplementation complete the real liquid-equilibrium data closure without restoring live providers. Independently checked the retained fixture bytes and original native result SHA/pointer; they match exactly. This is saved-data verification, not a new EOS evaluation.
- Every nested ConservedState, Rates and ExactStepLedger passes its original constructor and a derived-field roundtrip comparison. Terminal observations additionally bind face/cell/species and mechanical rate shapes to their actual saved stage state. The previous one-dimensional reaction-array attack is rejected.
- validate_binding returns the freshly parsed, externally bound record. The returned object is the validated consumer object; replaced public fields on the input wrapper receive no validation authority. No resume authorization is implied.
- Whole committed prefix mechanical presence, strict six-diagnostic types (excluding bool), and selected-cell/liquid/vapor correction indices are now checked. The wrong-cell correction test specifically reaches correction_selected_indices; it does not claim a physical correction fixture.

Canonical primitive handling, duplicate-key rejection, explicit type allowlist, immutable bytes-backed arrays and mapping proxies remain intact. Frozen operator identity is captured without invoking a failed live getter; actual external binding remains a separate live guard and reconstructs mode-specific identities from the supplied original operator. Source-state conservation and every speculative numerical proof are intentionally not re-audited by this codec.

Independent pure test rerun: 18 passed in 12.05 s. Author tests09 records 18 passed in 12.20 s; earlier failures are retained. No native calls, installations or repository edits occurred in this review. Apply the saved equilibrium fixture alongside the portable test; temporary conftest overlay is not production code.

Residual scope: decoding validates structure and selected committed associations, not every speculative comparison, cumulative physical conservation, pressure certificates, EOS results or restart admissibility. Those require the existing independent audits and a separately designed resume layer. APPROVE does not promote compact research JSON into resumable state.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — explicit evidence codec only; earlier HIGH findings resolved.


## Numeric-policy compatibility final delta

APPROVE source 18fc962896b26a786620880e6190b882358af001f215fa602a50eea96b85118f / tests e5c0993d2625b0e87c72650e6f79e568ef60243b697a72cfb01d14ea5efb8bbe. The complete production diff from f03 is limited to float-annotated values admitting exact Python int or float. It preserves integer representation and identity, excludes bool and subclasses, and does not change explicit six-gate/observation checks, costs, canonical float parsing or policy constructor validation. The actual original case energy_scale_j=1 regression preserves its int through the codec and explicitly refuses True. Author tests10: 19 passed in 12.03 s; original integer-policy RED retained. No additional review findings; no EOS. Prior approval did miss this legitimate-policy compatibility gap and is superseded by this repaired snapshot.
