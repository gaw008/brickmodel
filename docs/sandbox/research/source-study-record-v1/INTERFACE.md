# Source study record interface (baseline be506b6)

This is a complete passive run-evidence format with actual observation, trial, prefix, ledger, root, writeback, dry-path and pressure-result contents. It is not a provider/model checkpoint. It neither constructs a water backend nor attaches archived process identities to current objects.

## Core API (implementation agent owns record/schema/audit and unit tests)

```python
encode_source_study(
    roots: Mapping[str, object], *,
    contexts: tuple[SourceObservationContext, ...],
    captures: tuple[Mapping[str, object], ...] = (),
    metadata: Mapping[str, object] | None = None,
    provenance: Mapping[str, str] | None = None,
) -> bytes

decode_source_study(raw: bytes, *, expected_contexts=None) -> SourceStudyRecord

import_saved_source_study(
    raw: bytes, *, source_format='source_multicell_native_v1',
    provenance: Mapping[str, str] | None = None,
) -> SourceStudyRecord
```

`roots` has explicit stage keys: `seed`, `proposal`, `approach`, `refinement`, `common_endpoint`, `transition`, `failure`. Missing/unreached stages may be absent. Runtime objects must belong to a closed list; object annotations do not permit arbitrary objects. Each actual dataclass field is retained. Detached live fields become explicit reference records, not fabricated runtime instances.

`record.canonical_bytes`, `.sha256`, `.roots`, `.contexts`, `.captures`, `.metadata`, `.provenance`, `.observations`, `.audit`, `.check()` are public. Containers and numerical arrays are immutable snapshots. `.roots` is a Mapping with passive `SourceStudyNode` records and exact primitive/array leaves; accessing `.roots['transition'].numerical_event_accepted` reads the saved value, not new acceptance authority.

`.captures` is a tuple of complete immutable mappings in original top-level capture order. It preserves original ordinal, input, time, mode vector, object-admission assertions, evaluation or failure, and all known per-attempt metadata. `.observations` has exactly the same length/order; each successfully validated evaluation yields a `SourceObservationRecord`, and a failed capture yields `None`, including a returned evaluation whose post-return validation failed. That raw return remains complete in `.captures[index]["evaluation"]` and is counted as `unvalidated_returned_top_captures`; it is not a successful observation. Thus `--capture-index` remains the original zero-based index, even though the stored record DAG deduplicates repeated observations internally. No index is silently renumbered.

`.metadata` contains all remaining explicitly supported original top-level run fields, including initial-energy attempts, returned candidates, declared inputs and policies, constructor/callback budgets and counts, source/model provenance, original live-parameter identity assertions, and the entire `new_pressure_study` wrapper (actual extra requests/returns/failures, partial wet pairs/declarations and original status). Import never drops an unrecognized typed field or unsupported type; it fails explicitly. String/mapping metadata remain reported claims, not source authentication.

`.contexts` is a tuple of distinct original `SourceObservationContext` values, keyed by complete operator/energy/fixed-mass/mode identity. Explicit capture modes are retained; missing original modes remain unknown, not inferred from zero inventory.

`.audit` is an immutable mapping with `validation_scope`, `checks` counts, `verified` scope labels, `not_verified` labels and `material_qualified=False`, `resume_authorized=False`, `source_assets_verified=False`. It covers complete known schema, successful observation associations, original attempt/time/policy bindings, available pure prefix/root/writeback arithmetic and committed cross-stage/ledger/gate associations. It does not call runtime stage `.check()` through fake adapters. Live identity assertions, source-wide EOS hypotheses and numerical qualification are not re-established from JSON. Original negative-inventory seed failures remain valid evidence and are never relabelled success.

## Encoding and resource boundaries

Reuse exact_record primitive pack/unpack/canonical for valid finite binary64, Fraction and arrays, without changing its registry. Use the source_observation closed schema and validators for all four source-rate variants. A new private closed registry owns the study-specific types and exact field sets. Do not import a class named by JSON.

The canonical format is a bounded acyclic content-addressed node table. Every reference resolves, each node digest is recomputed, extra/unused/cyclic nodes and unknown tags are rejected. Structural deduplication does not change capture indices, step count or claimed process-local live identities. Complete numerical contents remain in nodes; digest equality is not an arithmetic audit.

Observed parent native record: 45,936,648 bytes, 510,041 value nodes, maximum depth 37, 82 distinct tagged types; details ACTUAL_NATIVE_TYPES.json. Reviewer measured the outer wrapper separately (larger). Final import and canonical byte ceilings are each 64 MiB, depth 96, parsed values 2,000,000, DAG nodes 200,000, array elements 250,000 per array, and integer size 4,096 bits. The actual complete original N3 canonical record is 805,474 bytes / 1,371 nodes / 32 capture indices; the closed registry supports 96 classes. Arrays must pass shape/product/value quotas before allocation. Exact integer bit budgets must accommodate the real recorded Fractions (reviewer observed 1,169-bit integers), without unbounded inputs.

## Live fields and compatibility

- SourcePrefixTrial.adapter and SourceTerminal.dry_adapter: passive adapter reference with original private identity and explicit modes when actually available; energy identity and fixed masses remain complete fields of the surrounding trial. Frozen original identities must be captured without invoking a now-failed live guard.
- SourceInversePressure.storage / SourceDryPressure.storage / SourceSharedDryVolume.storage / SourceSharedWetVolume.storage: passive storage reference. A saved process address/digest is not a live object and cannot pass same-object admission.
- Shared volume `.volume` is a complete passive ManufacturedFixedFluidVolume and is retained, including original uncertainty.
- Wet observation water object IDs are recorded integers, and every complete WaterState/reference/implementation/assets field is retained. No state_tp call occurs during codec use.
- Legacy research serializer deliberately omitted adapter/dry_adapter/storage and lost Python aliasing. Import records this explicit absence rather than inventing those objects or pretending original pair input-binding hashes can all be reproduced from absent process identities.

## Root-owned boundary

Root owns source_record_io.py, source_observation_service compatibility wrappers, source_study_service.py, CLI and service tests. The service writes with exclusive publication and reads regular bounded files. `inspect` selects original capture index/cell and returns existing SourceObservationRecord values plus full study audit metadata. `import` accepts only the named old format and writes the complete new format once. Unsupported/partial formats get named errors, never a summary-only or hash-only output.
