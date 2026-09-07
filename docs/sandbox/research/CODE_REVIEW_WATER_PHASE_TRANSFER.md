# Independent review: finite-rate water phase transfer

Scope: `water_phase_transfer.py`, focused tests and `WATER_PHASE_TRANSFER.md`. The reviewer inspected the complete wrapper and surrounding chemical-potential, rigid-fluid storage and conservative-rate contracts.

## Physical and numerical audit

The wrapper uses the current per-cell coupled storage solution, not cached T/P or an assumed fixed gas pore volume. Actual vapor partial pressure is computed from water mol inventory, the registered R, current T and current gas volume; liquid pressure is the current mechanical pressure. The chemical equilibrium function is independent of the current vapor inventory and is therefore usable at zero vapor inventory with a surviving liquid interface.

The supplied `K` has units mol/(s Pa), giving `r=K*(p_eq-p_v)` in mol/s. This is an explicit pressure-difference kinetic approximation; equilibrium chemistry does not determine K. Per-cell coefficients are immutable, finite and nonnegative, with explicit identity/version/classification/source IDs and manufactured-mode gates. Active transfer requires the same source-gated IdealWaterVapor bridge and liquid reference/assets as the chemical model; arbitrary H2O-labelled Shomate calorics cannot be substituted.

The liquid and gas H2O source entries are exactly opposite molar rates. Base face energy and cell power are preserved, with no second latent-heat or pressure-work term. For an isolated cell, U stays fixed while the next inversion responds to changed phase inventories; phase enthalpy/internal-energy differences therefore appear through temperature feedback rather than an added energy source. Full original base inverse and chemical-equilibrium diagnostics remain in the result.

For positive vapor pressure, `Delta_mu=R*T*ln(p_eq/p_v)` has the same sign as `p_eq-p_v`; consequently `r*Delta_mu/T` is nonnegative. The code computes this pressure-derived force using log1p near equilibrium rather than subtracting large chemical potentials, and labels the definition. This is a diagnostic consistent with the *computed* equilibrium pressure; it does not establish arbitrarily precise true near-equilibrium chemical differences beyond the retained chemical residual and conditional storage budget.

At p_v=0 the ideal gas chemical potential tends to negative infinity, while the selected pressure-difference rate remains finite. The wrapper explicitly reports the zero-vapor limit and leaves chemical potential/entropy production absent, avoiding fake finite values. At zero liquid inventory with active K, it exits because interface/nucleation physics is missing. K=0 skips phase chemistry. Trial inventories are not clipped; the integrator must reject a step that exceeds finite inventory. The model does not promise successful continuation through liquid depletion.

Exact Fraction intermediates protect trace partial pressure and K times pressure difference from silent intermediate underflow. Nonzero unrepresentable rates or chemical/entropy diagnostics raise a numerical contract error. Physical water-domain failures map to DomainExit; derived numerical failures remain distinct.

## Verification scope

The preregistered tests require actual sealed-cell evaporation and condensation integration with source-gated liquid/ideal water and manufactured carrier gas/K. Saved-state water conservation is 1e-11 mol and U conservation 1e-7 J; temperature feedback must exceed 1e-4 K in the expected direction. These are numerical coupling tests rather than measured kinetic or wet-brick validation.

Additional inspected tests cover source/caloric mismatch, inactive chemistry at high temperature, finite-inventory overstep rejection without clipping, zero-vapor semantics, explicit no-interface exit and tiny nonzero rate failure. The final 16-case suite does not include a separate system-entropy trajectory or near-equilibrium entropy-convergence benchmark; the entropy-production discussion above is an algebra/code audit, not a claim that such an expanded runtime benchmark passed.

Source SHA-256: `18aa8b72defb5bd06eb1fbe8f4519233d15b22cf05160d820497b626852e2d4f`.

Test SHA-256: `0499cbd72644889a6a1f76d25b466ea8dcdd1db4b80aa6db9fd29882e93f12b1`.

Document SHA-256: `0b430d784dfcec670cd115c6bc4a61054bb51e7cad12f6badb800c7463386650`.

Final independent command: `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_phase_transfer.py -q --junitxml=/private/tmp/water-phase-transfer-review-final.xml`.

Result: **16 passed in 61.11 s**. XML inspection confirms 16 tests, zero failures, errors or skips, time 61.111 s. XML SHA-256: `e1bbbeb62b13378e9554d21525708cbbb03318fb3bec557c642520175a660ce0`. Source, test and document hashes were rechecked after completion. Historical implementer runs are not substituted for this final reviewer run.

Both actual phase-transfer trajectories passed the preregistered saved-state water/U balances and opposite temperature feedback. The deliberate excessive-inventory trial was rejected with the original state preserved and an explicit rejection-budget status. No inventory clipping or duplicated latent energy was observed. The full installed-project regression is a separate parent-run check, not claimed by this focused review.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — no unresolved physical or code defects in this bounded implementation. It remains an existing-interface, declared-kinetics approximation with conditional storage error budgets, not a complete wet-brick phase-change model.
