# Final independent native-runner review

APPROVE the prepared single experiment using exactly:

- run_native.py SHA-256: a7916d30ee0eb0abf5852a76c5b92eec3a70acd1b0e130cd05a1dc556f2d6e71
- PREREGISTRATION.md SHA-256: 68d1e4b1cf41b96d262574fff57e6d7e659eea6d4619b9820edd0e130d815551

The runner, registration, unchanged predecessor and both fixed helper hashes were independently read and checked. Production and runner files were read-only. The initial registration had swapped the labels of the three IntegrationPolicy tolerances; the final two corrected lines now match the unchanged code: relative 1e-8, amount 1e-7 mol, energy 1e-3 J. The original document and correction record remain in the author evidence directory. No numerical threshold was changed by that correction.

The new 1e-11 mol liquid scenario is explicitly identified, with H derived from its actual initial evaporation probe and U from one actual forward source evaluation. The source-volume/error declaration, caloric/EOS providers and envelopes, gas inventories, geometry, transfer coefficient, original integration controls and event/roundoff gates remain unchanged. The affine terminal method is explicit, and the water molar mass comes from the actual chemical reference and is checked against the storage reference. This is a new numerical case, not a retrospective amendment of the older 1e-6 mol results.

The actual mode change constructs both a new SourceWetColumn and a new ExactSourceColumn. The observation wrapper therefore compares all column fields except interface mode and its derived identity cache, plus exact source type, energy and species identity; it allows only the original wet object or a different explicit dry object. This agrees with with_depleted_cells and does not route dry calls through the original wet adapter.

Resources are consistent: 16 actual callbacks per seed/approach/shifted trial, 24 per dry path, total 97 = 1 + 3*16 + 2*24, and the existing 210 s outer signal request. The expected 32 calls is not asserted as an observation. Constructor starts and completed reference anchors are recorded individually, and every attempted source callback is saved before execution, followed by returned data or its real exception. Native internal updates are not falsely counted as constructor anchors. Returned candidates are persisted before transition postprocessing, and known exception records plus chained causes are retained. Actual completion and conditional numerical event acceptance are separate; no pressure-pass or material-qualification assertion is introduced.

The recursive serializer preserves dataclass type/fields, exact Fraction numerators and denominators, array dtype/shape/data, and explicit nonfinite diagnostic tags, omitting only named live adapter/dry_adapter/storage fields. Adapter provenance is separately retained. Atomic pending-file replacement is retained.

Three independent pure control cases passed using the actual save, timeout and top exception-handler AST from these bytes: postprocessing failure preserves returned diagnostic/candidate context and the nested cause; the runner's own timeout persists resource_limit and its TimeoutError; an ordinary TimeoutError persists failed rather than claiming the outer limit. Exact fractions and nonfinite array diagnostics survive strict JSON persistence. Evidence: runner_failure_paths.py, runner-failure-paths-result.json/log and the three runner-*.json outputs. These probes use explicitly synthetic diagnostic data only, invoke no run(), construct no physical model and call neither source evaluation nor EOS. They do not substitute for the authorized native experiment or validate physics.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — the documentation finding is closed. The parent may perform the single preregistered run after its source/installed checks; no native run was performed by this reviewer.
