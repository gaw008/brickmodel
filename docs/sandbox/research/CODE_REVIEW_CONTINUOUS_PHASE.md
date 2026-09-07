# Independent review: continuous caloric phase adapter

Reviewed current unstaged/staged scope and the complete changed `IdealGasPhase` implementation with `ContinuousShomateGas`, existing `PhaseStorage`, and downstream `RigidStorage` call sites. Read the new tests and `CONTINUOUS_PHASE.md`. No implementation changes were made by reviewer.

## Findings

No actionable findings in this bounded change.

The adapter now accepts the exact continuous provider type and forwards its complete temperature range and h/u/Cp/Cv behavior. A non-None segment index is rejected for this type. Original ShomateGas still requires an explicit single branch, and the low-temperature water bridge retains its existing mass/identity gate. No second anchor or formation-energy offset is added: source/model reference conventions and publicly retained segment offsets remain with the explicit continuous provider.

Derived classification and all source/method/constant IDs are preserved. A manufactured source remains manufactured after construction of the continuous provider and phase; downstream `RigidStorage` still rejects it without its own explicit opt-in. This is declared-source model assembly, not new material admission or an approval of caller-supplied numerical envelopes.

The direct import has no circular dependency in the inspected graph (`continuous_caloric` depends on `thermochemistry`, not `phase_storage`). Existing original-branch behavior and the water bridge path remain distinct.

## Actual checks

Command:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_continuous_phase.py tests/sandbox/test_phase_storage.py tests/sandbox/test_rigid_storage.py -q
```

Result: **43 passed in 18.94 s**. This includes the 3 newly added assembly tests, original phase-storage tests and actual closed-storage tests; it is not a whole-repository test claim.

Independent reviewer probes, separate from the added test implementation:

- Built a continuous real NIST O2 provider anchored at 500 K, assembled actual `RigidStorage` with zero liquid and 0.1 mol O2 in 0.001 m³. Computed target U independently by SciPy quadrature over original Cp segments plus the unchanged source anchor and explicit `-RT` term.
- Inverted targets at **650, 700, 701, 1999, 2000, 2001 and 2500 K**, using one 300–4000 K bracket. This crosses both actual O2 source seams, rather than only a manufactured seam. Maximum observed absolute temperature error was **5.297806637827307e-11 K**, within the independently imposed 1e-6 K check; energy residuals also met 1e-6 J.
- Replaced both `WaterProperties.state_tp` and `state_tp_response` with raising sentinels during all seven zero-liquid inversions. No water property call occurred, so the high-temperature branch does not depend on silently expanding the liquid-water domain.
- A continuous NIST H2O provider queried at 300 K was rejected with `ContinuousCaloricError`: no automatic IAPWS-to-NIST join was introduced.
- Continuous-provider segment selections 0, False and 1 were all rejected; only None is permitted.

These are numerical/model-assembly checks using explicitly declared error envelopes. They do not establish wet-brick or nonideal-mixture validity, equilibrium continuity, or independent admission of an error envelope.

## Reviewed identities

```text
eb339df4cc11c551f76239d542323a6280e22a4097e6b8e68043c6d4742fa21f  src/sludge_sandbox/phase_storage.py
666ffad93f2bfcdf9345d9f50611555d674beac560c73d5aa547531b84af2e84  tests/sandbox/test_continuous_phase.py
```

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE for explicit continuous-caloric phase assembly, preserving the documented scientific and numerical qualification limits. No source edits or Git commit by reviewer.
