# Point probe review

APPROVE for the stated bounded diagnostic scope. Read-only review; reviewer did not run EOS, probe, or trajectory.

Inspected point_probe.py SHA256: 9e30949a345beeec365a8c02e1f6cd561d79f03478f23cea6ee4728ba6505124. Registered and copied case bytes both hash 00413e9f5282916264940ef1bcf0391de9f1f65032fe614392dda8733097247c.

The script asserts installed runtime identity against both saved runtime identities before construction and again after evaluation. It builds the registered case with the retained water directory and reconstructs the last accepted serialized state and time, including mechanical stretches. The prior saved-data audit verified record/case/source binding. Since the retained run has zero events, the original existing-liquid interface modes are also the correct final modes. That reasoning would require revision for a record with committed depletion events; this probe is deliberately scoped to this failed record.

snapshot evaluates the actual coupled operator, so this is more than a standalone storage inverse and may perform face diagnostics too. It does not integrate a new trajectory or change state, input, or tolerance. SolidFluidState exposes mechanical, fluid_state, volume_error_bound_m3 and pressure_error_bound_pa exactly where the probe extracts them. Each row consistently uses one cell's thermal state and its underlying fluid state. combined_minus_fluid_pa is the rounded difference of two reported upper bounds, useful for attributing the added solid/current-volume enclosure; it is not an independently certified physical error or an exact reconstruction of the internal added bound. volume_residual and volume_resolution come from the same pressure closure. The wording correctly limits the observation to the accepted wet state, not the rejected terminal event state, and disclaims independent validation.

No blocking issue found for this diagnostic. It does not itself decompose every subterm (e.g. liquid declared volume uncertainty versus pressure residual); any stronger causal attribution still needs those terms or an independently justified bound. Approval does not certify the EOS or make the failed event experiment pass.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE for bounded diagnostic interpretation only.
