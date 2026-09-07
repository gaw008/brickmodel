# Independent review: explicit water interface modes

Verdict: APPROVE for explicit interface-state handling, not event localization or a nucleation model.

Reviewed the full modified WaterPhaseTransfer, its original callers/diagnostics, new tests and frozen documentation. The default remains existing_liquid; an active coefficient at zero liquid still exits. An explicit depleted_no_nucleation mode requires exactly zero stored liquid and preserves K, source identities, underlying host evaluation and complete Rates. with_depleted_cells returns an immutable replacement and checks indices/zero inventory; it is caller authorization, not independent certification that an event occurred.

Dry screening uses actual decoded T and gas total pressure as a hypothetical planar-interface liquid pressure. Dry mechanical liquid_pressure is None and cannot be used as an actual liquid state. The hypothetical equilibrium has a separate field; actual interface equilibrium, chemical potential and entropy production remain absent. Strict mode rejects nominal supersaturation or unsupported chemical domain. Explicit metastable_no_nucleation permits the stated research branch, including diagnosed unknown/supersaturation, without swallowing numerical/source failures. This is not an inverse-error-enclosed noncondensation certificate. K=0 does not bypass an explicitly requested dry screen or its source compatibility check.

Base liquid transport and reaction sources remain intact. The exact sum of represented left/right face and reaction terms detects positive net liquid reappearance; the implementation and documentation correctly do not claim a gross production/consumption audit. Negative net dry-liquid removal remains subject to ordinary state positivity. Source gates cover the source-identical original low chemical model even when caloric storage uses JoinedWaterVapor. New result fields are appended and old positional field order is retained.

Independent final execution: 11 passed in 1.58 s, XML `/private/tmp/water-interface-modes-review.xml`. Tests cover old active wet behavior, immutable explicit switching, strict/metastable supersaturation, actual Joined high-temperature dry-host heating and energy accounting, net liquid production, invalid modes/indices, propagated numerical failure, and strict dry screening with zero K. The high-temperature trajectory starts dry; it does not prove depletion or physically qualified nucleation suppression. The temperature assertion there is nominal; its energy ledger is checked independently at 1e-7 J absolute.

Author-reported earlier 7-pass/2-failure history exposed the absent dry liquid pressure; final code explicitly uses the stated hypothetical total-pressure assumption. This reviewer verified the final implementation/test behavior, not that prior author test invocation.

## SHA256 bindings

- `src/sludge_sandbox/water_phase_transfer.py`: `07879b60864f00ada8c05a01468a32ec7c8afcb549807daf920809a99fcd5350`
- `tests/sandbox/test_water_interface_modes.py`: `370c6a616f616005fc3b5b1f5b656aa0b2a5c31e0513d70b4cb8d3e7861d2071`
- `docs/sandbox/WATER_INTERFACE_MODES.md`: `e365fbfb3634fbc746dc8b1fe59541d6ef140027e962c6714fbe9ff09278b0ff`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE within the explicit mode contract. Complete event integration is reviewed separately.
