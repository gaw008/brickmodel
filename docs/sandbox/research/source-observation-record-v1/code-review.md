# Source observation codec/service final code review

Approve the final source/test bytes listed in `CODE_REVIEW_FINAL.json`. No unresolved findings remain in the reviewed scope. Production files were read-only throughout; this reviewer ran no model/provider/EOS, installation, or old numerical test suite.

The codec keeps a closed registry of 39 passive dataclasses, using the existing exact-time and exact-record numeric primitives without altering the older registry. It preserves complete field sets, rejects unknown or misplaced types, retains constructor-derived fields by checked reconstruction, and snapshots arrays through read-only storage. Its interface explicitly separates caller-declared provenance and content binding from physical/source authentication, material qualification and resume authority. The four supported source observation families are covered by the author's actual manufactured fixtures; those are numerical tests, not material evidence.

The CLI selects one explicit capture, carries original indices/context and complete-file hash, and displays the original saved values and source declarations. It does not assert full-run verification, source-asset verification, or material validation. The small N3 fixture retains exact original captures 0 and 16, including ordinals 1 and 17. Its documentation identifies the full original artifact and extraction scope.

## Closed findings and actual evidence

- The service's 600-level outer identity previously raised an uncaught RecursionError. The same payload now returns structured `failed/source_capture_identity_shape` in 0.0496 s.
- The actual idle FIFO previously blocked the size-only reader. The same reader AST now rejects the opened non-regular descriptor in 0.0443 s. The full CLI FIFO regression is separately present in the author's 15 passing tests.
- The original outer/inner capture-time mismatch was statically identified here and reproduced by Root. Independent final controls reject it with `source_capture_time_mismatch`; a regular-file symlink remains usable. Those two controls took 0.1373 s.
- The frozen codec previously accepted a missing internal shared gas observation, swapped gas states belonging to different cells, and a detached mechanical source-label set. The same three passive payloads now reject with specific presence/inventory/source errors, while the untouched saved observation remains valid. This took 0.1280 s.
- The codec previously accepted an invented `full_inverse_direction_certified` direction label alongside the original false full-inverse flag. It now rejects the original payload with `source_liquid_direction_qualification`; the original observation remains valid. This took 0.1205 s.

All initial accepted/rejected results, source snapshots and payloads remain in their original locations. Fixed results are in separate `service-fixed-review`, `codec-fixed-review`, and `qualification-fixed-review` directories. The fixes use original producer structure, exact represented n/Vgas arithmetic, original R, source-label containment, and the original two direction labels. They introduce no EOS call, scientific tolerance change, or qualification promotion.

The author's saved XML records 30 codec tests before the association fixes, then 34 final codec tests with zero failures/errors/skips in 2.538 s. The final service suite has 15 passing tests in 0.862 s. These XMLs were read, not rerun by this reviewer. Final aggregate source and installed XML each record 93 passed, respectively 15.940 s and 16.030 s. The reviewed installed package has 131 Python modules and 138 package files; all 138 current source/installed hashes and all seven frozen execution inputs matched in read-only verification.

## Final bytes

| File | SHA-256 |
|---|---|
| source_observation_record.py | `6882370c7beeb7d5124085b1e751e98dd15a16dd08abd347e7f81a413a3b3c0c` |
| source_observation_schema.py | `60c0440a8c9c868db1153646ad1f17ce109d4d37cbb4c6ac3e24cad9c9566f8d` |
| source_observation_service.py | `d97925b10f8eeff9e58e6250fc5c48ca06cceeed21012a8ef32651058c0adc3f` |
| cli.py | `020d24362ac66cd5166772fa35dce5631639aca8a9ba225245a183e841bac29e` |
| test_source_observation_record.py | `15e56c00b06c43e236c88d0feee6711efa0fcfbec023a246a6405db08a2d9ae5` |
| test_source_observation_cli.py | `cd9f7114a1cade7a95a0bd93eed2baafce89123caf4212574f2f0009bbbc9045` |

`SAVED_RUNNER_REVIEW.md` records the pre-execution approval. The one installed saved-input exercise subsequently passed 1,813 checks over all 111 observations in 20.660949375 s with zero guarded live-physics calls. The saved result SHA is `d2b926d3569094131f3f2fd87a54a94f7be42233634a4e225aaa29969faaec7b`. This reviewer reopened all 111 canonical files and verified their saved hashes, canonical framing and bindings without invoking the codec. The reported check total matches the runner’s fixed per-record/per-cell checks. `SAVED_EXERCISE_REVIEW.json` records these checks and the installed CLI output/hash parity: original N3 capture index 16, ordinal 17, selected original cell 1. No test, EOS or codec replay was repeated. This is observation preservation, not verification of the surrounding numerical transitions or a new physical simulation.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — reviewed code and bounded saved-input runner; seven concrete failure cases were closed without new physical evaluations. Final delivery evidence remains a separate review scope.
