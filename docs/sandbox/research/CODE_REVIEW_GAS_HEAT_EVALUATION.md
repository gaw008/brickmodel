# GasHeatEvaluation independent review

Verdict: **APPROVE** for the diagnostic extraction. No change to transport, reaction, thermochemistry or boundary equations was found. This does not implement moving geometry or mechanical-work coupling.

Read the complete model and existing tests, and inspected the working-tree diff against HEAD. The old `__call__` body is retained in `evaluate` through its existing exception handling; only the final Rates wrapping changes. `__call__` now returns `evaluate(...).rates`. The additional frozen record holds tuple temperatures, the exact gas-state objects used at faces, and existing aggregate source identities. No provider-domain or manufactured-material gate is removed.

## Independent old-implementation comparison

Saved HEAD source to `/private/tmp/gas-heat-model-before-evaluation.py`, SHA256 `6019ac11662e8cb79ce75d0ed786c753cfe419904f74901eee750e45737cdbd9`. Extracted and compiled its actual old `__call__` AST, using the unchanged module helpers. It does not call the newly introduced evaluation method.

Executed that old method on a two-cell manufactured fixture with unequal temperature, pressure and composition, nonzero conduction, Darcy/diffusive transport, A→B reaction, external gas reservoir, and time-dependent prescribed surface temperature. Frozen old outputs are now independently recorded in `test_gas_heat_evaluation.py`. The new evaluation matches all four Rates arrays exactly, including nonzero internal and external species/energy rates and both reaction rows; cell power remains zero as required by the original model. This is a regression oracle against the previous operator, not an independent continuum-physics validation.

The added test also intercepts actual face inputs and verifies object identity with returned gas states: both internal donors and the outer cell are the same decoded objects, while the external donor is the configured reservoir. It checks the complete source union including distinct heat/gas-boundary identities. Existing new tests count one temperature decoding call, check frozen diagnostics and preserve a property-domain exit. Existing model tests cover source-wrapper mutation detection, numerical failure versus domain exit, input gates and callback/code-error propagation.

## Actual bounded validation

Independently ran `test_gas_heat_evaluation.py` and `test_gas_heat_model.py`: **30 passed in 0.37 s**, XML `/private/tmp/gas-heat-evaluation-review.xml`. No full sandbox or wet/EOS experiment was rerun. `git diff --check` passed. Only the authorized new test and this report were edited by the reviewer; no production-source edits or Git commit.

Final SHA256 bindings:

- `src/sludge_sandbox/gas_heat_model.py`: `b14d4c6b22fa06d6d499868b6c24e909a3ba960cee552c58df6023696bc69cf3`
- `tests/sandbox/test_gas_heat_evaluation.py`: `a7f1d6eb2f99315adf9adba2477f039f091bf79f52dcfac7487440a4e6e8336d`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded single-decode diagnostic extraction with preserved old Rates behavior.
