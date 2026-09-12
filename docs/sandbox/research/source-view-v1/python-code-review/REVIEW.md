# Source-view Python/CLI/HTTP final review

**APPROVE for the recorded source versions.** No unresolved CRITICAL, HIGH or MEDIUM findings remain in this bounded review. The initial two HIGH findings and one MEDIUM finding were reproduced, repaired and independently checked. Initial findings and failures remain in `INITIAL_REVIEW.md`, `INITIAL_FILES.json`, `BOUNDARY_PROBES.json`, `INDEPENDENT_RED.log/xml` and `EVENT_REMAINDER_RED.log/xml`; this final result does not replace those failures.

Scope: new `source_run_view.py`; HEAD deltas in `source_study_service.py`, `local_app.py`, `cli.py`; corresponding source-view Python/HTTP tests. The root's added `arlabosse95` CLI parser and command branch are included. HEAD was `48568d3ba88f33368ce85d8f5809e3ede3335565`; changes remain in the shared working tree. No production files, source tests or run evidence were edited by this reviewer. Frontend review and actual browser verification are separate work.

## Findings closed

- **HIGH — cancellation from view-only mode:** `JobManager.cancel_job` now checks the absence of a case before storage lookup, worker notification or `request_cancel`. The independent check uses a nonempty temporary job store and verifies no cancellation file is published. Existing case-enabled behavior retains its original path.
- **HIGH — serialized response amplification:** `_DisplayBudget` charges JSON punctuation, UTF-8/escaped keys and strings, integer output and repeated reference values during traversal. `project_builder_path` applies the budget while expanding the DAG, and `browser_value` budgets the final browser representation before serialization. The original 70,536-byte fixture allocated 16,780,800 serialized bytes before rejection; the final independent test verifies the amplified list never reaches whole-value JSON serialization. Structure, per-projection and final-response limits remain explicit; this is not a claim that all admitted bundle data occupies only 1 MiB of process memory.
- **MEDIUM — malformed saved data escaping the error boundary:** explicit checks cover projection fields, sequences, references, binary64/fraction encodings, source registry shapes and event objects/payloads. The first repair still raised AttributeError/KeyError for a JSON-list event or missing builder payload; those two real failures are retained in `EVENT_REMAINDER_RED.log`. Final event structural failures become explicit unknown provenance. The catch only handles `source_view_builder_` errors: changed hashes and invalid paths still reject the view. Ordinary malformed projection errors remain controlled `RunError` or unknown provenance.

## Boundary assessment

The mount is supplied by the trusted startup caller. Browser requests cannot change it or supply artifact filesystem paths; asset IDs select only recorded assets. Loopback binding and the exact single Host, Origin and token checks remain ahead of route input processing. The source-view routes retain data-only parsing, bounded artifact reads, path containment and final same-byte hash verification. Passive record admission/decode is shared once per request with the display service; the added code has no provider construction, replay or restoration call. Rational components remain strings, and trial/failed/no-return identities and qualification flags are preserved. Canonical export preserves original record text and retains its separately documented larger limit and non-replayable scope.

The `arlabosse95` CLI parses explicit decimal/fraction moisture and temperature, requires K/degC, converts parse failures into the existing failed-JSON/status-1 protocol, and leaves source verification to the previously approved module. The independent Kelvin fraction check confirms `7363/20 K`, unknown heat at `1/10`, and false material/full-cycle qualification remain exact. The material module SHA is unchanged from its separate approved review.

## Verification and versions

`INDEPENDENT_GREEN.log/xml`: **7 passed in 1.06s**. Source hashes before and after those tests match. These checks use disposable fixtures, a fake persisted job and bounded passive JSON; no EOS, integration, restoration, socket or installation operation occurred. The final event tests accept either `RunError` or explicit unknown, both allowed by the original finding; `test_before_event_normalization.py` preserves the earlier stricter assertion and its real exception failures.

Author logs were read rather than counted as independent reruns: `REVIEW_PYTHON_GREEN.log` has 60 passing tests before the final event guard, `REVIEW_HTTP_GREEN.log` has 37 passing tests, and `REVIEW_EVENT_INTEGRITY_GREEN.log` has 6 final targeted passes. The root's Arlabosse CLI log has 60 passes. These are overlapping incremental checks, not a claim of a final combined full-suite run.

Exact reviewed versions are also in `FINAL_FILES.json`; source-view files agree with the author's `docs/sandbox/research/source-view-v1/REVIEW_FIX_READY.json`:

| File | SHA-256 |
|---|---|
| src/sludge_sandbox/source_run_view.py | 17caee81e5b1d82f7fd322a27ce440f7fcd5171289e29b0975dc81a272e36a29 |
| src/sludge_sandbox/source_study_service.py | 468128d311d9b3059bb6562d4ad0713dfc134f4b565b7c98222fc621d41d766d |
| src/sludge_sandbox/local_app.py | 975acc603d2055ece020c893ee096d67dcb9a833ef0f7b18145fd3cba938e89f |
| src/sludge_sandbox/cli.py | a61bc5628c334519486b2dea56c9e0dc5d97b4c675f502bda87f4a4f6512a1d1 |
| tests/sandbox/test_source_run_view.py | 0a3da521fd6d206c8f30b7c44d5808b40b3b56e96d6033a3673c4fe8a14d2b17 |
| tests/sandbox/test_source_run_view_http.py | 8e0d8bfa9212e897f916bb9cedb11deb3053913f2d4990ebf07088e8658f5394 |
| src/sludge_sandbox/arlabosse_desorption95.py | a197a22c095c87f4e388b86c648b7cdcd18cbf75eed34575e10ca09f347137f8 |
| tests/sandbox/test_arlabosse_desorption95.py | c187ced07649e85f34c8ba8de7bec89d6bce10dfbb858bdcc854634cfea8df66 |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded Python/CLI/HTTP code and security scope at the recorded hashes. This does not approve physical qualification, full-cycle completion or frontend/browser acceptance.
