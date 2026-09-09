# Exact core continuation candidate

This adds actual continuation to the exact core, not to the legacy service, CLI, or saved arbitrary providers. No EOS or repository mutation was performed. Native validation remains outstanding.

## API

`integrate_exact_depletion(original_initial, actual_original_operator, start=original_start, end=original_end, integration_policy=original_policy, event_policy=original_event_policy, continuation=ExactContinuationRequest(...), cancel=None, on_commit=None)`.

The frozen request contains `parent_bytes`, an externally authoritative `expected_parent_sha256`, `case_sha256`, and `runtime_identity`. Runtime must equal the currently executing runtime both before and after admission. Previous read-only added-module compatibility is NOT execution compatibility. Callers must retain the request/parent bytes and their provenance; the unchanged numerical result schema does not itself add a service lineage envelope.

Admission freshly parses original canonical bytes and runs all four actual audits against explicit original inputs and the live original source. It then restores mode-specific live operators and numeric histories; historical observation nodes remain data, never live inverse/provider objects. Canonical committed terminal ledger aliases are retained. A previously issued partial report or manually replaced object cannot authorize continuation.

Only cancelled accepted interior prefixes, or exhausted resource-limit prefixes, are accepted. An exhausted resource-limit prefix returns the same reason with zero physics callbacks. Original policies, initial state, start/end, all committed and discarded histories, cumulative costs and correction totals are preserved. Remaining step/rejection allowances derive from original cumulative counters. New active wall starts at continuation entry, includes all admission and restoration, and is added once to prior cumulative wall (outward binary64 representation). Idle time is excluded. Restarted adaptive work is explicit; no bit-identical global adaptivity assertion is made.

The optional `on_commit` receives immutable `(accepted_steps, committed_packet_count, exact_time)` only after a nonempty globally audited atomic publication. No state/provider/operator is exposed. Return values are ignored. Observer exceptions return a failed result with the already committed prefix retained. Default `None` keeps previous numerical behavior; comparison against baseline removes only elapsed-wall telemetry.

Original component schema is seeded from the historical first accepted ledger. Every later commit recomputes original-initial N/E/component/mechanical cumulative budgets with historical corrections and once-only panel aliases. The original step budget counts accepted ordinary panels, interrupted replan panels, and terminal attempts; rejected ordinary trials retain their separate original rejection budget.

## Tests and limitations

Pure tests use the existing explicitly instrumented two-cell numerical fixture, with no water EOS. Its partial typed host shells need the same constructor/geometry/observation seams as earlier pure proof tests. The four audit functions themselves are not mocked; current runtime is replaced with the explicit fixture identity only in tests. This proves numerical control and record/resource handling, not native material behavior. All original numerical gates remain unchanged.

Evidence includes repeated cancellation/resume; cancellation after a packet; cancellation inside an uncommitted speculative refinement with all prior evidence/costs retained; final strict encode and all-four-audit passes; exhausted credits with zero callbacks; hash/runtime/original-policy refusal; admission-wall debit; observer failure; and full baseline numerical parity excluding elapsed telemetry. First parity failure compared real wall durations and is preserved in tests02.log. The first speculative-cancel trigger used a nonexistent fixture mode and did not cancel; tests04.log is preserved, then corrected to the actual `depleted_no_nucleation` mode without numerical changes.

Historical wall/cost consistency retains the original audit qualification: recorded authoritative telemetry is debited; it is not independently reconstructed OS scheduling or every discarded callback from arrays. This core candidate is not standalone artifact authentication or service execution permission.

Final combined validation: `tests07.log`, **25 passed in 14.91 s** (9 continuation tests plus 16 original exact-driver tests). Command uses `run_tests.py` to preload the candidate before pytest loads the repository-wide conftest and fixed codec registry. `tests06.log` preserves the mixed-import harness failure: repository conftest preloaded the old result classes before temporary overlay, so strict identity checks correctly refused mismatched classes. No production validation was weakened; the corrected harness preloads one coherent candidate module identity.

Frozen driver SHA256: `5c06f392fa8415a8b6d57e9605e04074052cc9a2e04225a5df9ec35b8a2028a2`.
Admission SHA256: `a3819fba56f7bdf8009be1f8c7a06449f7e6c2750e663c2063ecbf56103c7432`.
Tests SHA256: `13b7b353eb0a8d17155cf5a896e460b0dcc93a5d208139a5c2646bc733ed0a1d`.

## Portable application paths

- `exact_depletion_integration.py` → `src/sludge_sandbox/exact_depletion_integration.py`, hash 5c06f392fa8415a8b6d57e9605e04074052cc9a2e04225a5df9ec35b8a2028a2.
- `exact_continuation_admission.py` → `src/sludge_sandbox/exact_continuation_admission.py`, hash a3819fba56f7bdf8009be1f8c7a06449f7e6c2750e663c2063ecbf56103c7432.
- `test_exact_continuation.py` → `tests/sandbox/test_exact_continuation.py`, hash f17531439b8869a9efdebac6f829a210b630e14a2824ba107f22d3f49f941141.
- `exact_driver_baseline_v1.py` → `tests/sandbox/exact_driver_baseline_v1.py`, hash be323c820fe9f0c0981bb3bc7b4db817c8931c2501e704e394ae85a4c815a16b.

Portable tests contain the same nine tests, only changing the adjacent frozen baseline snapshot filename. No temporary paths, git commands, or dynamic source checkout dependencies. `tests08-portable.log`: **9 passed in 8.90 s**. The temporary preload helper is NOT a production artifact; installed tests import the formal package directly.
