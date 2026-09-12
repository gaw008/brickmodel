# Independent managed source application code / process review

**Verdict: APPROVE the frozen application snapshot.** No unresolved confident CRITICAL, HIGH, MEDIUM or LOW findings remain in this review. This is code review and software/passive-record evidence, not a successful new native journey or scientific/material qualification.

The review covers uncommitted changes since `4a8504d`: `job_supervisor.py`, `cli.py`, new `source_execution_service.py`, new `source_terminal_record.py`, their scoped tests, and the pre-registered `native_driver.py` / `run_supervised_native01.py` harness. The complete adapter plan and final native protocol were read. No production files were edited by this reviewer; no commit, EOS call, physical integration, worker physical workload or native journey was performed.

## Final exact files and execution evidence

- `job_supervisor.py`: `54ae1e5ca6ecb83c2cde6d87df9f8a2669ffc07b39c760244f46b1dc5ed6a980`
- `cli.py`: `3a793ef5ce4735ce9e9c949979bc3e190f0ebc6a3a6dd475ac7444f8601baca9`
- `source_execution_service.py`: `5d8c720d226705502da2ab270ab1e8d33c4e547316af8b9f15f7af2a63555c74`
- `source_terminal_record.py`: `888275dcc7fa98cc71922788f16caffc1b369989cb2e66134b1cd7021170c79c`
- `native_driver.py`: `c8ff22a9235881ee7dabfebb9fb22c5619cb829e2367e2bec33f62394bcd296e`
- `run_supervised_native01.py`: `da099619e263b6ebf62e8b8dac2d39d25752b9200ec83ec316d01c4f7b8bd78c`
- `NATIVE_PLAN.md`: `3d13f41fef084fed946318688524c1223cc13731f1e609ac4691b34564762a93`

`FINAL_FILES_BEFORE.json` and `FINAL_FILES_AFTER.json` bind all ten production/test/harness/protocol files. They are unchanged across final testing. `git diff --check` passed.

The final test command uses the Python 3.12 environment at `/private/tmp/brick-cooling-thermoelastic-v1/installed-venv/bin/python`, with `PYTHONPATH` explicitly selecting the current source tree. It runs three repository files (`test_source_execution_supervisor.py`, `test_source_execution_service.py`, `test_source_terminal_record.py`) and four independent reviewer files (`test_supervisor_independent.py`, `test_service_pauses_independent.py`, `test_service_run_bindings_independent.py`, `test_terminal_pause_request_independent.py`). Actual result: **143 passed in 12.22 s**, recorded in `FINAL_TESTS.log` and `FINAL_TESTS.xml`. This is source-tree verification; it does not replace the root's forthcoming installed-package freeze and native acceptance.

## Defects found and closed

The following are historical review findings, all fixed in the final hashes above. Original failure logs are retained, not replaced with green output.

1. **Valid paused problem comparison failed on NumPy arrays.** Direct `ExactIntegrationProblem ==` reached ndarray truth conversion; changed to the existing exact numeric comparison. `PAUSE_RED.log/.xml` captured one real failure and one passing companion check. The related four-component `SourceOrdinaryStepSizes.binding()` comparison was also fixed; it was already corrected before this reviewer's test ran, so no independent RED is claimed for that part.
2. **Requested pause count did not bind the result.** Paused advance/resume records accepted zero or incorrect requested new-step counts; completed advance/resume records could exceed a positive requested pause count. Paused records now require exact positive new-step equality, and completed records allow only no pause or finishing within the requested new-step count. `PAUSE_REQUEST_RED.log/.xml` captured four failures and two passes; `TERMINAL_PAUSE_RED.log/.xml` captured two failures. Final regressions pass.
3. **Source-run correspondence omitted managed mode and admitted asset digest.** The adapter now requires `managed_execution is True` and matches the saved summary's asset manifest digest with admission. `RUN_BINDING_RED.log/.xml` captured two failures. These tests replace the lower scientific reader deliberately: they test the adapter's use of an already-validated summary, not the lower reader or native material behavior.
4. **Request symlink identity was lost before admission.** Root's additional correction preserves the original absolute source-execute request path instead of resolving it before no-follow admission. Existing command semantics are unchanged. The final suite includes root's new refusal-before-launch regression.

