# Ordinary program-knot endpoint repair

Baseline c3abc7a. The outer wet ordinary scheduler repeatedly rounded segment endpoints, leaving a one-ULP panel before .05 when using .005 steps. Original constant-source reproduction:2 failed/6 passed, with conserved accepted prefixes ending at .049999999999999996 and an unrepresentable next midpoint.

The new private endpoint chooser in depletion_integration.py absorbs only a bounded cap-rounding tail into the preceding complete panel. It checks exact Fraction inventory safety for both nominal cap and actual duration, one boundary ULP/local32 ULP, and at most32 cap ULP duration adjustment. All actual stage/ledger weights and existing midpoint guards remain. Direct adjacent-float intervals remain failures. Event approach/terminal algorithms were not changed.

## Actual verification

- Original8 cases now pass. Expanded14 cases cover analytic inventory/energy prefixes, dyadic and standalone controls, small representable versus unrepresentable intervals, cancellation, explicit piecewise restarts, inventory/cap alias, negative/zero clocks, a narrow cap at a large clock, and two current-accuracy affine events.
- 102 related integration/depletion tests passed in31.62s.
- Non-editable installed full suite:1293 passed, zero failures/errors/skips, XML573.270s; session33496 terminal exit0. All43 actually imported installed modules matched source before/after. Frozen source/test hashes remained unchanged.
- The unchanged historical coarse-accuracy affine file is still3 pass/2 fail: its two event paths now complete, but original analyticA errors1.82883264e-10 and1.65367720e-10 mol exceed the original1e-10 gate. Full trajectories and XML are preserved. Current existing rel1e-11 accuracy at the same .005 cap passes the original gate; the old rel1e-7 output was not reclassified or erased.

These are numerical/manufactured oracles, not raw-sludge material validation, full firing convergence or a proof that local tolerances bound all global errors.

## Evidence

The ZIP preserves59 original files, including old/candidate source, frozen final tests, baseline failure XML/hex times/ledgers, candidate and expanded results, retained affine failures, installed checks, full XML and independent numerical/code reviews. Each entry was reopened and its SHA-256/length checked against manifest.json. Selected reports/plans/XML are readable under readable/; terminal-verification.json gives the final actual suite evidence. Initial candidate-freeze records that once said running are historical snapshots superseded by the terminal record.

The optional test writer's knot_hex and remaining_to_knot_exact_s use a legacy .05 reference even in other-boundary cases. Treat those two fields as reference diagnostics, not configured per-case boundaries; actual settings are in the saved test source and trajectory times/ledgers are authoritative. This nonblocking review caveat is retained explicitly.

Original source-focused runs used PYTHONPATH=src:tests/sandbox and the isolated installed Python. The full suite ran from /private/tmp with no source PYTHONPATH using the non-editable package. To reproduce, install the locked dev/water environment and run the saved tests against the indicated source/installed baseline; optional BRICK_KNOT_EVIDENCE_DIR must be a new existing output directory because evidence files refuse overwrite. The historical affine test file intentionally still demonstrates its coarse-accuracy failures.

A bounded official-source access recheck for Lu2026 yielded no new readable methods; see LU2026_ACCESS_CHECK.md. Missing material evidence remains missing.

The next delivery dependency is NEXT_DELIVERY_STEP.md: shared case loading, Python/CLI execution and source lookup without importing test helpers, then the same API for the UI. Unsupported real-material inputs must be blocked explicitly; a manufactured verification case cannot silently substitute for them. Full raw-sludge evidence, free sintering/cooling, public three-mechanism/held-out validation, complete UI and multigeneration search remain required and unfinished.
