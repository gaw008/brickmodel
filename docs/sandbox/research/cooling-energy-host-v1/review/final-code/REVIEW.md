# Final scoped code review

Verdict: **APPROVE the reviewed storage, native host, and research driver code**. No actionable issue above the 80% confidence threshold was found. This is an internal code review, not full-phase numerical acceptance or material validation. The first formal native experiment remains failed.

Scope: repository `codex/physics-sandbox-v1`, baseline `3c61bf7`; new `thermoelastic_energy_storage.py`, `thermoelastic_energy_host.py`, research `run_validation.py`, `supervise.py`, `test_driver.py`, and both source energy tests. `git diff --staged` and `git diff` were empty because these files were untracked; all seven full files and relevant native/plate contracts were read. No source, driver, tests, preregistration, or Git state was changed. Review writes are confined to this directory.

## Version binding

| File | SHA256 |
|---|---|
| storage | `d98d6dccff4e31895da642ffa170ecd208c60e6e55b27ac5e314c36ace3f4579` |
| host | `3f23da5d4612004cdb5baa1b490fbd249c8e2f2554337dcddb14a8677953c8c9` |
| driver | `574a80ef01617045fc71beabf4234dc179201723d0f079398336ba8439db1f97` |
| supervisor | `96f89838487e3733631f57a3bd04bcce81e8f294b5a6e6516e6a483b88ba1710` |

All seven hashes are recorded in `EVIDENCE_CHECK.json`. The current host differs from the prior independently reviewed candidate only in using its package-relative storage import. The prior storage and interval-Newton mathematical reviews and native-host review were read; their proofs were not rerun.

## Code and evidence conclusions

- Immutable explicit inventory, shape/identity checks, scalar input validation, one final plate evaluation per successful decode, native face orientation, and exactly one local work component are consistent with the surrounding interfaces. Proven physical-domain failures remain distinct from malformed input and unresolved numerical decoding.
- The research entry point validates isolated installed imports and frozen input hashes before execution, then checks the same hashes afterward. The actual execution freeze also binds the broader installed package and source files. Helper injection is for explicitly marked fake tests; it is not treated as independent scientific evidence.
- Returned native states, times, step ledgers, terminal status, RHS summaries, and initialization rounding are serialized before accepted-state reconstruction. Exclusive creation preserves prior evidence. Both trajectories and all preregistered completeness/convergence gates must succeed before the worker can pass. Supervisor success additionally requires a reaped zero-exit child, readable result, required artifacts, unchanged inputs, and the shared deadline.
- Finite-point domain checks and descriptive stress/work reconstruction diagnostics retain their declared scope. The independent driver numerical review and examination of actual run diagnostics remain separate from this code verdict; no threshold was added or relaxed here.

## Verification and observed failed run

All seven files passed syntax/AST parsing without import or bytecode writes. Existing source and installed logs were read: each reports 168 passed (1.34 s and 1.31 s respectively). These tests were not rerun by this reviewer. No native integration, old trajectory, or new mathematical probe was executed.

During this review root supplied the existing `native01` failure. Read-only inspection and 12 structural assertions confirm `numerical_failure / unresolvable_stage_time`, last accepted time 0.3 s, 61 saved states/times, 60 complete matching step ledgers, 421 successful RHS calls, and zero failed decodes. All 61 accepted prefixes are audited. The fine path was not started. Worker and supervisor both retain `passed=false`; incomplete comparisons and time convergence remain false; the child was reaped and before/after hashes match. The accepted inventory bytes and energy identities are preserved. Details are in `EVIDENCE_CHECK.json`.

The numerical clock failure belongs to the unchanged core integrator, which root is investigating separately. It prevents claiming native cooling phase completion. Approval of the files above does not approve a future integrator correction or a rerun under changed inputs.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — scoped frozen code only; formal native experiment failed and full-phase acceptance remains open.
