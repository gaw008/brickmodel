# Final code review: source-multicell-transition-v1

APPROVE for the six reviewed file hashes in CODE_REVIEW_FINAL.json. No open production findings remain. Baseline 3fdea988f23a42ecb993f4ff7830a425aa232c9d. Production and author test files were read-only. This approval does not claim the author's combined suite, installation or native execution has finished.

## Closed finding

[MEDIUM] Selected pressure compatibility view lacked live storage binding.

`SourceDryCandidate.check` strictly bound every new matrix entry to the actual cell storage but only compared the older `pressure_endpoints` view by content. An actual N3 candidate accepted replacing its selected bound with an equal-content record backed by a distinct storage object. The same replacement in the full matrix was correctly rejected; a caller using the old selected view could then fail the new shared-pressure admission despite successful candidate validation.

The independent actual source probe retained this RED: matrix01.xml/log, 1 failed in 12.34 s, 32 actual source callbacks, no native EOS. Root added `bound.storage is terminal.dry_adapter.column.storages[selected_cell_index]` with `source_selected_pressure_storage_changed`; the bound itself need not be the same instance. Repeating only this bounded probe passed: matrix02.xml/log, 1 passed in 11.97 s, 32 actual source callbacks, no native EOS. The original RED is retained. The source snapshot was captured after the fix; its timing is explicitly recorded rather than claiming an unavailable pre-fix hash.

## Integration and accounting checks

The N3 actual fixture selects cell 1 and executes both mixed wet/dry paths. New 2×N pressure records bind each cell's actual storage/state/inverse and dry/wet type. The selected dry legacy view retains its two endpoints. Top-level N/U/T/reported-P values are maxima over every cell; full and selected pressure are unresolved unless all cells resolve. Shared evidence replaces only the selected dry cell's P test; wet-cell failures remain visible and prevent transition acceptance. Both original pressure comparisons are retained. Two path indexes and the selected spatial cell index remain separate and both candidates must select the same cell.

The path audit accumulates ordinary and exact terminal contributions per cell using the original face incidence, then computes global sums. Each local residual and the global residual uses the original absolute N/U budgets without multiplying them by N. The independent probe added exactly 2^-24 mol to each of three O2 cells: each increment is below the original 1e-7 mol budget, but their sum exceeds it. `_audit_path` correctly rejected the global residual. This complements the author's opposite-cell cancellation tests and does not alter the scientific tolerances.

Writeback is confined to the selected liquid/vapor pair, with all cell U values and other amounts unchanged. Event storage roundoff is assigned once to the selected cell and summed once globally. Actual shared face energy retains the signed liquid donor enthalpy and its projection; an energy increase is not required when reference enthalpy is negative. Root retained the first test's incorrect energy-direction expectation and changed it to the actual signed ledger balance, without changing production arithmetic.

The terminal helper validates the actual saved decoded-liquid/source/inverse data, reconstructs the original Darcy/enthalpy arithmetic and total face energy, and excludes an affine donor sign reversal over the full sampled panel. This is a saved affine numerical condition, not full continuous physical donor certification. Only the selected cell changes to the explicit dry mode. A newly declared manufactured table with zero dry mobility follows the existing face law; the unchanged positive dry mobility case retains its actual domain exit. Initially mixed or repeated events remain outside the all-initial-cells-wet guard.

Partial pressure rows are appended after each completed cell; a later wet-cell assessment failure retains earlier items together with the already completed reference and captures. Existing callback limits, original remaining policy, failure records and passive replay remain in place. The reviewer disabled actual evaluation during the checks after fixture construction, and native construction was prohibited throughout the independent probe.

## Validation scope

- Independent reviewer: one retained RED and its one passing recheck, 64 actual manufactured source callbacks total, zero native EOS, no installation or old suite reruns.
- Terminal author: frozen three-file report states 14 tests passed / 9.009 s, with 54 old N1 field comparisons and three identical prior refusals. These are author evidence, not additional reviewer executions.
- Root combined four-group source suite is still pending at this report's completion and is not represented as passed. Subsequent run/install evidence must be checked separately.

The current fixture, algebra, source qualifications and ledger checks support this bounded N-grid numerical event path. They do not validate real material, certify unresolved wet-cell pressure, or complete rewetting, repeated events or the full original Goal.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 open / 1 closed | pass |
| LOW | 0 | pass |

Verdict: APPROVE — no open findings in the reviewed bytes; final author and installation gates remain separate.

## Subsequent author validation evidence

After the code review completed, the author final source and installed suites both finished: 52 passed, console 78.58/78.33 s. Both XML files were read with zero errors, failures or skips. This updates the earlier time-specific pending status; the reviewer did not rerun these suites. Native execution and final package identity are separate runner gates.
