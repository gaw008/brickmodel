# Independent review: phase-aware inverse brackets

Verdict: APPROVE for explicit numerical search-interval selection, without any material-domain extension.

Read the complete SolidFluidHeat change, surrounding constructor/state/decode contracts, new tests and documentation. The optional dry interval is selected per cell solely when the actual liquid inventory column is exactly zero. Positive amounts including 1e-100 mol retain the original transport interval; neither an interface label, estimated temperature nor an epsilon changes phase classification. Default None stays implicit across dataclasses.replace, while explicit per-cell intervals retain strict length checks and immutable nested tuples.

All enabled policies require id/version/reason and report numerical_policy classification. Result diagnostics append fields after the existing positional contract. The selected interval is passed into the original complete SolidFluidStorage inverse with actual solid/liquid/gas inventories and U and the same inverse/error policy. The implementation does not swap to a gas-only inverse, change energy reference, broaden the water EOS, suppress active-phase checks or qualify a high-temperature liquid domain. Constructor validation is numerical; physical/domain rejection still occurs during the actual inverse. A physically unavailable search endpoint can therefore reject a broad interval rather than silently extrapolate.

Independent final execution: 9 passed in 1.57 s; XML `/private/tmp/phase-aware-inverse-review.xml`. Actual full single-cell evaluations recover wet 300 K and dry 502 K within 2e-5 K absolute while preserving input U. The original narrow interval rejects the high-temperature dry state; a new out-of-domain interval still fails. Other tests verify policy metadata, interval validation, immutability, trace positive liquid and mixed-cell/default-replacement selection. The mixed-cell test uses synthetic U only to verify selection; it is not claimed as full mixed-cell thermodynamic inversion. Actual depletion/long-run switching remains separate event-host evidence.

No confirmed unresolved issue in this bounded change. Underlying source identities, manufactured gates, transport and reaction logic are unchanged. No extra expensive host or full installed suite was run.

## SHA256 bindings

- `src/sludge_sandbox/solid_fluid_heat.py`: `680c0280e99f4be1614bd104f83de409a76159f9e68ce03b70e8589b202d3267`
- `tests/sandbox/test_phase_aware_inverse.py`: `170bf7e3663116478e3a088a386e465d9c7801090d129084ab05e7151921219b`
- `docs/sandbox/PHASE_AWARE_INVERSE.md`: `8a8c68a309aa2d22936f0a5342943a63938d38f102b9c2db15c07f7d5969e7c9`

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE within the numerical interval-selection scope.