The independent paused-shell test was extended after the NumPy RED to add realistic positive step counts, then changed to mock the new `_verify_paused_claim` boundary. It deliberately excludes filesystem claim evidence; seven separate repository tests exercise the real claim files, counter increments, original/new saved debit bounds, failed claims, missing reconstruction and wrong target. `test_service_pauses_initial.snapshot` retains the initial shell associated with the original NumPy failure.

## Reviewed boundaries and practical limits

- The supervisor dispatches only the fixed installed `sys.executable -I -m sludge_sandbox.source_execution_worker REQUEST` entry. There is no shell interpolation, caller-selected executable/module, replay of saved code, second scheduler or arbitrary process signalling. The original live `Popen` handle, inherited flock descriptor, cancel/grace/kill/wait path and persisted-not-live process distinction remain intact. Missing clean child metrics remain unknown.
- Seven independent real short-process fixtures verify preparation timeout/refusal, preparation failure, irrelevant option rejection, cancellation-sentinel symlink refusal without writing its target, child reaping, and inherited-lock survival after the owner dies. They are bounded manufactured workloads. No stored PID was used to signal a process, and the orphan fixture has a two-second self-termination deadline and explicit release sentinel.
- Source admission keeps exact original request bytes and rejects non-null caller external budgets, output/cancel path changes, source/job overlap, reused outputs, malformed JSON and symlinks. Directory/file/type/depth/aggregate work bounds precede lower readers. Moved continuation jobs do not follow historical absolute input paths as authority.
- Worker status, process observation, artifact validity, qualification and remaining restore authority stay separate. Failed/unknown counts remain unknown. Nonzero process exits, cancellation/timeout, missing/conflicting reports and source/request mismatches cannot become successful execution. A valid but claimed packet remains unavailable; incomplete or broken-symlink claims cannot be cleared for retry.
- The terminal reader uses a fixed source/numeric type allowlist and bounded passive graph projection. Paths/live providers remain data labels; no saved class names trigger imports or native constructors. Unknown types, malformed graphs, unsupported result fields, failed callbacks/native scopes, unsupported mechanical/work-component states and failed publication tails are rejected rather than silently ignored. Shared graph comparisons are memoized.
- Accepted states, exact clocks, callback ordinal/role ordering, source callback input/return associations, native-scope close records, original parent counters, local and full-chain balances, genuine saved completed committed frame, restored event/numerical prefix and claim debit/counters are checked. This is explicitly **not** a new controller arithmetic replay, EOS authentication, source/material qualification or full-cycle validation.
- Historical public archive tests use the original saved numeric records with explicit seams for missing private parent/packet asset admission and relocated claim pointers. Tests retain the negative case showing that the public archive itself is not an admitted complete run. They must not be reported as a genuine restored native run or as evidence that missing assets were supplied.

## Pre-registered harness review

The harness is statically approved for the root's single planned parent → pause → resume application journey after installed-package freeze. It derives the endpoint from the fresh parent's exact Fraction plus `3/64`, preserves the one-step/eight-observation prefix, retains the original cumulative numerical/resource/material gates, and separately checks that reusing the consumed packet is refused with the exact `source_execution_service_restore_already_claimed` reason before any fourth worker launches. The harness has not been executed by this reviewer.

The driver SIGTERM handler raises into the owning application supervisor so its live source worker can be cancelled/killed/reaped. The outer research supervisor contains only its original process group; escaped worker sessions are not independently contained by that outer group. The protocol states this limitation. It is not a machine-wide containment or hard real-time guarantee.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — no unresolved confident findings in the final frozen snapshot. Installed execution and the actual native journey remain separate acceptance work.
