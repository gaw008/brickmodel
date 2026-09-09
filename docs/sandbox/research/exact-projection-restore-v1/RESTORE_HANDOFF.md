# Numerical projection restoration only

Source SHA256 6c5ec48fda6c2600ca9000bd9b4c87c2f09a8cfa58d83e4c8e73abc0cd9e6d25.
Portable test SHA256 75dfbe4f33d4a6f447bc9c2c9b521fc2327f6e4dae3370c1e755439d15b2fd94.
Actual restore-tests02: 8 passed in9.80s. No EOS, installation or repository edits.

API `restore_exact_projection(raw, *, original_operator, case_sha256, runtime_identity) -> RestoredExactProjection` consumes fresh bytes, reparses strict record and consumes the externally bound validation return. It accepts no caller-provided cached record or audit token. The wrapper always declares resume_authorized=False.

Typed ExactDepletionResult, frames, paths, ledgers, states, policies and value-only numerical root/writeback evidence are reconstructed from a fixed whitelist. Actual external operators are rebuilt only for saved modes with live source checking. Saved TerminalObservation and Observation remain explicitly labeled immutable EvidenceNode numerical projections: they are not WaterTransferEvaluation and contain no fabricated live inverse or provider graph. This is therefore a numerical projection, not a general Python object roundtrip or a callback-ready historical evaluation.

For each committed event the accepted step is uniquely located by exact start/end and complete packed ledger equality. Before/after states and correction cell/selected clock association must agree. The frame's terminal panel is then replaced to reference the SAME actual object from result.steps. This repairs the current core's id(ledger) correction-association seam without changing any saved value. Full packed result must match the original decoded result before and after rebinding, and the re-encoded strict bytes are identical in the complete roundtrip test. Historical speculative attempts/refinements and cumulative costs are retained.

Tests cover completed and cancelled prefixes; record/codec equality; actual object aliases; duplicate frame, missing step, changed ledger and correction cell/clock association refusal; fresh bytes/source requirement. Correction negative controls inject explicitly fabricated association attacks into an exact-zero fixture, not a claim that a correction was physically required. Existing test_exact_record.make is an instrumented source-bound numerical fixture; these tests do not run EOS.

No root/panel/refinement/resource audit is granted by this helper. Constructors enforce their own value contracts, but the separately implemented terminal proof, full original-prefix, six-gate comparison and cumulative-resource audits remain required before any continuation mechanism. No continuation argument/API is added in this task. Actual core use after restore must acknowledge the saved-observation protocol; callers must not treat historical EvidenceNode observations as live provider evaluations.

Apply only exact_projection_restore.py and test_exact_projection_restore.py after review. The local conftest is a temporary relative-path overlay, not a production change.
