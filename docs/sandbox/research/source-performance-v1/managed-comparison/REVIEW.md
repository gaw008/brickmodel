# Complete matched RHS graph comparison

APPROVE for the bounded numerical and identity comparison. `final04.log` completed successfully in 0.012843083997722715 seconds. The comparison used only saved JSON, source data bytes, standard-library arithmetic and hashing: zero provider constructions, zero EOS calls, and zero new integration steps.

The original `rhs01/segment/events/000015.json` and managed `rhs02/events/000015.json` each contain 200 nodes, 229 references, six arrays, 456 binary64 markers, 24 Fraction markers, 41 qualification fields and 1,397 primitive values. The complete graph, node types, key sets, list order, lengths and reference aliasing were compared. Every numerical value, array element, Fraction, residual, branch, iteration count, source label and qualification is exactly equal. There is no tolerant numeric comparison or broad deletion of hashes or identities.

Only these 18 graph leaves differ, with every occurrence fixed to an explicit path in `COMPARISON.json`:

| Kind | Occurrences | Independent justification |
| --- | ---: | --- |
| Outer invocation phase label | 1 | `ordinary_source_segment` becomes `single_source_rhs_comparison`; physical phase fields remain equal. |
| Water canonical descriptor | 1 | Reconstruct the old descriptor with exactly the approved wrapper hash and new runtime manifest fields. |
| Water implementation identity | 4 | Recompute each side from its full recorded schema, provider, source IDs and descriptor. |
| Configuration identity | 1 | Recompute each full case JSON, including the manifest asset. |
| Storage/energy identity | 9 | Recompute the full original canonical storage operands, preserving all physical values and source data. |
| Column/operator identity | 2 | Recompute the original complete canonical column plus liquid transport binding. |

The case differs at exactly four paths: profile, manifest asset path, manifest asset byte length and manifest asset SHA. Both asset entries are checked against the actual retained manifest files. The descriptor differs only in wrapper SHA, kernel SHA, the three explicit execution-source SHA entries, and the explicit managed execution contract. The complete CoolProp configuration, fluid contents, runtime/library identity, reference convention, ideal-water assets, numerical limits and all other descriptor fields remain equal. Each new execution-source hash is checked against both the recorded installed runtime and current frozen source bytes. The old wrapper and kernel hashes are checked against the original recorded runtime.

All four derived identities on both sides exactly match their recorded identities. `COMPARISON.json` contains the full old and new values and a reason for every permitted difference, including the complete old and new canonical descriptor strings. `original-rhs.json` and `managed-rhs.json` preserve the original full input files byte for byte.

Three independent comparator controls also pass: changing saved pressure by one upward binary64 ULP, upgrading a false qualification to true, or replacing an energy identity with an unapproved value is rejected. These are comparator checks, not additional physical simulations.

The saved managed result records one verified scope, four entry and four exit validations, 2,045 native operations, no primary/exit error, and a closed worker lease. The scope's fluid/config/kernel identities are independently checked against the same approved manifest and descriptor. The saved result remains `material_qualified=false` and `source_resume_authorized=false`, with zero accepted integration steps.

The original measured RHS took 6.382242000021506 seconds and the managed measured RHS took 1.7192298330483027 seconds. This is one matched RHS comparison. Reconstruction uses different workflows and is not claimed equivalent; no full integration or firing-cycle speedup is established. A bounded closed worker checks source configuration at entry and exit under its explicit execution contract; this result does not claim that aggregation detects arbitrary hostile transient setters or changes the default per-call API contract.

The earlier `derive01.log` failure came from an incorrect literal in this independent digest reconstruction; the saved first script and result retain that failed audit attempt. `derive02.log` established the corrected four independent identities. `final03.log` then rejected this comparator's incorrect assumption that the case changed only its profile; the case also explicitly changes the selected manifest asset path/bytes/SHA. `compare_complete.before-case-fields.py` preserves that version. The final comparator admits only the four concrete case paths and validates the actual manifest bytes. No physics was rerun or altered to obtain the final pass.

Validation command: `/private/tmp/brick-water-backend-probe/venv/bin/python /private/tmp/brick-source-performance-v1/managed-comparison/compare_complete.py`. Standard-library AST parsing also passed. This review adds only scratch evidence and does not modify production code, tests, manifests, installed packages or native records.
