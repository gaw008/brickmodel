# Source-view Python/CLI/HTTP review — initial findings

The initial AUTHOR_READY version has two HIGH findings and one MEDIUM finding. All three are independently reproduced without EOS, integration, restoration, sockets, or changes to any real run. Scope includes the new passive-view module and the associated source-study/CLI/local-HTTP deltas and tests. The frontend has a separate reviewer. Exact initial versions are in INITIAL_FILES.json.

[HIGH] View-only mode still publishes cancellation requests for existing jobs
File: src/sludge_sandbox/local_app.py:253
Issue: New view-only startup (`case=None`) guards validation, launch and continuation, but retains the unchanged POST `/api/jobs/<id>/cancel` route and unguarded `cancel_job`. Reusing a storage directory containing an existing job lets an authenticated view-only browser create that job's cancel.json even when this manager has no owned worker. An active external supervisor sharing that job can observe and execute the request. This violates the new read-only contract and can interrupt real work.
Fix: Reject cancellation in view-only mode before inspecting or mutating job storage; test an existing persisted job, not only an empty storage directory.
Evidence: BOUNDARY_PROBES.json records an actual cancellation file in a temporary fake job, `view_only=true`, `owned_worker_active=false`.

[HIGH] Response size is checked after amplified JSON has already been allocated
File: src/sludge_sandbox/source_run_view.py:31
Issue: browser_value limits individual strings and node visits, then calls full json.dumps before checking the 1MiB total. A hash-valid small builder DAG can refer repeatedly to a large shared string. A 70,536-byte graph with 256 references to 64KiB text allocated 16,780,800 bytes before rejection; the current limits permit gigabyte-scale amplification. The trusted mount path does not establish that archived JSON content is safe to expand. A selected observation can exhaust the local server's memory before the promised size guard fires.
Fix: Charge a cumulative encoded-byte budget during expansion, including keys, repeated strings and punctuation, and stop before constructing/serializing an oversized response. Preserve exact rational strings and do not silently truncate evidence.
Evidence: BOUNDARY_PROBES.json; the independent regression rejects reaching whole amplified-list serialization at all.

[MEDIUM] Malformed saved projection escapes controlled error handling
File: src/sludge_sandbox/source_run_view.py:159
Issue: A saved selected node with `fields: []` passes the outer JSON/dict checks and raises AttributeError at `.items()`. Neither `_source_trace` nor the HTTP error boundary catches that exception, so the request disconnects rather than returning a controlled error or explicit unknown provenance. Builder event hashes establish byte identity, not schema validity.
Fix: Validate object/sequence/field shapes and primitive encodings before use, raising RunError for malformed data. Include the builder event object itself in this validation.
Evidence: test_malformed_builder_cell_is_a_controlled_data_error fails with the actual AttributeError.

Independent initial checks: INDEPENDENT_RED.log/xml has **3 failed, 1 passed in 0.46s**. The passing test changes a disposable source asset between bundle admission and final reading; the final same-bytes hash guard correctly rejects it. Host/Origin/token protection, fixed loopback binding, opaque asset selection, lossless rational display, exclusive CLI output creation, and preserved trial/failure identities have no additional findings so far.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 2 | warn |
| MEDIUM | 1 | info |
| LOW | 0 | pass |

Verdict: WARNING — two HIGH issues should be resolved before merge. This report is the initial version; approval requires reviewing the fixes and recording their final hashes.
