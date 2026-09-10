# Native pressure controller opt-in candidate

Scope: apply only `mass_wet_exact_controller.py`, the new `mass_wet_controller_pressure.py`, and the portable `test_mass_wet_native_controller.py`. Do not apply baseline, conftest, prepare.py, parity runner, or archived failure snapshots. No repository, installed package or native EOS was changed or run by this candidate task.

The keyword-only `pressure_session=None` retains the original controller path and base result. The opt-in uses one caller-supplied actual PressureSession throughout ordinary stages, rejected trials, terminal comparisons and independent refinements. Event/common contexts describe their actual role, exact time, current source/modes, cell and original frozen controller inputs. They never masquerade as a stage full/fine context. Existing samples supply rates and full states; no extra host observation is requested. Depleted cells retain the original dry formula; zero liquid with a wet mode is refused.

The explicit NativePressureMixedControllerResult retains every original result field, entry input bytes, before/after immutable session snapshots and comparison contexts. Both old pack and encode_mixed_run refuse it. This is not a new codec, service or resume permission. The session proof is conditional on its declared liquid branch and original uncertainty contract, not new material qualification.

Original whole-packet atomic publication, exact event order, two consecutive passes, independent halved approach and grid, all six differences and original prefix checks remain. Completed comparison rows are retained on later failure; incomplete rows are not fabricated. Session attempts retain failed proof/cost evidence. The guard chain is stage.guard -> native_cancel -> controller.native_guard; each stage wall allowance is bounded by remaining controller wall, while the original session construction deadline and cumulative budget persist.

## Actual failure and correction

Root initially suspected a Stop would bypass the existing ValueError handler and lose the current path. Inspection corrected this: Stop inherits ValueError and the path/refinement already survived. The actual reproduced defect was only loss of a completed first comparison row when the next row was cancelled. `partial-comparison-red.xml/log` preserves the failing test and `before-partial-comparison-fix/` the previous source. The minimal fix records the already completed immutable rows in the existing refinement; no additional journal or path restructuring was added.

## Validation and its limits

- tests03: 13 passed in 94.60 seconds, authoritative process 5455 exit 0. Includes real manufactured full two-event packet, all three comparison passes, independent path, ordinary pressure failures, event first/second proof failures, independent last proof failure, partial row preservation, input mutation, actual context mismatch and both old codec refusal entrypoints.
- tests02: 8 passed in 86.92 seconds, comprising independent last-event proof failure plus all seven original controller regressions (including independent DOP853 and prefix checks). The subsequent source delta is native-only comparison-row preservation and helper mode validation.
- default-parity.json preserves complete nested non-wall equality with the untouched baseline for default wet refusal and fixture resource failure. Only elapsed_seconds and module-name aliases were normalized.
- tests04-history separately adds the requested preexisting-history sentinel and explicitly injected first-trial rejection. The trial's computed states/evidence/costs remain unchanged; this is orchestration coverage, not a claim its scientific comparison failed. Final log/XML records its actual outcome.

PressureSession.query/snapshot are explicitly instrumented on the concrete class in these tests. The storage, stage, exact root, panel, writeback, modes and controller run real manufactured analytic implementations. These tests do not claim a fresh HEOS pressure proof or native full-controller execution. Session and mathematical proof tests are separate previously frozen dependencies. Source freezes are pending independent reviewer approval, not author approval.

## Reproduce pure candidate tests

From the repository root, use the existing Python environment with `PYTHONPATH=src`, pytest `--rootdir` set to this candidate directory, and its test file. The adjacent conftest prepends this directory only for candidate overlay and adds existing repository sandbox tests; it is not production code. Do not run prepare.py to reconstruct the final source: it predates the preserved partial-row fix. `candidate.patch` and FREEZE.json identify the final bytes.
