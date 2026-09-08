# Programmed free-slab integration: independent code review

Verdict: **APPROVE** for the inspected implementation and test snapshot. No outstanding blocking findings. This is a bounded coupling/code review, not validation of real sludge material properties or a complete firing cycle.

## Inspected snapshot

Repository: `/Users/wanggaoying/Desktop/brickmodel-github`. SHA-256 hashes were rechecked when this report was saved:

| File | SHA-256 |
|---|---|
| `src/sludge_sandbox/programmed_solid_fluid_heat.py` | `12c08266d73c1580125a2a270da0898f0657d2e890fc50deb1e6380f5ede49e5` |
| `src/sludge_sandbox/depletion_integration.py` | `16b4b122615fde77bd81ce8e2f073c326ce4496d1712a05e1b287cc479880b39` |
| `tests/sandbox/test_programmed_free_solid_slab.py` | `b922cc0ec1657d6bfd5fa0669e00d8f41af8b89a0b519790b4707ec81f66ac8f` |
| `tests/sandbox/test_programmed_free_slab_wet.py` | `9e583266a79f48a68e25360b49bfae5c4ba2020740a79b393e524ee7ea8f0015` |

Review was read-only; no EOS calls, test execution, installs, source edits, or test edits were performed by this reviewer. This report is the only requested output file.

## Implementation findings

- Exact `FreeSolidSlab` admission uses the actual current host transport geometry for boundary conduction and reservoir transport. Existing reaction rates, cell power components, and mechanical rates are forwarded. Program gas pressure remains explicitly separate from the constant mechanical traction.
- A separate full operator content digest binds the base model, program content, boundary coefficients, coefficient provenance, surface policy, and manufactured admission. Runtime checks cover evaluation, state checks, and the operator identity getter. The supported base graph does not recurse through the wrapper.
- The depletion spine includes this checked operator identity, protecting cached binding against program changes that retain the same labels or source IDs. Stored-energy identity is preserved because the energy definition has not changed.
- The emitted evaluation carries the checked operator identity and the union of wrapper and actual base evaluation source IDs. The final getter rechecks content before the result is returned. Optional tail fields preserve existing positional construction compatibility.

## Rejected intermediate candidate and resolution

The intermediate candidate with SHA prefix `2b7fc879` was rejected for an error-boundary defect: `_check_content` called `_digest` directly. A runtime NaN or unsupported-object mutation could raise `DeformingStorageError` outside the ordinary integrator's `IntegrationError` boundary, bypassing structured failure and accepted-prefix preservation.

The corrected candidate `b7b6d9868330876c52056193a4afc1e1b268d7457ed280efa1be02ef707651c5` catches `DeformingStorageError`, `TypeError`, `AttributeError`, and `OverflowError`, then raises `ProgrammedSolidFluidHeatError('invalid_runtime_programmed_operator_content')` with the original cause. Valid but changed content raises `runtime_programmed_operator_content_changed`. Both are integration errors. The inspected production snapshot retains that correction and adds the emitted trace fields described above.

Regression coverage includes NaN and unsupported-object mutations after exactly one accepted 0.001 s step, structured numerical failure, the intact two-state/one-step prefix, and checkpoint auditing. Tests also distinguish same-ID/different-content operator identity from unchanged energy identity. The breakpoint test uses a non-divisor 0.007 s cap with explicit breakpoints, so breakpoint landing is not merely an aligned-step coincidence. An earlier fixture's initial-volume oracle was corrected to its actual initial geometry; this did not relax its physical gate.

## Wet test review

The test explicitly combines native water thermodynamics with manufactured solid mechanics and transport. Its virtual boundary program and separate mechanical traction are qualified; it does not claim real-material validation.

Two step caps must produce different accepted meshes. Checks retain positive stretches; sealed mass faces; fixed inert/solid inventories; per-cell water conservation; per-cell energy ledgers; represented and exact-stage mechanical increments; global cancellation of constraint work; and external pressure work plus boundary heat balance. Checkpoint auditing and opposite cell liquid-inventory changes are required. Final current geometry, inverse states, gas states, free-mechanics solution, surface solve residuals, source IDs, and operator identity are persisted. A separate current-area/current-width conduction calculation checks the surface result. Coarse/fine state and inverse-temperature gates remain explicit.

Encoded runs are saved before assertions, and the final evaluation snapshot is saved before surface assertions. The inspected save helper writes strict JSON to a temporary sibling and atomically replaces the artifact. This preserves usable diagnostic output if a subsequent gate fails.

## Execution evidence boundary

The parent reports that the frozen native run completed with exit code 0, matching source hashes, and `1 passed in 130.45s`. Those execution results were not independently rerun or independently audited by this reviewer. Approval here rests on the completed code/test inspection, with the exact inspected snapshot recorded above.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **APPROVE** — prior digest exception blocker is resolved; no outstanding findings in this scoped snapshot.
